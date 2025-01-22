"""Payment agent for processing invoice payments using Payman AI and Langchain."""

from typing import Dict, Optional, List
import os
import json
from datetime import datetime
import traceback
from pathlib import Path
from dotenv import load_dotenv
from langchain.agents import create_openai_functions_agent, AgentExecutor
from langchain import hub
from composio_langchain import ComposioToolSet

from src.tools.payment_tools import (
    BalanceTool,
    SearchPayeesTool,
    SendPaymentTool,
    CheckoutUrlTool
)
from src.tools.shared_tools import (
    debug_print,
    format_error,
    format_currency
)
from src.openai_client import get_openai_client

# Load environment variables
load_dotenv()

# Initialize OpenAI client
openai_client = get_openai_client()

# Initialize payment tools
balance_tool = BalanceTool()
search_payees_tool = SearchPayeesTool()
send_payment_tool = SendPaymentTool()
checkout_url_tool = CheckoutUrlTool()

# Initialize LangChain components for email
print("\n🔧 Initializing LangChain components...")

# Get Composio API key
composio_api_key = os.getenv("COMPOSIO_API_KEY")
if not composio_api_key:
    raise ValueError("COMPOSIO_API_KEY environment variable not found")
print(f"Composio API Key present: {'✓' if composio_api_key else '✗'}")

# Initialize Composio toolset
composio_toolset = ComposioToolSet(api_key=composio_api_key)
tools = composio_toolset.get_tools(actions=['GMAIL_REPLY_TO_THREAD'])

