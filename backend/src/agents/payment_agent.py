"""Payment agent for processing invoice payments using Payman AI and Langchain."""

from typing import Dict, Optional, List, Any
import os
import json
from datetime import datetime
import traceback
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor
from langchain.prompts.chat import MessagesPlaceholder
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import Tool
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from composio_langchain import ComposioToolSet
from langsmith import Client
from tools.shared_tools import (
    format_error,
    format_currency,
    ensure_directory,
    DEBUG,
    debug_print
)

from tools.payment_tools import (
    BalanceTool,
    SearchPayeesTool,
    SendPaymentTool,
    CheckoutUrlTool
)

# Load environment variables
load_dotenv()

# Initialize LangSmith client
langsmith_client = Client()

# Get OpenAI API key
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY environment variable not found")
debug_print(f"OpenAI API Key present: {'✓' if openai_api_key else '✗'}")

# Initialize OpenAI client
openai_client = ChatOpenAI(
    model="gpt-4-turbo-preview",
    temperature=0,
    api_key=openai_api_key
)
debug_print(f"OpenAI client initialized with model: {openai_client.model_name}")

# Enable debug mode for verbose output
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
debug_print(f"Debug mode: {'enabled' if DEBUG else 'disabled'}")

# Initialize payment tools
balance_tool = BalanceTool()
search_payees_tool = SearchPayeesTool()
send_payment_tool = SendPaymentTool()
checkout_url_tool = CheckoutUrlTool()

# Initialize LangChain components for email
debug_print("\n🔧 Initializing LangChain components...")

# Get Composio API key
composio_api_key = os.getenv("COMPOSIO_API_KEY")
if not composio_api_key:
    raise ValueError("COMPOSIO_API_KEY environment variable not found")
debug_print(f"Composio API Key present: {'✓' if composio_api_key else '✗'}")

# Initialize Composio toolset
composio_toolset = ComposioToolSet(api_key=composio_api_key)
tools = composio_toolset.get_tools(actions=['GMAIL_REPLY_TO_THREAD'])

# Create the prompt template
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful AI assistant that processes invoice payments."),
    MessagesPlaceholder(variable_name="chat_history"),
    ("user", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad")
])

# Create the chain
chain = (
    RunnablePassthrough.assign(
        chat_history=lambda x: x.get("chat_history", []),
        agent_scratchpad=lambda x: x.get("intermediate_steps", [])
    )
    | prompt
    | openai_client
    | StrOutputParser()
)

# Create the agent executor
agent_executor = AgentExecutor(
    agent=chain,
    tools=tools,
    verbose=DEBUG,  # Only show verbose output in debug mode
    tags=["invoice-agent", "email-communication"],
    metadata={
        "agent_type": "email_communication",
        "agent_version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "production")
    }
)

debug_print("✅ LangChain components initialized")

