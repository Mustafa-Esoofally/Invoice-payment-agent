"""Script to extract payment information from PDF invoices."""

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.messages import SystemMessage, HumanMessage
import json
from pathlib import Path
from datetime import datetime
import time
import os
from dotenv import load_dotenv
import sys

from src.openai_client import get_openai_client

class PaymentExtractor:
    """Extract and validate payment information from invoices."""
    
    def __init__(self):
        """Initialize with OpenAI client."""
        self.llm = get_openai_client()
    
    def extract(self, text: str) -> dict:
        """Extract payment details from invoice text."""
        try:
            messages = [
                SystemMessage(content="""Extract payment details from invoices with high precision.
                
                Rules:
                1. Only extract explicitly stated information
                2. Use final total with all taxes/fees
                3. Format dates as YYYY-MM-DD
                4. Remove currency symbols from amounts
                5. Use "individual" or "business" for contact type
                6. Look for bank details including:
                   - Account holder name
                   - Account number
                   - Account type (checking/savings)
                   - Routing number
                   - Bank name
                7. Extract all contact information:
                   - Email
                   - Phone
                   - Full address
                   - Tax ID if available
                8. Use payment section for payee details
                9. Use "BILLED TO" section for customer details"""),
                HumanMessage(content=f"Extract payment details from this invoice:\n{text}")
            ]
            
            functions = [{
                "name": "extract_payment_details",
                "description": "Extract payment details from invoice text",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "payee": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "contact_type": {"type": "string", "enum": ["individual", "business"]},
                                "email": {"type": "string"},
                                "phone": {"type": "string"},
                                "address": {"type": "string"},
                                "tax_id": {"type": "string"}
                            },
                            "required": ["name", "contact_type"]
                        },
                        "bank_details": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string", "enum": ["US_ACH"], "default": "US_ACH"},
                                "account_holder_name": {"type": "string"},
                                "account_number": {"type": "string"},
                                "account_type": {"type": "string", "enum": ["checking", "savings"]},
                                "routing_number": {"type": "string"},
                                "bank_name": {"type": "string"}
                            }
                        },
                        "payment": {
                            "type": "object",
                            "properties": {
                                "amount": {"type": "number"},
                                "currency": {"type": "string", "default": "USD"},
                                "description": {"type": "string"}
                            },
                            "required": ["amount"]
                        },
                        "invoice": {
                            "type": "object",
                            "properties": {
                                "number": {"type": "string"},
                                "date": {"type": "string", "format": "date"},
                                "due_date": {"type": "string", "format": "date"}
                            },
                            "required": ["number"]
                        },
                        "customer": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "email": {"type": "string"},
                                "phone": {"type": "string"},
                                "address": {"type": "string"}
                            }
                        }
                    },
                    "required": ["payee", "payment", "invoice"]
                }
            }]
            
            response = self.llm.invoke(
                messages,
                functions=functions,
                function_call={"name": "extract_payment_details"}
            )
            
            if hasattr(response, 'additional_kwargs') and 'function_call' in response.additional_kwargs:
                func_call = response.additional_kwargs['function_call']
                if func_call and 'arguments' in func_call:
                    return json.loads(func_call['arguments'])
            
            return {"error": "No valid extraction"}
            
        except Exception as e:
            error_msg = str(e)
            print(error_msg)

            if "invalid_api_key" in error_msg:
                return {"error": "Invalid API key. Please check your OpenAI API key."}
            elif "insufficient_quota" in error_msg:
                return {"error": "OpenAI API quota exceeded. Please check your billing status."}
            else:
                return {"error": f"Extraction failed: {error_msg}"}
    
    def validate(self, data: dict) -> list:
        """Validate extracted payment information."""
        issues = []
        
        # Check payee information
        if not data.get("payee", {}).get("name"):
            issues.append("Missing payee name")
        if not data.get("payee", {}).get("contact_type"):
            issues.append("Missing contact type (individual/business)")
        if not any([data.get("payee", {}).get("email"), data.get("payee", {}).get("phone")]):
            issues.append("Missing contact method (email or phone)")
        
        # Check bank details
        bank = data.get("bank_details", {})
        if bank:
            if not bank.get("account_holder_name"):
                issues.append("Missing account holder name")
            if not bank.get("account_number"):
                issues.append("Missing account number")
            if not bank.get("account_type"):
                issues.append("Missing account type (checking/savings)")
        
        # Check payment information
        if not data.get("payment", {}).get("amount"):
            issues.append("Missing payment amount")
        elif data["payment"]["amount"] <= 0:
            issues.append("Invalid payment amount")
        
        # Check invoice information
        if not data.get("invoice", {}).get("number"):
            issues.append("Missing invoice number")
        if not data.get("invoice", {}).get("due_date"):
            issues.append("Missing due date")
        
        return issues

def process_pdfs(directory: str):
    """Process all PDFs in directory for payment information."""
    test_dir = Path(directory)
    if not test_dir.exists():
        print("Test directory not found")
        return
    
    pdf_files = list(test_dir.glob("*.pdf"))
    if not pdf_files:
        print("No PDF files found")
        return
    
    print(f"Found {len(pdf_files)} PDF files")
    
    extractor = PaymentExtractor()
    results = []
    
    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"\nProcessing {i}/{len(pdf_files)}: {pdf_path.name}")
        print("-" * 50)
        
        try:
            # Load PDF text
            loader = PyPDFLoader(str(pdf_path))
            pages = loader.load()
            text = " ".join(page.page_content for page in pages)
            
            # Extract and validate
            start_time = time.time()
            data = extractor.extract(text)
            duration = time.time() - start_time
            
            if "error" in data:
                print(f"Error: {data['error']}")
                continue
            
            # Print minimal extraction summary
            print("\nExtracted Information:")
            print(f"Payee: {data['payee']['name']}")
            print(f"Amount: ${data['payment']['amount']} {data['payment'].get('currency', 'USD')}")
            print(f"Invoice: {data['invoice']['number']}")
            
            # Validate
            issues = extractor.validate(data)
            if issues:
                print("\nValidation Issues:")
                for issue in issues:
                    print(f"- {issue}")
            
            # Store result
            results.append({
                "filename": pdf_path.name,
                "timestamp": datetime.now().isoformat(),
                "duration": round(duration, 2),
                "extraction": data,
                "issues": issues
            })
            
        except Exception as e:
            print(f"Error: {str(e)}")
    
    # Save results
    if results:
        output_file = test_dir / "extraction_results.json"
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "timestamp": datetime.now().isoformat(),
                    "total_files": len(pdf_files),
                    "successful": len([r for r in results if not r.get("issues")]),
                    "results": results
                }, f, indent=2, ensure_ascii=False)
            print(f"\nResults saved to: {output_file}")
        except Exception as e:
            print(f"\nFailed to save results: {str(e)}")
    else:
        print("\nNo successful extractions to save")

if __name__ == "__main__":
    process_pdfs("invoice data/test") 