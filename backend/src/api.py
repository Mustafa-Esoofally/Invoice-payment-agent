"""FastAPI service for invoice processing using multi-agent system."""

from typing import Dict, Optional, List, Any
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import json
from datetime import datetime, timedelta
import re
from pathlib import Path
from firebase_admin import initialize_app, credentials, firestore, storage
from dotenv import load_dotenv

from auth.auth import jwt_auth
from agents.pdf_agent import extract_text
from agents.payment_agent import process_payment
from tools.payment_tools import BalanceTool, SearchPayeesTool, SendPaymentTool, CheckoutUrlTool

# Load environment variables and validate
load_dotenv()

# Validate required environment variables
required_env_vars = [
    "OPENAI_API_KEY",
    "COMPOSIO_API_KEY",
    "JWT_SECRET"
]

# Add Firebase environment variables if running on Render
if os.getenv('RENDER'):
    required_env_vars.extend([
        "FIREBASE_PROJECT_ID",
        "FIREBASE_PRIVATE_KEY_ID",
        "FIREBASE_PRIVATE_KEY",
        "FIREBASE_CLIENT_EMAIL",
        "FIREBASE_CLIENT_ID",
        "FIREBASE_CLIENT_CERT_URL",
        "FIREBASE_STORAGE_BUCKET"
    ])

missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

# Initialize Firebase Admin SDK
try:
    # Check if running in production (Render)
    if os.getenv('RENDER'):
        # Use environment variable for Firebase credentials
        firebase_creds = {
            "type": "service_account",
            "project_id": os.getenv('FIREBASE_PROJECT_ID'),
            "private_key_id": os.getenv('FIREBASE_PRIVATE_KEY_ID'),
            "private_key": os.getenv('FIREBASE_PRIVATE_KEY').replace('\\n', '\n'),
            "client_email": os.getenv('FIREBASE_CLIENT_EMAIL'),
            "client_id": os.getenv('FIREBASE_CLIENT_ID'),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": os.getenv('FIREBASE_CLIENT_CERT_URL')
        }
        cred = credentials.Certificate(firebase_creds)
    else:
        # Local development - use credentials file
        cred = credentials.Certificate("payman-agent-render-firebase-adminsdk-fbsvc-76639f1307.json")
    
    app = initialize_app(cred, {
        'storageBucket': os.getenv('FIREBASE_STORAGE_BUCKET', 'payman-agent-render.firebasestorage.app')
    })
    db = firestore.client()
    bucket = storage.bucket()
except Exception as e:
    raise ValueError(f"Failed to initialize Firebase: {str(e)}")

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

class ScanInboxRequest(BaseModel):
    """Request model for scanning inbox."""
    query: Optional[str] = "subject:invoice has:attachment newer_than:7d"
    max_results: Optional[int] = 10

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

async def get_customer_invoices(customer_id: str) -> List[Dict]:
    """Get all invoices for a customer from Firebase."""
    invoices = []
    query = db.collection("invoices").where("customer_id", "==", customer_id)
    docs = query.stream()
    
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

