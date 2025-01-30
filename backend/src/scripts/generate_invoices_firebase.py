"""Script for generating test invoice data in Firebase."""

import os
import sys
import uuid
from datetime import datetime
from typing import Dict, List
from dotenv import load_dotenv
from firebase_admin import initialize_app, credentials, firestore, storage, get_app

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

# Initialize Firebase
try:
    firebase_app = get_app()
    print("Using existing Firebase app")
except ValueError:
    try:
        cred = credentials.Certificate("../byrdeai-firebase-adminsdk-fbsvc-a168a9a31d.json")
        firebase_app = initialize_app(cred, {
            'storageBucket': 'byrdeai.firebasestorage.app'
        })
        print("Initialized new Firebase app")
    except Exception as e:
        print(f"Error initializing Firebase: {str(e)}")
        raise

# Initialize Firestore and Storage
db = firestore.client()
bucket = storage.bucket()

def list_storage_files(prefix: str = "") -> List[Dict]:
    """List all files in Firebase Storage with given prefix."""
    print(f"\n📂 Listing files with prefix: {prefix}")
    try:
        blobs = bucket.list_blobs(prefix=prefix)
        files = []
        
        for blob in blobs:
            # Generate a signed URL that doesn't expire
            url = f"https://firebasestorage.googleapis.com/v0/b/{bucket.name}/o/{blob.name.replace('/', '%2F')}?alt=media"
            files.append({
                "name": blob.name,
                "url": url,
                "created": blob.time_created,
                "updated": blob.updated,
                "size": blob.size,
                "content_type": blob.content_type
            })
            print(f"Found file: {blob.name}")
            print(f"URL: {url}")
        
        return files
    except Exception as e:
        print(f"\n❌ Error listing files: {str(e)}")
        raise

def create_invoice_record(customer_id: str, file_info: Dict) -> str:
    """Create an invoice record in Firestore."""
    invoice_id = str(uuid.uuid4())
    
    invoice_data = {
        "customer_id": customer_id,
        "file_name": file_info["name"],
        "file_url": file_info["url"],
        "status": "pending",
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }
    
    # Store in Firestore
    db.collection("invoices").document(invoice_id).set(invoice_data)
    print(f"\n✅ Created invoice record: {invoice_id}")
    print(f"  File: {file_info['name']}")
    print(f"  Customer: {customer_id}")
    
    return invoice_id

def main():
    """Main function to create invoice records."""
    print("\n🚀 Starting Invoice Record Creation")
    print("=" * 50)
    
    # List files from storage
    print("\n📂 Fetching files from Firebase Storage...")
    files = list_storage_files()
    
    if not files:
        print("\n❌ No files found in storage")
        return
    
    print(f"\n📊 Found {len(files)} files")
    
    # Create records for each file
    customer_id = "cust_001"  # Using the first customer from our previous setup
    created_records = []
    
    for file_info in files:
        try:
            invoice_id = create_invoice_record(customer_id, file_info)
            created_records.append(invoice_id)
        except Exception as e:
            print(f"\n❌ Error creating record for {file_info['name']}: {str(e)}")
    
    print("\n📊 Summary:")
    print(f"Total files processed: {len(files)}")
    print(f"Records created: {len(created_records)}")
    print("=" * 50)

if __name__ == "__main__":
    main() 