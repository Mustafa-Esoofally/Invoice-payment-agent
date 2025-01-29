"""Script to create a test invoice in Firebase."""

import os
import sys
import traceback
from datetime import datetime, timedelta
from dotenv import load_dotenv
from firebase_admin import credentials, initialize_app, firestore

# Load environment variables
load_dotenv()

def create_test_invoice():
    """Create a test invoice in Firebase."""
    try:
        print("\n🔍 Checking Firebase credentials file...")
        cred_path = "byrdeai-firebase-adminsdk-fbsvc-a168a9a31d.json"
        if not os.path.exists(cred_path):
            raise FileNotFoundError(f"Firebase credentials file not found at: {cred_path}")
        print(f"✅ Found credentials file: {cred_path}")
        
        # Initialize Firebase
        print("\n🔄 Initializing Firebase...")
        cred = credentials.Certificate(cred_path)
        app = initialize_app(cred)
        print("✅ Firebase initialized successfully")
        
        # Get Firestore client
        print("\n🔄 Getting Firestore client...")
        db = firestore.client()
        print("✅ Firestore client initialized")
        
        # Test invoice data
        current_time = datetime.now()
        due_date = current_time + timedelta(days=30)
        
        invoice_data = {
            "recipient": "Test Company LLC",
            "amount": 1000.00,
            "invoice_number": f"TEST-{current_time.strftime('%Y%m%d-%H%M%S')}",
            "description": "Test Invoice for Payment API",
            "created_at": current_time.isoformat(),
            "status": "pending",
            "due_date": due_date.isoformat(),
            "currency": "USD",
            "pdf_url": "https://firebasestorage.googleapis.com/v0/b/byrdeai.firebasestorage.app/o/Black%20White%20Minimalist%20Modern%20Business%20Invoice.pdf?alt=media&token=29e22ac9-50d0-4518-a33c-88ac335f72e4"
        }
        
        print("\n🔄 Adding invoice to Firebase...")
        # Add to Firebase under test customer
        customer_id = "test_customer"
        invoice_ref = db.collection("customers").document(customer_id)\
                       .collection("invoices").document()
                       
        invoice_ref.set(invoice_data)
        
        print("\n✅ Test invoice created successfully")
        print(f"Customer ID: {customer_id}")
        print(f"Invoice ID: {invoice_ref.id}")
        print("Invoice data:")
        print(invoice_data)
        
    except Exception as e:
        print(f"\n❌ Error creating test invoice: {str(e)}")
        print("\nTraceback:")
        traceback.print_exc()
        print(f"\nPython version: {sys.version}")
        print(f"Platform: {sys.platform}")

if __name__ == "__main__":
    create_test_invoice() 
