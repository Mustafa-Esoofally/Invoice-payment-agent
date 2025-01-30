"""Script to upload invoice files to Firebase Storage."""

import os
from firebase_admin import credentials, initialize_app, storage
from dotenv import load_dotenv

load_dotenv()

def init_firebase():
    """Initialize Firebase Admin SDK."""
    cred = credentials.Certificate("payman-agent-render-firebase-adminsdk-fbsvc-76639f1307.json")
    app = initialize_app(cred, {
        'storageBucket': 'payman-agent-render.appspot.com'
    })
    bucket = storage.bucket()
    return bucket

def upload_file(bucket, source_file_path: str, destination_blob_path: str) -> bool:
    """
    Upload a file to Firebase Storage.
    
    Args:
        bucket: Storage bucket
        source_file_path: Path to the local file to upload
        destination_blob_path: Path where to store the file in Firebase Storage
        
    Returns:
        bool: True if upload successful, False otherwise
    """
    try:
        blob = bucket.blob(destination_blob_path)
        blob.upload_from_filename(source_file_path)
        print(f"✅ File {source_file_path} uploaded to {destination_blob_path}")
        return True
    except Exception as e:
        print(f"❌ Error uploading file: {str(e)}")
        return False

def main():
    """Main function to upload invoice files."""
    try:
        bucket = init_firebase()
        
        # Upload sample invoice
        source_file = "../../invoice data/test/Blue and Yellow Geometric Invoice.pdf"
        destination_path = "invoices/Blue and Yellow Geometric Invoice.pdf"
        
        if not os.path.exists(source_file):
            print(f"❌ Source file not found: {source_file}")
            return
            
        upload_file(bucket, source_file, destination_path)
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    main() 
