"""Payment agent for processing invoice payments using Payman AI and Langchain."""

from typing import Dict, Optional, List
import os
import json
from datetime import datetime
import traceback
from pathlib import Path
from dotenv import load_dotenv
from langchain.agents import create_openai_functions_agent, AgentExecutor
from langchain_openai import ChatOpenAI
from langchain import hub
from composio_langchain import ComposioToolSet

from tools.payment_tools import (
    BalanceTool,
    SearchPayeesTool,
    SendPaymentTool,
    CheckoutUrlTool
)
from tools.shared_tools import (
    debug_print,
    format_error,
    format_currency
)

# Load environment variables
load_dotenv()

# Initialize payment tools
balance_tool = BalanceTool()
search_payees_tool = SearchPayeesTool()
send_payment_tool = SendPaymentTool()
checkout_url_tool = CheckoutUrlTool()

# Initialize LangChain components for email
print("\n🔧 Initializing LangChain components...")

openai_api_key = os.getenv("OPENAI_API_KEY")
print(f"OpenAI API Key present: {'✓' if openai_api_key else '✗'}")

llm = ChatOpenAI(api_key=openai_api_key)
prompt = hub.pull("hwchase17/openai-functions-agent")

composio_api_key = os.getenv("COMPOSIO_API_KEY")
print(f"Composio API Key present: {'✓' if composio_api_key else '✗'}")

# Initialize Composio toolset
composio_toolset = ComposioToolSet(api_key=composio_api_key)
tools = composio_toolset.get_tools(actions=['GMAIL_REPLY_TO_THREAD'])

# Create agent with Composio tools
agent = create_openai_functions_agent(llm, tools, prompt)
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

def search_or_create_payee(recipient: str) -> Optional[Dict]:
    """Search for a payee by name."""
    try:
        print(f"\n🔍 Searching payee database for: {recipient}")
        result = search_payees_tool.run(recipient)
        print(f"Search result: {result}")
        
        if not result:
            print("❌ No search results")
            return None
            
        # Parse JSON response
        try:
            # Handle both string and dict responses
            if isinstance(result, str):
                if result.startswith('{'): # JSON object
                    payees = [json.loads(result)]
                elif result.startswith('['): # JSON array
                    payees = json.loads(result)
                else:
                    print("❌ Invalid response format")
                    return None
            elif isinstance(result, dict):
                payees = [result]
            elif isinstance(result, list):
                payees = result
            else:
                print("❌ Invalid response type")
                return None
                
            if not payees:
                print("📋 Search Result: No payees found")
                return None
                
            # Find exact match
            for payee in payees:
                if payee.get("name", "").lower() == recipient.lower():
                    print(f"✅ Found matching payee: {payee.get('name')}")
                    return payee
                    
            print(f"📋 Search Result: No payees found matching '{recipient}'")
            return None
            
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON response from search: {str(e)}")
            print(f"Raw response: {result}")
            return None
            
    except Exception as e:
        print(f"❌ Error searching payees: {str(e)}")
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
        result = send_payment_tool.run(json.dumps({
            "amount": amount,
            "payee_id": payee_id,
            "description": description
        }))
        
        if not result:
            return None
            
        try:
            data = json.loads(result)
            return data.get("payment_id")
        except json.JSONDecodeError:
            return None
            
    except Exception as e:
        print(f"❌ Error sending payment: {str(e)}")
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
            if (payment.get("invoice_number") == invoice_number and 
                payment.get("recipient") == recipient and 
                payment.get("success")):
                return True
                
        return False
        
    except Exception:
        return False

def save_payment_history(email_data: Dict, invoice_data: Dict, result: Dict):
    """Save payment attempt to history."""
    try:
        # Create history directory if it doesn't exist
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
                
        # Add new entry
        entry = {
            "timestamp": datetime.now().isoformat(),
            "invoice_data": invoice_data,
            "email_data": email_data,
            "result": result
        }
        
        history.append(entry)
        
        # Save updated history
        with open(history_file, "w") as f:
            json.dump(history, f, indent=2)
            
    except Exception as e:
        print(f"❌ Error saving payment history: {str(e)}")

def send_bank_details_request(email_data: Dict, debug: bool = False) -> bool:
    """Send an email requesting bank details from the recipient using LangChain agent."""
    try:
        print("\n📧 Bank Details Request Process")
        print("==============================")
        
        print("\n1️⃣ Input Data Validation:")
        print("Email Data:")
        print(json.dumps(email_data, indent=2))
        
        # Check required fields
        thread_id = email_data.get('thread_id')
        recipient = email_data.get('sender')
        
        print("\nRequired Fields:")
        print(f"- Thread ID: {'✓' if thread_id else '✗'} ({thread_id})")
        print(f"- Recipient: {'✓' if recipient else '✗'} ({recipient})")
        
        if not thread_id:
            print("\n❌ Validation Failed: Missing thread_id")
            return False
            
        if not recipient:
            print("\n❌ Validation Failed: Missing recipient email")
            return False
            
        print("\n✅ Validation Passed")
            
        # Prepare email message
        message = """Thank you for your invoice submission. To process your payment, we need your bank details:

Please provide:
- Bank Account Number
- Routing Number
- Bank Name
- Account Name (as it appears on the account)

This information will be securely stored and used only for this payment.

Best regards,
Payment Processing Team"""
        
        print("\n📝 Message Content:")
        print(message)
        print(f"\nMessage Length: {len(message)} chars")
        
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
            
            print("\nAgent Task:")
            print(json.dumps(task, indent=2))
            
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
            else:
                error = result.get('error', 'Unknown error') if isinstance(result, dict) else str(result)
                print(f"\n❌ Email Sending Failed:")
                print(f"- Error: {error}")
            
            return success
            
        except Exception as e:
            print(f"\n❌ Email Sending Error:")
            print(f"- Error Type: {type(e).__name__}")
            print(f"- Error Message: {str(e)}")
            traceback.print_exc()
            return False
        
    except Exception as e:
        print(f"\n❌ Process Error:")
        print(f"- Error Type: {type(e).__name__}")
        print(f"- Error Message: {str(e)}")
        traceback.print_exc()
        return False

