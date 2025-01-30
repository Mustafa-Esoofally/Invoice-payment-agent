"""JWT authentication middleware."""

from typing import Optional
from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from dotenv import load_dotenv
import os

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    raise ValueError("JWT_SECRET environment variable not set")

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
                algorithms=["HS256"]
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

jwt_auth = JWTBearer() 