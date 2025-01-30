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
from pathlib import Path
from firebase_admin import firestore, storage, initialize_app, credentials
from tools.shared_tools import format_error, ensure_directory
from tools.auth import verify_jwt

# Load environment variables
load_dotenv()

# Initialize Firebase Admin SDK
cred = credentials.Certificate("payman-agent-render-firebase-adminsdk-fbsvc-76639f1307.json")
app = initialize_app(cred, {
    'storageBucket': 'payman-agent-render.firebasestorage.app'
})
db = firestore.client()
bucket = storage.bucket()

# Initialize FastAPI app
app = FastAPI(
    title="Invoice Payment Agent API",
    description="API for processing invoice payments using AI agents",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PayInvoiceRequest(BaseModel):
    """Request model for invoice payment."""
    invoice_id: str

def serialize_firebase_data(data: Any) -> Any:
    """Serialize Firebase data types to JSON-compatible format."""
    if isinstance(data, dict):
        return {k: serialize_firebase_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [serialize_firebase_data(item) for item in data]
    elif str(type(data)) == "<class 'google.api_core.datetime_helpers.DatetimeWithNanoseconds'>":
        return data.isoformat()
    elif hasattr(data, '_seconds'):  # Firebase Timestamp
        return datetime.fromtimestamp(data._seconds).isoformat()
    elif str(type(data)) == "<class 'google.cloud.firestore_v1.transforms.Sentinel'>":
        return datetime.now().isoformat()
    elif isinstance(data, datetime):
        return data.isoformat()
    return data

@app.post("/pay-invoice")
async def pay_invoice(
    request: PayInvoiceRequest,
    claims: Dict = Depends(verify_jwt)
) -> Dict:
    """Process payment for a specific invoice."""
    try:
        # Validate customer_id from JWT token
        customer_id = claims.get("customer_id")
        if not customer_id:
            raise HTTPException(
                status_code=400, 
                detail="Customer ID not found in token"
            )

        # Get the invoice from Firebase
        invoice_ref = db.collection("invoices").document(request.invoice_id)
        invoice_doc = invoice_ref.get()
        
        if not invoice_doc.exists:
            raise HTTPException(
                status_code=404,
                detail="Invoice not found"
            )
            
        # Get invoice data and serialize it
        invoice_data = invoice_doc.to_dict()
        invoice_data["id"] = invoice_doc.id
        
        # Verify the invoice belongs to the authenticated customer
        if invoice_data.get("customer_id") != customer_id:
            raise HTTPException(
                status_code=403,
                detail="Not authorized to access this invoice"
            )
        
        # Get the file path from invoice data
        file_path = invoice_data.get("file_path")
        if not file_path:
            raise HTTPException(
                status_code=400,
                detail="Invoice file path not found"
            )
        
        # Create downloads directory if it doesn't exist
        downloads_dir = Path("downloads")
        downloads_dir.mkdir(exist_ok=True)
        
        # Generate local file path - ensure safe filename
        file_name = os.path.basename(file_path)
        if not file_name:
            file_name = f"invoice_{request.invoice_id}.pdf"
        else:
            import re
            file_name = re.sub(r'[<>:"/\\|?*]', '_', file_name)
            
        local_path = downloads_dir / file_name
        
        try:
            # Download using Firebase Admin SDK
            blob = bucket.blob(file_path)
            blob.download_to_filename(str(local_path))
            
            if not os.path.exists(local_path):
                raise HTTPException(
                    status_code=500,
                    detail="Failed to download invoice file"
                )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to download invoice file: {str(e)}"
            )
        
        # Update invoice status to processing
        invoice_ref.update({
            "status": "processing",
            "processing_started_at": firestore.SERVER_TIMESTAMP,
            "local_file_path": str(local_path)
        })

        # Extract payment details from PDF
        try:
            payment_details = extract_text(str(local_path), extract_metadata=True)
            
            if not payment_details or "error" in payment_details:
                raise ValueError(payment_details.get("error", "Failed to extract payment details from PDF"))
            
            # Update invoice with extracted details
            invoice_ref.update({
                "extracted_details": payment_details,
                "last_updated": firestore.SERVER_TIMESTAMP
            })
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to extract payment details: {str(e)}"
            )
        
        # Process payment
        try:
            payment_result = await process_payment({
                "invoice_id": request.invoice_id,
                "invoice_number": payment_details.get("invoice_number"),
                "amount": payment_details.get("paid_amount"),
                "recipient": payment_details.get("recipient"),
                "due_date": payment_details.get("due_date"),
                "description": payment_details.get("description"),
                "customer_id": customer_id,
                "bank_details": payment_details.get("bank_details", {}),
                "payee_details": payment_details.get("payee_details", {}),
                "customer_details": payment_details.get("customer", {})
            })
            
            if not payment_result.get("success"):
                raise ValueError(payment_result.get("error", "Payment processing failed"))
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Payment processing failed: {str(e)}"
            )
        
        # Update invoice status to paid
        invoice_ref.update({
            "status": "paid",
            "paid_at": firestore.SERVER_TIMESTAMP,
            "payment_details": {
                "processed_at": datetime.now().isoformat(),
                "status": "success",
                "amount": payment_details.get("paid_amount"),
                "recipient": payment_details.get("recipient"),
                "description": payment_details.get("description"),
                "bank_details": payment_details.get("bank_details", {}),
                "file_processed": True,
                "file_path": str(local_path)
            }
        })
        
        # Get updated invoice data
        updated_invoice = invoice_ref.get().to_dict()
        updated_invoice["id"] = invoice_doc.id
        
        return {
            "success": True,
            "message": "Payment processed successfully",
            "invoice": serialize_firebase_data(updated_invoice),
            "payment_details": payment_details,
            "file": {
                "name": file_name,
                "path": str(local_path),
                "processed": True
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up downloaded file if it exists
        if 'local_path' in locals() and os.path.exists(local_path):
            try:
                os.remove(local_path)
            except Exception:
                pass

@app.get("/health")
async def health_check() -> Dict:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "1.0.0"
    }

@app.get("/payment-history")
async def get_payment_history(claims: Dict = Depends(verify_jwt)) -> Dict[str, List]:
    """Get payment history."""
    try:
        customer_id = claims.get("customer_id")
        if not customer_id:
            raise HTTPException(
                status_code=400,
                detail="Customer ID not found in token"
            )
            
        # Get payments from Firestore
        payments = []
        payment_docs = db.collection("invoices").where("customer_id", "==", customer_id).where("status", "==", "paid").stream()
        
        for doc in payment_docs:
            payment = doc.to_dict()
            payment["id"] = doc.id
            payments.append(serialize_firebase_data(payment))
            
        return {"payments": payments}
        
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