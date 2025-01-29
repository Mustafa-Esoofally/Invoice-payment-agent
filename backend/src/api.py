"""FastAPI service for invoice processing using multi-agent system."""

from typing import Dict, Optional, List, Any
from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import json
from datetime import datetime, timedelta
import traceback
import jwt
import aiohttp
from pathlib import Path
from firebase_admin import initialize_app, credentials, firestore, storage, get_app
from dotenv import load_dotenv
from agents.payment_agent import process_payment
from agents.pdf_agent import extract_text

# Load environment variables
load_dotenv()

# Initialize Firebase
try:
    firebase_app = get_app()
    print("Using existing Firebase app")
except ValueError:
    try:
        cred = credentials.Certificate("../byrdeai-firebase-adminsdk-fbsvc-a168a9a31d.json")
        firebase_app = initialize_app(cred)
        print("Initialized new Firebase app")
    except Exception as e:
        print(f"Error initializing Firebase: {str(e)}")
        raise

db = firestore.client()
print("Connected to Firestore database")

print("\n🚀 Starting Invoice Payment Agent API")
print("=" * 50)

# JWT Settings
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key")  # Should be properly configured in .env
ALGORITHM = "HS256"

# Security
security = HTTPBearer()

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

def verify_jwt(credentials: HTTPAuthorizationCredentials = Security(security)) -> Dict:
    """Verify JWT token and return claims."""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        return payload
    except jwt.exceptions.InvalidTokenError as e:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid authentication credentials: {str(e)}"
        )

class ScanInboxRequest(BaseModel):
    """Request model for scanning inbox."""
    gmail_auth_token: str
    query: Optional[str] = "subject:invoice has:attachment newer_than:7d"
    max_results: Optional[int] = 10

class PaymentRequest(BaseModel):
    """Request model for invoice payment."""
    invoice_number: str
    paid_amount: float
    recipient: str

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
        return datetime.now().isoformat()  # For SERVER_TIMESTAMP, use current time in response
    elif isinstance(data, datetime):  # Add this line to handle Python datetime objects
        return data.isoformat()
    return data

async def get_customer_invoices(customer_id: str) -> List[Dict]:
    """Get all invoices for a customer from Firebase."""
    invoices = []
    docs = db.collection("invoices").where("customer_id", "==", customer_id).stream()
    
    for doc in docs:
        try:
            invoice_data = doc.to_dict()
            invoice_data["id"] = doc.id
            serialized_data = serialize_firebase_data(invoice_data)
            invoices.append(serialized_data)
        except Exception as e:
            print(f"Error processing invoice {doc.id}: {str(e)}")
    
    return invoices

async def mock_scan_emails(query: str, max_results: int) -> List[Dict]:
    """Mock function to simulate email scanning."""
    # Create test invoice file if it doesn't exist
    test_file = Path("test_data/mock-invoice-3.pdf")
    test_file.parent.mkdir(parents=True, exist_ok=True)
    
    if not test_file.exists():
        with open(test_file, "w") as f:
            f.write("""INVOICE

Invoice Number: INV-2024-003
Date: 2024-01-29
Due Date: 2024-02-28

Bill To:
Test Customer
123 Test Street
Test City, TC 12345

Description: Cloud Services - February 2024
Amount: $3,500.00
Currency: USD

Payment Details:
Bank: Test Bank
Account Holder: New Tech Corp
Account Type: Checking
Account Number: 1234567890
Routing Number: 987654321

Please make payment by the due date.
Thank you for your business!
""")
    
    return [
        {
            "invoice_number": "INV-2024-003",
            "amount": 3500.00,
            "currency": "USD",
            "due_date": (datetime.now() + timedelta(days=30)).isoformat(),
            "recipient": "New Tech Corp",
            "description": "Cloud Services - February 2024",
            "file_url": str(test_file.absolute()),
            "file_name": "invoice-3.pdf",
            "bank_details": {
                "account_name": "New Tech Corp",
                "account_number": "1234567890",
                "routing_number": "987654321",
                "bank_name": "Test Bank",
                "account_type": "checking"
            },
            "metadata": {
                "invoice_date": datetime.now().isoformat(),
                "payment_terms": "Net 30",
                "po_number": "PO-2024-003",
                "tax_amount": 350.00,
                "subtotal": 3150.00
            }
        }
    ]

