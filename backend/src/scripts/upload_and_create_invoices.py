"""Script to upload invoice files and create invoice records."""

import os
from typing import Dict, Any
from firebase_admin import credentials, initialize_app, firestore, storage
from dotenv import load_dotenv

load_dotenv()

def init_firebase():
    """Initialize Firebase Admin SDK."""
    cred = credentials.Certificate("payman-agent-render-firebase-adminsdk-fbsvc-76639f1307.json")
    app = initialize_app(cred, {
        'storageBucket': 'payman-agent-render.firebasestorage.app'
    })
    db = firestore.client()
    bucket = storage.bucket()
    return db, bucket

def upload_file(bucket, source_file_path: str, destination_blob_path: str) -> bool:
    """Upload a file to Firebase Storage."""
    try:
        blob = bucket.blob(destination_blob_path)
        blob.upload_from_filename(source_file_path)
        print(f"✅ File uploaded: {destination_blob_path}")
        return True
    except Exception as e:
        print(f"❌ Error uploading file: {str(e)}")
        return False

def create_invoice_record(db: firestore.Client, invoice_data: Dict[str, Any]) -> str:
    """Create an invoice record in Firestore."""
    try:
        invoice_ref = db.collection('invoices').document()
        invoice_ref.set(invoice_data)
        print(f"✅ Invoice record created with ID: {invoice_ref.id}")
        return invoice_ref.id
    except Exception as e:
        print(f"❌ Error creating invoice record: {str(e)}")
        return None

def main():
    """Main function to upload files and create invoice records."""
    db, bucket = init_firebase()
    
    # Path to test invoices
    test_dir = "../invoice data/test"
    
    # Process each PDF file in the test directory
    for filename in os.listdir(test_dir):
        if filename.endswith('.pdf'):
            source_path = os.path.join(test_dir, filename)
            storage_path = f"test/{filename}"  # Store in test directory
            
            print(f"\nProcessing: {filename}")
            print("-" * 50)
            
            # Upload file to Firebase Storage
            if upload_file(bucket, source_path, storage_path):
                # Create invoice record
                invoice_data = {
                    'customer_id': f'CUST{hash(filename) % 1000:03d}',
                    'filename': filename,
                    'storage_path': storage_path,
                    'amount': 1000.00,  # Example amount
                    'status': 'pending',
                    'created_at': firestore.SERVER_TIMESTAMP
                }
                
                invoice_id = create_invoice_record(db, invoice_data)
                if invoice_id:
                    print(f"  👤 Customer ID: {invoice_data['customer_id']}")

if __name__ == "__main__":
    main() 