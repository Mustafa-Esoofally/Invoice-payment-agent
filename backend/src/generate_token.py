"""Generate JWT token for testing using Firebase customer data."""

import jwt
import datetime
import os
from dotenv import load_dotenv
from config.firebase_config import db

# Load environment variables
load_dotenv()

# Get JWT secret from environment
JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    raise ValueError("JWT_SECRET not found in environment variables")

# Get customers from Firebase
print("\n🔍 Fetching customers from Firebase...")
customers = db.collection("customers").stream()
customer_list = []

for customer in customers:
    customer_data = customer.to_dict()
    customer_data['id'] = customer.id
    customer_list.append(customer_data)
    print(f"\n👤 Customer found:")
    print(f"  ID: {customer.id}")
    print(f"  Name: {customer_data.get('name', 'N/A')}")
    print(f"  Email: {customer_data.get('email', 'N/A')}")

if not customer_list:
    print("\n❌ No customers found in Firebase")
    exit(1)

# Use the first customer for token generation
customer = customer_list[0]
print(f"\n✨ Using customer for token generation:")
print(f"  ID: {customer['id']}")
print(f"  Name: {customer.get('name', 'N/A')}")
print(f"  Email: {customer.get('email', 'N/A')}")

# Generate token with 7 days expiry
token = jwt.encode(
    {
        'customer_id': customer['id'],
        'exp': (datetime.datetime.utcnow() + datetime.timedelta(days=7)).timestamp(),
        'iat': datetime.datetime.utcnow().timestamp(),
        'name': customer.get('name', 'Unknown'),
        'email': customer.get('email', 'unknown@example.com')
    },
    JWT_SECRET,
    algorithm='HS256'
)

# Create authorization header
auth_header = f'Bearer {token}'

# Save to file
with open('auth_token.txt', 'w') as f:
    f.write(auth_header)

print('\n🔑 Generated JWT Token:')
print('=' * 50)
print(f'\nAuthorization: {auth_header}\n')
print('=' * 50)
print('\n✅ Token saved to auth_token.txt')
print('You can use this token in the Authorization header for API requests') 