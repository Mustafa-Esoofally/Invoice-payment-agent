from typing import Dict, Any, Optional, List
import os
import json
from dotenv import load_dotenv
from paymanai import Paymanai

# Load environment variables
load_dotenv()

# Initialize Payman client
client = Paymanai(
    x_payman_api_secret=os.getenv("PAYMAN_API_SECRET"),
    base_url=os.getenv("PAYMAN_BASE_URL")
)

def get_balance() -> float:
    """Get the current spendable balance."""
    try:
        balance = client.balances.get_spendable_balance("USD")
        return float(balance)
    except Exception as e:
        print(f"Failed to get balance: {str(e)}")
        return 0.0

def generate_checkout_url(
    amount: float,
    currency: str = "USD",
    memo: str = None,
    customer_name: str = None
) -> str:
    """Generate a checkout URL for adding funds."""
    try:
        # Call the API with the correct parameter names
        response = client.payments.initiate_customer_deposit(
            amount_decimal=amount,
            customer_id="default",  # Required field
            customer_name=customer_name,
            memo=memo,
            fee_mode="INCLUDED_IN_AMOUNT"
        )
        return response.checkout_url if hasattr(response, 'checkout_url') else None
    except Exception as e:
        print(f"Failed to generate checkout URL: {str(e)}")
        return None

def search_payees(
    name: Optional[str] = None,
    contact_email: Optional[str] = None,
    type: str = "US_ACH"
) -> List[Dict]:
    """Search for payment destinations."""
    try:
        print(f"Searching for payees...")
        response = client.payments.search_payees(
            name=name,
            contact_email=contact_email,
            type=type
        )
        
        # Parse the response if it's a string
        if isinstance(response, str):
            try:
                payees = json.loads(response)
            except json.JSONDecodeError:
                print("Failed to parse payees response")
                return []
        else:
            payees = response

        if payees:
            print(f"Found {len(payees)} payees")
            for payee in payees[:5]:  # Show first 5 payees
                print(f"- Name: {payee.get('name', 'Unknown')} (ID: {payee.get('id', 'Unknown')})")
        return payees
    except Exception as e:
        print(f"Failed to search payees: {str(e)}")
        return []

def send_payment(amount: float, destination_id: str, memo: Optional[str] = None) -> Any:
    """Send a payment to a destination."""
    try:
        # Send the payment using keyword arguments
        payment = client.payments.send_payment(
            amount_decimal=str(amount),
            payment_destination_id=destination_id,
            memo=memo if memo else None
        )
        return payment
    except Exception as e:
        print(f"Payment failed: {str(e)}")
        raise e

def process_batch_payments(payments: List[Dict]) -> None:
    """Process a batch of payments."""
    print("\n🏁 Starting batch payment processing...")
    
    for payment in payments:
        # Check current balance before each payment
        balance = get_balance()
        print(f"\n📝 Processing payment {payment.get('id', 'Unknown')}:")
        print(f"Recipient: {payment.get('recipientName')}")
        print(f"Amount: ${payment.get('amount'):.2f} {payment.get('currency', 'USD')}")
        print(f"Current balance: ${balance:.2f}\n")

        # Check if we have sufficient funds
        if balance < payment['amount']:
            required_amount = payment['amount'] - balance
            print("⚠️ Insufficient funds for payment.")
            print(f"Additional funds needed: ${required_amount:.2f} USD")
            
            # Generate checkout URL for adding funds
            checkout_url = generate_checkout_url(
                amount=required_amount,
                currency=payment.get('currency', 'USD'),
                memo=f"Add funds for payment to {payment.get('recipientName')}",
                customer_name=payment.get('customerName')
            )
            
            if checkout_url:
                print(f"💳 Add funds: {checkout_url}")
            print("\nSkipping this payment until funds are available.\n")
            continue

        # Search for payee
        print(f"Searching for payee: {payment.get('recipientName')}")
        payees = search_payees(name=payment.get('recipientName'))
        
        if not payees:
            print(f"❌ No payee found for {payment.get('recipientName')}")
            continue

        # Send payment
        try:
            result = send_payment(
                amount=payment['amount'],
                destination_id=payees[0].get('id'),
                memo=payment.get('memo', f"Payment to {payment.get('recipientName')}")
            )
            print("✅ Payment processed successfully")
            print(f"Payment ID: {result.id if hasattr(result, 'id') else 'Unknown'}")
            
            # Get updated balance after payment
            new_balance = get_balance()
            print(f"New balance: ${new_balance:.2f} USD\n")
        except Exception as e:
            print(f"❌ Error processing payment: {str(e)}")
            continue

    print("\n✅ Batch payment processing completed")

def main():
    try:
        # Sample payments data (you can load this from a JSON file)
        sample_payments = [
            {
                "id": "1",
                "recipientName": "Tech Consulting Services",
                "amount": 50000.0,  # Large amount to test insufficient funds
                "currency": "USD",
                "memo": "Test payment 1",
                "customerName": "John Doe"
            },
            {
                "id": "2",
                "recipientName": "Tech Solutions LLC",
                "amount": 15.0,
                "currency": "USD",
                "memo": "Test payment 2"
            }
        ]

        # Process batch payments
        process_batch_payments(sample_payments)

    except Exception as e:
        print(f"\n❌ Batch processing failed: {str(e)}")

if __name__ == "__main__":
    main() 