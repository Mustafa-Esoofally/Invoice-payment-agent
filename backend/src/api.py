"""FastAPI application for invoice payment processing."""

import os
from typing import Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.multi_agent import process_invoices
from src.agents.payment_agent import get_payment_history

# Initialize FastAPI app
app = FastAPI(title="Invoice Payment Agent API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Check required environment variables
if not os.getenv("COMPOSIO_API_KEY"):
    raise ValueError("COMPOSIO_API_KEY environment variable is required")

print("\n🚀 Starting Invoice Payment Agent API")
print("==================================================")
print("Composio API Key present: ✓")

@app.get("/payment-history")
async def get_history() -> JSONResponse:
    """Get payment history."""
    try:
        history = await get_payment_history()
        if "error" in history:
            raise HTTPException(status_code=500, detail=history["error"])
        return JSONResponse(content=history)
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/process-invoices")
async def process_invoice_emails() -> JSONResponse:
    """Process invoice emails and make payments."""
    try:
        result = await process_invoices()
        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail={
                    "message": "Failed to process invoices",
                    "error": result["error"]
                }
            )
        return JSONResponse(content=result)
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"\n[API] ❌ HTTP error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Failed to process invoices",
                "error": str(e)
            }
        )

def main():
    """Run the FastAPI server using uvicorn."""
    import uvicorn
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

if __name__ == "__main__":
    main() 