"""Payment agent for processing invoice payments using Payman AI and Langchain."""

from typing import Dict, Optional
import os
import json
from dotenv import load_dotenv
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_openai import ChatOpenAI
from langchain import hub

from tools.payment_tools import tools as payment_tools
from tools.shared_tools import (
    debug_print,
    format_error,
    format_currency
)

# Load environment variables
load_dotenv()

def extract_payment_amount(invoice_data: Dict) -> Optional[float]:
    """Extract the final payment amount from invoice data.
    
    Prioritizes paid_amount as it represents the actual amount to be paid.
    If not found, checks other fields:
    - paid_amount (primary)
    - payment_amount
    - final_payment
    - amount_paid
    
    Args:
        invoice_data (dict): Invoice data
        
    Returns:
        float or None: Final payment amount if found, None otherwise
    """
    # First check paid_amount as it's the primary field
    amount = invoice_data.get('paid_amount')
    if amount is not None:
        try:
            amount = float(amount)
            if amount > 0:
                return amount
        except (ValueError, TypeError):
            pass
    
    # Fallback fields that might contain the payment amount
    amount_fields = [
        'payment_amount',
        'final_payment',
        'amount_paid'
    ]
    
    # Try each field
    for field in amount_fields:
        amount = invoice_data.get(field)
        if amount is not None:
            try:
                amount = float(amount)
                if amount > 0:
                    return amount
            except (ValueError, TypeError):
                continue
    
    return None

def create_payment_agent(debug: bool = False):
    """Create a Langchain agent for payment processing."""
    # Initialize LLM
    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4"),
        temperature=0
    )
    
    # Get base prompt from hub
    prompt = hub.pull("hwchase17/openai-functions-agent")
    
    # Create agent
    agent = create_openai_functions_agent(llm, tools=payment_tools, prompt=prompt)
    
    # Create agent executor
    agent_executor = AgentExecutor(
        agent=agent,
        tools=payment_tools,
        verbose=debug
    )
    
    return agent_executor

def process_payment(
    invoice_data: Dict,
    debug: bool = False
) -> Dict:
    """Process a payment using the Langchain payment agent.
    
    Args:
        invoice_data (dict): Invoice data including amount and recipient
        debug (bool): Enable debug output
        
    Returns:
        dict: Payment result
    """
    try:
        if debug:
            debug_print("Processing Invoice", invoice_data)
        
        # Extract the final payment amount
        amount = extract_payment_amount(invoice_data)
        
        if amount is None:
            return {
                "success": False,
                "error": "Could not find final payment amount in invoice data"
            }
        
        if debug:
            debug_print("Payment Amount", {
                "amount": format_currency(amount)
            })
        
        # Create payment agent
        agent = create_payment_agent(debug)
        
        # Format prompt for the agent
        prompt = f"""Process this invoice payment:

Invoice Details:
{json.dumps(invoice_data, indent=2)}

Payment Amount: {format_currency(amount)}

Follow these steps:
1. Check the current balance using get_balance
2. Search for the payee using search_payees with the recipient name
3. Send the payment using send_payment with:
   - amount: {amount}
   - recipient: {invoice_data.get('recipient')}
   - description: Payment for {invoice_data.get('invoice_number')}

If any step fails, explain why and stop processing.
"""
        
        # Run agent
        result = agent.invoke({"input": prompt})
        result["amount"] = amount
        return result
        
    except Exception as e:
        error = format_error(e)
        if debug:
            debug_print("Agent Error", error)
        return {"success": False, "error": str(e)}

def main():
    """Example usage of payment agent"""
    try:
        print("\n🚀 Starting Payment Processing Test")
        print("=" * 50)
        
        # Example invoice data
        invoice_data = {
            "invoice_number": "INV-2024-001",
            "recipient": "Slingshot AI",
            "date": "2024-01-17",
            "due_date": "2024-02-17",
            "description": "AI Development Services",
            "subtotal": 8500.00,
            "tax": 722.50,
            "discount": 850.00,
            "total": 8372.50,
            "paid_amount": 2500.00,
            "balance_due": 5872.50  # Final amount to pay
        }
        
        # Process payment using agent
        result = process_payment(invoice_data, debug=True)
        print("\n✅ Agent Response:")
        print(json.dumps(result, indent=2))
                
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")

if __name__ == "__main__":
    main() 