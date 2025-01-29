"""Script to test invoice scanning and payment workflow."""

import os
import sys
import json
import requests
from datetime import datetime, timedelta
import jwt
from dotenv import load_dotenv
from typing import Dict, List, Optional

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

# API Settings
API_URL = "http://localhost:8000"
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key")
ALGORITHM = "HS256"

def generate_test_jwt(customer_id: str) -> str:
    """Generate a test JWT token for API testing."""
    payload = {
        "customer_id": customer_id,
        "exp": datetime.utcnow() + timedelta(days=1)
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)
    return token

def print_invoice_details(invoice: Dict, index: Optional[int] = None) -> None:
    """Print invoice details in a readable format."""
    data = invoice.get("data", {})
    print("\n" + "=" * 50)
    if index is not None:
        print(f"📄 Invoice {index + 1}:")
    else:
        print(f"📄 Invoice Details:")
    print(f"  ID: {invoice.get('id')}")
    print(f"  Status: {invoice.get('status', 'unknown')}")
    print(f"  Created At: {invoice.get('created_at')}")
    print(f"  Customer ID: {invoice.get('customer_id')}")
    if data:
        print("\n  Invoice Data:")
        print(f"    Number: {data.get('invoice_number')}")
        print(f"    Amount: {data.get('currency', 'USD')} {data.get('amount')}")
        print(f"    Recipient: {data.get('recipient')}")
        print(f"    Due Date: {data.get('due_date')}")
        print(f"    Description: {data.get('description')}")
        print(f"    File: {data.get('file_name')}")
    else:
        print(f"  File URL: {invoice.get('file_url')}")
    print("=" * 50)

def scan_invoices(customer_id: str) -> List[Dict]:
    """Scan and retrieve invoices for a customer."""
    try:
        print("\n🔍 Scanning Invoices")
        print("=" * 50)
        
        # Generate JWT token
        token = generate_test_jwt(customer_id)
        
        # API endpoint
        url = f"{API_URL}/scan-inbox"
        
        # Request headers
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # Request body
        data = {
            "gmail_auth_token": "test_token",
            "query": "subject:invoice",
            "max_results": 10
        }
        
        print(f"👤 Customer ID: {customer_id}")
        print(f"🔎 Fetching invoices...")
        
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        
        result = response.json()
        
        # Print all invoices
        all_invoices = []
        
        if result.get("existing_invoices"):
            print("\n📂 Existing Invoices:")
            for i, invoice in enumerate(result["existing_invoices"]):
                print_invoice_details(invoice, i)
                all_invoices.append(invoice)
                
        if result.get("new_invoices"):
            print("\n📥 New Invoices:")
            start_idx = len(all_invoices)
            for i, invoice in enumerate(result["new_invoices"], start_idx):
                print_invoice_details(invoice, i)
                all_invoices.append(invoice)
        
        # Print summary
        summary = result.get("summary", {})
        print("\n📊 Summary:")
        print(f"  Total Invoices: {summary.get('total_invoices', 0)}")
        print(f"  - Existing: {summary.get('existing_count', 0)}")
        print(f"  - New: {summary.get('new_count', 0)}")
        print(f"  Total Amount: USD {summary.get('total_amount', 0):,.2f}")
        
        return all_invoices
        
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Error scanning invoices: {str(e)}")
        if hasattr(e.response, 'text'):
            print(f"Response: {e.response.text}")
        return []

def pay_invoice(customer_id: str, invoice_id: str) -> bool:
    """Pay a specific invoice."""
    try:
        print("\n💳 Processing Payment")
        print("=" * 50)
        
        # Generate JWT token
        token = generate_test_jwt(customer_id)
        
        # API endpoint
        url = f"{API_URL}/pay-invoice/{invoice_id}"
        
        # Request headers
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        print(f"👤 Customer ID: {customer_id}")
        print(f"📄 Invoice ID: {invoice_id}")
        print(f"💸 Processing payment...")
        
        response = requests.post(url, headers=headers)
        response.raise_for_status()
        
        result = response.json()
        
        if result.get("success"):
            print("\n✅ Payment Successful!")
            print(f"Payment ID: {result.get('payment_details', {}).get('payment_id')}")
            print(f"Method: {result.get('payment_details', {}).get('payment_method')}")
            print(f"Timestamp: {result.get('payment_details', {}).get('timestamp')}")
            return True
        else:
            print(f"\n❌ Payment Failed: {result.get('message', 'Unknown error')}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Error processing payment: {str(e)}")
        if hasattr(e.response, 'text'):
            print(f"Response: {e.response.text}")
        return False

def main():
    """Main function to test the workflow."""
    try:
        print("\n🚀 Starting Payment Workflow Test")
        print("=" * 50)
        
        # Test customer ID
        customer_id = "test_customer_1"
        
        # First scan for invoices
        invoices = scan_invoices(customer_id)
        
        if not invoices:
            print("\n❌ No invoices found!")
            return
            
        # Let user select an invoice
        while True:
            print("\n🔍 Select an invoice to pay (1-{}) or 'q' to quit: ".format(len(invoices)))
            choice = input("Enter choice: ").strip().lower()
            
            if choice == 'q':
                print("\n👋 Exiting...")
                break
                
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(invoices):
                    selected_invoice = invoices[idx]
                    print("\n📄 Selected Invoice:")
                    print_invoice_details(selected_invoice)
                    
                    confirm = input("\n💳 Proceed with payment? (y/n): ").strip().lower()
                    if confirm == 'y':
                        success = pay_invoice(customer_id, selected_invoice["id"])
                        if success:
                            print("\n✅ Payment workflow completed successfully!")
                        else:
                            print("\n❌ Payment workflow failed!")
                        break
                    else:
                        print("\n⏭️ Payment cancelled")
                else:
                    print("\n❌ Invalid invoice number!")
            except ValueError:
                print("\n❌ Invalid input! Please enter a number or 'q'")
                
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")

if __name__ == "__main__":
    main() 