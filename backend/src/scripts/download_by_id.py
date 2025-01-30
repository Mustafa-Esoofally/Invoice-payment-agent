"""Script to download invoice by ID."""

import os
import sys
import requests
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

def get_invoice(db: firestore.Client, invoice_id: str):
    """Get invoice data from Firestore."""
    invoice_ref = db.collection('invoices').document(invoice_id)
    invoice = invoice_ref.get()
    return invoice.to_dict() if invoice.exists else None

def download_invoice(bucket, storage_path: str, output_path: str) -> bool:
    """Download invoice file from Firebase Storage."""
    try:
        # Create downloads directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Download the file
        blob = bucket.blob(storage_path)
        blob.download_to_filename(output_path)
        
        print(f"✅ Invoice downloaded to: {output_path}")
        return True
    except Exception as e:
        print(f"❌ Error downloading file: {str(e)}")
        return False

def main(invoice_id: str):
    """Main function to download invoice."""
    if not invoice_id:
        print("❌ Please provide an invoice ID")
        return
        
    db, bucket = init_firebase()
    
    # Get invoice data
    invoice_data = get_invoice(db, invoice_id)
    if not invoice_data:
        print(f"❌ Invoice not found: {invoice_id}")
        return
    
    # Get storage path
    storage_path = invoice_data.get('storage_path')
    if not storage_path:
        print("❌ No storage path found in invoice data")
        return
    
    # Download the file
    filename = invoice_data.get('filename', f'invoice_{invoice_id}.pdf')
    output_path = os.path.join('downloads', filename)
    download_invoice(bucket, storage_path, output_path)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python download_by_id.py <invoice_id>")
        sys.exit(1)
    
    main(sys.argv[1]) 