# Create agent with Composio tools
prompt = hub.pull("hwchase17/openai-functions-agent")
agent = create_openai_functions_agent(openai_client, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
print("✅ LangChain components initialized")

def extract_payment_amount(invoice_data: Dict) -> Optional[float]:
    """Extract the final payment amount from invoice data."""
    amount = invoice_data.get('paid_amount')
    if amount is not None:
        try:
            amount = float(amount)
            if amount > 0:
                return amount
        except (ValueError, TypeError):
            pass
    
    return None

def check_balance() -> float:
    """Get current balance."""
    try:
        print("\n💰 Checking Balance")
        result = balance_tool.run("")  # Empty string as tool_input
        print(f"Balance Tool Response: {result}")
        
        # Extract numeric balance from string "Current balance: $X.XX"
        if not result or "Current balance:" not in result:
            print("❌ Invalid balance response")
            return 0.0
            
        try:
            balance_str = result.split("$")[1].strip()
            balance = float(balance_str)
            print(f"✅ Current Balance: ${balance:,.2f}")
            return balance
        except (IndexError, ValueError) as e:
            print(f"❌ Error parsing balance: {str(e)}")
            print(f"Raw response: {result}")
            return 0.0
            
    except Exception as e:
        print(f"❌ Error checking balance: {str(e)}")
        traceback.print_exc()
        return 0.0

def search_or_create_payee(recipient_name: str) -> Optional[Dict]:
    """Search for a payee by name or create if not found."""
    try:
        print("\n🔍 PAYEE SEARCH WORKFLOW")
        print("=" * 50)
        
        print("\n1️⃣ Search Parameters:")
        print("-" * 30)
        print(json.dumps({
            "name": recipient_name,
            "type": "US_ACH"
        }, indent=2))
        
        # Search for existing payee
        print("\n2️⃣ Searching Payman Database...")
        result = search_payees_tool.run(json.dumps({
            "name": recipient_name,
            "type": "US_ACH"
        }))
        
        if not result:
            print("\n❌ Search failed - no response from Payman")
            return None
            
        try:
            # Parse response
            if isinstance(result, str):
                payees = json.loads(result)
            else:
                payees = result
                
            print(f"\n✅ Search complete - Found {len(payees) if payees else 0} payees")
            
            if not payees:
                print("\n⚠️ No matching payees found")
                return None
                
            # Show found payees
            print("\n3️⃣ Found Payees:")
            print("-" * 30)
            for idx, payee in enumerate(payees[:5], 1):  # Show first 5 payees
                print(f"\nPayee {idx}:")
                print(f"- ID: {payee.get('id', 'Unknown')}")
                print(f"- Name: {payee.get('name', 'Unknown')}")
                print(f"- Type: {payee.get('type', 'Unknown')}")
                print(f"- Status: {payee.get('status', 'Unknown')}")
                if payee.get('contact_email'):
                    print(f"- Email: {payee.get('contact_email')}")
                if payee.get('contact_phone'):
                    print(f"- Phone: {payee.get('contact_phone')}")
            
            # Return first matching payee
            selected_payee = payees[0]
            print(f"\n✅ Selected Payee:")
            print("-" * 30)
            print(json.dumps(selected_payee, indent=2))
            
            return selected_payee
            
        except json.JSONDecodeError as e:
            print(f"\n❌ Failed to parse payee search response:")
            print(f"Error: {str(e)}")
            print(f"Raw response: {result}")
            return None
            
    except Exception as e:
        print(f"\n❌ Payee search error:")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {str(e)}")
        traceback.print_exc()
        return None

def generate_checkout_url(amount: float, memo: str = "") -> Optional[str]:
    """Generate a checkout URL for adding funds."""
    try:
        result = checkout_url_tool.run(json.dumps({
            "amount": amount,
            "memo": memo
        }))
        
        if not result:
            return None
            
        try:
            data = json.loads(result)
            return data.get("url")
        except json.JSONDecodeError:
            return None
            
    except Exception as e:
        print(f"❌ Error generating checkout URL: {str(e)}")
        return None

def send_payment(amount: float, payee_id: str, description: str = "") -> Optional[str]:
    """Send a payment to a payee."""
    try:
        print("\n💸 Payment Request:")
        print("-" * 30)
        params = {
            "amount": float(amount),
            "destination_id": payee_id,
            "memo": description
        }
        print(json.dumps(params, indent=2))
        
        # Convert params to JSON string for tool input
        result = send_payment_tool.run(tool_input=json.dumps(params))
        
        if not result:
            print("\n❌ No response from payment tool")
            return None
            
        print("\n✅ Payment Tool Response:")
        print("-" * 30)
        print(result)
        
        # Extract payment ID from response
        if "Reference:" in result:
            payment_id = result.split("Reference:")[1].strip()
            return payment_id
        
        return None
            
    except Exception as e:
        print(f"\n❌ Error sending payment:")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {str(e)}")
        traceback.print_exc()
        return None

def is_invoice_processed(invoice_number: str, recipient: str) -> bool:
    """Check if an invoice has already been processed."""
    try:
        history_file = Path("invoice data/payment_history.json")
        if not history_file.exists():
            return False
            
        with open(history_file, "r") as f:
            history = json.load(f)
            
        for payment in history:
            invoice_data = payment.get("invoice_data", {})
            result = payment.get("result", {})
            if (invoice_data.get("invoice_number") == invoice_number and 
                invoice_data.get("recipient") == recipient and 
                result.get("success")):
                return True
                
        return False
        
    except Exception as e:
        print(f"❌ Error checking payment history: {str(e)}")
        return False

def save_payment_history(email_data: Dict, invoice_data: Dict, result: Dict):
    """Save payment attempt to history if not already present."""
    try:
        history_dir = Path("invoice data")
        history_dir.mkdir(exist_ok=True)
        history_file = history_dir / "payment_history.json"
        
        # Load existing history
        history = []
        if history_file.exists():
            try:
                with open(history_file, "r") as f:
                    history = json.load(f)
            except json.JSONDecodeError:
                history = []
                
        # Check if this invoice is already in history
        for entry in history:
            if (entry["email_data"].get("message_id") == email_data.get("message_id") and
                entry["email_data"].get("attachment_id") == email_data.get("attachment_id")):
                print("\n⚠️ Invoice already exists in payment history - skipping update")
                return
                
            if (entry["invoice_data"].get("invoice_number") == invoice_data.get("invoice_number") and
                entry["invoice_data"].get("date") == invoice_data.get("date") and
                entry["invoice_data"].get("paid_amount") == invoice_data.get("paid_amount") and
                entry["invoice_data"].get("recipient") == invoice_data.get("recipient")):
                print("\n⚠️ Similar invoice found in payment history - skipping update")
                return
                
        # Format the entry with consistent structure
        entry = {
            "timestamp": datetime.now().isoformat(),
            "email_data": {
                "thread_id": email_data.get("thread_id", ""),
                "message_id": email_data.get("message_id", ""),
                "sender": email_data.get("sender", ""),
                "subject": email_data.get("subject", ""),
                "attachment_id": email_data.get("attachment_id", "")
            },
            "invoice_data": {
                "invoice_number": invoice_data.get("invoice_number", ""),
                "paid_amount": invoice_data.get("paid_amount", 0.0),
                "recipient": invoice_data.get("recipient", ""),
                "date": invoice_data.get("date", ""),
                "due_date": invoice_data.get("due_date", ""),
                "description": invoice_data.get("description", "")
            },
            "result": {
                "success": result.get("success", False),
                "error": result.get("error"),
                "email_sent": result.get("email_sent", False),
                "payment_id": result.get("payment_id")
            }
        }
        
        # Add new record only if not already present
        print("\n✅ Adding new invoice to payment history")
        history.append(entry)
        
        # Save updated history
        with open(history_file, "w") as f:
            json.dump(history, f, indent=2)
            
    except Exception as e:
        print(f"❌ Error saving payment history: {str(e)}")
        traceback.print_exc()

async def send_bank_details_request(
    thread_id: str, 
    recipient: str, 
    amount: float,
    payee_exists: bool = False
) -> Dict:
    """Send an email requesting bank details from the recipient using LangChain agent."""
    try:
        print("\n📧 Bank Details Request Process")
        print("==============================")
        
        print("\n1️⃣ Input Data Validation:")
        print("Email Data:")
        print(json.dumps({
            "thread_id": thread_id,
            "recipient": recipient,
            "amount": amount,
            "payee_exists": payee_exists
        }, indent=2))
        
        # Check required fields
        if not thread_id:
            print("\n❌ Validation Failed: Missing thread_id")
            return {
                "success": False,
                "error": "Missing thread_id"
            }
            
        if not recipient:
            print("\n❌ Validation Failed: Missing recipient email")
            return {
                "success": False,
                "error": "Missing recipient email"
            }
            
        print("\n✅ Validation Passed")
            
        # Prepare email message
        if payee_exists:
            message = f"""Thank you for your invoice submission for ${amount:,.2f}. We found your payee profile in our system, but we need your bank details for this payment:

Please provide:
- Bank Account Number
- Routing Number
- Bank Name
- Account Name (as it appears on the account)
- Account Type (checking/savings)

This information will be securely stored and used for future payments.

Best regards,
Payment Processing Team"""
        else:
            message = f"""Thank you for your invoice submission for ${amount:,.2f}. To process your payment, we need to set up your payee profile with bank details:

Please provide:
- Bank Account Number
- Routing Number
- Bank Name
- Account Name (as it appears on the account)
- Account Type (checking/savings)

This information will be securely stored and used for future payments.

Best regards,
Payment Processing Team"""

        # print("\n📝 Message Content:")
        # print(message)
        # print(f"\nMessage Length: {len(message)} chars")
        
        print("\n3️⃣ Sending Email via LangChain Agent:")
        try:
            # Format task for LangChain agent
            task = {
                "action": "GMAIL_REPLY_TO_THREAD",
                "parameters": {
                    "thread_id": thread_id,
                    "message_body": message,
                    "recipient_email": recipient,
                    "user_id": "me",
                    "is_html": False
                }
            }
            
            # print("\nAgent Task:")
            # print(json.dumps(task, indent=2))
            
            # Execute email reply via LangChain agent
            result = agent_executor.invoke({
                "input": f"Send an email reply using these parameters: {json.dumps(task)}"
            })
            
            print("\n5️⃣ Processing Agent Response:")
            print("Raw Response:")
            print(json.dumps(result, indent=2))
            
            # Check if email was sent successfully
            if isinstance(result, dict):
                output = result.get('output', '').lower()
                success = ('email sent' in output or 
                         'reply sent' in output or 
                         'successfully sent' in output)
            else:
                output = str(result).lower()
                success = ('email sent' in output or 
                         'reply sent' in output or 
                         'successfully sent' in output)
            
            if success:
                print("\n✅ Email Sent Successfully!")
                print("- Success: True")
                print(f"- Thread ID: {thread_id}")
                print(f"- Recipient: {recipient}")
                return {
                    "success": True,
                    "thread_id": thread_id,
                    "recipient": recipient
                }
            else:
                error = result.get('error', 'Failed to send email') if isinstance(result, dict) else 'Failed to send email'
                print(f"\n❌ Email Sending Failed:")
                print(f"- Error: {error}")
                return {
                    "success": False,
                    "error": error
                }
            
        except Exception as e:
            print(f"\n❌ Email Sending Error:")
            print(f"- Error Type: {type(e).__name__}")
            print(f"- Error Message: {str(e)}")
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e)
            }
        
    except Exception as e:
        print(f"\n❌ Process Error:")
        print(f"- Error Type: {type(e).__name__}")
        print(f"- Error Message: {str(e)}")
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }

def is_duplicate_invoice(invoice_data: Dict, email_data: Dict) -> Optional[Dict]:
    """Check if invoice has already been processed or attempted.
    Returns None if no duplicate found or if invoice was already processed successfully."""
    try:
        history_file = Path("invoice data/payment_history.json")
        if not history_file.exists():
            return None
            
        with open(history_file, "r") as f:
            history = json.load(f)
            
        # Check for exact matches first
        for record in history:
            if (record["email_data"].get("message_id") == email_data.get("message_id") and
                record["email_data"].get("attachment_id") == email_data.get("attachment_id")):
                if record["result"].get("success") or record["result"].get("error") == "Invoice already processed":
                    print("\n⚠️ Invoice was already processed successfully - skipping history update")
                    return None
                return record
                
        # Check for similar invoices (same number, date, amount)
        for record in history:
            if (record["invoice_data"].get("invoice_number") == invoice_data.get("invoice_number") and
                record["invoice_data"].get("date") == invoice_data.get("date") and
                record["invoice_data"].get("paid_amount") == invoice_data.get("paid_amount") and
                record["invoice_data"].get("recipient") == invoice_data.get("recipient")):
                if record["result"].get("success") or record["result"].get("error") == "Invoice already processed":
                    print("\n⚠️ Similar invoice was already processed successfully - skipping history update")
                    return None
                return record
                
        return None
        
    except Exception as e:
        print(f"❌ Error checking payment history: {str(e)}")
        return None

