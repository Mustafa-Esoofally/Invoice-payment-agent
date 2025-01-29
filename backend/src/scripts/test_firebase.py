"""Minimal script to test Firebase initialization."""

import os
import sys
import traceback

def test_firebase():
    """Test Firebase initialization."""
    try:
        print("\nTesting imports...")
        print(f"Current working directory: {os.getcwd()}")
        print("Basic imports successful")
        
        print("\nTrying firebase-admin import...")
        from firebase_admin import credentials, initialize_app, firestore
        print("Firebase imports successful")
        
        print("\nChecking credentials file...")
        cred_path = "byrdeai-firebase-adminsdk-fbsvc-a168a9a31d.json"
        if not os.path.exists(cred_path):
            raise FileNotFoundError(f"Credentials file not found at: {cred_path}")
        print(f"Found credentials file at: {cred_path}")
        
        print("\nInitializing Firebase...")
        cred = credentials.Certificate(cred_path)
        app = initialize_app(cred)
        print("Firebase initialized successfully")
        
        print("\nTesting Firestore access...")
        db = firestore.client()
        docs = db.collection("customers").limit(1).get()
        print(f"Successfully accessed Firestore. Found {len(list(docs))} documents")
        
        print("\n✅ All tests passed!")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print("\nFull traceback:")
        traceback.print_exc()
        print(f"\nPython version: {sys.version}")
        print(f"Platform: {sys.platform}")

if __name__ == "__main__":
    test_firebase() 