"""FastAPI service for invoice processing using multi-agent system."""

from typing import Dict, Optional, List
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import json
from datetime import datetime
from dotenv import load_dotenv
import traceback

from src.multi_agent import process_invoice_emails
from src.tools.shared_tools import format_error, ensure_directory
from src.composio_client import init_composio
from src.config.firebase_config import db
from src.config.auth import jwt_auth
from src.tools.payment_tools import SendPaymentTool, SearchPayeesTool, BalanceTool

# Load environment variables
load_dotenv()

print("\n🚀 Starting Invoice Payment Agent API")
print("=" * 50)

# Initialize Composio client
init_composio()
print("✅ Composio client initialized")

# Initialize payment tools
send_payment_tool = SendPaymentTool()
search_payees_tool = SearchPayeesTool()
balance_tool = BalanceTool()
print("✅ Payment tools initialized")

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

class ScanInboxRequest(BaseModel):
    """Request model for scanning inbox."""
    gmail_token: str
    query: Optional[str] = "subject:invoice has:attachment newer_than:7d"
    max_results: Optional[int] = 10

class PayInvoiceRequest(BaseModel):
    """Request model for paying invoice."""
    invoice_id: str

@app.post("/scan-inbox")
async def scan_inbox(
    request: ScanInboxRequest,
    customer_id: str = Depends(jwt_auth)
):
    """Scan inbox for invoices and store them in Firebase."""
    try:
        print(f"\n📨 Scanning Inbox for Customer {customer_id} at {datetime.now().isoformat()}")
        
        # Process invoices using existing multi-agent system
        result = await process_invoice_emails(
            query=request.query,
            max_results=request.max_results,
            gmail_token=request.gmail_token
        )
        
        # Store invoices in Firebase
        for invoice in result.get("invoices", []):
            invoice_ref = db.collection("customers").document(customer_id)\
                           .collection("invoices").document()
            invoice["id"] = invoice_ref.id
            invoice["created_at"] = datetime.now().isoformat()
            invoice["status"] = "pending"
            invoice_ref.set(invoice)
            
        return {
            "success": True,
            "message": f"Processed {len(result.get('invoices', []))} invoices",
            "invoices": result.get("invoices", [])
        }
        
    except Exception as e:
        print(f"\n❌ Scan Inbox Error: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@app.post("/pay-invoice")
async def pay_invoice(
    request: PayInvoiceRequest,
    customer_id: str = Depends(jwt_auth)
):
    """Pay an invoice using Payman."""
    try:
        print(f"\n💰 Processing Payment for Invoice {request.invoice_id}")
        
        # Get invoice from Firebase
        invoice_ref = db.collection("customers").document(customer_id)\
                       .collection("invoices").document(request.invoice_id)
        invoice = invoice_ref.get()
        
        if not invoice.exists:
            raise HTTPException(
                status_code=404,
                detail=f"Invoice {request.invoice_id} not found"
            )
            
        invoice_data = invoice.to_dict()
        if invoice_data.get("status") == "paid":
            raise HTTPException(
                status_code=400,
                detail=f"Invoice {request.invoice_id} has already been paid"
            )
            
        # Check available balance
        balance_response = balance_tool._run()
        current_balance = float(balance_response.split("$")[1].split()[0])
        
        if current_balance < invoice_data["amount"]:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient balance. Required: ${invoice_data['amount']:.2f}, Available: ${current_balance:.2f}"
            )
            
        # Search for payee
        search_params = {
            "name": invoice_data["recipient"],
            "type": "US_ACH"
        }
        payees_response = search_payees_tool._run(json.dumps(search_params))
        payees = json.loads(payees_response)
        
        if not payees:
            raise HTTPException(
                status_code=404,
                detail=f"No payee found for {invoice_data['recipient']}. Please set up the payee first."
            )
            
        payee = payees[0]
        
        # Send payment
        payment_params = {
            "amount": float(invoice_data["amount"]),
            "destination_id": payee["id"],
            "memo": invoice_data.get("description", f"Invoice {invoice_data['invoice_number']}")
        }
        
        payment_response = send_payment_tool._run(json.dumps(payment_params))
        
        if "❌" in payment_response:
            raise HTTPException(
                status_code=500,
                detail=f"Payment failed: {payment_response.split('❌ Payment failed: ')[1]}"
            )
            
        # Extract payment reference
        payment_ref = payment_response.split("Reference: ")[1]
        
        # Update invoice in Firebase
        invoice_ref.update({
            "status": "paid",
            "payment": {
                "success": True,
                "transaction_id": payment_ref,
                "amount": invoice_data["amount"],
                "timestamp": datetime.now().isoformat(),
                "payee_id": payee["id"],
                "payee_name": payee["name"]
            },
            "paid_at": datetime.now().isoformat()
        })
        
        return {
            "success": True,
            "message": "Payment processed successfully",
            "payment": {
                "transaction_id": payment_ref,
                "amount": invoice_data["amount"],
                "recipient": payee["name"],
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"\n❌ Payment Error: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=str(e)
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