async def process_payment(invoice_data: Dict) -> Dict:
    """Process payment for an invoice."""
    try:
        print("\n" + "="*50)
        print("💳 PAYMENT PROCESSING WORKFLOW")
        print("="*50)
        
        print("\n📝 Invoice Data:")
        print("-" * 30)
        print(json.dumps(invoice_data, indent=2))
        
        # Check for required fields
        required_fields = ["invoice_number", "paid_amount", "recipient"]
        missing_fields = [f for f in required_fields if not invoice_data.get(f)]
        
        if missing_fields:
            error = {
                "success": False,
                "error": f"Missing required fields: {', '.join(missing_fields)}",
                "invoice_number": invoice_data.get("invoice_number")
            }
            print("\n❌ Validation Error:")
            print("-" * 30)
            print(json.dumps(error, indent=2))
            return error
        
        # Check for duplicate invoice first
        print("\n🔍 Checking for duplicate invoice...")
        print("-" * 30)
        duplicate = is_duplicate_invoice(invoice_data, invoice_data.get("email_data", {}))
        
        if duplicate:
            # If the duplicate was successfully processed, return early without updating history
            if duplicate["result"].get("success"):
                print("\n⚠️ Invoice was previously processed successfully:")
                print("-" * 30)
                print(json.dumps({
                    "invoice_number": duplicate["invoice_data"].get("invoice_number"),
                    "recipient": duplicate["invoice_data"].get("recipient"),
                    "amount": duplicate["invoice_data"].get("paid_amount"),
                    "date": duplicate["invoice_data"].get("date"),
                    "processed_at": duplicate["timestamp"],
                    "payment_id": duplicate["result"].get("payment_id")
                }, indent=2))
                
                return {
                    "success": False,
                    "error": "Invoice was previously processed successfully",
                    "invoice_number": invoice_data["invoice_number"],
                    "duplicate_info": {
                        "processed_at": duplicate["timestamp"],
                        "payment_id": duplicate["result"].get("payment_id"),
                        "status": "success"
                    }
                }
            
            # For failed or pending duplicates, preserve original status and error
            print("\n⚠️ Duplicate invoice found:")
            print("-" * 30)
            print(json.dumps({
                "invoice_number": duplicate["invoice_data"].get("invoice_number"),
                "recipient": duplicate["invoice_data"].get("recipient"),
                "amount": duplicate["invoice_data"].get("paid_amount"),
                "date": duplicate["invoice_data"].get("date"),
                "processed_at": duplicate["timestamp"],
                "status": duplicate["result"].get("status", "pending" if duplicate["result"].get("email_sent") else "failed"),
                "error": duplicate["result"].get("error")
            }, indent=2))
            
            return {
                "success": False,
                "error": duplicate["result"].get("error", "Duplicate invoice found"),
                "invoice_number": invoice_data["invoice_number"],
                "duplicate_info": {
                    "processed_at": duplicate["timestamp"],
                    "status": duplicate["result"].get("status", "pending" if duplicate["result"].get("email_sent") else "failed"),
                    "error": duplicate["result"].get("error")
                }
            }
            
        print("✅ No duplicate found - proceeding with payment processing")
        
        # Check if invoice was already processed
        if is_invoice_processed(
            invoice_data["invoice_number"],
            invoice_data["recipient"]
        ):
            error = {
                "success": False,
                "error": "Invoice was already processed",
                "invoice_number": invoice_data["invoice_number"]
            }
            print("\n❌ Duplicate Invoice:")
            print("-" * 30)
            print(json.dumps(error, indent=2))
            return error
            
        # Check available balance
        balance = check_balance()
        if balance < invoice_data["paid_amount"]:
            error = {
                "success": False,
                "error": f"Insufficient balance: {format_currency(balance)} < {format_currency(invoice_data['paid_amount'])}",
                "invoice_number": invoice_data["invoice_number"]
            }
            print("\n❌ Balance Error:")
            print("-" * 30)
            print(json.dumps(error, indent=2))
            return error
            
        print("\n💰 Balance Check:")
        print("-" * 30)
        print(json.dumps({
            "available": format_currency(balance),
            "required": format_currency(invoice_data["paid_amount"])
        }, indent=2))
        
        # First try using extracted bank details
        bank_details = invoice_data.get("bank_details", {})
        if bank_details and all([
            bank_details.get("account_number"),
            bank_details.get("routing_number"),
            bank_details.get("account_type")
        ]):
            print("\n🏦 Using extracted bank details for payment...")
            print("-" * 30)
            print(json.dumps({
                "account_type": bank_details["account_type"],
                "account_holder": invoice_data["recipient"],
                "routing_number": bank_details["routing_number"][-4:],  # Show last 4 digits only
                "account_number": bank_details["account_number"][-4:]   # Show last 4 digits only
            }, indent=2))
            
            # Create payment destination with bank details
            payment_destination = {
                "type": "US_ACH",
                "accountHolderName": invoice_data["recipient"],
                "accountNumber": bank_details["account_number"],
                "accountType": bank_details["account_type"].lower(),
                "routingNumber": bank_details["routing_number"],
                "name": f"{invoice_data['recipient']}'s {bank_details['account_type']} Account",
                "contactDetails": {
                    "contactType": invoice_data.get("payee_details", {}).get("contact_type", "individual"),
                    "email": invoice_data.get("payee_details", {}).get("email", ""),
                    "phoneNumber": invoice_data.get("payee_details", {}).get("phone", ""),
                    "address": invoice_data.get("payee_details", {}).get("address", ""),
                    "taxId": invoice_data.get("payee_details", {}).get("tax_id", "")
                }
            }
            
            print("\n💸 Sending payment with bank details...")
            print("-" * 30)
            params = {
                "amount": float(invoice_data["paid_amount"]),
                "payment_destination": payment_destination,
                "memo": invoice_data.get("description", f"Invoice {invoice_data['invoice_number']}")
            }
            print(json.dumps(params, indent=2))
            
            # Send payment with bank details
            result = send_payment_tool.run(tool_input=json.dumps(params))
            
            if result and "Reference:" in result:
                payment_id = result.split("Reference:")[1].strip()
                print("\n✅ Payment sent successfully!")
                print(f"Payment ID: {payment_id}")
                return {
                    "success": True,
                    "payment_id": payment_id,
                    "invoice_number": invoice_data["invoice_number"],
                    "payment_method": "bank_details"
                }
        
        # If bank details not complete, try finding existing payee
        print("\n🔍 Searching for payee in Payman...")
        print("-" * 30)
        print(f"Recipient Name: {invoice_data['recipient']}")
        
        payee = search_or_create_payee(invoice_data["recipient"])
        
        if payee:
            print("\n✅ Payee found in Payman:")
            print("-" * 30)
            print(json.dumps(payee, indent=2))
            
            # Send payment using payee ID
            print("\n💸 Sending payment via Payman...")
            payment_id = send_payment(
                amount=invoice_data["paid_amount"],
                payee_id=payee["id"],
                description=invoice_data.get("description", f"Invoice {invoice_data['invoice_number']}")
            )
            
            if payment_id:
                print("\n✅ Payment sent successfully!")
                print(f"Payment ID: {payment_id}")
                return {
                    "success": True,
                    "payment_id": payment_id,
                    "invoice_number": invoice_data["invoice_number"],
                    "payment_method": "existing_payee"
                }
        
        # If neither bank details nor payee found, send email request
        print("\n📧 Bank details and payee missing - sending email request")
        email_result = await send_bank_details_request(
            thread_id=invoice_data.get("email_data", {}).get("thread_id"),
            recipient=invoice_data.get("email_data", {}).get("sender"),
            amount=invoice_data["paid_amount"],
            payee_exists=False
        )
        
        return {
            "success": False,
            "error": "Bank details and payee information required",
            "email_sent": email_result.get("success", False),
            "invoice_number": invoice_data["invoice_number"],
            "action_required": "bank_details",
            "payee_exists": False
        }
            
    except Exception as e:
        print(f"\n❌ Payment processing error:")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {str(e)}")
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e),
            "invoice_number": invoice_data.get("invoice_number")
        }

def main():
    """Example usage of payment agent"""
    try:
        print("\n🚀 Starting Payment Processing Test")
        print("=" * 50)
        
        # Example invoice data
        invoice_data = {
            "invoice_number": "INV-2024-001",
            "recipient": "Slingshot AI",
            "date": "2024-01-17",
            "due_date": "2024-02-17",
            "description": "AI Development Services",
            "subtotal": 8500.00,
            "tax": 722.50,
            "discount": 850.00,
            "total": 8372.50,
            "paid_amount": 2500.00,
            "balance_due": 5872.50  # Final amount to pay
        }
        
        # Process payment using agent
        result = process_payment(invoice_data)
        print("\n✅ Agent Response:")
        print(json.dumps(result, indent=2))
                
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")

if __name__ == "__main__":
    main() 