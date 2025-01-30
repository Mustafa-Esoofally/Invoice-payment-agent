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
        cred = credentials.Certificate("byrdeai-firebase-adminsdk-fbsvc-a168a9a31d.json")
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
    query: Optional[str] = "subject:invoice has:attachment newer_than:7d"
    max_results: Optional[int] = 10

class PaymentRequest(BaseModel):
    """Request model for invoice payment."""
    invoice_number: str
    paid_amount: float
    recipient: str

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
        return datetime.now().isoformat()  # For SERVER_TIMESTAMP, use current time in response
    elif isinstance(data, datetime):  # Add this line to handle Python datetime objects
        return data.isoformat()
    return data

async def get_customer_invoices(customer_id: str) -> List[Dict]:
    """Get all invoices for a customer from Firebase."""
    print(f"\n🔍 Filtering invoices for customer_id: {customer_id}")
    
    invoices = []
    query = db.collection("invoices").where("customer_id", "==", customer_id)
    docs = query.stream()
    
    for doc in docs:
        try:
            invoice_data = doc.to_dict()
            invoice_data["id"] = doc.id
            serialized_data = serialize_firebase_data(invoice_data)
            invoices.append(serialized_data)
            print(f"  ✓ Found invoice: {invoice_data.get('data', {}).get('invoice_number', 'No Number')}")
        except Exception as e:
            print(f"  ✗ Error processing invoice {doc.id}: {str(e)}")
    
    print(f"  📊 Total invoices found: {len(invoices)}")
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
    request: ScanInboxRequest = ScanInboxRequest(),
    claims: Dict = Depends(verify_jwt)
) -> Dict:
    """Get existing invoices for the authenticated customer."""
    try:
        print("\n" + "=" * 50)
        print("🔍 Fetching Customer Invoices")
        print("=" * 50)
        
        # Extract and validate customer_id from JWT token
        print("\n🔐 Validating Authentication...")
        customer_id = claims.get("customer_id")
        if not customer_id:
            print("❌ No customer_id found in JWT token")
            raise HTTPException(
                status_code=400, 
                detail="Customer ID not found in token"
            )
            
        print("\n👤 Authenticated Customer:")
        print(f"  ID: {customer_id}")
        print(f"  Name: {claims.get('name', 'Not provided')}")
        print(f"  Email: {claims.get('email', 'Not provided')}")
        print("-" * 30)

        # Get existing invoices for the authenticated customer
        existing_invoices = await get_customer_invoices(customer_id)
        
        # Calculate total amount
        total_amount = 0
        if existing_invoices:
            print("\n📄 Customer's Invoices:")
            for invoice in existing_invoices:
                await print_invoice_details(invoice)
                data = invoice.get("data", {})
                amount = data.get("amount", 0)
                total_amount += amount

        print("\n📊 Invoice Summary for Customer {customer_id}:")
        print(f"  Total Invoices: {len(existing_invoices)}")
        print(f"  Total Amount: USD {total_amount:,.2f}")
        print("=" * 50)

        return {
            "success": True,
            "message": f"Found {len(existing_invoices)} invoices for customer {customer_id}",
            "customer": {
                "id": customer_id,
                "name": claims.get('name', 'Not provided'),
                "email": claims.get('email', 'Not provided')
            },
            "invoices": existing_invoices,
            "summary": {
                "total_invoices": len(existing_invoices),
                "total_amount": total_amount
            }
        }

    except Exception as e:
        print(f"\n❌ Error Fetching Invoices: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

async def download_file(url: str, local_path: str) -> bool:
    """Download a file from URL to local path."""
    try:
        print("\nDownload Details:")
        print(f"  Original URL: {url}")
        print(f"  Target Path: {os.path.abspath(local_path)}")
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        
        # If the URL is a local file path, copy the file instead of downloading
        if os.path.exists(url):
            import shutil
            print("  Using local file copy method")
            shutil.copy2(url, local_path)
            return True
            
        # Otherwise, try to download from URL
        from urllib.parse import quote, urlparse, parse_qs, urlencode, unquote
        
        # Parse the URL
        parsed_url = urlparse(url)
        print(f"\nURL Components:")
        print(f"  Scheme: {parsed_url.scheme}")
        print(f"  Netloc: {parsed_url.netloc}")
        print(f"  Path: {parsed_url.path}")
        print(f"  Query: {parsed_url.query}")
        
        # For Firebase Storage URLs, handle the URL differently
        if 'firebasestorage.googleapis.com' in parsed_url.netloc:
            # Get the bucket and object path
            path_parts = parsed_url.path.split('/')
            # The object name is after /o/ in the path
            obj_name_idx = path_parts.index('o') + 1 if 'o' in path_parts else -1
            
            if obj_name_idx != -1 and obj_name_idx < len(path_parts):
                # Get the encoded object name
                obj_name = unquote(path_parts[obj_name_idx])
                print(f"\nFirebase Storage Object:")
                print(f"  Object Name: {obj_name}")
                
                # Create a new properly encoded URL
                encoded_obj_name = quote(obj_name, safe='')
                new_path = '/'.join(path_parts[:obj_name_idx]) + '/' + encoded_obj_name
                encoded_url = f"{parsed_url.scheme}://{parsed_url.netloc}{new_path}?{parsed_url.query}"
            else:
                encoded_url = url
        else:
            # For other URLs, use the original URL
            encoded_url = url
        
        print(f"\nDownload URL:")
        print(f"  Encoded URL: {encoded_url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        async with aiohttp.ClientSession() as session:
            print("\nMaking HTTP Request...")
            async with session.get(encoded_url, headers=headers) as response:
                print(f"  Status Code: {response.status}")
                print(f"  Content Type: {response.headers.get('content-type', 'unknown')}")
                print(f"  Content Length: {response.headers.get('content-length', 'unknown')} bytes")
                
                if response.status == 200:
                    with open(local_path, 'wb') as f:
                        total_size = 0
                        while True:
                            chunk = await response.content.read(8192)
                            if not chunk:
                                break
                            f.write(chunk)
                            total_size += len(chunk)
                            
                    file_size = os.path.getsize(local_path)
                    print(f"\nFile Download Complete:")
                    print(f"  ✓ Saved to: {os.path.abspath(local_path)}")
                    print(f"  ✓ File size: {file_size:,} bytes")
                    print(f"  ✓ MD5 hash: {response.headers.get('etag', 'unknown')}")
                    return True
                else:
                    print(f"\nDownload Failed:")
                    print(f"  ✗ Status Code: {response.status}")
                    print(f"  ✗ Error: {await response.text()}")
                    return False
    except Exception as e:
        print(f"\nError During Download:")
        print(f"  ✗ Type: {type(e).__name__}")
        print(f"  ✗ Message: {str(e)}")
        traceback.print_exc()
        return False

@app.post("/pay-invoice")
async def pay_invoice(
    request: PayInvoiceRequest,
    claims: Dict = Depends(verify_jwt)
) -> Dict:
    """Process payment for a specific invoice."""
    try:
        print("\n" + "=" * 50)
        print("💳 Processing Invoice Payment")
        print("=" * 50)
        
        # Extract and validate customer_id from JWT token
        print("\n🔐 Validating Authentication...")
        customer_id = claims.get("customer_id")
        if not customer_id:
            print("❌ No customer_id found in JWT token")
            raise HTTPException(
                status_code=400, 
                detail="Customer ID not found in token"
            )
            
        print("\n👤 Authenticated Customer:")
        print(f"  ID: {customer_id}")
        print(f"  Name: {claims.get('name', 'Not provided')}")
        print(f"  Email: {claims.get('email', 'Not provided')}")
        print("-" * 30)

        # Get the invoice from Firebase
        print(f"\n🔍 Fetching invoice {request.invoice_id}...")
        invoice_ref = db.collection("invoices").document(request.invoice_id)
        invoice_doc = invoice_ref.get()
        
        if not invoice_doc.exists:
            print("❌ Invoice not found")
            raise HTTPException(
                status_code=404,
                detail="Invoice not found"
            )
            
        # Get invoice data and serialize it
        invoice_data = invoice_doc.to_dict()
        invoice_data["id"] = invoice_doc.id
        
        # Verify the invoice belongs to the authenticated customer
        if invoice_data.get("customer_id") != customer_id:
            print("❌ Invoice does not belong to authenticated customer")
            raise HTTPException(
                status_code=403,
                detail="Not authorized to access this invoice"
            )
        
        # Print invoice details
        print("\n📄 Raw Invoice Data:")
        serialized_data = serialize_firebase_data(invoice_data)
        print(json.dumps(serialized_data, indent=2))
        await print_invoice_details(serialized_data)
        
        # Extract file_url from invoice data
        print("\n🔍 Looking for file URL in invoice data...")
        
        # Try to get file_url from all possible locations
        file_url = None
        file_name = None
        
        # First try to get from root level
        if "file_url" in invoice_data:
            file_url = invoice_data["file_url"]
            file_name = invoice_data.get("file_name")
            print(f"  ✓ Found file_url in root: {file_url}")
        
        # Then try in the data field
        elif "data" in invoice_data:
            data = invoice_data["data"]
            if isinstance(data, dict):
                if "file_url" in data:
                    file_url = data["file_url"]
                    file_name = data.get("file_name")
                    print(f"  ✓ Found file_url in data: {file_url}")
                elif "file" in data:
                    file_data = data["file"]
                    if isinstance(file_data, str):
                        file_url = file_data
                        print(f"  ✓ Found file_url in data.file: {file_url}")
                    elif isinstance(file_data, dict):
                        file_url = file_data.get("url")
                        file_name = file_data.get("name")
                        print(f"  ✓ Found file_url in data.file object: {file_url}")
            
        if not file_url:
            print("\n❌ No file URL found in invoice data")
            print("Available fields in invoice:")
            for key, value in invoice_data.items():
                print(f"  - {key}: {type(value)}")
            if "data" in invoice_data:
                print("\nAvailable fields in data:")
                data = invoice_data["data"]
                if isinstance(data, dict):
                    for key, value in data.items():
                        print(f"  - {key}: {type(value)}")
            raise HTTPException(
                status_code=400,
                detail="Invoice file URL not found"
            )
        
        # Convert file URL to proper path if it's a local file
        if os.path.isabs(file_url):
            file_url = os.path.normpath(file_url)
            print(f"  ✓ Normalized local file path: {file_url}")
        
        # Create downloads directory if it doesn't exist
        downloads_dir = Path("downloads")
        downloads_dir.mkdir(exist_ok=True)
        
        # Generate local file path - ensure safe filename
        if not file_name:
            file_name = f"invoice_{request.invoice_id}.pdf"
        else:
            # Replace potentially problematic characters in filename
            import re
            file_name = re.sub(r'[<>:"/\\|?*]', '_', file_name)
            
        local_path = downloads_dir / file_name
        
        # Download or copy the invoice file
        print(f"\n📥 Processing invoice file...")
        print(f"  Source: {file_url}")
        print(f"  Destination: {local_path}")
        
        if not await download_file(file_url, str(local_path)):
            print("❌ Failed to process invoice file")
            raise HTTPException(
                status_code=500,
                detail="Failed to process invoice file"
            )
        
        if not os.path.exists(local_path):
            print("❌ File was not downloaded correctly")
            raise HTTPException(
                status_code=500,
                detail="File was not downloaded correctly"
            )
            
        print(f"✅ File processed successfully ({os.path.getsize(local_path)} bytes)")
        
        # Update invoice status to processing
        print("\n📝 Updating invoice status to processing...")
        invoice_ref.update({
            "status": "processing",
            "processing_started_at": firestore.SERVER_TIMESTAMP,
            "local_file_path": str(local_path)
        })
        
        # Here you would typically integrate with a payment processor
        # For now, we'll just simulate a successful payment
        print("\n💰 Processing payment...")
        
        # Update invoice status to paid
        print("\n✅ Payment successful! Updating invoice status...")
        invoice_ref.update({
            "status": "paid",
            "paid_at": firestore.SERVER_TIMESTAMP,
            "payment_details": {
                "processed_at": datetime.now().isoformat(),
                "status": "success",
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
            "file": {
                "name": file_name,
                "path": str(local_path),
                "processed": True
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"\n❌ Error Processing Payment: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up downloaded file if it exists
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