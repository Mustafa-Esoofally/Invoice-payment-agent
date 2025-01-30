"""Script to generate and upload sample invoice data to Firebase."""

import os
import sys
from datetime import datetime, timedelta
import random
import traceback
import uuid
from firebase_admin import initialize_app, credentials, firestore, get_app
import json

# Sample invoice file URLs from Firebase Storage
INVOICE_FILES = [
    {
        "url": "https://storage.googleapis.com/payman-agent-render.firebasestorage.app/templates/Black%20White%20Minimalist%20Modern%20Business%20Invoice.pdf",
        "name": "Black White Minimalist Modern Business Invoice.pdf"
    },
    {
        "url": "https://storage.googleapis.com/payman-agent-render.firebasestorage.app/templates/Simple%20Minimalist%20Aesthetic%20Business%20Invoice.pdf",
        "name": "Simple Minimalist Aesthetic Business Invoice.pdf"
    }
]

def generate_invoice(customer_id):
    """Generate an invoice with the specified schema."""
    # Generate a random invoice file from the available options
    invoice_file = random.choice(INVOICE_FILES)
    
    # Generate a unique invoice ID using UUID
    invoice_id = str(uuid.uuid4())
    
    # Create a local file path for processing
    local_file_path = f"downloads/invoice_{invoice_id}.pdf"
    
    # Get current timestamp
    now = datetime.now()
    
    return {
        "created_at": now.isoformat(),
        "customer_id": customer_id,
        "file_name": invoice_file["name"],
        "file_url": invoice_file["url"],
        "local_file_path": local_file_path,
        "status": "pending",
        "payment_details": {
            "file_path": local_file_path,
            "file_processed": True,
            "processed_at": now.isoformat(),
            "status": "success"
        }
    }

def main():
    """Main function to generate and upload sample data."""
    try:
        print("\nStarting invoice data generation...")
        
        # Initialize Firebase
        try:
            firebase_app = get_app()
            print("Using existing Firebase app")
        except ValueError as e:
            print(f"No existing Firebase app found: {str(e)}")
            try:
                current_dir = os.path.dirname(os.path.abspath(__file__))
                cred_path = os.path.join(current_dir, "payman-agent-render-firebase-adminsdk-fbsvc-76639f1307.json")
                
                print(f"Looking for credentials at: {cred_path}")
                if not os.path.exists(cred_path):
                    raise FileNotFoundError(f"Firebase credentials file not found at: {cred_path}")
                
                print("Reading credentials file...")
                cred = credentials.Certificate(cred_path)
                print("Initializing Firebase app...")
                firebase_app = initialize_app(cred)
                print("Firebase app initialized successfully")

            except Exception as init_error:
                print(f"Error during Firebase initialization: {str(init_error)}")
                print("Traceback:")
                traceback.print_exc()
                raise

        # Get Firestore client
        print("\nGetting Firestore client...")
        db = firestore.client()
        print("Firestore client obtained successfully")
        
        # Get list of customer IDs
        customers_ref = db.collection('customers')
        customers = customers_ref.stream()
        customer_ids = [doc.id for doc in customers]
        
        if not customer_ids:
            raise ValueError("No customers found in the database")
        
        # Generate and upload invoice data
        num_invoices = 10  # Generate 10 invoices
        
        print(f"\nGenerating {num_invoices} sample invoices...")
        for i in range(num_invoices):
            # Randomly select a customer
            customer_id = random.choice(customer_ids)
            
            # Generate invoice data
            invoice_data = generate_invoice(customer_id)
            
            # Add to Firestore with auto-generated ID
            doc_ref = db.collection('invoices').document()
            doc_ref.set(invoice_data)
            
            print(f"✓ Created invoice for customer {customer_id}")
            print(f"  ID: {doc_ref.id}")
            print(f"  File: {invoice_data['file_name']}")
        
        print("\n✅ Sample invoice data generation complete!")

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print("Traceback:")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 