@app.post("/scan-inbox")
async def scan_inbox(
    request: ScanInboxRequest = ScanInboxRequest(),
    customer_id: str = Depends(jwt_auth)
) -> Dict:
    """Get existing invoices for the authenticated customer."""
    try:
        # Get existing invoices for the authenticated customer
        existing_invoices = await get_customer_invoices(customer_id)
        
        # Calculate total amount
        total_amount = sum(invoice.get("data", {}).get("amount", 0) for invoice in existing_invoices)

        return {
            "success": True,
            "message": f"Found {len(existing_invoices)} invoices for customer {customer_id}",
            "customer": {
                "id": customer_id
            },
            "invoices": existing_invoices,
            "summary": {
                "total_invoices": len(existing_invoices),
                "total_amount": total_amount
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/pay-invoice")
async def pay_invoice(
    request: PayInvoiceRequest,
    customer_id: str = Depends(jwt_auth)
) -> Dict:
    """Process payment for a specific invoice."""
    try:
        print("\n" + "="*50)
        print("💳 PAYMENT PROCESSING WORKFLOW")
        print("="*50)

        # Get the invoice from Firebase
        print(f"\n1️⃣ Fetching invoice {request.invoice_id}...")
        invoice_ref = db.collection("invoices").document(request.invoice_id)
        invoice_doc = invoice_ref.get()
        
        if not invoice_doc.exists:
            print("❌ Invoice not found")
            raise HTTPException(status_code=404, detail="Invoice not found")
            
        # Get invoice data and verify ownership
        print("\n2️⃣ Verifying invoice ownership...")
        invoice_data = invoice_doc.to_dict()
        invoice_data["id"] = invoice_doc.id
        print(f"Invoice Data: {json.dumps(serialize_firebase_data(invoice_data), indent=2)}")
        
        if invoice_data.get("customer_id") != customer_id:
            print(f"❌ Access denied - Invoice belongs to {invoice_data.get('customer_id')}, not {customer_id}")
            raise HTTPException(status_code=403, detail="Not authorized to access this invoice")
        print("✅ Invoice ownership verified")
        
        # Get and validate file path
        print("\n3️⃣ Validating file path...")
        file_path = invoice_data.get("file_path")
        if not file_path:
            print("❌ No file path found in invoice data")
            raise HTTPException(status_code=400, detail="Invoice file path not found")
        print(f"✅ File path found: {file_path}")
        
        # Setup file download
        print("\n4️⃣ Setting up file download...")
        downloads_dir = Path("downloads")
        downloads_dir.mkdir(exist_ok=True)
        
        file_name = os.path.basename(file_path)
        if not file_name:
            file_name = f"invoice_{request.invoice_id}.pdf"
        else:
            file_name = re.sub(r'[<>:"/\\|?*]', '_', file_name)
            
        local_path = downloads_dir / file_name
        print(f"Download path: {local_path}")
        
        try:
            # Download file
            print("\n5️⃣ Downloading invoice file...")
            blob = bucket.blob(file_path)
            blob.download_to_filename(str(local_path))
            
            if not os.path.exists(local_path):
                print("❌ File download failed - File not found at local path")
                raise HTTPException(status_code=500, detail="Failed to download invoice file")
            print(f"✅ File downloaded successfully ({os.path.getsize(local_path)} bytes)")
            
        except Exception as e:
            print(f"❌ File download error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to download invoice file: {str(e)}")
        
        # Update status to processing
        print("\n6️⃣ Updating invoice status to processing...")
        invoice_ref.update({
            "status": "processing",
            "processing_started_at": firestore.SERVER_TIMESTAMP,
            "local_file_path": str(local_path)
        })
        print("✅ Status updated")

        try:
            # Extract payment details
            print("\n7️⃣ Extracting payment details from PDF...")
            payment_details = extract_text(str(local_path), extract_metadata=True)
            
            if not payment_details or "error" in payment_details:
                error_msg = payment_details.get("error", "Failed to extract payment details from PDF")
                print(f"❌ Extraction failed: {error_msg}")
                raise ValueError(error_msg)
            
            print("Extracted Payment Details:")
            print(json.dumps(payment_details, indent=2))
            
            # Save extracted details regardless of payment outcome
            metadata_update = {
                "extracted_details": payment_details,
                "last_updated": firestore.SERVER_TIMESTAMP,
                "metadata": {
                    "extraction_timestamp": firestore.SERVER_TIMESTAMP,
                    "invoice_number": payment_details.get("invoice_number"),
                    "invoice_date": payment_details.get("date"),
                    "due_date": payment_details.get("due_date"),
                    "amount": payment_details.get("paid_amount"),
                    "recipient": payment_details.get("recipient"),
                    "description": payment_details.get("description"),
                    "bank_details": {
                        "type": payment_details.get("bank_details", {}).get("type"),
                        "bank_name": payment_details.get("bank_details", {}).get("bank_name"),
                        "account_holder": payment_details.get("bank_details", {}).get("account_holder_name")
                    },
                    "customer_info": payment_details.get("customer", {}),
                    "payee_info": payment_details.get("payee_details", {})
                }
            }
            invoice_ref.update(metadata_update)
            print("✅ Metadata saved to Firebase")
            
        except Exception as e:
            print(f"❌ Payment details extraction error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to extract payment details: {str(e)}")
        
        try:
            # Process payment
            print("\n9️⃣ Processing payment...")
            print("\n[PAYMAN] Payment Flow:")
            print("-" * 50)
            
            # 1. Check balance first
            print("\n[PAYMAN] 1. Checking balance...")
            balance_tool = BalanceTool()
            balance_result = balance_tool.run("")
            print(f"Balance check result: {balance_result}")
            
            # Save balance check result
            invoice_ref.update({
                "payment_processing": {
                    "balance_check": {
                        "timestamp": firestore.SERVER_TIMESTAMP,
                        "available_balance": float(balance_result.split("$")[1].replace(",", "").split()[0]),
                        "required_amount": payment_details.get("paid_amount"),
                        "status": "insufficient" if "insufficient" in balance_result.lower() else "sufficient"
                    }
                }
            })
            
            # 2. Search for existing payee
            print("\n[PAYMAN] 2. Searching for payee...")
            search_tool = SearchPayeesTool()
            search_params = {
                "name": payment_details.get("recipient"),
                "type": "US_ACH"
            }
            search_result = search_tool.run(json.dumps(search_params))
            print(f"Search result: {search_result}")
            
            # Save payee search result
            if isinstance(search_result, list) and search_result:
                payee_data = search_result[0]
                invoice_ref.update({
                    "payment_processing.payee_details": {
                        "timestamp": firestore.SERVER_TIMESTAMP,
                        "payee_id": payee_data.get("id"),
                        "name": payee_data.get("name"),
                        "status": payee_data.get("status"),
                        "type": payee_data.get("type"),
                        "contact_details": payee_data.get("contactDetails", {})
                    }
                })
            
            # 3. Prepare payment data
            payment_data = {
                "invoice_id": request.invoice_id,
                "invoice_number": payment_details.get("invoice_number"),
                "paid_amount": payment_details.get("paid_amount"),
                "amount": payment_details.get("paid_amount"),
                "recipient": payment_details.get("recipient"),
                "due_date": payment_details.get("due_date"),
                "description": payment_details.get("description"),
                "customer_id": customer_id,
                "bank_details": payment_details.get("bank_details", {}),
                "payee_details": payment_details.get("payee_details", {}),
                "customer_details": payment_details.get("customer", {})
            }
            print("\n[PAYMAN] 3. Payment Request Data:")
            print(json.dumps(payment_data, indent=2))
            
            # Save payment request data
            invoice_ref.update({
                "payment_processing.payment_request": {
                    "timestamp": firestore.SERVER_TIMESTAMP,
                    "request_data": payment_data
                }
            })
            
            # 4. Process payment
            print("\n[PAYMAN] 4. Processing payment...")
            payment_result = await process_payment(payment_data)
            
            if not payment_result.get("success"):
                error_msg = payment_result.get("error", "Payment processing failed")
                print(f"\n[PAYMAN] ❌ Payment failed: {error_msg}")
                
                # Save failure details
                invoice_ref.update({
                    "status": "failed",
                    "payment_processing.status": "failed",
                    "payment_processing.error": {
                        "timestamp": firestore.SERVER_TIMESTAMP,
                        "message": error_msg,
                        "details": payment_result
                    }
                })
                raise HTTPException(status_code=400, detail=error_msg)
            
            print("\n[PAYMAN] ✅ Payment processed successfully")
            print("\n[PAYMAN] Payment Response Details:")
            print("-" * 50)
            print(f"• Reference ID: {payment_result.get('payment_id')}")
            print(f"• Status: {payment_result.get('status', 'completed')}")
            print(f"• Payment Method: {payment_result.get('payment_method')}")
            if payment_result.get('external_reference'):
                print(f"• External Reference: {payment_result.get('external_reference')}")
            print(f"• Invoice Number: {payment_result.get('invoice_number')}")
            print("-" * 50)
            
            print("\nPayment Result:")
            print(json.dumps(payment_result, indent=2))
            
            # Save successful payment details
            payment_update = {
                "status": "paid",
                "paid_at": datetime.now().isoformat(),
                "payment_processing": {
                    "status": "completed",
                    "completed_at": datetime.now().isoformat(),
                    "payment_details": {
                        "processed_at": datetime.now().isoformat(),
                        "status": "success",
                        "amount": payment_details.get("paid_amount"),
                        "recipient": payment_details.get("recipient"),
                        "description": payment_details.get("description"),
                        "bank_details": payment_details.get("bank_details", {}),
                        "payment_id": payment_result.get("payment_id"),
                        "payment_method": payment_result.get("payment_method"),
                        "external_reference": payment_result.get("external_reference"),
                        "transaction_details": payment_result
                    },
                    "file_processed": True,
                    "file_path": str(local_path)
                }
            }
            print("Final Update Data:")
            print(json.dumps(payment_update, indent=2))
            
            # Convert timestamps before updating Firebase
            firebase_payment_update = payment_update.copy()
            firebase_payment_update["paid_at"] = firestore.SERVER_TIMESTAMP
            firebase_payment_update["payment_processing"]["completed_at"] = firestore.SERVER_TIMESTAMP
            
            invoice_ref.update(firebase_payment_update)
            print("✅ Payment finalized")
        
        except Exception as e:
            print(f"\n❌ Payment processing error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Payment processing failed: {str(e)}")
        finally:
            # Clean up downloaded file
            if 'local_path' in locals() and os.path.exists(local_path):
                try:
                    print("\n🧹 Cleaning up downloaded file...")
                    os.remove(local_path)
                    print("✅ File cleanup successful")
                except Exception as e:
                    print(f"⚠️ File cleanup failed: {str(e)}")

        # Get updated invoice data
        updated_invoice = invoice_ref.get().to_dict()
        updated_invoice["id"] = invoice_doc.id
        
        response = {
            "success": True,
            "message": "Payment processed successfully",
            "invoice": serialize_firebase_data(updated_invoice),
            "payment_details": {
                "payment_id": payment_result.get("payment_id"),
                "status": payment_result.get("status", "completed"),
                "amount": payment_details.get("paid_amount"),
                "recipient": payment_details.get("recipient"),
                "payment_method": payment_result.get("payment_method"),
                "external_reference": payment_result.get("external_reference"),
                "processed_at": datetime.now().isoformat(),
                "description": payment_details.get("description"),
                "invoice_number": payment_details.get("invoice_number"),
                "transaction_details": payment_result
            },
            "file": {
                "name": file_name,
                "path": str(local_path),
                "processed": True
            }
        }

        print("\n✨ Payment Processing Complete!")
        print("="*50)
        return response

    except Exception as e:
        print(f"\n❌ Unexpected Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check() -> Dict:
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )