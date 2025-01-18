"""Payment agent for processing invoice payments."""

from typing import Dict, List, Optional
from pathlib import Path
import os
import json

from tools.shared_tools import (
    debug_print,
    format_error,
    format_currency,
    ensure_directory
)

class PaymentAgent:
    """Agent for processing invoice payments."""
    
    def __init__(self, debug: bool = False):
        """Initialize the payment agent
        
        Args:
            debug (bool): Enable debug output
        """
        self.debug = debug
        
        if self.debug:
            debug_print("Payment Agent Initialized", {
                "debug_mode": debug
            })
    
    def process_payment(
        self,
        invoice_data: Dict,
        payment_method: str = "bank_transfer",
        currency: str = "USD"
    ) -> Dict:
        """Process a payment for an invoice
        
        Args:
            invoice_data (dict): Invoice data including amount and recipient
            payment_method (str): Payment method to use
            currency (str): Currency code
            
        Returns:
            dict: Payment result
        """
        try:
            if self.debug:
                debug_print("Payment Request", {
                    "invoice_data": invoice_data,
                    "payment_method": payment_method,
                    "currency": currency
                })
            
            # Validate invoice data
            required_fields = ["amount", "recipient", "invoice_number"]
            missing_fields = [f for f in required_fields if f not in invoice_data]
            
            if missing_fields:
                error = {
                    "success": False,
                    "error": f"Missing required fields: {', '.join(missing_fields)}"
                }
                if self.debug:
                    debug_print("Validation Error", error)
                return error
            
            # Format amount for display
            formatted_amount = format_currency(
                float(invoice_data["amount"]),
                currency
            )
            
            # Process payment (mock implementation)
            payment_result = {
                "success": True,
                "payment_id": "PAY123",  # Would be real ID from payment provider
                "amount": formatted_amount,
                "recipient": invoice_data["recipient"],
                "invoice_number": invoice_data["invoice_number"],
                "payment_method": payment_method,
                "status": "completed",
                "timestamp": "2024-01-17T12:00:00Z"  # Would be real timestamp
            }
            
            if self.debug:
                debug_print("Payment Success", payment_result)
                
            return payment_result
            
        except Exception as e:
            error = format_error(e)
            if self.debug:
                debug_print("Payment Error", error)
            return {"success": False, "error": str(e)}
    
    def validate_invoice(self, invoice_data: Dict) -> Dict:
        """Validate invoice data format and required fields
        
        Args:
            invoice_data (dict): Invoice data to validate
            
        Returns:
            dict: Validation result
        """
        try:
            if self.debug:
                debug_print("Validation Request", {
                    "invoice_data": invoice_data
                })
            
            # Required fields
            required_fields = [
                "invoice_number",
                "amount",
                "recipient",
                "date",
                "due_date"
            ]
            
            # Optional fields with defaults
            optional_fields = {
                "currency": "USD",
                "payment_method": "bank_transfer",
                "description": "",
                "line_items": []
            }
            
            # Check required fields
            missing_fields = [f for f in required_fields if f not in invoice_data]
            
            if missing_fields:
                error = {
                    "success": False,
                    "error": f"Missing required fields: {', '.join(missing_fields)}"
                }
                if self.debug:
                    debug_print("Validation Error", error)
                return error
            
            # Add defaults for missing optional fields
            for field, default in optional_fields.items():
                if field not in invoice_data:
                    invoice_data[field] = default
            
            # Validate amount format
            try:
                amount = float(invoice_data["amount"])
                if amount <= 0:
                    raise ValueError("Amount must be positive")
            except ValueError as e:
                error = {
                    "success": False,
                    "error": f"Invalid amount: {str(e)}"
                }
                if self.debug:
                    debug_print("Amount Error", error)
                return error
            
            response = {
                "success": True,
                "validated_data": invoice_data
            }
            
            if self.debug:
                debug_print("Validation Success", response)
                
            return response
            
        except Exception as e:
            error = format_error(e)
            if self.debug:
                debug_print("Validation Error", error)
            return {"success": False, "error": str(e)}

def main():
    """Example usage of PaymentAgent"""
    try:
        # Initialize agent
        agent = PaymentAgent(debug=True)
        
        # Example invoice data
        invoice_data = {
            "invoice_number": "INV-2024-001",
            "amount": 1500.00,
            "recipient": "Slingshot AI",
            "date": "2024-01-17",
            "due_date": "2024-02-17",
            "description": "AI Development Services"
        }
        
        # Validate invoice
        validation_result = agent.validate_invoice(invoice_data)
        
        if validation_result["success"]:
            # Process payment
            agent.process_payment(validation_result["validated_data"])
                
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    main() 