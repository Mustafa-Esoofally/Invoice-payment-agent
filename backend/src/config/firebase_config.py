"""Firebase configuration module."""

import os
from firebase_admin import credentials, initialize_app, firestore
from dotenv import load_dotenv

load_dotenv()

def init_firebase():
    """Initialize Firebase Admin SDK."""
    cred = credentials.Certificate("byrdeai-firebase-adminsdk-fbsvc-a168a9a31d.json")
    app = initialize_app(cred)
    db = firestore.client()
    return db

# Initialize Firestore client
db = init_firebase()
print("✅ Firebase initialized") 