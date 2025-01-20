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
    history_dir = ensure_directory("payment_history")
    history_file = os.path.join(history_dir, "payment_history.json")
    
    # Load existing history
    existing_history = []
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r') as f:
                existing_history = json.load(f)
        except json.JSONDecodeError:
            existing_history = []
    
    # Add timestamp to payment data
    payment_data["timestamp"] = datetime.now().isoformat()
    
    # Add new payment to history
    existing_history.append(payment_data)
    
    # Save updated history
    with open(history_file, 'w') as f:
        json.dump(existing_history, f, indent=2)

def process_invoice_emails(
    query: str = "subject:invoice has:attachment newer_than:7d",
    max_results: int = 10,
    download_dir: str = "downloads",
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
                "max_results": max_results
            })
        
        # Ensure download directory exists
        download_dir = ensure_directory(download_dir)
        
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
                
                # Extract invoice data (mock implementation)
                invoice_data = {
                    "invoice_number": "INV-2024-001",  # Would be extracted from PDF
                    "paid_amount": 2500.00,  # Would be extracted from PDF
                    "recipient": "Slingshot AI",  # Would be extracted from PDF
                    "date": email["timestamp"],
                    "due_date": "2024-02-17",  # Would be extracted from PDF
                    "description": extract_result["pages"][0]["text"][:100]
                }
                
                # Process payment
                payment_result = process_payment(
                    invoice_data,
                    debug=debug
                )
                
                # Add success flag if not present
                if "success" not in payment_result:
                    payment_result["success"] = "error" not in payment_result
                
                # Create payment history entry
                payment_history = {
                    "email": {
                        "subject": email["subject"],
                        "sender": email["sender"],
                        "timestamp": email["timestamp"]
                    },
                    "invoice": invoice_data,
                    "payment": {
                        "success": payment_result["success"],
                        "amount": invoice_data["paid_amount"],
                        "recipient": invoice_data["recipient"],
                        "reference": payment_result.get("output", None),
                        "error": payment_result.get("error", None) if not payment_result["success"] else None
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