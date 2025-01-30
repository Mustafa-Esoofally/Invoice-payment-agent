"""Test script for managing Firebase test data and API testing."""

import os
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
import jwt
from dotenv import load_dotenv
from firebase_admin import initialize_app, credentials, firestore, storage, get_app
import argparse

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

class FirebaseEncoder(json.JSONEncoder):
    """Custom JSON encoder for Firebase objects."""
    def default(self, obj: Any) -> Any:
        if hasattr(obj, '_seconds'):  # Handle Firebase timestamps
            return datetime.fromtimestamp(obj._seconds).isoformat()
        return super().default(obj)

# Initialize Firebase
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
CRED_PATH = os.path.join(BACKEND_DIR, "byrdeai-firebase-adminsdk-fbsvc-a168a9a31d.json")

try:
    firebase_app = get_app()
except ValueError:
    cred = credentials.Certificate(CRED_PATH)
    firebase_app = initialize_app(cred, {
        'storageBucket': 'byrdeai'
    })

db = firestore.client()
bucket = storage.bucket()

# JWT settings from .env
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key")
ALGORITHM = "HS256"

def get_file_url(blob_name: str) -> str:
    """Get a signed URL for a file in Firebase Storage."""
    blob = bucket.blob(blob_name)
    return blob.generate_signed_url(
        version="v4",
        expiration=timedelta(days=7),
        method="GET"
    )

def list_storage_files(prefix: str = "invoices/") -> List[str]:
    """List all files in Firebase Storage with given prefix."""
    blobs = bucket.list_blobs(prefix=prefix)
    return [blob.name for blob in blobs]

def generate_test_jwt(customer_id: str) -> str:
    """Generate a test JWT token for API testing."""
    payload = {
        "customer_id": customer_id,
        "exp": datetime.utcnow() + timedelta(days=1)
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)
    return token

def serialize_firebase_data(data: Any) -> Any:
    """Serialize Firebase data types to JSON-compatible format."""
    if isinstance(data, dict):
        return {k: serialize_firebase_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [serialize_firebase_data(item) for item in data]
    elif str(type(data)) == "<class 'google.api_core.datetime_helpers.DatetimeWithNanoseconds'>":
        return data.isoformat()
    elif hasattr(data, '_seconds'):  # Firebase Timestamp
        return datetime.fromtimestamp(data._seconds).isoformat()
    return data

def list_all_invoices() -> List[Dict]:
    """List all invoices in Firebase."""
    invoices = []
    docs = db.collection("invoices").stream()
    
    for doc in docs:
        try:
            invoice_data = doc.to_dict()
            invoice_data["id"] = doc.id
            serialized_data = serialize_firebase_data(invoice_data)
            invoices.append(serialized_data)
        except Exception as e:
            print(f"Error processing invoice {doc.id}: {str(e)}")
    
    return invoices

def add_test_invoice(customer_id: str, invoice_data: Dict) -> str:
    """Add a test invoice to Firebase."""
    invoice_ref = db.collection("invoices").document()
    data = {
        "customer_id": customer_id,
        "created_at": firestore.SERVER_TIMESTAMP,
        "status": "pending",
        "data": invoice_data
    }
    invoice_ref.set(data)
    return invoice_ref.id

def create_sample_invoices():
    """Create sample invoices for testing."""
    # Test customer IDs
    customers = ["test_customer_1", "test_customer_2"]
    
    # Sample invoice data
    sample_invoices = [
        {
            "invoice_number": "INV-2024-001",
            "amount": 1500.00,
            "currency": "USD",
            "due_date": (datetime.now() + timedelta(days=30)).isoformat(),
            "recipient": "Tech Solutions Inc",
            "description": "Software Development Services - Q1 2024",
            "file_url": "https://example.com/placeholder-invoice-1.pdf",  # Placeholder URL
            "file_name": "invoice-1.pdf",
            "bank_details": {
                "account_name": "Tech Solutions Inc",
                "account_number": "1234567890",
                "routing_number": "987654321",
                "bank_name": "Chase Bank"
            },
            "metadata": {
                "invoice_date": datetime.now().isoformat(),
                "payment_terms": "Net 30",
                "po_number": "PO-2024-001",
                "tax_amount": 150.00,
                "subtotal": 1350.00
            }
        },
        {
            "invoice_number": "INV-2024-002",
            "amount": 2750.00,
            "currency": "USD",
            "due_date": (datetime.now() + timedelta(days=15)).isoformat(),
            "recipient": "Digital Dynamics LLC",
            "description": "Cloud Infrastructure Services - January 2024",
            "file_url": "https://example.com/placeholder-invoice-2.pdf",  # Placeholder URL
            "file_name": "invoice-2.pdf",
            "bank_details": {
                "account_name": "Digital Dynamics LLC",
                "account_number": "0987654321",
                "routing_number": "123456789",
                "bank_name": "Bank of America"
            },
            "metadata": {
                "invoice_date": datetime.now().isoformat(),
                "payment_terms": "Net 15",
                "po_number": "PO-2024-002",
                "tax_amount": 250.00,
                "subtotal": 2500.00
            }
        }
    ]
    
    # Add invoices for each customer
    for customer_id in customers:
        for invoice in sample_invoices:
            invoice_id = add_test_invoice(customer_id, invoice)
            print(f"Created invoice {invoice_id} for customer {customer_id}")
            print(f"Invoice Number: {invoice['invoice_number']}")
            print(f"Amount: {invoice['currency']} {invoice['amount']}")
            print("-" * 50)

def main():
    """Main function to run the test script."""
    parser = argparse.ArgumentParser(description="Firebase Invoice Test Data Manager")
    parser.add_argument("action", choices=["list", "create", "token", "files"], help="Action to perform")
    parser.add_argument("--customer-id", help="Customer ID for token generation")
    parser.add_argument("--raw", action="store_true", help="Show raw data without pretty printing")
    
    args = parser.parse_args()
    
    if args.action == "list":
        invoices = list_all_invoices()
        print("\nCurrent Invoices:")
        if args.raw:
            print(invoices)
        else:
            try:
                print(json.dumps(invoices, indent=2))
            except TypeError as e:
                print("Error serializing to JSON:", str(e))
                print("\nRaw data:")
                print(invoices)
        
    elif args.action == "create":
        create_sample_invoices()
        print("\nSample invoices created successfully!")
        
    elif args.action == "token":
        if not args.customer_id:
            print("Error: --customer-id is required for token generation")
            sys.exit(1)
        token = generate_test_jwt(args.customer_id)
        print(f"\nJWT Token for {args.customer_id}:")
        print(token)
        
    elif args.action == "files":
        files = list_storage_files()
        print("\nAvailable invoice files in Firebase Storage:")
        for file in files:
            print(f"- {file}")
            print(f"  URL: {get_file_url(file)}")

if __name__ == "__main__":
    main() 