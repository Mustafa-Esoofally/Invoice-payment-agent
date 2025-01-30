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
        # Get the current file's directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        cred_path = os.path.join(current_dir, "payman-agent-render-firebase-adminsdk-fbsvc-76639f1307.json")
        print(f"\n🔑 Firebase Credentials:")
        print(f"  Directory: {current_dir}")
        print(f"  Full path: {cred_path}")
        print(f"  File exists: {os.path.exists(cred_path)}")
        
        # Read and validate the credentials file
        with open(cred_path, 'r', encoding='utf-8') as f:
            cred_json = json.load(f)
            print("\n📄 Credential File Contents:")
            print(f"  type: {cred_json.get('type')}")
            print(f"  project_id: {cred_json.get('project_id')}")
            print(f"  client_email: {cred_json.get('client_email')}")
            print(f"  private_key_id: {cred_json.get('private_key_id')}")
            print(f"  Has private_key: {'private_key' in cred_json}")
            
            # Verify private key format
            private_key = cred_json.get('private_key', '')
            if private_key:
                print("\n🔐 Private Key Validation:")
                print(f"  Starts with: {private_key.startswith('-----BEGIN PRIVATE KEY-----')}")
                print(f"  Ends with: {private_key.endswith('-----END PRIVATE KEY-----\n')}")
                print(f"  Length: {len(private_key)} characters")
                print(f"  Line endings: {'\\n' in private_key}")
        
        # Initialize credentials
        print("\n🔄 Initializing Firebase Admin SDK:")
        cred = credentials.Certificate(cred_path)
        print("  ✓ Credentials initialized")
        
        # Initialize app with explicit configuration
        firebase_app = initialize_app(cred, {
            'storageBucket': 'payman-agent-render.firebasestorage.app',
            'projectId': cred_json['project_id']
        })
        print("  ✓ Firebase app initialized")
        
        # Test connection
        db = firestore.client()
        test_doc = db.collection('test').document('test')
        print("  ✓ Firestore connection tested")
        
    except json.JSONDecodeError as e:
        print(f"\n❌ Error parsing credentials JSON:")
        print(f"  Error: {str(e)}")
        raise
    except Exception as e:
        print(f"\n❌ Error initializing Firebase:")
        print(f"  Type: {type(e).__name__}")
        print(f"  Error: {str(e)}")
        print("\nStack trace:")
        traceback.print_exc()
        raise

# Initialize Firestore
db = firestore.client()
print("Connected to Firestore database")

