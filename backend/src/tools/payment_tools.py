"""Payment tools module for handling payment operations using LangChain tools."""

from typing import List, Dict, Any, Optional, Union, TypeVar, Callable
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
import os
import json
from dotenv import load_dotenv
from paymanai import Paymanai
from functools import wraps
import traceback
import requests

# Load environment variables
load_dotenv()

# Initialize Payman client
client = Paymanai(
    x_payman_api_secret=os.getenv("PAYMAN_API_SECRET"),
    environment="sandbox"
)

# Type definitions
T = TypeVar('T')
PaymanResponse = Union[Dict[str, Any], Any]

def handle_api_response(response: PaymanResponse, key: str = None) -> Any:
    """Handle Payman API response consistently."""
    if isinstance(response, str):
        try:
            response = json.loads(response)
        except json.JSONDecodeError:
            return None
    
    if isinstance(response, dict):
        return response.get(key) if key else response
    return getattr(response, key) if key and hasattr(response, key) else response

def safe_api_call(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator to handle API calls safely."""
    @wraps(func)
    def wrapper(*args, **kwargs) -> T:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            return f"❌ Error: {str(e)}"
    return wrapper

# Define input schemas
class PaymentItem(BaseModel):
    """Schema for a single payment item."""
    id: str = Field(..., description="Payment ID")
    amount: float = Field(..., description="Payment amount")
    currency: str = Field("USD", description="Currency code")
    recipientName: str = Field(..., description="Name of the recipient")
    description: Optional[str] = Field(None, description="Payment description")
    memo: Optional[str] = Field(None, description="Payment memo")

class BatchPaymentSchema(BaseModel):
    """Schema for batch payments."""
    payments: List[PaymentItem] = Field(..., description="List of payment details")

class SendPaymentSchema(BaseModel):
    """Schema for single payment."""
    amount: float = Field(..., description="Amount to send")
    destination_id: str = Field(..., description="ID of the payment destination")
    memo: Optional[str] = Field(None, description="Optional memo for the payment")

class CheckoutUrlSchema(BaseModel):
    """Schema for checkout URL generation."""
    amount: float = Field(..., description="Amount for checkout")
    currency: str = Field("USD", description="Currency code")
    memo: Optional[str] = Field(None, description="Optional memo")
    customer_name: Optional[str] = Field(None, description="Optional customer name")

class PaymentResult(BaseModel):
    """Schema for payment result."""
    payment_id: str
    recipient: str
    amount: float
    status: str
    reference: Optional[str] = None
    error: Optional[str] = None

def format_payment_summary(results: List[PaymentResult], total_amount: float, final_balance: Optional[float] = None) -> str:
    """Format payment results into a readable summary."""
    successful = [r for r in results if r.status == 'success']
    failed = [r for r in results if r.status == 'failed']
    
    summary = []
    
    if successful:
        summary.append("✅ Successful Payments:")
        for r in successful:
            summary.append(f"- Payment {r.payment_id}: ${r.amount:.2f} to {r.recipient} (Ref: {r.reference})")
    
    if failed:
        if summary:
            summary.append("")
        summary.append("❌ Failed Payments:")
        for r in failed:
            summary.append(f"- Payment {r.payment_id}: ${r.amount:.2f} to {r.recipient} ({r.error})")
    
    summary.append("")
    summary.append(f"📊 Summary:")
    summary.append(f"- Total payments: {len(results)}")
    summary.append(f"- Successful: {len(successful)}")
    summary.append(f"- Failed: {len(failed)}")
    summary.append(f"- Total amount processed: ${sum(r.amount for r in successful):.2f}")
    if final_balance is not None:
        summary.append(f"- Remaining balance: ${final_balance:.2f}")
    
    return "\n".join(summary)

# Define LangChain tools
class BalanceTool(BaseTool):
    name: str = "get_balance"
    description: str = "Get the current spendable balance in USD"
    
    @safe_api_call
    def _run(self, *args: Any, **kwargs: Any) -> str:
        """Get the current spendable balance."""
        balance = client.balances.get_spendable_balance("USD")
        return f"Current balance: ${float(balance):.2f}"

class SearchPayeesTool(BaseTool):
    """Tool for searching payment destinations."""
    
    name: str = "search_payees"
    description: str = "Search for payment destinations by name or email"
    
    @safe_api_call
    def _run(self, tool_input: str) -> str:
        """Search for payment destinations."""
        try:
            # Parse search parameters
            params = json.loads(tool_input)
            
            print("\n[PAYMAN] �� Search Request:")
            print("-" * 40)
            print(json.dumps(params, indent=2))
            
            # Call Payman API
            response = client.payments.search_payees(
                name=params.get("name"),
                contact_email=params.get("contact_email"),
                type=params.get("type", "US_ACH")
            )
            
            # Parse the response if it's a string
            if isinstance(response, str):
                try:
                    payees = json.loads(response)
                except json.JSONDecodeError:
                    print("\n[PAYMAN] ❌ Failed to parse API response - Invalid JSON")
                    return json.dumps([])
            else:
                payees = response
            
            # Log search results
            if payees:
                print(f"\n[PAYMAN] ✅ Found {len(payees)} payees in Payman")
                for idx, payee in enumerate(payees[:3], 1):  # Show first 3 payees
                    print(f"\n[PAYMAN] 👤 Payee {idx}:")
                    print(f"  • Name: {payee.get('name', 'Unknown')}")
                    print(f"  • ID: {payee.get('id', 'Unknown')}")
            else:
                print("\n[PAYMAN] ⚠️ No payees found in Payman")
            
            return json.dumps(payees)
            
        except Exception as e:
            print(f"\n[PAYMAN] ❌ API Error:")
            print(f"  • Type: {type(e).__name__}")
            print(f"  • Details: {str(e)}")
            return json.dumps([])
    
    def _arun(self, tool_input: str) -> str:
        """Async version of run."""
        raise NotImplementedError("SearchPayeesTool does not support async")

class SendPaymentTool(BaseTool):
    name: str = "send_payment"
    description: str = "Send a payment to a destination. Requires amount (float), destination_id (str), and optional memo (str)."
    
    @safe_api_call
    def _run(self, tool_input: str) -> str:
        """Send a payment to a destination."""
        try:
            # Parse payment parameters
            params = json.loads(tool_input)
            
            print(f"\n[PAYMAN] 💸 Processing payment request:")
            print("-" * 40)
            print(json.dumps(params, indent=2))
            
            # Send payment using Payman client
            payment = client.payments.send_payment(
                amount_decimal=float(params["amount"]),
                payment_destination_id=params["destination_id"],
                memo=params.get("memo")
            )
            
            # Handle response
            if isinstance(payment, str):
                try:
                    payment = json.loads(payment)
                except json.JSONDecodeError:
                    print("\n[PAYMAN] ❌ Failed to parse API response - Invalid JSON")
                    return "❌ Payment failed: Invalid API response"
            
            # Extract reference
            ref = handle_api_response(payment, 'reference') or 'Unknown'
            print(f"\n[PAYMAN] ✅ Payment processed successfully")
            print(f"  • Reference: {ref}")
            
            return f"✅ Payment sent successfully! Reference: {ref}"
            
        except Exception as e:
            print(f"\n[PAYMAN] ❌ Payment Error:")
            print(f"  • Type: {type(e).__name__}")
            print(f"  • Details: {str(e)}")
            return f"❌ Payment failed: {str(e)}"

class BatchPaymentsTool(BaseTool):
    name: str = "process_batch_payments"
    description: str = "Process a batch of payments from a JSON file or list of payment details."
    args_schema: type[BatchPaymentSchema] = BatchPaymentSchema
    
    @safe_api_call
    def _run(self, payments: List[PaymentItem], **kwargs: Any) -> str:
        """Process a batch of payments."""
        results: List[PaymentResult] = []
        total_amount = sum(p.amount for p in payments)
        
        # Check current balance
        balance = float(client.balances.get_spendable_balance("USD"))
        if balance < total_amount:
            return f"❌ Error: Insufficient funds. Required: ${total_amount:.2f}, Available: ${balance:.2f}"
        
        print(f"\n[PAYMAN] 📦 Processing batch payment:")
        print(f"  • Number of payments: {len(payments)}")
        print(f"  • Total amount: ${total_amount:.2f}")
        
        for payment in payments:
            try:
                print(f"\n[PAYMAN] 📝 Processing individual payment:")
                print(f"  • ID: {payment.id}")
                print(f"  • Recipient: {payment.recipientName}")
                print(f"  • Amount: ${payment.amount:.2f} {payment.currency}")
                
                # Search for payee
                response = client.payments.search_payees(
                    name=payment.recipientName,
                    type="US_ACH"
                )
                payees = handle_api_response(response)
                
                if not payees:
                    results.append(PaymentResult(
                        payment_id=payment.id,
                        recipient=payment.recipientName,
                        amount=payment.amount,
                        status='failed',
                        error="Payee not found"
                    ))
                    continue
                
                # Get the first matching payee
                payee = handle_api_response(payees[0])
                if not payee:
                    results.append(PaymentResult(
                        payment_id=payment.id,
                        recipient=payment.recipientName,
                        amount=payment.amount,
                        status='failed',
                        error="Invalid payee data"
                    ))
                    continue
                
                payee_id = handle_api_response(payee, 'id')
                payee_name = handle_api_response(payee, 'name') or payment.recipientName
                
                if not payee_id:
                    results.append(PaymentResult(
                        payment_id=payment.id,
                        recipient=payment.recipientName,
                        amount=payment.amount,
                        status='failed',
                        error="Missing payee ID"
                    ))
                    continue
                
                print(f"[PAYMAN] 🎯 Found payee ID: {payee_id}")
                
                # Send payment
                result = client.payments.send_payment(
                    amount_decimal=payment.amount,
                    payment_destination_id=payee_id,
                    memo=payment.memo or f"Payment {payment.id} to {payee_name}"
                )
                
                ref = handle_api_response(result, 'reference') or 'Unknown'
                results.append(PaymentResult(
                    payment_id=payment.id,
                    recipient=payee_name,
                    amount=payment.amount,
                    status='success',
                    reference=ref
                ))
                print("[PAYMAN] ✅ Payment completed successfully")
            
            except Exception as e:
                results.append(PaymentResult(
                    payment_id=payment.id,
                    recipient=payment.recipientName,
                    amount=payment.amount,
                    status='failed',
                    error=str(e)
                ))
        
        try:
            final_balance = float(client.balances.get_spendable_balance("USD"))
        except:
            final_balance = None
        
        return format_payment_summary(results, total_amount, final_balance)

class CheckoutUrlTool(BaseTool):
    name: str = "generate_checkout_url"
    description: str = "Generate a checkout URL for adding funds. Requires amount (float), optional currency (str), memo (str), and customer_name (str)."
    args_schema: type[CheckoutUrlSchema] = CheckoutUrlSchema
    
    @safe_api_call
    def _run(self, amount: float, currency: str = "USD", memo: Optional[str] = None, customer_name: Optional[str] = None, **kwargs: Any) -> str:
        """Generate a checkout URL for adding funds."""
        print(f"[PAYMAN] 🔗 Generating checkout URL for ${amount:.2f}")
        response = client.payments.initiate_customer_deposit(
            amount_decimal=amount,
            customer_id="default",
            customer_name=customer_name,
            memo=memo,
            fee_mode="INCLUDED_IN_AMOUNT"
        )
        url = handle_api_response(response, 'checkout_url')
        return f"✅ Checkout URL generated: {url}" if url else "❌ Error: Failed to generate checkout URL"

# Create tool instances
tools = [
    BalanceTool(),
    SearchPayeesTool(),
    SendPaymentTool(),
    BatchPaymentsTool(),
    CheckoutUrlTool()
] 