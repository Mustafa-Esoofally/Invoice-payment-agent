"""Authentication utilities for token generation and validation."""

from typing import Dict, Optional, List
from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from datetime import datetime, timedelta
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get JWT secret from environment
JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    raise ValueError("JWT_SECRET not found in environment variables")

ALGORITHM = "HS256"

def generate_token(
    customer_id: str,
    name: str = None,
    email: str = None,
    expiry_days: int = 7
) -> str:
    """Generate a JWT token for a customer.
    
    Args:
        customer_id (str): Customer ID to generate token for
        name (str, optional): Customer name. Defaults to None.
        email (str, optional): Customer email. Defaults to None.
        expiry_days (int, optional): Token expiry in days. Defaults to 7.
        
    Returns:
        str: Generated JWT token
    """
    # Set expiration time
    expiration = datetime.utcnow() + timedelta(days=expiry_days)
    
    # Build payload
    payload = {
        'customer_id': customer_id,
        'exp': expiration.timestamp(),
        'iat': datetime.utcnow().timestamp()
    }
    
    # Add optional fields if provided
    if name:
        payload['name'] = name
    if email:
        payload['email'] = email
        
    # Generate token
    token = jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)
    return token

def generate_test_token(customer_id: str = "cust_001", expiry_hours: int = 24) -> str:
    """Generate a test JWT token.
    
    Args:
        customer_id (str, optional): Test customer ID. Defaults to "cust_001".
        expiry_hours (int, optional): Token expiry in hours. Defaults to 24.
        
    Returns:
        str: Generated test JWT token
    """
    name = "Test User"
    email = f"test.user@{customer_id}.com"
    
    # Generate token with shorter expiry for testing
    token = generate_token(
        customer_id=customer_id,
        name=name,
        email=email,
        expiry_days=expiry_hours/24  # Convert hours to days
    )
    return token

def save_token_to_file(token: str, filename: str = "auth_token.txt") -> None:
    """Save token to a file with proper Authorization header format.
    
    Args:
        token (str): JWT token to save
        filename (str, optional): Output filename. Defaults to "auth_token.txt".
    """
    auth_header = f'Bearer {token}'
    
    # Ensure we save to the src directory
    file_path = Path("src") / filename
    
    with open(file_path, 'w') as f:
        f.write(auth_header)
    
    print(f'\n✅ Token saved to {filename}')
    print('You can use this token in the Authorization header for API requests')

def generate_test_tokens(customer_ids: Optional[List[str]] = None) -> Dict[str, str]:
    """Generate test tokens for multiple customers.
    
    Args:
        customer_ids (List[str], optional): List of customer IDs. 
            Defaults to ["cust_001" through "cust_005"].
            
    Returns:
        Dict[str, str]: Dictionary mapping customer IDs to tokens
    """
    if customer_ids is None:
        customer_ids = [f"cust_{str(i).zfill(3)}" for i in range(1, 6)]
    
    tokens = {}
    print("\n🔑 Generated Test Tokens:")
    print("=" * 50)
    
    for customer_id in customer_ids:
        token = generate_test_token(customer_id)
        tokens[customer_id] = token
        
        print(f"\nCustomer: {customer_id}")
        print(f"Token: {token}")
        print("-" * 50)
    
    return tokens

class JWTBearer(HTTPBearer):
    """JWT Bearer token authentication."""
    
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)

    async def __call__(self, request: Request) -> Optional[str]:
        """Validate JWT token and extract customer_id."""
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)
        
        if not credentials:
            raise HTTPException(
                status_code=403,
                detail="Invalid authorization code."
            )

        if not credentials.scheme == "Bearer":
            raise HTTPException(
                status_code=403,
                detail="Invalid authentication scheme."
            )

        try:
            payload = jwt.decode(
                credentials.credentials,
                JWT_SECRET,
                algorithms=[ALGORITHM]
            )
            customer_id = payload.get("customer_id")
            if not customer_id:
                raise HTTPException(
                    status_code=403,
                    detail="customer_id claim missing from token"
                )
            return customer_id
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=403,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=403,
                detail="Invalid token"
            )

# Create authentication middleware instance
jwt_auth = JWTBearer()

if __name__ == "__main__":
    # Example usage
    print("\n1️⃣ Generating a production token")
    token = generate_token("cust_001", "John Doe", "john@example.com")
    save_token_to_file(token)
    
    print("\n2️⃣ Generating test tokens")
    test_tokens = generate_test_tokens() 