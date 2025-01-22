"""Multi-agent system for processing invoice emails and payments."""

from typing import Dict, List, Optional
from pathlib import Path
import os
import json
from datetime import datetime

from src.tools.shared_tools import (
    debug_print,
    format_error,
    ensure_directory
)
from src.agents.email_agent import fetch_emails, download_attachment
from src.agents.pdf_agent import extract_text
from src.agents.payment_agent import process_payment

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
                print(f"✅ Moved processed PDF to: {dst_path}")
                
    except Exception as e:
        print(f"❌ Error saving payment history: {str(e)}")

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
    print("\n📄 Extracted Invoice Data:")
    print("=" * 50)
    
    # Basic Invoice Info
    print("\n📋 Basic Information:")
    print(f"Invoice Number: {payment_info.get('invoice_number', 'Not found')}")
    print(f"Amount: ${payment_info.get('paid_amount', 0):,.2f}")
    print(f"Date: {payment_info.get('date', 'Not found')}")
    print(f"Due Date: {payment_info.get('due_date', 'Not specified')}")
    print(f"Description: {payment_info.get('description', 'Not found')}")
    
    # Recipient Info
    print("\n👤 Recipient Information:")
    print(f"Name: {payment_info.get('recipient', 'Not found')}")
    
    # Bank Details
    bank_details = payment_info.get('bank_details', {})
    print("\n🏦 Bank Details:")
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

