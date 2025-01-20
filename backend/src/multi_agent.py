"""Multi-agent system for processing invoice emails and payments."""

from typing import Dict, List, Optional
from pathlib import Path
import os

from tools.shared_tools import (
    debug_print,
    format_error,
    ensure_directory
)
from agents.email_agent import fetch_emails, download_attachment
from agents.pdf_agent import extract_text
from agents.payment_agent import validate_invoice, process_payment

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
                    "amount": 1500.00,  # Would be extracted from PDF
                    "recipient": "Slingshot AI",  # Would be extracted from PDF
                    "date": email["timestamp"],
                    "due_date": "2024-02-17",  # Would be extracted from PDF
                    "description": extract_result["pages"][0]["text"][:100]
                }
                
                # Validate invoice data
                validation_result = validate_invoice(
                    invoice_data,
                    debug=debug
                )
                
                if not validation_result["success"]:
                    continue
                
                # Process payment
                payment_result = process_payment(
                    validation_result["validated_data"],
                    debug=debug
                )
                
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
                print(f"  Amount: {invoice['invoice']['amount']}")
                print(f"  Recipient: {invoice['invoice']['recipient']}")
                print(f"  Due Date: {invoice['invoice'].get('due_date', 'Not specified')}")
                
                print("\n💳 Payment Status:")
                print(f"  ID: {invoice['payment']['payment_id']}")
                print(f"  Status: {invoice['payment']['status']}")
                print(f"  Method: {invoice['payment']['payment_method']}")
                print("=" * 50)
        else:
            print(f"\n❌ Error: {result['error']}")
                
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")

if __name__ == "__main__":
    main() 