def process_payment(invoice_data: Dict, email_data: Dict = None, debug: bool = False) -> Dict:
    """Process payment for an invoice using Payman."""
    try:
        print("\n" + "="*50)
        print("💸 Starting Payment Processing Workflow")
        print("="*50)
        
        print("\n📄 Input Data:")
        print("-" * 30)
        print("Invoice Data:")
        print(json.dumps(invoice_data, indent=2))
        print("\nEmail Data:")
        print(json.dumps(email_data, indent=2))
        print("-" * 30)
        
        # Extract payment amount
        print("\n1️⃣ Extracting Payment Amount")
        amount = extract_payment_amount(invoice_data)
        if not amount:
            print("❌ No valid payment amount found in invoice")
            return {
                "success": False,
                "error": "No valid payment amount found"
            }
        print(f"✅ Payment Amount: ${amount:,.2f}")
        
        # Get recipient
        print("\n2️⃣ Extracting Recipient")
        recipient = invoice_data.get("recipient")
        if not recipient:
            print("❌ No recipient found in invoice")
            return {
                "success": False,
                "error": "No recipient found"
            }
        print(f"✅ Recipient: {recipient}")
            
        # Search for payee
        print(f"\n3️⃣ Searching Payee Database")
        print(f"🔍 Searching for: {recipient}")
        payee = search_or_create_payee(recipient)
        if payee:
            print(f"✅ Payee Found:")
            print(json.dumps(payee, indent=2))
        else:
            print(f"❌ Payee Not Found")
            
            print("\n4️⃣ Bank Details Request Flow")
            print("-" * 30)
            
            if not email_data:
                print("❌ Cannot request bank details - No email data available")
                return {
                    "success": False,
                    "error": f"Could not find payee: {recipient}. No email data available.",
                    "email_sent": False
                }
                
            print("📧 Sending bank details request email...")
            email_sent = send_bank_details_request(email_data, debug=True)
            
            print(f"\n📝 Saving to payment history...")
            failed_result = {
                "success": False,
                "error": "Payee not found - Bank details requested",
                "email_sent": email_sent
            }
            save_payment_history(email_data, invoice_data, failed_result)
            
            return {
                "success": False,
                "error": f"Could not find payee: {recipient}. Bank details request sent.",
                "email_sent": email_sent
            }
            
        # Check if invoice has already been processed
        print("\n5️⃣ Checking Previous Processing")
        invoice_number = invoice_data.get("invoice_number")
        if invoice_number and is_invoice_processed(invoice_number, recipient):
            print(f"❌ Invoice {invoice_number} already processed")
            return {
                "success": False,
                "error": f"Invoice {invoice_number} for {recipient} has already been processed"
            }
        print("✅ Invoice not previously processed")
            
        # Check balance
        print("\n6️⃣ Checking Available Balance")
        balance = check_balance()
        print(f"Required Amount: ${amount:,.2f}")
        print(f"Available Balance: ${balance:,.2f}")
        
        if amount > balance:
            print("\n❌ Insufficient Balance")
            print("-" * 30)
            
            print("🔄 Generating checkout URL...")
            checkout_url = generate_checkout_url(
                amount=amount - balance,
                memo=f"Add funds for payment to {recipient}"
            )
            
            if email_data:
                print("📧 Sending insufficient funds notification...")
                email_sent = send_bank_details_request(email_data, debug=True)
                
                return {
                    "success": False,
                    "error": "Insufficient balance",
                    "checkout_url": checkout_url if checkout_url else None,
                    "email_sent": email_sent
                }
            else:
                return {
                    "success": False,
                    "error": "Insufficient balance",
                    "checkout_url": checkout_url if checkout_url else None
                }
            
        print("✅ Sufficient balance available")
            
        # Generate reference number
        print("\n7️⃣ Processing Payment")
        reference = f"INV-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        print(f"Payment Reference: {reference}")
            
        # Send payment
        print(f"💸 Sending payment to {recipient}...")
        payment_id = send_payment(
            amount=amount,
            payee_id=payee.get("id"),
            description=f"Invoice payment (Ref: {reference})"
        )
        
        if payment_id:
            print(f"\n✅ Payment Successful!")
            print(f"Payment ID: {payment_id}")
            result = {
                "success": True,
                "payment_id": payment_id,
                "reference": reference,
                "amount": amount,
                "recipient": recipient,
                "payee_id": payee.get("id")
            }
            print("\n📝 Saving to payment history...")
            save_payment_history(email_data or {}, invoice_data, result)
            return result
        else:
            print("\n❌ Payment Failed - No payment ID returned")
            return {
                "success": False,
                "error": "Payment failed - no payment ID returned"
            }
            
    except Exception as e:
        error_msg = str(e)
        print(f"\n❌ Error in payment processing: {error_msg}")
        if debug:
            traceback.print_exc()
        return {
            "success": False,
            "error": error_msg
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
        result = process_payment(invoice_data, debug=True)
        print("\n✅ Agent Response:")
        print(json.dumps(result, indent=2))
                
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")

if __name__ == "__main__":
    main() 