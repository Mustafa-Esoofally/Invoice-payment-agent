"""Authentication utilities for the API."""

from typing import Dict
import jwt
from fastapi import HTTPException, Header
from functools import wraps

# JWT configuration
JWT_SECRET = "your-secret-key"  # In production, this should be in environment variables
JWT_ALGORITHM = "HS256"

def verify_jwt(authorization: str = Header(...)) -> Dict:
    """Verify JWT token from Authorization header.
    
    Args:
        authorization (str): Authorization header value
        
    Returns:
        Dict: JWT claims
        
    Raises:
        HTTPException: If token is invalid or missing
    """
    try:
        # Check if Authorization header exists
        if not authorization:
            raise HTTPException(
                status_code=401,
                detail="Authorization header is missing"
            )
            
        # Extract token from Bearer scheme
        if not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=401,
                detail="Invalid authorization scheme"
            )
            
        token = authorization.split(" ")[1]
        
        # Verify and decode token
        claims = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM]
        )
        
        # Verify required claims
        if not claims.get("customer_id"):
            raise HTTPException(
                status_code=401,
                detail="Invalid token: missing customer_id"
            )
            
        return claims
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Authentication error: {str(e)}"
        ) 