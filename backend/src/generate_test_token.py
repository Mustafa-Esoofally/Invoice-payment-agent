"""Script to generate a test JWT token for API testing."""

import jwt
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get JWT secret from environment variable
JWT_SECRET = os.getenv("JWT_SECRET", "3THyJasmgCZoguT7xwoiaYI4r27fSixi")
ALGORITHM = "HS256"

def generate_token(customer_id: str):
    """Generate a JWT token for testing."""
    # Token expiration time (24 hours from now)
    expiration = datetime.utcnow() + timedelta(hours=24)
    
    # Token payload
    payload = {
        "customer_id": customer_id,
        "name": "Test User",
        "email": f"test.user@{customer_id}.com",
        "exp": expiration
    }
    
    # Generate token
    token = jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)
    return token

def main():
    """Generate test tokens for each customer."""
    # Generate tokens for our test customers
    customers = ["cust_001", "cust_002", "cust_003", "cust_004", "cust_005"]
    
    print("\n🔑 Generated Test Tokens:")
    print("=" * 50)
    
    for customer_id in customers:
        token = generate_token(customer_id)
        print(f"\nCustomer: {customer_id}")
        print(f"Token: {token}")
        print("-" * 50)

if __name__ == "__main__":
    main() 