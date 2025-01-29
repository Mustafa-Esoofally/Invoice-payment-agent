"""Script for generating test invoice data in Firebase."""

import os
import sys
from datetime import datetime
from typing import Dict, List
from dotenv import load_dotenv
from firebase_admin import initialize_app, credentials, firestore, get_app

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

# Initialize Firebase
try:
    firebase_app = get_app()
except ValueError:
    cred = credentials.Certificate("byrdeai-firebase-adminsdk-fbsvc-a168a9a31d.json")
    firebase_app = initialize_app(cred)

db = firestore.client()

def generate_test_data() -> List[Dict]:
    """Generate simplified test data for 5 invoices."""
    return [
        {
            "file_url": "https://storage.googleapis.com/byrdeai/invoices/tech_solutions_001.pdf",
            "status": "pending"
        },
        {
            "file_url": "https://storage.googleapis.com/byrdeai/invoices/digital_dynamics_002.pdf",
            "status": "pending"
        },
        {
            "file_url": "https://storage.googleapis.com/byrdeai/invoices/new_tech_003.pdf",
            "status": "pending"
        },
        {
            "file_url": "https://storage.googleapis.com/byrdeai/invoices/innovate_systems_004.pdf",
            "status": "pending"
        },
        {
            "file_url": "https://storage.googleapis.com/byrdeai/invoices/global_tech_005.pdf",
            "status": "pending"
        }
    ]

def store_test_invoices(customer_id: str) -> None:
    """Store test invoices in Firebase for a given customer."""
    print(f"\n💾 Storing test invoices for customer: {customer_id}")
    print("=" * 50)
    
    test_data = generate_test_data()
    
    for i, invoice in enumerate(test_data, 1):
        # Create the document data with minimal fields
        invoice_data = {
            "customer_id": customer_id,
            "file_url": invoice["file_url"],
            "status": invoice["status"]
        }
        
        # Store in Firebase
        invoice_ref = db.collection("invoices").document()
        invoice_ref.set(invoice_data)
        
        # Print details
        print(f"\n📄 Stored Invoice {i}:")
        print(f"  ID: {invoice_ref.id}")
        print(f"  Customer: {customer_id}")
        print(f"  Status: {invoice['status']}")
        print(f"  File URL: {invoice['file_url']}")
        print("-" * 50)
    
    print(f"\n📊 Summary for {customer_id}:")
    print(f"  Total Invoices: {len(test_data)}")
    print("=" * 50)

def main():
    """Main function to generate test data."""
    print("\n🚀 Starting Test Data Generation")
    print("=" * 50)
    
    # Store invoices for both test customers
    customers = ["test_customer_1", "test_customer_2"]
    for customer_id in customers:
        store_test_invoices(customer_id)
    
    print("\n✅ Test Data Generation Complete!")

if __name__ == "__main__":
    main() 