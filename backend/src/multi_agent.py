"""Multi-agent system for processing invoice emails and payments."""

from typing import Dict, List, Optional
from pathlib import Path
import os
import json
from datetime import datetime

from tools.shared_tools import (
    debug_print,
    format_error,
    ensure_directory
)
from agents.email_agent import fetch_emails, download_attachment
from agents.pdf_agent import extract_text
from agents.payment_agent import process_payment

def save_payment_history(payment_data: Dict) -> None:
    """Save payment data to JSON file.
    
    Args:
        payment_data (Dict): Payment data to save
    """
    history_dir = Path("invoice data")
    history_dir.mkdir(exist_ok=True)
    history_file = history_dir / "payment_history.json"
    
    # Load existing history
    existing_history = []
    if history_file.exists():
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
    
    # Create unified record structure
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
            "email_sent": payment_data.get("result", {}).get("email_sent", False),
            "payment_id": (payment_data.get("result", {}).get("payment_id") or 
                         payment_data.get("payment", {}).get("reference"))
        }
    }
    
    # Add new record
    existing_history.append(unified_record)
    
    # Save updated history
    with open(history_file, 'w') as f:
        json.dump(existing_history, f, indent=2)

def process_invoice_emails(
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
        if debug:
            debug_print("Process Request", {
                "query": query,
                "max_results": max_results,
                "download_dir": download_dir
            })
        
        # Ensure base invoice data directory exists
        invoice_data_dir = ensure_directory("invoice data")
        
        # Ensure email attachments directory exists and create date-based subdirectory
        base_dir = ensure_directory(download_dir)
        today = datetime.now().strftime("%Y-%m-%d")
        download_dir = os.path.join(base_dir, today)
        download_dir = ensure_directory(download_dir)
        
        if debug:
            debug_print("Download Directory", {
                "invoice_data_dir": invoice_data_dir,
                "attachments_dir": base_dir,
                "date_dir": today,
                "full_path": download_dir
            })
        
        # Fetch emails with attachments
        fetch_result = fetch_emails(
            query=query,
            max_results=max_results,
            debug=debug
        )
        
        if not fetch_result["success"]:
            return fetch_result
        
        processed_invoices = []
        for email in fetch_result["emails"]:
            # Process each attachment
            for attachment in email["attachments"]:
                if not attachment["mime_type"].lower().endswith("pdf"):
                    continue
                    
                # Download attachment
                download_result = download_attachment(
                    message_id=email["message_id"],
                    attachment_id=attachment["attachment_id"],
                    filename=attachment["filename"],
                    download_dir=download_dir,
                    debug=debug
                )
                
                if not download_result["success"]:
                    continue
                
                # Extract text from PDF
                extract_result = extract_text(
                    download_result["file_path"],
                    debug=debug
                )
                
                if not extract_result["success"]:
                    continue
                
                # Use extracted payment information
                payment_info = extract_result.get("payment_info", {})
                if not payment_info:
                    continue
                
                # Create invoice data from extracted info
                invoice_data = {
                    "invoice_number": payment_info.get("invoice_number") or f"INV-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                    "paid_amount": payment_info.get("paid_amount"),
                    "recipient": payment_info.get("recipient"),
                    "date": email["timestamp"],
                    "due_date": payment_info.get("due_date"),
                    "description": payment_info.get("description")
                }
                
                # Process payment
                email_data = {
                    "thread_id": email["thread_id"],
                    "message_id": email["message_id"],
                    "sender": email["sender"],
                    "subject": email["subject"]
                }

                if debug:
                    debug_print("Payment Request", {
                        "invoice_data": invoice_data,
                        "email_data": email_data
                    })

                payment_result = process_payment(invoice_data)

                if debug:
                    debug_print("Payment Response", payment_result)
                
                # Add success flag if not present
                if "success" not in payment_result:
                    payment_result["success"] = "error" not in payment_result
                
                # Create payment history entry
                payment_history = {
                    "email_data": email_data,
                    "invoice_data": invoice_data,
                    "result": {
                        "success": payment_result["success"],
                        "error": payment_result.get("error"),
                        "email_sent": False,
                        "payment_id": payment_result.get("payment_id")
                    }
                }
                
                # Save payment history
                save_payment_history(payment_history)
                
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
        
        if debug:
            debug_print("Process Complete", {
                "total_processed": response["total_processed"]
            })
            
        return response
        
    except Exception as e:
        error = format_error(e)
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