def serialize_firebase_data(data: Any) -> Any:
    """Serialize Firebase data types to JSON-compatible format."""
    if isinstance(data, dict):
        return {k: serialize_firebase_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [serialize_firebase_data(item) for item in data]
    elif str(type(data)) == "<class 'google.api_core.datetime_helpers.DatetimeWithNanoseconds'>":
        return data.isoformat()
    elif hasattr(data, '_seconds'):  # Firebase Timestamp
        return datetime.fromtimestamp(data._seconds).isoformat()
    elif str(type(data)) == "<class 'google.cloud.firestore_v1.transforms.Sentinel'>":
        return datetime.now().isoformat()
    elif isinstance(data, datetime):
        return data.isoformat()
    return data

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
        debug_print("\n💰 Checking Balance")
        result = balance_tool.run("")  # Empty string as tool_input
        debug_print(f"Balance Tool Response: {result}")
        
        # Extract numeric balance from string "Current balance: $X.XX"
        if not result or "Current balance:" not in result:
            debug_print("❌ Invalid balance response")
            return 0.0
            
        try:
            balance_str = result.split("$")[1].strip()
            balance = float(balance_str)
            debug_print(f"✅ Current Balance: ${balance:,.2f}")
            return balance
        except (IndexError, ValueError) as e:
            debug_print(f"❌ Error parsing balance: {str(e)}")
            debug_print(f"Raw response: {result}")
            return 0.0
            
    except Exception as e:
        debug_print(f"❌ Error checking balance: {str(e)}")
        traceback.print_exc()
        return 0.0

def search_or_create_payee(recipient_name: str) -> Optional[Dict]:
    """Search for a payee by name or create if not found."""
    try:
        debug_print("\n🔍 PAYEE SEARCH WORKFLOW")
        debug_print("=" * 50)
        
        debug_print("\n1️⃣ Search Parameters:")
        debug_print("-" * 30)
        debug_print(json.dumps({
            "name": recipient_name,
            "type": "US_ACH"
        }, indent=2))
        
        # Search for existing payee
        debug_print("\n2️⃣ Searching Payman Database...")
        result = search_payees_tool.run(json.dumps({
            "name": recipient_name,
            "type": "US_ACH"
        }))
        
        if not result:
            debug_print("\n❌ Search failed - no response from Payman")
            return None
            
        try:
            # Parse response
            if isinstance(result, str):
                payees = json.loads(result)
            else:
                payees = result
                
            debug_print(f"\n✅ Search complete - Found {len(payees) if payees else 0} payees")
            
            if not payees:
                debug_print("\n⚠️ No matching payees found")
                return None
                
            # Show found payees
            debug_print("\n3️⃣ Found Payees:")
            debug_print("-" * 30)
            for idx, payee in enumerate(payees[:5], 1):  # Show first 5 payees
                debug_print(f"\nPayee {idx}:")
                debug_print(f"- ID: {payee.get('id', 'Unknown')}")
                debug_print(f"- Name: {payee.get('name', 'Unknown')}")
                debug_print(f"- Type: {payee.get('type', 'Unknown')}")
                debug_print(f"- Status: {payee.get('status', 'Unknown')}")
                if payee.get('contact_email'):
                    debug_print(f"- Email: {payee.get('contact_email')}")
                if payee.get('contact_phone'):
                    debug_print(f"- Phone: {payee.get('contact_phone')}")
            
            # Return first matching payee
            selected_payee = payees[0]
            debug_print(f"\n✅ Selected Payee:")
            debug_print("-" * 30)
            debug_print(json.dumps(selected_payee, indent=2))
            
            return selected_payee
            
        except json.JSONDecodeError as e:
            debug_print(f"\n❌ Failed to parse payee search response:")
            debug_print(f"Error: {str(e)}")
            debug_print(f"Raw response: {result}")
            return None
            
    except Exception as e:
        debug_print(f"\n❌ Payee search error:")
        debug_print(f"Error Type: {type(e).__name__}")
        debug_print(f"Error Message: {str(e)}")
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
        debug_print(f"❌ Error generating checkout URL: {str(e)}")
        return None

def send_payment(amount: float, payee_id: str, description: str = "") -> Optional[str]:
    """Send a payment to a payee."""
    try:
        debug_print("\n💸 Payment Request:")
        debug_print("-" * 30)
        params = {
            "amount": float(amount),
            "destination_id": payee_id,
            "memo": description
        }
        debug_print(json.dumps(params, indent=2))
        
        # Convert params to JSON string for tool input
        result = send_payment_tool.run(tool_input=json.dumps(params))
        
        if not result:
            debug_print("\n❌ No response from payment tool")
            return None
            
        debug_print("\n✅ Payment Tool Response:")
        debug_print("-" * 30)
        debug_print(result)
        
        # Extract payment ID from response
        if "Reference:" in result:
            payment_id = result.split("Reference:")[1].strip()
            return payment_id
        
        return None
            
    except Exception as e:
        debug_print(f"\n❌ Error sending payment:")
        debug_print(f"Error Type: {type(e).__name__}")
        debug_print(f"Error Message: {str(e)}")
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
        debug_print(f"❌ Error checking payment history: {str(e)}")
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
                debug_print("\n⚠️ Invoice already exists in payment history - skipping update")
                return
                
            if (entry["invoice_data"].get("invoice_number") == invoice_data.get("invoice_number") and
                entry["invoice_data"].get("date") == invoice_data.get("date") and
                entry["invoice_data"].get("paid_amount") == invoice_data.get("paid_amount") and
                entry["invoice_data"].get("recipient") == invoice_data.get("recipient")):
                debug_print("\n⚠️ Similar invoice found in payment history - skipping update")
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
        debug_print("\n✅ Adding new invoice to payment history")
        history.append(entry)
        
        # Save updated history
        with open(history_file, "w") as f:
            json.dump(history, f, indent=2)
            
    except Exception as e:
        debug_print(f"❌ Error saving payment history: {str(e)}")
        traceback.print_exc()

async def send_bank_details_request(
    thread_id: str,
    recipient: str,
    amount: float,
    payee_exists: bool = False
) -> Dict:
    """Send an email requesting bank details from the recipient using LangChain agent."""
    try:
        debug_print("\n📧 Bank Details Request Process")
        debug_print("==============================")
        
        debug_print("\n1️⃣ Input Data Validation:")
        debug_print("Email Data:")
        debug_print(json.dumps({
            "thread_id": thread_id,
            "recipient": recipient,
            "amount": amount,
            "payee_exists": payee_exists
        }, indent=2))
        
        # Check required fields
        if not thread_id:
            debug_print("\n❌ Validation Failed: Missing thread_id")
            return {
                "success": False,
                "error": "Missing thread_id"
            }
            
        if not recipient:
            debug_print("\n❌ Validation Failed: Missing recipient email")
            return {
                "success": False,
                "error": "Missing recipient email"
            }
            
        debug_print("\n✅ Validation Passed")
            
        # Prepare email message
        message = (
            f"Hello,\n\n"
            f"We received your invoice for {format_currency(amount)}. "
        )
        
        if payee_exists:
            message += (
                "We found your payee profile in our system, but we need your bank account details "
                "to process this payment.\n\n"
                "Please provide:\n"
                "1. Bank Account Number\n"
                "2. Routing Number\n"
                "3. Account Type (Checking/Savings)\n\n"
            )
        else:
            message += (
                "To process your payment, we need to set up your payee profile and collect your bank details.\n\n"
                "Please provide:\n"
                "1. Full Legal Name (as it appears on your bank account)\n"
                "2. Bank Account Number\n"
                "3. Routing Number\n"
                "4. Account Type (Checking/Savings)\n"
                "5. Contact Email\n"
                "6. Contact Phone (optional)\n"
                "7. Mailing Address\n"
                "8. Tax ID (SSN/EIN)\n\n"
            )
            
        message += (
            "You can reply directly to this email with the requested information.\n\n"
            "Thank you for your cooperation.\n\n"
            "Best regards,\n"
            "Payman AI"
        )
        
        debug_print("\n3️⃣ Sending Email via LangChain Agent:")
        try:
            # Format task for LangChain agent
            task = {
                "action": "GMAIL_REPLY_TO_THREAD",
                "parameters": {
                    "thread_id": thread_id,
                    "message": message
                }
            }
            
            # Execute agent with task
            result = await agent_executor.arun(
                json.dumps(task)
            )
            
            debug_print("\n5️⃣ Processing Agent Response:")
            debug_print("Raw Response:")
            debug_print(json.dumps(result, indent=2))
            
            # Check if email was sent successfully
            success = (
                isinstance(result, dict) and
                result.get('success') is True and
                result.get('action') == 'GMAIL_REPLY_TO_THREAD'
            )
            
            if success:
                debug_print("\n✅ Email Sent Successfully!")
                debug_print("- Success: True")
                debug_print(f"- Thread ID: {thread_id}")
                debug_print(f"- Recipient: {recipient}")
                return {
                    "success": True,
                    "thread_id": thread_id,
                    "recipient": recipient
                }
            else:
                error = result.get('error', 'Failed to send email') if isinstance(result, dict) else 'Failed to send email'
                debug_print(f"\n❌ Email Sending Failed:")
                debug_print(f"- Error: {error}")
                return {
                    "success": False,
                    "error": error,
                    "thread_id": thread_id,
                    "recipient": recipient
                }
            
        except Exception as e:
            debug_print(f"\n❌ Email Sending Error:")
            debug_print(f"- Error Type: {type(e).__name__}")
            debug_print(f"- Error Message: {str(e)}")
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "thread_id": thread_id,
                "recipient": recipient
            }
        
    except Exception as e:
        debug_print(f"\n❌ Process Error:")
        debug_print(f"- Error Type: {type(e).__name__}")
        debug_print(f"- Error Message: {str(e)}")
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e),
            "thread_id": thread_id,
            "recipient": recipient
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
                    debug_print("\n⚠️ Invoice was already processed successfully - skipping history update")
                    return None
                return record
                
        # Check for similar invoices (same number, date, amount)
        for record in history:
            if (record["invoice_data"].get("invoice_number") == invoice_data.get("invoice_number") and
                record["invoice_data"].get("date") == invoice_data.get("date") and
                record["invoice_data"].get("paid_amount") == invoice_data.get("paid_amount") and
                record["invoice_data"].get("recipient") == invoice_data.get("recipient")):
                if record["result"].get("success") or record["result"].get("error") == "Invoice already processed":
                    debug_print("\n⚠️ Similar invoice was already processed successfully - skipping history update")
                    return None
                return record
                
        return None
        
    except Exception as e:
        debug_print(f"❌ Error checking payment history: {str(e)}")
        return None

