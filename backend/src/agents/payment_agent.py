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

# Initialize OpenAI client
openai_client = ChatOpenAI(
    model="gpt-4-turbo-preview",
    temperature=0,
    api_key=openai_api_key
)

# Enable debug mode for verbose output
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# Initialize payment tools
balance_tool = BalanceTool()
search_payees_tool = SearchPayeesTool()
send_payment_tool = SendPaymentTool()
checkout_url_tool = CheckoutUrlTool()

# Initialize LangChain components for email

# Get Composio API key
composio_api_key = os.getenv("COMPOSIO_API_KEY")
if not composio_api_key:
    raise ValueError("COMPOSIO_API_KEY environment variable not found")

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
    verbose=False,
    tags=["invoice-agent", "email-communication"],
    metadata={
        "agent_type": "email_communication",
        "agent_version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "production")
    }
)

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
        result = balance_tool.run("")  # Empty string as tool_input
        
        # Extract numeric balance from string "Current balance: $X.XX"
        if not result or "Current balance:" not in result:
            return 0.0
            
        try:
            balance_str = result.split("$")[1].strip()
            balance = float(balance_str)
            return balance
        except (IndexError, ValueError) as e:
            return 0.0
            
    except Exception as e:
        traceback.print_exc()
        return 0.0

def search_or_create_payee(recipient_name: str) -> Optional[Dict]:
    """Search for a payee by name or create if not found."""
    try:
        # Search for existing payee
        result = search_payees_tool.run(json.dumps({
            "name": recipient_name,
            "type": "US_ACH"
        }))
        
        if not result:
            return None
            
        try:
            # Parse response
            if isinstance(result, str):
                payees = json.loads(result)
            else:
                payees = result
                
            if not payees:
                return None
                
            # Show found payees
            for idx, payee in enumerate(payees[:5], 1):  # Show first 5 payees
                if payee.get('contact_email'):
                    return payee
            
            # Return first matching payee
            return payees[0]
            
        except json.JSONDecodeError as e:
            return None
            
    except Exception as e:
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
        return None

def send_payment(amount: float, payee_id: str, description: str = "") -> Optional[str]:
    """Send a payment to a payee."""
    try:
        params = {
            "amount": float(amount),
            "destination_id": payee_id,
            "memo": description
        }
        
        # Convert params to JSON string for tool input
        result = send_payment_tool.run(tool_input=json.dumps(params))
        
        if not result:
            return None
            
        # Extract payment ID from response
        if "Reference:" in result:
            payment_id = result.split("Reference:")[1].strip()
            return payment_id
        
        return None
            
    except Exception as e:
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
                return
                
            if (entry["invoice_data"].get("invoice_number") == invoice_data.get("invoice_number") and
                entry["invoice_data"].get("date") == invoice_data.get("date") and
                entry["invoice_data"].get("paid_amount") == invoice_data.get("paid_amount") and
                entry["invoice_data"].get("recipient") == invoice_data.get("recipient")):
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
        history.append(entry)
        
        # Save updated history
        with open(history_file, "w") as f:
            json.dump(history, f, indent=2)
            
    except Exception as e:
        traceback.print_exc()

async def send_bank_details_request(
    thread_id: str,
    recipient: str,
    amount: float,
    payee_exists: bool = False
) -> Dict:
    """Send an email requesting bank details from the recipient using LangChain agent."""
    try:
        # Check required fields
        if not thread_id:
            return {
                "success": False,
                "error": "Missing thread_id"
            }
            
        if not recipient:
            return {
                "success": False,
                "error": "Missing recipient email"
            }
            
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
        
        # Check if email was sent successfully
        success = (
            isinstance(result, dict) and
            result.get('success') is True and
            result.get('action') == 'GMAIL_REPLY_TO_THREAD'
        )
        
        if success:
            return {
                "success": True,
                "thread_id": thread_id,
                "recipient": recipient
            }
        else:
            error = result.get('error', 'Failed to send email') if isinstance(result, dict) else 'Failed to send email'
            return {
                "success": False,
                "error": error,
                "thread_id": thread_id,
                "recipient": recipient
            }
        
    except Exception as e:
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
                    return None
                return record
                
        # Check for similar invoices (same number, date, amount)
        for record in history:
            if (record["invoice_data"].get("invoice_number") == invoice_data.get("invoice_number") and
                record["invoice_data"].get("date") == invoice_data.get("date") and
                record["invoice_data"].get("paid_amount") == invoice_data.get("paid_amount") and
                record["invoice_data"].get("recipient") == invoice_data.get("recipient")):
                if record["result"].get("success") or record["result"].get("error") == "Invoice already processed":
                    return None
                return record
                
        return None
        
    except Exception as e:
        return None

async def process_payment(payment_data: Dict) -> Dict:
    """Process a payment using the payment tools."""
    try:
        # 1. Search for payee
        search_result = search_payees_tool.run(json.dumps({
            "name": payment_data.get("recipient"),
            "type": "US_ACH"
        }))
        
        if not search_result:
            return {
                "success": False,
                "error": "Payee not found",
                "error_type": "PayeeNotFound"
            }
        
        try:
            payees = json.loads(search_result) if isinstance(search_result, str) else search_result
        except json.JSONDecodeError:
            return {
                "success": False,
                "error": "Invalid payee search response",
                "error_type": "InvalidResponse"
            }
        
        if not payees:
            return {
                "success": False,
                "error": "No matching payee found",
                "error_type": "PayeeNotFound"
            }
        
        payee = payees[0]
        payee_id = payee.get("id")
        
        if not payee_id:
            return {
                "success": False,
                "error": "Invalid payee data - missing ID",
                "error_type": "InvalidPayeeData"
            }
        
        # 2. Send payment
        payment_params = {
            "amount": float(payment_data.get("amount", 0)),
            "destination_id": payee_id,
            "memo": payment_data.get("description", "")
        }
        
        payment_result = send_payment_tool.run(json.dumps(payment_params))
        
        if not payment_result:
            return {
                "success": False,
                "error": "Payment failed - no response",
                "error_type": "PaymentFailed"
            }
        
        try:
            result = json.loads(payment_result)
        except json.JSONDecodeError:
            return {
                "success": False,
                "error": "Invalid payment response",
                "error_type": "InvalidResponse"
            }
        
        if not result.get("success"):
            return {
                "success": False,
                "error": result.get("error", "Payment failed"),
                "error_type": result.get("error_type", "PaymentFailed"),
                "details": result.get("details", {})
            }
        
        return {
            "success": True,
            "payment_id": result.get("payment_id"),
            "status": result.get("status", "completed"),
            "payment_method": result.get("payment_method", "existing_payee"),
            "external_reference": result.get("external_reference"),
            "invoice_number": payment_data.get("invoice_number"),
            "details": result.get("details", {})
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }

def main():
    """Example usage of payment agent"""
    try:
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
        return result
                
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "invoice_number": invoice_data.get("invoice_number")
        }

if __name__ == "__main__":
    main() 