"""Script to generate and upload sample customer data to Firebase."""

import os
import sys
from datetime import datetime, timedelta
import random
import traceback
from firebase_admin import initialize_app, credentials, firestore, get_app
import json

print(f"Python version: {sys.version}")
print(f"Current working directory: {os.getcwd()}")

# Sample data
COMPANY_NAMES = [
    "Tech Solutions Inc", "Data Systems Corp", "Cloud Services Ltd",
    "Digital Solutions Inc", "AI Technologies Corp", "Smart Systems Ltd",
    "Future Tech Inc", "Innovation Labs Corp", "Tech Dynamics Ltd",
    "Digital Ventures Inc"
]

INDUSTRIES = [
    "Technology", "Finance", "Healthcare", "Manufacturing", "Retail"
]

COMPANY_SIZES = [
    "1-10", "10-50", "50-100", "100-500", "500+"
]

SUBSCRIPTION_TIERS = [
    "basic", "premium", "enterprise"
]

def generate_customer(customer_id):
    """Generate a customer profile with the specified schema."""
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

def main():
    """Main function to generate and upload sample data."""
    try:
        print("\nStarting sample data generation...")
        
        # Initialize Firebase
        try:
            firebase_app = get_app()
            print("Using existing Firebase app")
        except ValueError as e:
            print(f"No existing Firebase app found: {str(e)}")
            try:
                current_dir = os.path.dirname(os.path.abspath(__file__))
                cred_path = os.path.join(current_dir, "payman-agent-render-firebase-adminsdk-fbsvc-76639f1307.json")
                
                print(f"Looking for credentials at: {cred_path}")
                if not os.path.exists(cred_path):
                    raise FileNotFoundError(f"Firebase credentials file not found at: {cred_path}")
                
                print("Reading credentials file...")
                cred = credentials.Certificate(cred_path)
                print("Initializing Firebase app...")
                firebase_app = initialize_app(cred)
                print("Firebase app initialized successfully")

            except Exception as init_error:
                print(f"Error during Firebase initialization: {str(init_error)}")
                print("Traceback:")
                traceback.print_exc()
                raise

        # Get Firestore client
        print("\nGetting Firestore client...")
        db = firestore.client()
        print("Firestore client obtained successfully")
        
        # Generate and upload customer data
        num_customers = 5
        
        print(f"\nGenerating {num_customers} sample customers...")
        for i in range(num_customers):
            customer_id = f"cust_{str(i+1).zfill(3)}"
            customer_data = generate_customer(customer_id)
            
            # Set document with customer_id as the document ID
            doc_ref = db.collection('customers').document(customer_id)
            doc_ref.set(customer_data)
            print(f"✓ Created customer: {customer_id} - {customer_data['company']}")
        
        print("\n✅ Sample data generation complete!")

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print("Traceback:")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 