async def process_payment(invoice_data: Dict) -> Dict:
    """Process payment for an invoice."""
    try:
        # Add run metadata for tracing
        run_metadata = {
            "invoice_number": invoice_data.get("invoice_number"),
            "recipient": invoice_data.get("recipient"),
            "amount": invoice_data.get("paid_amount"),
            "date": invoice_data.get("date"),
            "workflow_type": "payment_processing"
        }
        
        # Add run tags for filtering
        run_tags = [
            "invoice-agent",
            "payment-processing",
            f"amount_{invoice_data.get('paid_amount', 0)}",
            f"recipient_{invoice_data.get('recipient', '').lower().replace(' ', '_')}"
        ]
        
        # Update agent executor with run-specific metadata
        agent_executor.metadata.update(run_metadata)
        agent_executor.tags.extend(run_tags)
        
        debug_print("\n" + "="*50)
        debug_print("💳 PAYMENT PROCESSING WORKFLOW")
        debug_print("="*50)
        
        debug_print("\n📝 Invoice Data:")
        debug_print("-" * 30)
        # Serialize the data before JSON dumps
        serialized_data = serialize_firebase_data(invoice_data)
        debug_print(json.dumps(serialized_data, indent=2))
        
        # Check for required fields
        required_fields = ["invoice_number", "paid_amount", "recipient"]
        missing_fields = [f for f in required_fields if not invoice_data.get(f)]
        
        if missing_fields:
            error = {
                "success": False,
                "error": f"Missing required fields: {', '.join(missing_fields)}",
                "invoice_number": invoice_data.get("invoice_number")
            }
            debug_print("\n❌ Validation Error:")
            debug_print("-" * 30)
            debug_print(json.dumps(error, indent=2))
            return error
        
        # Check for duplicate invoice first
        debug_print("\n🔍 Checking for duplicate invoice...")
        debug_print("-" * 30)
        duplicate = is_duplicate_invoice(invoice_data, invoice_data.get("email_data", {}))
        
        if duplicate:
            # If the duplicate was successfully processed, return early without updating history
            if duplicate["result"].get("success"):
                debug_print("\n⚠️ Invoice was previously processed successfully:")
                debug_print("-" * 30)
                debug_print(json.dumps({
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
            debug_print("\n⚠️ Duplicate invoice found:")
            debug_print("-" * 30)
            debug_print(json.dumps({
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
            
        debug_print("✅ No duplicate found - proceeding with payment processing")
        
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
            debug_print("\n❌ Duplicate Invoice:")
            debug_print("-" * 30)
            debug_print(json.dumps(error, indent=2))
            return error
            
        # Check available balance
        balance = check_balance()
        if balance < invoice_data["paid_amount"]:
            error = {
                "success": False,
                "error": f"Insufficient balance: {format_currency(balance)} < {format_currency(invoice_data['paid_amount'])}",
                "invoice_number": invoice_data["invoice_number"]
            }
            debug_print("\n❌ Balance Error:")
            debug_print("-" * 30)
            debug_print(json.dumps(error, indent=2))
            return error
            
        debug_print("\n💰 Balance Check:")
        debug_print("-" * 30)
        debug_print(json.dumps({
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
            debug_print("\n🏦 Using extracted bank details for payment...")
            debug_print("-" * 30)
            debug_print(json.dumps({
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
            
            debug_print("\n💸 Sending payment with bank details...")
            debug_print("-" * 30)
            params = {
                "amount": float(invoice_data["paid_amount"]),
                "payment_destination": payment_destination,
                "memo": invoice_data.get("description", f"Invoice {invoice_data['invoice_number']}")
            }
            debug_print(json.dumps(params, indent=2))
            
            # Send payment with bank details
            result = send_payment_tool.run(tool_input=json.dumps(params))
            
            if result and "Reference:" in result:
                payment_id = result.split("Reference:")[1].strip()
                debug_print("\n✅ Payment sent successfully!")
                debug_print(f"Payment ID: {payment_id}")
                return {
                    "success": True,
                    "payment_id": payment_id,
                    "invoice_number": invoice_data["invoice_number"],
                    "payment_method": "bank_details"
                }
        
        # If bank details not complete, try finding existing payee
        debug_print("\n🔍 Searching for payee in Payman...")
        debug_print("-" * 30)
        debug_print(f"Recipient Name: {invoice_data['recipient']}")
        
        payee = search_or_create_payee(invoice_data["recipient"])
        
        if payee:
            debug_print("\n✅ Payee found in Payman:")
            debug_print("-" * 30)
            debug_print(json.dumps(payee, indent=2))
            
            # Send payment using payee ID
            debug_print("\n💸 Sending payment via Payman...")
            payment_id = send_payment(
                amount=invoice_data["paid_amount"],
                payee_id=payee["id"],
                description=invoice_data.get("description", f"Invoice {invoice_data['invoice_number']}")
            )
            
            if payment_id:
                debug_print("\n✅ Payment sent successfully!")
                debug_print(f"Payment ID: {payment_id}")
                return {
                    "success": True,
                    "payment_id": payment_id,
                    "invoice_number": invoice_data["invoice_number"],
                    "payment_method": "existing_payee"
                }
        
        # If neither bank details nor payee found, send email request
        debug_print("\n📧 Bank details and payee missing - sending email request")
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
        # Log error to LangSmith
        langsmith_client.create_run(
            name="payment_processing_error",
            error=str(e),
            inputs={"invoice_data": invoice_data},
            outputs={"error": str(e), "error_type": type(e).__name__},
            tags=["invoice-agent", "error", "payment-processing"],
            metadata={
                "error_type": type(e).__name__,
                "invoice_number": invoice_data.get("invoice_number"),
                "workflow_type": "payment_processing"
            },
            run_type="chain"
        )
        
        debug_print(f"\n❌ Payment processing error:")
        debug_print(f"Error Type: {type(e).__name__}")
        debug_print(f"Error Message: {str(e)}")
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e),
            "invoice_number": invoice_data.get("invoice_number")
        }

def main():
    """Example usage of payment agent"""
    try:
        debug_print("\n🚀 Starting Payment Processing Test")
        debug_print("=" * 50)
        
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
        debug_print("\n✅ Agent Response:")
        debug_print(json.dumps(result, indent=2))
                
    except Exception as e:
        debug_print(f"\n❌ Error: {str(e)}")

if __name__ == "__main__":
    main() 