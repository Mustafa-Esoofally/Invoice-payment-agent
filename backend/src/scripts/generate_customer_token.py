import os
import jwt
from datetime import datetime, timedelta
from dotenv import load_dotenv
from firebase_admin import initialize_app, credentials, firestore, get_app
import random

# Load environment variables
load_dotenv()

# Initialize Firebase
try:
    firebase_app = get_app()
    print("Using existing Firebase app")
except ValueError:
    try:
        cred = credentials.Certificate("byrdeai-firebase-adminsdk-fbsvc-a168a9a31d.json")
        firebase_app = initialize_app(cred)
        print("Initialized new Firebase app")
    except Exception as e:
        print(f"Error initializing Firebase: {str(e)}")
        raise

# Initialize Firestore
db = firestore.client()

def get_random_customer():
    """Fetch a random customer from Firebase customers collection."""
    customers = list(db.collection("customers").stream())
    if not customers:
        raise Exception("No customers found in the database")
    
    # Select a random customer
    random_customer = random.choice(customers)
    return random_customer.to_dict(), random_customer.id

def generate_token(customer_data: dict, customer_id: str):
    """Generate JWT token for the customer."""
    # Get JWT secret from environment
    jwt_secret = os.getenv("JWT_SECRET")
    if not jwt_secret:
        raise Exception("JWT_SECRET not found in environment variables")
    
    # Prepare token payload
    payload = {
        "customer_id": customer_id,
        "name": customer_data.get("name", "Not provided"),
        "email": customer_data.get("email", "Not provided"),
        "exp": datetime.utcnow() + timedelta(days=30)  # Token expires in 30 days
    }
    
    # Generate token
    token = jwt.encode(payload, jwt_secret, algorithm="HS256")
    return token, payload

def main():
    print("\n🔍 Fetching random customer from Firebase...")
    try:
        # Get random customer
        customer_data, customer_id = get_random_customer()
        print("\n👤 Selected Customer:")
        print(f"  ID: {customer_id}")
        print(f"  Name: {customer_data.get('name', 'Not provided')}")
        print(f"  Email: {customer_data.get('email', 'Not provided')}")
        
        # Generate token
        print("\n🔐 Generating JWT token...")
        token, payload = generate_token(customer_data, customer_id)
        
        print("\n✅ Token generated successfully!")
        print("\nToken Payload:")
        for key, value in payload.items():
            print(f"  {key}: {value}")
        
        print("\n📝 JWT Token:")
        print(token)
        
        # Save token to file
        with open("auth_token.txt", "w") as f:
            f.write(token)
        print("\n💾 Token saved to auth_token.txt")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        raise

if __name__ == "__main__":
    main() 