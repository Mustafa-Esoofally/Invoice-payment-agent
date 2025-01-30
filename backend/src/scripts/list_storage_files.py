"""Script to list files in Firebase Storage."""

from firebase_admin import credentials, initialize_app, storage
from dotenv import load_dotenv

load_dotenv()

def init_firebase():
    """Initialize Firebase Admin SDK."""
    cred = credentials.Certificate("payman-agent-render-firebase-adminsdk-fbsvc-76639f1307.json")
    app = initialize_app(cred, {
        'storageBucket': 'payman-agent-render.firebasestorage.app'
    })
    bucket = storage.bucket()
    return bucket

def list_files(bucket):
    """List all files in the bucket."""
    blobs = bucket.list_blobs()
    print("\nFiles in storage:")
    print("-" * 50)
    for blob in blobs:
        print(f"📄 {blob.name}")
    print("-" * 50)

def main():
    """Main function to list storage files."""
    try:
        bucket = init_firebase()
        list_files(bucket)
    except Exception as e:
        print(f"❌ Error listing files: {str(e)}")

if __name__ == "__main__":
    main() 