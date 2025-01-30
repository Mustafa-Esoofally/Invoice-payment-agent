"""Script to create invoice records in Firestore."""

import os
import time
from typing import Dict, Any
from firebase_admin import credentials, initialize_app, firestore, storage
from dotenv import load_dotenv

load_dotenv()

def init_firebase():
    """Initialize Firebase Admin SDK."""
    cred = credentials.Certificate("payman-agent-render-firebase-adminsdk-fbsvc-76639f1307.json")
    app = initialize_app(cred, {
        'storageBucket': 'payman-agent-render.appspot.com'
    })
    db = firestore.client()
    bucket = storage.bucket()
    return db, bucket

def get_file_url(bucket, file_path: str) -> str:
    """
    Get the public URL for a file in Firebase Storage.
    
    Args:
        bucket: Storage bucket
        file_path: Path to the file in storage
        
    Returns:
        str: Public URL of the file
    """
    blob = bucket.blob(file_path)
    expiration = int(time.time() + 3600)  # URL valid for 1 hour from now
    return blob.generate_signed_url(expiration=expiration)

def create_invoice_record(db: firestore.Client, invoice_data: Dict[str, Any]) -> str:
    """
    Create an invoice record in Firestore.
    
    Args:
        db: Firestore client
        invoice_data: Dictionary containing invoice data
        
    Returns:
        str: Created invoice ID
    """
    invoice_ref = db.collection('invoices').document()
    invoice_ref.set(invoice_data)
    return invoice_ref.id

def main():
    """Main function to create invoice records."""
    db, bucket = init_firebase()
    
    # List of invoice files in storage
    invoice_files = [
        'test/Blue and Yellow Geometric Invoice.pdf',
        'test/Black And Gray Minimal Freelancer Invoice.pdf',
        'test/Black White Minimalist Modern Business Invoice.pdf',
        'test/Fashion Invoice.pdf',
        'test/Simple Minimalist Business Invoice.pdf',
        'test/White Minimalist Business Invoice.pdf'
    ]
    
    # Create records for each invoice
    for file_path in invoice_files:
        try:
            file_url = get_file_url(bucket, file_path)
            
            # Example invoice data
            invoice_data = {
                'customer_id': f'CUST{hash(file_path) % 1000:03d}',  # Generate a unique customer ID
                'file_url': file_url,
                'file_path': file_path,
                'amount': 1000.00,  # Example amount
                'status': 'pending',
                'created_at': firestore.SERVER_TIMESTAMP
            }
            
            invoice_id = create_invoice_record(db, invoice_data)
            print(f"✅ Invoice record created for {file_path}")
            print(f"  📄 Invoice ID: {invoice_id}")
            print(f"  👤 Customer ID: {invoice_data['customer_id']}")
            print()
            
        except Exception as e:
            print(f"❌ Error creating invoice record for {file_path}: {str(e)}")

if __name__ == "__main__":
    main() 