# Initialize Storage bucket
bucket = storage.bucket('payman-agent-render.firebasestorage.app')
print("Connected to Storage bucket")

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
            
        # For Firebase Storage URLs
        if 'storage.googleapis.com' in url or 'firebasestorage.googleapis.com' in url:
            try:
                # Extract file path from URL
                from urllib.parse import urlparse, unquote
                parsed_url = urlparse(url)
                path_parts = parsed_url.path.split('/o/')
                
                if len(path_parts) == 2:
                    # URL format: https://storage.googleapis.com/BUCKET_NAME/o/FILE_PATH
                    file_path = unquote(path_parts[1].split('?')[0])
                else:
                    # Alternative format: extract from the full path
                    path_segments = parsed_url.path.split('/')
                    if len(path_segments) >= 4:  # At least /BUCKET/o/FILE_PATH
                        file_path = unquote('/'.join(path_segments[3:]).split('?')[0])
                    else:
                        raise ValueError("Could not extract file path from URL")
                
                print(f"  Firebase Storage details:")
                print(f"    File path: {file_path}")
                
                # Use Firebase Admin SDK to download
                try:
                    print(f"  Accessing Firebase Storage...")
                    blob = bucket.blob(file_path)
                    
                    # Download using Firebase Admin SDK
                    print(f"  Downloading blob to {local_path}...")
                    blob.download_to_filename(local_path)
                    
                    # Verify download
                    if os.path.exists(local_path):
                        file_size = os.path.getsize(local_path)
                        print(f"  ✓ File downloaded successfully ({file_size:,} bytes)")
                        return True
                    else:
                        print("  ✗ File was not downloaded")
                        return False
                
                except Exception as e:
                    print(f"  ✗ Firebase Storage error: {str(e)}")
                    return False
                    
            except Exception as e:
                print(f"  ✗ Error processing Firebase Storage URL: {str(e)}")
                traceback.print_exc()
                return False
        
        # For other URLs, use aiohttp
        print("  Using HTTP download method")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    with open(local_path, 'wb') as f:
                        while True:
                            chunk = await response.content.read(8192)
                            if not chunk:
                                break
                            f.write(chunk)
                    
                    file_size = os.path.getsize(local_path)
                    print(f"  ✓ File downloaded successfully ({file_size:,} bytes)")
                    return True
                else:
                    print(f"  ✗ HTTP download failed with status {response.status}")
                    print(f"  ✗ Error: {await response.text()}")
                    return False
                    
    except Exception as e:
        print(f"\nDownload Error:")
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
        
        # Get the file path from invoice data
        print("\n🔍 Looking for file path in invoice data...")
        file_path = invoice_data.get("file_path")
        if not file_path:
            print("❌ No file path found in invoice data")
            raise HTTPException(
                status_code=400,
                detail="Invoice file path not found"
            )
        print(f"  ✓ Found file path: {file_path}")
        
        # Create downloads directory if it doesn't exist
        downloads_dir = Path("downloads")
        downloads_dir.mkdir(exist_ok=True)
        
        # Generate local file path - ensure safe filename
        file_name = os.path.basename(file_path)
        if not file_name:
            file_name = f"invoice_{request.invoice_id}.pdf"
        else:
            # Replace potentially problematic characters in filename
            import re
            file_name = re.sub(r'[<>:"/\\|?*]', '_', file_name)
            
        local_path = downloads_dir / file_name
        
        # Download the invoice file using Firebase Storage
        print(f"\n📥 Processing invoice file...")
        print(f"  Source path: {file_path}")
        print(f"  Destination: {local_path}")
        
        try:
            # Download using Firebase Admin SDK
            print(f"  Accessing Firebase Storage...")
            blob = bucket.blob(file_path)
            
            # Download the file
            print(f"  Downloading blob to {local_path}...")
            blob.download_to_filename(str(local_path))
            
            # Verify download
            if os.path.exists(local_path):
                file_size = os.path.getsize(local_path)
                print(f"  ✓ File downloaded successfully ({file_size:,} bytes)")
            else:
                print("  ✗ File was not downloaded")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to download invoice file"
                )
        except Exception as e:
            print(f"  ✗ Firebase Storage error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to download invoice file: {str(e)}"
            )
        
        # Update invoice status to processing
        print("\n📝 Updating invoice status to processing...")
        invoice_ref.update({
            "status": "processing",
            "processing_started_at": firestore.SERVER_TIMESTAMP,
            "local_file_path": str(local_path)
        })

        # Extract payment details from PDF using PDF Agent
        print("\n📄 Extracting payment details from PDF...")
        try:
            # Extract text and payment details from PDF
            payment_details = extract_text(str(local_path), extract_metadata=True, debug=True)
            
            if not payment_details or "error" in payment_details:
                raise ValueError(payment_details.get("error", "Failed to extract payment details from PDF"))
                
            print("\n💳 Extracted Payment Details:")
            print(json.dumps(payment_details, indent=2))
            
            # Update invoice with extracted details
            invoice_ref.update({
                "extracted_details": payment_details,
                "last_updated": firestore.SERVER_TIMESTAMP
            })
            
        except Exception as e:
            print(f"  ✗ Error extracting payment details: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to extract payment details: {str(e)}"
            )
        
        # Process payment using extracted details
        print("\n💰 Processing payment...")
        try:
            # Process payment using payment agent
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
                
            print("  ✓ Payment processed successfully")
            
        except Exception as e:
            print(f"  ✗ Payment processing error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Payment processing failed: {str(e)}"
            )
        
        # Update invoice status to paid
        print("\n✅ Payment successful! Updating invoice status...")
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
        print(f"\n❌ Error Processing Payment: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up downloaded file if it exists
        if 'local_path' in locals() and os.path.exists(local_path):
            try:
                print("\n🧹 Cleaning up downloaded file...")
                os.remove(local_path)
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