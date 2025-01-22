"""Multi-agent system for processing invoice emails and payments."""

from typing import Dict, List, Optional, Literal, TypedDict, Sequence, Union, cast, Any
from pathlib import Path
import os
import json
from datetime import datetime
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolExecutor
from langchain_core.messages import HumanMessage, BaseMessage, AIMessage
from langchain.agents import create_react_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from src.tools.shared_tools import (
    debug_print,
    format_error,
    ensure_directory
)
from src.agents.email_agent import process_emails, get_gmail_tools
from src.agents.pdf_agent import extract_invoice_data, tools as pdf_tools
from src.agents.payment_agent import process_payment, tools as payment_tools
from src.openai_client import get_openai_client

# Initialize LLM and tools
llm = get_openai_client()
gmail_tools = get_gmail_tools()

# Define state type
class AgentState(TypedDict):
    messages: Sequence[BaseMessage]
    data: Dict[str, Any]
    next: Optional[str]

# Create specialized agent prompts
email_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are the email processing expert in a team of AI agents.
Your task is to find and process invoice emails efficiently.
Use Gmail tools to search, fetch, and handle attachments.
When done, indicate if PDF extraction is needed or if there were any errors.

Tools available: {tools}
Tool names: {tool_names}"""),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

pdf_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are the PDF extraction expert in a team of AI agents.
Your task is to extract structured data from invoice PDFs accurately.
Use PDF tools to parse and validate invoice information.
When done, indicate if payment processing is needed or if there were any errors.

Tools available: {tools}
Tool names: {tool_names}"""),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

payment_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are the payment processing expert in a team of AI agents.
Your task is to process invoice payments safely and accurately.
Use payment tools to validate and execute payments.
When done, indicate FINAL ANSWER with the payment result or any errors.

Tools available: {tools}
Tool names: {tool_names}"""),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

# Create specialized agents
def create_agent(llm, tools, prompt):
    """Create a React agent with proper tool handling."""
    tool_names = [tool.name for tool in tools]
    tool_strings = [f"{tool.name}: {tool.description}" for tool in tools]
    
    # Create agent with tool information
    return create_react_agent(
        llm=llm,
        tools=tools,
        prompt=prompt.partial(
            tools="\n".join(tool_strings),
            tool_names=", ".join(tool_names)
        )
    )

# Initialize agents
email_agent = create_agent(llm, gmail_tools, email_prompt)
pdf_agent = create_agent(llm, pdf_tools, pdf_prompt)
payment_agent = create_agent(llm, payment_tools, payment_prompt)

def get_next_node(state: AgentState) -> Dict[str, float]:
    """Get next node probabilities based on state."""
    try:
        last_message = state["messages"][-1]
        content = last_message.content.lower()
        
        # Initialize all probabilities to 0
        next_nodes = {
            "email_processor": 0.0,
            "pdf_processor": 0.0,
            "payment_processor": 0.0,
            "__end__": 0.0
        }
        
        # Set probability based on message content
        if "error" in content:
            next_nodes["__end__"] = 1.0
        elif "pdf" in content:
            next_nodes["pdf_processor"] = 1.0
        elif "payment" in content:
            next_nodes["payment_processor"] = 1.0
        elif "final" in content:
            next_nodes["__end__"] = 1.0
        else:
            next_node = state.get("next", "__end__")
            next_nodes[next_node] = 1.0
            
        return next_nodes
        
    except Exception as e:
        print(f"Error in get_next_node: {str(e)}")
        return {"__end__": 1.0}

async def email_node(state: AgentState) -> AgentState:
    """Process invoice emails."""
    try:
        print("\n[EMAIL] 📧 Processing emails...")
        email_result = await process_emails()
        
        if not email_result["success"]:
            return {
                "messages": [*state["messages"], AIMessage(content=f"Email processing failed: {email_result['error']}")],
                "data": state["data"],
                "next": "__end__"
            }
            
        emails = email_result["data"]
        if not emails:
            return {
                "messages": [*state["messages"], AIMessage(content="No invoice emails found")],
                "data": state["data"],
                "next": "__end__"
            }
            
        # Process emails to extract essential information
        processed_emails = []
        for msg in emails:
            processed_msg = {
                'id': msg.get('messageId'),
                'thread_id': msg.get('threadId'),
                'subject': msg.get('subject'),
                'sender': msg.get('sender'),
                'attachments': [
                    {
                        'filename': att.get('filename'),
                        'id': att.get('attachmentId')
                    }
                    for att in msg.get('attachmentList', [])
                ]
            }
            processed_emails.append(processed_msg)
            
        return {
            "messages": [
                *state["messages"],
                AIMessage(content=f"Found {len(processed_emails)} invoice emails with attachments. Moving to PDF processing.")
            ],
            "data": {**state["data"], "emails": processed_emails},
            "next": "pdf_processor"
        }
        
    except Exception as e:
        error_msg = f"Error in email processing: {str(e)}"
        print(f"[EMAIL] ❌ {error_msg}")
        return {
            "messages": [*state["messages"], AIMessage(content=error_msg)],
            "data": state["data"],
            "next": "__end__"
        }

async def pdf_node(state: AgentState) -> AgentState:
    """Process PDF attachments."""
    try:
        print("\n[PDF] 📄 Processing attachments...")
        emails = state["data"].get("emails", [])
        if not emails:
            return {
                "messages": [*state["messages"], AIMessage(content="No emails to process")],
                "data": state["data"],
                "next": "__end__"
            }
            
        pdf_results = []
        for email in emails:
            for attachment in email.get("attachments", []):
                result = await extract_invoice_data(attachment["id"])
                if result["success"]:
                    pdf_results.append({
                        "email_id": email["id"],
                        "attachment_id": attachment["id"],
                        "data": result["data"]
                    })
                    
        if not pdf_results:
            return {
                "messages": [*state["messages"], AIMessage(content="No invoice data extracted from PDFs")],
                "data": state["data"],
                "next": "__end__"
            }
            
        return {
            "messages": [
                *state["messages"],
                AIMessage(content=f"Extracted data from {len(pdf_results)} PDFs. Moving to payment processing.")
            ],
            "data": {**state["data"], "pdf_results": pdf_results},
            "next": "payment_processor"
        }
        
    except Exception as e:
        error_msg = f"Error in PDF processing: {str(e)}"
        print(f"[PDF] ❌ {error_msg}")
        return {
            "messages": [*state["messages"], AIMessage(content=error_msg)],
            "data": state["data"],
            "next": "__end__"
        }

async def payment_node(state: AgentState) -> AgentState:
    """Process payments."""
    try:
        print("\n[PAYMENT] 💸 Processing payments...")
        pdf_results = state["data"].get("pdf_results", [])
        if not pdf_results:
            return {
                "messages": [*state["messages"], AIMessage(content="No invoice data to process payments")],
                "data": state["data"],
                "next": "__end__"
            }
            
        payment_results = []
        for result in pdf_results:
            payment = await process_payment(result["data"])
            if payment["success"]:
                payment_results.append({
                    "email_id": result["email_id"],
                    "attachment_id": result["attachment_id"],
                    "payment": payment["data"]
                })
                
        if not payment_results:
            return {
                "messages": [*state["messages"], AIMessage(content="No payments processed")],
                "data": state["data"],
                "next": "__end__"
            }
            
        return {
            "messages": [
                *state["messages"],
                AIMessage(content=f"Successfully processed {len(payment_results)} payments. FINAL ANSWER: Workflow complete.")
            ],
            "data": {**state["data"], "payment_results": payment_results},
            "next": "__end__"
        }
        
    except Exception as e:
        error_msg = f"Error in payment processing: {str(e)}"
        print(f"[PAYMENT] ❌ {error_msg}")
        return {
            "messages": [*state["messages"], AIMessage(content=error_msg)],
            "data": state["data"],
            "next": "__end__"
        }

async def process_invoices(query: str = "subject:invoice has:attachment newer_than:7d") -> Dict:
    """Process invoices using multi-agent workflow."""
    try:
        print("\n[SYSTEM] 🚀 Starting invoice processing workflow...")
        
        # Process emails
        print("\n[EMAIL] 📧 Processing emails...")
        email_result = await process_emails(query)
        
        if not email_result["success"]:
            return {
                "success": False,
                "messages": [f"Email processing failed: {email_result['error']}"],
                "error": email_result["error"]
            }
            
        emails = email_result["data"]
        if not emails:
            return {
                "success": True,
                "messages": ["No invoice emails found"],
                "data": {}
            }
            
        messages = [f"Found {len(emails)} invoice emails with attachments"]
        data = {"emails": emails}
        
        # Process PDFs
        print("\n[PDF] 📄 Processing PDFs...")
        pdf_results = []
        
        for email in emails:
            for attachment in email.get("attachments", []):
                result = await extract_invoice_data(attachment["id"])
                if result["success"]:
                    pdf_results.append({
                        "email_id": email["id"],
                        "attachment_id": attachment["id"],
                        "data": result["data"]
                    })
                    
        if not pdf_results:
            return {
                "success": True,
                "messages": messages + ["No invoice data extracted from PDFs"],
                "data": data
            }
            
        messages.append(f"Extracted data from {len(pdf_results)} PDFs")
        data["pdf_results"] = pdf_results
        
        # Process payments
        print("\n[PAYMENT] 💸 Processing payments...")
        payment_results = []
        
        for result in pdf_results:
            payment = await process_payment(result["data"])
            if payment["success"]:
                payment_results.append({
                    "email_id": result["email_id"],
                    "attachment_id": result["attachment_id"],
                    "payment": payment["data"]
                })
                
        if not payment_results:
            return {
                "success": True,
                "messages": messages + ["No payments processed"],
                "data": data
            }
            
        messages.append(f"Successfully processed {len(payment_results)} payments")
        data["payment_results"] = payment_results
        
        print("\n[SYSTEM] ✅ Workflow complete")
        return {
            "success": True,
            "messages": messages,
            "data": data
        }
        
    except Exception as e:
        error_msg = str(e)
        print(f"\n[SYSTEM] ❌ Workflow error: {error_msg}")
        return {
            "success": False,
            "messages": [f"Error: {error_msg}"],
            "error": error_msg
        }

def save_payment_history(payment_data: Dict) -> None:
    """Save payment data to JSON file.
    
    Args:
        payment_data (Dict): Payment data to save
    """
    try:
        history_file = os.path.join("invoice data", "payment_history.json")
        
        # Load existing history
        existing_history = []
        if os.path.exists(history_file):
            try:
                with open(history_file, 'r') as f:
                    existing_history = json.load(f)
            except json.JSONDecodeError:
                existing_history = []
        
        # Check for duplicates based on message_id and thread_id
        email = payment_data.get("email", {})
        email_data = payment_data.get("email_data", {})
        message_id = email_data.get("message_id") or email.get("message_id")
        thread_id = email_data.get("thread_id") or email.get("thread_id")
        
        # Remove any existing entries with the same message_id or thread_id
        existing_history = [
            record for record in existing_history 
            if not (
                (record.get("email_data", {}).get("message_id") == message_id) or
                (record.get("email_data", {}).get("thread_id") == thread_id) or
                (record.get("email", {}).get("message_id") == message_id) or
                (record.get("email", {}).get("thread_id") == thread_id)
            )
        ]
        
        # Create unified record structure with error categorization
        unified_record = {
            "timestamp": datetime.now().isoformat(),
            "email_data": {
                "thread_id": thread_id,
                "message_id": message_id,
                "sender": email_data.get("sender") or email.get("sender"),
                "subject": email_data.get("subject") or email.get("subject")
            },
            "invoice_data": payment_data.get("invoice_data") or payment_data.get("invoice", {}),
            "result": {
                "success": (payment_data.get("result", {}).get("success", False) or 
                           payment_data.get("payment", {}).get("success", False)),
                "error": (payment_data.get("result", {}).get("error") or 
                         payment_data.get("payment", {}).get("error")),
                "error_type": categorize_error(payment_data),
                "email_sent": payment_data.get("result", {}).get("email_sent", False),
                "payment_id": (payment_data.get("result", {}).get("payment_id") or 
                             payment_data.get("payment", {}).get("reference"))
            }
        }
        
        # Add new record
        existing_history.append(unified_record)
        
        # Save updated history with pretty formatting
        with open(history_file, 'w') as f:
            json.dump(existing_history, f, indent=2)
            
        # Move processed PDF to processed directory if available
        if "attachment" in payment_data:
            src_path = payment_data["attachment"].get("file_path")
            if src_path and os.path.exists(src_path):
                filename = os.path.basename(src_path)
                dst_path = os.path.join("invoice data", "processed", filename)
                os.rename(src_path, dst_path)
                print(f"[SYSTEM] ✅ Processed PDF moved to: {dst_path}")
                
    except Exception as e:
        print(f"[SYSTEM] ❌ Error saving payment history: {str(e)}")

def categorize_error(payment_data: Dict) -> str:
    """Categorize the type of error in payment processing.
    
    Args:
        payment_data (Dict): Payment processing data
        
    Returns:
        str: Error category
    """
    error = (payment_data.get("result", {}).get("error") or 
             payment_data.get("payment", {}).get("error", ""))
    
    if not error:
        return "none"
    
    error = error.lower()
    if "insufficient balance" in error:
        return "insufficient_funds"
    elif "failed to find or create payee" in error:
        return "payee_creation_failed"
    elif "missing" in error or "required" in error:
        return "validation_error"
    else:
        return "other"

def print_extracted_data(payment_info: Dict, debug: bool = False) -> None:
    """Print extracted payment information in a readable format.
    
    Args:
        payment_info (Dict): Extracted payment information
        debug (bool): Enable debug output
    """
    print("\n[INVOICE] �� Extracted Data:")
    print("=" * 50)
    
    print("\n[INVOICE] 📋 Basic Information:")
    print(f"  • Invoice Number: {payment_info.get('invoice_number', 'Not found')}")
    print(f"  • Amount: ${payment_info.get('paid_amount', 0):,.2f}")
    print(f"  • Date: {payment_info.get('date', 'Not found')}")
    print(f"  • Due Date: {payment_info.get('due_date', 'Not specified')}")
    print(f"  • Description: {payment_info.get('description', 'Not found')}")
    
    print("\n[INVOICE] 👤 Recipient Information:")
    print(f"  • Name: {payment_info.get('recipient_name', 'Not found')}")
    print(f"  • Email: {payment_info.get('recipient_email', 'Not found')}")
    print(f"  • Phone: {payment_info.get('recipient_phone', 'Not found')}")
    print(f"  • Address: {payment_info.get('recipient_address', 'Not found')}")
    
    # Recipient Info
    print("\n🏦 Bank Details:")
    bank_details = payment_info.get('bank_details', {})
    print(f"Bank Name: {bank_details.get('bank_name', 'Not found')}")
    print(f"Account Type: {bank_details.get('type', 'Not found')}")
    print(f"Account Holder: {bank_details.get('account_holder_name', 'Not found')}")
    print(f"Account Number: {bank_details.get('account_number', 'Not found')}")
    if bank_details.get('routing_number'):
        print(f"Routing Number: {bank_details.get('routing_number')}")
    
    # Customer Info
    customer = payment_info.get('customer', {})
    print("\n🏢 Customer Information:")
    print(f"Name: {customer.get('name', 'Not found')}")
    print(f"Email: {customer.get('email', 'Not found')}")
    print(f"Phone: {customer.get('phone', 'Not found')}")
    print(f"Address: {customer.get('address', 'Not found')}")
    
    # Payee Details
    payee = payment_info.get('payee_details', {})
    print("\n💼 Payee Details:")
    print(f"Type: {payee.get('contact_type', 'Not found')}")
    print(f"Email: {payee.get('email', 'Not found')}")
    print(f"Phone: {payee.get('phone', 'Not found')}")
    print(f"Address: {payee.get('address', 'Not found')}")
    if payee.get('tax_id'):
        print(f"Tax ID: {payee.get('tax_id')}")
    
    # Validation Issues
    validation_issues = []
    if not bank_details.get('account_type'):
        validation_issues.append("Missing account type")
    if not payee.get('email') and not payee.get('phone'):
        validation_issues.append("Missing contact method")
    if not payment_info.get('due_date'):
        validation_issues.append("Missing due date")
    
    if validation_issues:
        print("\n⚠️ Validation Issues:")
        for issue in validation_issues:
            print(f"- {issue}")
    
    print("\n" + "=" * 50)

def main():
    """Example usage of invoice processing"""
    try:
        print("\n🚀 Starting Invoice Processing Test")
        print("=" * 50)
        
        # Process invoice emails with detailed query
        query = "subject:invoice has:attachment newer_than:7d"
        max_results = 5
        
        print(f"\n1️⃣ Processing Invoice Emails...")
        print(f"Query: {query}")
        print(f"Max Results: {max_results}")
        
        result = process_invoices(
            query=query,
            max_results=max_results,
            debug=True
        )
        
        if result["success"]:
            print(f"\n✅ Successfully processed {result['total_processed']} invoices")
            
            # Show details for each processed invoice
            for invoice in result["invoices"]:
                print("\n📧 Email Details:")
                print(f"  Subject: {invoice['email']['subject']}")
                print(f"  From: {invoice['email']['sender']}")
                print(f"  Date: {invoice['email']['timestamp']}")
                
                print("\n📎 Attachment:")
                print(f"  Filename: {invoice['attachment']['filename']}")
                print(f"  Size: {invoice['attachment']['size']} bytes")
                
                print("\n💰 Invoice Data:")
                print(f"  Number: {invoice['invoice']['invoice_number']}")
                print(f"  Amount: {invoice['invoice']['paid_amount']}")
                print(f"  Recipient: {invoice['invoice']['recipient']}")
                print(f"  Due Date: {invoice['invoice'].get('due_date', 'Not specified')}")
                
                print("\n💳 Payment Status:")
                if invoice['payment']['success']:
                    print(f"  Amount: {invoice['payment']['amount']}")
                    print(f"  Reference: {invoice['payment']['output']}")
                else:
                    print(f"  Error: {invoice['payment']['error']}")
                print("=" * 50)
        else:
            print(f"\n❌ Error: {result['error']}")
                
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")

if __name__ == "__main__":
    main() 