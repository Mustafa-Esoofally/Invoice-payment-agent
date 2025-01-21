"""FastAPI service for invoice processing using multi-agent system."""

from typing import Dict, Optional, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import json
from dotenv import load_dotenv

from multi_agent import process_invoice_emails
from tools.shared_tools import format_error, ensure_directory

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Invoice Payment Agent API",
    description="API for processing invoice emails and payments using AI agents",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ProcessRequest(BaseModel):
    """Request model for invoice processing."""
    composio_account_id: str
    query: Optional[str] = "subject:invoice has:attachment newer_than:7d"
    max_results: Optional[int] = 10
    download_dir: Optional[str] = "invoice data/email_attachments"
    debug: Optional[bool] = False

@app.post("/process-invoices")
async def process_invoices(request: ProcessRequest) -> Dict:
    """Process invoice emails and make payments.
    
    Args:
        request (ProcessRequest): Processing request parameters
        
    Returns:
        dict: Processing results
    """
    try:
        # Set Composio account ID in environment
        os.environ["COMPOSIO_ACCOUNT_ID"] = request.composio_account_id
        
        # Process invoices
        result = process_invoice_emails(
            query=request.query,
            max_results=request.max_results,
            download_dir=request.download_dir,
            debug=request.debug
        )
        
        # Check if result has error
        if not result.get("success", False):
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Unknown error occurred")
            )
        
        return result
        
    except Exception as e:
        error = format_error(e)
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )

@app.get("/health")
async def health_check() -> Dict:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "1.0.0"
    }

@app.get("/payment-history")
async def get_payment_history() -> Dict[str, List]:
    """Get payment history.
    
    Returns:
        Dict[str, List]: List of payment records
    """
    try:
        history_file = "invoice data/payment_history.json"
        if not os.path.exists(history_file):
            return {"payments": []}
            
        with open(history_file, 'r') as f:
            history = json.load(f)
            
        # Transform data to match frontend expectations
        transformed_history = []
        for record in history:
            email_data = record.get("email_data", {})
            invoice_data = record.get("invoice_data", {})
            result = record.get("result", {})

            transformed_record = {
                "timestamp": record["timestamp"],
                "email": {
                    "subject": email_data.get("subject"),
                    "sender": email_data.get("sender"),
                    "timestamp": invoice_data.get("date")
                },
                "invoice": {
                    "invoice_number": invoice_data.get("invoice_number"),
                    "paid_amount": invoice_data.get("paid_amount"),
                    "recipient": invoice_data.get("recipient"),
                    "date": invoice_data.get("date"),
                    "due_date": invoice_data.get("due_date"),
                    "description": invoice_data.get("description")
                },
                "payment": {
                    "success": result.get("success", False),
                    "amount": invoice_data.get("paid_amount"),
                    "recipient": invoice_data.get("recipient"),
                    "reference": result.get("payment_id"),
                    "error": result.get("error")
                }
            }
            transformed_history.append(transformed_record)
            
        return {"payments": transformed_history}
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error reading payment history: {str(e)}"
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