async def print_invoice_details(invoice: Dict) -> None:
    """Print invoice details in a readable format."""
    data = invoice.get("data", {})
    print("\n" + "=" * 50)
    print(f"📄 Invoice Details:")
    print(f"  ID: {invoice.get('id')}")
    print(f"  Status: {invoice.get('status', 'unknown')}")
    print(f"  Created At: {invoice.get('created_at')}")
    print(f"  Customer ID: {invoice.get('customer_id')}")
    print("\n  Invoice Data:")
    print(f"    Number: {data.get('invoice_number')}")
    print(f"    Amount: {data.get('currency', 'USD')} {data.get('amount')}")
    print(f"    Recipient: {data.get('recipient')}")
    print(f"    Due Date: {data.get('due_date')}")
    print(f"    Description: {data.get('description')}")
    print(f"    File: {data.get('file_name')}")
    print("=" * 50)

@app.post("/scan-inbox")
async def scan_inbox(
    request: ScanInboxRequest,
    claims: Dict = Depends(verify_jwt)
) -> Dict:
    """Scan inbox for invoices and store them in Firebase."""
    try:
        print("\n🔍 Starting inbox scan...")
        
        customer_id = claims.get("customer_id")
        if not customer_id:
            raise HTTPException(status_code=400, detail="Customer ID not found in token")
            
        print(f"👤 Customer ID: {customer_id}")
        print(f"🔎 Query: {request.query}")
        print(f"📊 Max Results: {request.max_results}")

        # Get existing invoices for the customer
        print("\n📂 Fetching existing invoices from Firebase...")
        existing_invoices = await get_customer_invoices(customer_id)
        print(f"📊 Found {len(existing_invoices)} existing invoices")
        
        # Print existing invoice details
        total_amount = 0
        for invoice in existing_invoices:
            amount = invoice.get("data", {}).get("amount", 0)
            total_amount += amount
        
        # Mock email scanning instead of using process_invoice_emails
        print("\n📧 Scanning for new invoices...")
        new_invoice_data = await mock_scan_emails(
            query=request.query,
            max_results=request.max_results
        )

        # Store new invoices in Firebase
        new_invoices = []
        current_time = datetime.now().isoformat()
        
        print(f"\n💾 Storing {len(new_invoice_data)} new invoices in Firebase...")
        for invoice in new_invoice_data:
            # Create test invoice file if it doesn't exist
            test_file = Path("test_data/mock-invoice-3.pdf")
            test_file.parent.mkdir(parents=True, exist_ok=True)
            
            if not test_file.exists():
                with open(test_file, "w") as f:
                    f.write("""INVOICE

Invoice Number: INV-2024-003
Date: 2024-01-29
Due Date: 2024-02-28

Bill To:
Test Customer
123 Test Street
Test City, TC 12345

Description: Cloud Services - February 2024
Amount: $3,500.00
Currency: USD

Payment Details:
Bank: Test Bank
Account Holder: New Tech Corp
Account Type: Checking
Account Number: 1234567890
Routing Number: 987654321

Please make payment by the due date.
Thank you for your business!
""")
            
            # Update file URL to use local test file
            invoice["file_url"] = str(test_file.absolute())
            
            # First create the document data
            invoice_data = {
                "customer_id": customer_id,
                "created_at": firestore.SERVER_TIMESTAMP,
                "status": "pending",
                "data": invoice,
                "source": "email_scan"
            }
            
            # Store in Firebase
            invoice_ref = db.collection("invoices").document()
            invoice_ref.set(invoice_data)
            
            # Create response data with current timestamp
            response_data = {
                **invoice_data,
                "id": invoice_ref.id,
                "created_at": current_time
            }
            new_invoices.append(response_data)
            total_amount += invoice.get("amount", 0)

        print("\n📊 Scan Summary:")
        print(f"  Total Invoices: {len(existing_invoices) + len(new_invoices)}")
        print(f"  - Existing: {len(existing_invoices)}")
        print(f"  - New: {len(new_invoices)}")
        print(f"  Total Amount: USD {total_amount:,.2f}")
        print("=" * 50)

        return {
            "success": True,
            "message": f"Processed {len(new_invoices)} new invoices",
            "existing_invoices": existing_invoices,
            "new_invoices": new_invoices,
            "summary": {
                "total_invoices": len(existing_invoices) + len(new_invoices),
                "existing_count": len(existing_invoices),
                "new_count": len(new_invoices),
                "total_amount": total_amount
            }
        }

    except Exception as e:
        print(f"\n❌ Scan Inbox Error: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

async def download_file(url: str, local_path: str) -> bool:
    """Download a file from URL to local path."""
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    with open(local_path, 'wb') as f:
                        while True:
                            chunk = await response.content.read(8192)
                            if not chunk:
                                break
                            f.write(chunk)
                    return True
                return False
    except Exception as e:
        print(f"Error downloading file: {str(e)}")
        return False

@app.post("/pay-invoice/{invoice_id}")
async def pay_invoice(
    invoice_id: str,
    claims: Dict = Depends(verify_jwt)
) -> Dict:
    """Pay an invoice using Payman."""
    try:
        print("\n💳 Starting Invoice Payment Process")
        print("=" * 50)
        
        customer_id = claims.get("customer_id")
        if not customer_id:
            print("❌ No customer_id found in JWT claims")
            raise HTTPException(status_code=400, detail="Customer ID not found in token")
            
        print(f"👤 Customer ID: {customer_id}")
        print(f"📄 Invoice ID: {invoice_id}")

        # Get invoice from Firebase
        print("\n🔍 Fetching invoice from Firebase...")
        invoice_ref = db.collection("invoices").document(invoice_id)
        invoice = invoice_ref.get()
        
        if not invoice.exists:
            print(f"❌ Invoice {invoice_id} not found in Firebase")
            raise HTTPException(status_code=404, detail="Invoice not found")
            
        invoice_data = invoice.to_dict()
        invoice_data["id"] = invoice_id
        print("\n📄 Invoice Data:")
        print("-" * 30)
        print(json.dumps(serialize_firebase_data(invoice_data), indent=2))
        
        # Verify ownership
        if invoice_data["customer_id"] != customer_id:
            print(f"❌ Invoice belongs to {invoice_data['customer_id']}, but request is from {customer_id}")
            raise HTTPException(status_code=403, detail="Not authorized to pay this invoice")
            
        # Check if already paid
        if invoice_data["status"] == "paid":
            print("❌ Invoice is already paid")
            raise HTTPException(status_code=400, detail="Invoice already paid")

        # Get file URL from invoice data
        file_url = invoice_data.get("data", {}).get("file_url")
        if not file_url:
            print("❌ No file_url found in invoice data")
            raise HTTPException(status_code=400, detail="Invoice file URL not found")

        print(f"\n📄 File URL: {file_url}")

        # Download PDF file
        print("\n📥 Downloading invoice PDF...")
        downloads_dir = Path("downloads")
        downloads_dir.mkdir(exist_ok=True)
        local_path = downloads_dir / f"invoice_{invoice_id}.pdf"
        print(f"Saving to: {local_path}")
        
        if not await download_file(file_url, str(local_path)):
            print("❌ Failed to download invoice file")
            raise HTTPException(status_code=500, detail="Failed to download invoice file")

        print("✅ File downloaded successfully")

        # Process PDF and extract payment information
        print("\n🔍 Extracting payment information from PDF...")
        extraction_result = extract_text(str(local_path))
        
        if not extraction_result["success"]:
            print(f"❌ Extraction failed: {extraction_result.get('error')}")
            raise HTTPException(
                status_code=400, 
                detail=f"Failed to extract payment information: {extraction_result.get('error')}"
            )

        # Get payment information
        payment_info = extraction_result.get("payment_info", {})
        if "error" in payment_info:
            print(f"❌ Invalid payment info: {payment_info['error']}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid payment information: {payment_info['error']}"
            )

        print("\n💳 Extracted Payment Info:")
        print("-" * 30)
        print(json.dumps(payment_info, indent=2))

        # Update invoice data with extracted information
        invoice_data.update(payment_info)

        # Process payment using payment agent
        print("\n💸 Processing payment...")
        payment_result = await process_payment(invoice_data)
        
        if not payment_result["success"]:
            error_detail = payment_result.get("error", "Payment processing failed")
            print(f"\n❌ Payment Failed: {error_detail}")
            
            # Update invoice with failure details
            print("\n📝 Updating invoice with failure details...")
            invoice_ref.update({
                "last_payment_attempt": {
                    "timestamp": firestore.SERVER_TIMESTAMP,
                    "error": error_detail,
                    "status": "failed"
                }
            })
            
            raise HTTPException(status_code=400, detail=error_detail)

        # Update invoice status on success
        print("\n📝 Updating invoice status to paid...")
        invoice_ref.update({
            "status": "paid",
            "paid_at": firestore.SERVER_TIMESTAMP,
            "payment_id": payment_result.get("payment_id"),
            "payment_method": payment_result.get("payment_method")
        })

        print("\n✅ Payment successful!")
        print(f"Payment ID: {payment_result.get('payment_id')}")
        
        return {
            "success": True,
            "message": "Payment processed successfully",
            "payment_id": payment_result.get("payment_id"),
            "invoice_id": invoice_id,
            "status": "paid"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"\n❌ Payment Error: {str(e)}")
        print("Stack trace:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up downloaded file
        if 'local_path' in locals() and local_path.exists():
            try:
                print("\n🧹 Cleaning up downloaded file...")
                local_path.unlink()
                print("✅ File cleanup successful")
            except Exception as e:
                print(f"⚠️ Error cleaning up file: {str(e)}")

@app.get("/health")
async def health_check() -> Dict:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "1.0.0"
    }

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