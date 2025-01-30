"""Script to download invoice files from Firebase Storage."""

import os
import sys
import time
import requests
from typing import Optional, Tuple
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

def get_invoice_data(db: firestore.Client, invoice_id: str) -> Optional[dict]:
    """
    Get invoice data from Firestore.
    
    Args:
        db: Firestore client
        invoice_id: ID of the invoice to fetch
        
    Returns:
        dict: Invoice data if found, None otherwise
    """
    if not invoice_id:
        return None
        
    invoice_ref = db.collection('invoices').document(invoice_id.strip())
    invoice = invoice_ref.get()
    return invoice.to_dict() if invoice.exists else None

def get_file_url(bucket, file_path: str) -> str:
    """
    Get a fresh signed URL for a file in Firebase Storage.
    
    Args:
        bucket: Storage bucket
        file_path: Path to the file in storage
        
    Returns:
        str: Signed URL for the file
    """
    blob = bucket.blob(file_path)
    expiration = int(time.time() + 3600)  # URL valid for 1 hour from now
    return blob.generate_signed_url(expiration=expiration)

def download_invoice_file(file_url: str, output_path: str) -> bool:
    """
    Download invoice file from the given URL.
    
    Args:
        file_url: URL of the file to download
        output_path: Path where to save the file
        
    Returns:
        bool: True if download successful, False otherwise
    """
    try:
        response = requests.get(file_url)
        response.raise_for_status()
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(response.content)
        return True
    except Exception as e:
        print(f"❌ Error downloading file: {str(e)}")
        return False

def main(invoice_id: str = None):
    """Main function to download invoice files."""
    if not invoice_id:
        print("❌ Please provide an invoice ID")
        return
        
    db, bucket = init_firebase()
    
    # Get invoice data
    invoice_data = get_invoice_data(db, invoice_id)
    if not invoice_data:
        print(f"❌ Invoice with ID {invoice_id} not found")
        return
    
    # Get file path and generate fresh signed URL
    file_path = invoice_data.get('file_path')
    if not file_path:
        print("❌ No file path found in invoice data")
        return
    
    try:
        file_url = get_file_url(bucket, file_path)
    except Exception as e:
        print(f"❌ Error generating file URL: {str(e)}")
        return
    
    # Create downloads directory if it doesn't exist
    output_path = os.path.join('downloads', f'invoice_{invoice_id}.pdf')
    
    if download_invoice_file(file_url, output_path):
        print(f"✅ Invoice downloaded successfully to {output_path}")
    else:
        print("❌ Failed to download invoice")

if __name__ == "__main__":
    # Get invoice ID from command line argument or prompt
    invoice_id = sys.argv[1] if len(sys.argv) > 1 else input("Enter invoice ID: ").strip()
    main(invoice_id) 
