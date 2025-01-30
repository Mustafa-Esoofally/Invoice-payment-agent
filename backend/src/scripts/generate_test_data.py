"""Script to generate and upload sample customer and invoice data to Firebase."""

import os
import sys
from datetime import datetime, timedelta
import random
import traceback
import uuid
from pathlib import Path
from typing import Dict, List, Optional
from firebase_admin import initialize_app, credentials, firestore, get_app

# Sample data
COMPANY_NAMES = [
    "Tech Solutions Inc", "Data Systems Corp", "Cloud Services Ltd",
    "Digital Solutions Inc", "AI Technologies Corp", "Smart Systems Ltd",
    "Future Tech Inc", "Innovation Labs Corp", "Tech Dynamics Ltd",
    "Digital Ventures Inc"
]

INDUSTRIES = ["Technology", "Finance", "Healthcare", "Manufacturing", "Retail"]
COMPANY_SIZES = ["1-10", "10-50", "50-100", "100-500", "500+"]
SUBSCRIPTION_TIERS = ["basic", "premium", "enterprise"]

# Sample invoice file URLs from Firebase Storage
INVOICE_FILES = [
    {
        "url": "https://storage.googleapis.com/payman-agent-render.firebasestorage.app/templates/Black%20White%20Minimalist%20Modern%20Business%20Invoice.pdf",
        "name": "Black White Minimalist Modern Business Invoice.pdf"
    },
    {
        "url": "https://storage.googleapis.com/payman-agent-render.firebasestorage.app/templates/Simple%20Minimalist%20Aesthetic%20Business%20Invoice.pdf",
        "name": "Simple Minimalist Aesthetic Business Invoice.pdf"
    }
]

def init_firebase() -> None:
    """Initialize Firebase connection."""
    try:
        firebase_app = get_app()
        print("Using existing Firebase app")
    except ValueError:
        try:
            current_dir = Path(__file__).parent.parent
            cred_path = current_dir / "payman-agent-render-firebase-adminsdk-fbsvc-76639f1307.json"
            
            if not cred_path.exists():
                raise FileNotFoundError(f"Firebase credentials file not found at: {cred_path}")
            
            cred = credentials.Certificate(str(cred_path))
            firebase_app = initialize_app(cred)
            print("Firebase app initialized successfully")

        except Exception as e:
            print(f"Error during Firebase initialization: {str(e)}")
            traceback.print_exc()
            raise

def generate_customer(customer_id: str) -> Dict:
    """Generate a customer profile with the specified schema.
    
    Args:
        customer_id (str): Unique customer identifier
        
    Returns:
        Dict: Generated customer data
    """
    company = random.choice(COMPANY_NAMES)
    name = f"John Smith {customer_id}"  # Simplified for demo
    email = f"john.smith{customer_id}@example.com"
    
    return {
        "active": True,
        "company": company,
        "created_at": datetime.now().isoformat(),
        "customer_id": customer_id,
        "email": email,
        "metadata": {
            "company_size": random.choice(COMPANY_SIZES),
            "industry": random.choice(INDUSTRIES),
            "subscription_tier": random.choice(SUBSCRIPTION_TIERS)
        },
        "name": name,
        "settings": {
            "gmail_connected": random.choice([True, False])
        },
        "notification_preferences": {
            "email": True,
            "push": False
        }
    }

def generate_invoice(customer_id: str) -> Dict:
    """Generate an invoice with the specified schema.
    
    Args:
        customer_id (str): Customer ID to generate invoice for
        
    Returns:
        Dict: Generated invoice data
    """
    invoice_file = random.choice(INVOICE_FILES)
    invoice_id = str(uuid.uuid4())
    local_file_path = f"downloads/invoice_{invoice_id}.pdf"
    now = datetime.now()
    
    return {
        "created_at": now.isoformat(),
        "customer_id": customer_id,
        "file_name": invoice_file["name"],
        "file_url": invoice_file["url"],
        "local_file_path": local_file_path,
        "status": "pending",
        "payment_details": {
            "file_path": local_file_path,
            "file_processed": True,
            "processed_at": now.isoformat(),
            "status": "success"
        }
    }

def generate_customers(num_customers: int = 5) -> List[str]:
    """Generate and upload sample customer data.
    
    Args:
        num_customers (int): Number of customers to generate
        
    Returns:
        List[str]: List of generated customer IDs
    """
    print(f"\nGenerating {num_customers} sample customers...")
    db = firestore.client()
    customer_ids = []
    
    for i in range(num_customers):
        customer_id = f"cust_{str(i+1).zfill(3)}"
        customer_data = generate_customer(customer_id)
        
        # Set document with customer_id as the document ID
        doc_ref = db.collection('customers').document(customer_id)
        doc_ref.set(customer_data)
        customer_ids.append(customer_id)
        
        print(f"✓ Created customer: {customer_id} - {customer_data['company']}")
    
    return customer_ids

def generate_invoices(customer_ids: List[str], num_invoices: int = 10) -> None:
    """Generate and upload sample invoice data.
    
    Args:
        customer_ids (List[str]): List of customer IDs to generate invoices for
        num_invoices (int): Number of invoices to generate
    """
    print(f"\nGenerating {num_invoices} sample invoices...")
    db = firestore.client()
    
    for i in range(num_invoices):
        # Randomly select a customer
        customer_id = random.choice(customer_ids)
        
        # Generate invoice data
        invoice_data = generate_invoice(customer_id)
        
        # Add to Firestore with auto-generated ID
        doc_ref = db.collection('invoices').document()
        doc_ref.set(invoice_data)
        
        print(f"✓ Created invoice for customer {customer_id}")
        print(f"  ID: {doc_ref.id}")
        print(f"  File: {invoice_data['file_name']}")

def main():
    """Generate sample customer and invoice data."""
    try:
        print("\n🚀 Starting sample data generation...")
        print("=" * 50)
        
        # Initialize Firebase
        init_firebase()
        
        # Generate customers
        customer_ids = generate_customers(num_customers=5)
        print("\n✅ Customer generation complete!")
        
        # Generate invoices
        generate_invoices(customer_ids, num_invoices=10)
        print("\n✅ Invoice generation complete!")
        
        print("\n🎉 All sample data generated successfully!")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 