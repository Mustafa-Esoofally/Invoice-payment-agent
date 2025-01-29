"""Test script for the payment endpoint."""

import os
import sys
import jwt
import requests
import json
import traceback
from datetime import datetime, timedelta
from dotenv import load_dotenv
from firebase_admin import credentials, initialize_app, firestore

def test_payment_endpoint():
    """Test the payment endpoint."""
    try:
        print("\n🔄 Loading environment variables...")
        load_dotenv()
        jwt_secret = os.getenv("JWT_SECRET")
        if not jwt_secret:
            raise ValueError("JWT_SECRET not found in environment variables")
        print("✅ Environment variables loaded")
        
        # Test parameters
        customer_id = "test_customer"
        base_url = "http://localhost:8000"
        
        print("\n🔄 Initializing Firebase...")
        try:
            cred = credentials.Certificate("byrdeai-firebase-adminsdk-fbsvc-a168a9a31d.json")
            app = initialize_app(cred)
            db = firestore.client()
            print("✅ Firebase initialized")
        except Exception as firebase_error:
            print(f"❌ Firebase initialization error: {str(firebase_error)}")
            traceback.print_exc()
            return
        
        # Create JWT token
        print("\n🔄 Creating JWT token...")
        try:
            payload = {
                "customer_id": customer_id,
                "exp": datetime.utcnow() + timedelta(hours=1)
            }
            token = jwt.encode(payload, jwt_secret, algorithm="HS256")
            print(f"✅ JWT token created: {token}")
        except Exception as jwt_error:
            print(f"❌ JWT creation error: {str(jwt_error)}")
            traceback.print_exc()
            return
        
        # Get test invoice ID
        print("\n🔄 Getting test invoice...")
        try:
            invoices = db.collection("customers").document(customer_id)\
                        .collection("invoices")\
                        .where("status", "==", "pending")\
                        .order_by("created_at", direction=firestore.Query.DESCENDING)\
                        .limit(1)\
                        .stream()
            
            invoice_id = None
            for invoice in invoices:
                invoice_id = invoice.id
                print(f"✅ Found invoice:")
                print(f"ID: {invoice.id}")
                print("Data:", invoice.to_dict())
                break
                
            if not invoice_id:
                raise ValueError("No pending invoices found")
        except Exception as invoice_error:
            print(f"❌ Invoice retrieval error: {str(invoice_error)}")
            traceback.print_exc()
            return
        
        # Prepare request
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        data = {
            "invoice_id": invoice_id
        }
        
        # Send request
        print("\n🔄 Sending payment request...")
        try:
            response = requests.post(
                f"{base_url}/pay-invoice",
                headers=headers,
                json=data
            )
            
            print("\n✨ Response:")
            print(f"Status code: {response.status_code}")
            print("Headers:", dict(response.headers))
            
            try:
                response_json = response.json()
                print("Response body:")
                print(json.dumps(response_json, indent=2))
            except json.JSONDecodeError:
                print("Response text (not JSON):")
                print(response.text)
                
        except requests.RequestException as req_error:
            print(f"❌ Request error: {str(req_error)}")
            traceback.print_exc()
            return
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print("\nFull traceback:")
        traceback.print_exc()
        print(f"\nPython version: {sys.version}")
        print(f"Platform: {sys.platform}")

if __name__ == "__main__":
    test_payment_endpoint() 