async def process_invoice_emails(
    query: str = "subject:invoice has:attachment newer_than:7d",
    max_results: int = 10,
    download_dir: str = "invoice data/email_attachments",
    debug: bool = False
) -> Dict:
    """Process invoice emails with PDF attachments
    
    Args:
        query (str): Gmail search query
        max_results (int): Maximum number of results
        download_dir (str): Directory to save attachments
        debug (bool): Enable debug output
        
    Returns:
        dict: Processing results
    """
    try:
        print("\n🔄 Starting Invoice Email Processing")
        print("=" * 50)
        
        if debug:
            debug_print("Process Request", {
                "query": query,
                "max_results": max_results,
                "download_dir": download_dir
            })
        
        # Ensure all required directories exist
        base_dir = ensure_directory("invoice data")
        attachments_dir = ensure_directory(os.path.join(base_dir, "email_attachments"))
        processed_dir = ensure_directory(os.path.join(base_dir, "processed"))
        
        # Create date-based directory for attachments
        today = datetime.now().strftime("%Y-%m-%d")
        download_dir = ensure_directory(os.path.join(attachments_dir, today))
        
        # print(f"\n📁 Directory Structure:")
        # print(f"Base Directory: {base_dir}")
        # print(f"Attachments Directory: {attachments_dir}")
        # print(f"Today's Directory: {download_dir}")
        # print(f"Processed Directory: {processed_dir}")
        
        # if debug:
        #     debug_print("Directory Structure", {
        #         "base_dir": base_dir,
        #         "attachments_dir": attachments_dir,
        #         "download_dir": download_dir,
        #         "processed_dir": processed_dir,
        #         "date": today
        #     })
        
        # Fetch emails with attachments
        print("\n📧 Fetching Emails...")
        fetch_result = fetch_emails(
            query=query,
            max_results=max_results,
            debug=debug
        )
        
        if not fetch_result["success"]:
            print(f"❌ Failed to fetch emails: {fetch_result.get('error', 'Unknown error')}")
            return fetch_result
            
        print(f"✉️ Found {len(fetch_result['emails'])} emails to process")
        
        processed_invoices = []
        for idx, email in enumerate(fetch_result["emails"], 1):
            print(f"\n📨 Processing Email {idx}/{len(fetch_result['emails'])}")
            print(f"Subject: {email['subject']}")
            print(f"From: {email['sender']}")
            
            # Process each attachment
            for attachment in email["attachments"]:
                if not attachment["mime_type"].lower().endswith("pdf"):
                    print(f"⏩ Skipping non-PDF attachment: {attachment['filename']}")
                    continue
                    
                print(f"\n📎 Processing attachment: {attachment['filename']}")
                
                # Download attachment
                download_result = download_attachment(
                    message_id=email["message_id"],
                    attachment_id=attachment["attachment_id"],
                    filename=attachment["filename"],
                    download_dir=download_dir,
                    debug=debug
                )
                
                if not download_result["success"]:
                    print(f"❌ Failed to download attachment: {download_result.get('error', 'Unknown error')}")
                    continue
                
                print(f"✅ Downloaded: {download_result['file_path']}")
                
                # Extract text from PDF
                print("\n📄 Extracting text from PDF...")
                extract_result = extract_text(
                    download_result["file_path"],
                    debug=debug
                )
                
                if not extract_result["success"]:
                    print(f"❌ Failed to extract text: {extract_result.get('error', 'Unknown error')}")
                    continue
                
                print("✅ Text extraction successful")
                
                # Use extracted payment information
                payment_info = extract_result.get("payment_info", {})
                if not payment_info:
                    print("❌ No payment information found in PDF")
                    continue
                
                # Print extracted data in readable format
                print_extracted_data(payment_info, debug=debug)
                
                # Create invoice data from extracted info
                invoice_data = {
                    "invoice_number": payment_info.get("invoice_number") or f"INV-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                    "paid_amount": payment_info.get("paid_amount"),
                    "recipient": payment_info.get("recipient"),
                    "date": email["timestamp"],
                    "due_date": payment_info.get("due_date"),
                    "description": payment_info.get("description"),
                    "bank_details": payment_info.get("bank_details", {}),
                    "email_data": {
                        "thread_id": email["thread_id"],
                        "message_id": email["message_id"],
                        "sender": email["sender"],
                        "subject": email["subject"]
                    }
                }
                
                print("\n💳 Processing payment...")
                print(f"Invoice: {invoice_data['invoice_number']}")
                print(f"Amount: {invoice_data['paid_amount']}")
                print(f"Recipient: {invoice_data['recipient']}")
                
                if debug:
                    debug_print("Payment Request", {
                        "invoice_data": invoice_data
                    })

                # Process payment asynchronously
                payment_result = await process_payment(invoice_data)

                if debug:
                    debug_print("Payment Response", payment_result)
                
                # Add success flag if not present
                if "success" not in payment_result:
                    payment_result["success"] = "error" not in payment_result
                
                if payment_result["success"]:
                    print("✅ Payment processed successfully")
                else:
                    print(f"❌ Payment failed: {payment_result.get('error', 'Unknown error')}")
                
                # Create payment history entry
                payment_history = {
                    "email_data": invoice_data["email_data"],
                    "invoice_data": invoice_data,
                    "result": {
                        "success": payment_result["success"],
                        "error": payment_result.get("error"),
                        "email_sent": payment_result.get("email_sent", False),
                        "payment_id": payment_result.get("payment_id")
                    }
                }
                
                # Save payment history
                print("\n💾 Saving payment history...")
                save_payment_history(payment_history)
                print("✅ History saved")
                
                if not payment_result["success"]:
                    continue
                
                processed_invoices.append({
                    "email": {
                        "subject": email["subject"],
                        "sender": email["sender"],
                        "timestamp": email["timestamp"]
                    },
                    "attachment": {
                        "filename": attachment["filename"],
                        "file_path": download_result["file_path"],
                        "size": download_result["size"]
                    },
                    "invoice": invoice_data,
                    "payment": payment_result
                })
        
        response = {
            "success": True,
            "total_processed": len(processed_invoices),
            "invoices": processed_invoices
        }
        
        print(f"\n🎉 Processing Complete!")
        print(f"✅ Successfully processed {len(processed_invoices)} invoices")
        
        if debug:
            debug_print("Process Complete", {
                "total_processed": response["total_processed"]
            })
            
        return response
        
    except Exception as e:
        error = format_error(e)
        print(f"\n❌ Processing Error: {str(e)}")
        if debug:
            debug_print("Process Error", error)
        return {"success": False, "error": str(e)}

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
        
        result = process_invoice_emails(
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