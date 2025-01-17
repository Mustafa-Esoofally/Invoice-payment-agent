from email_pdf_processor import EmailPDFProcessor
from payment_agent import process_payment_request
from typing import Dict, List, Optional, Union
import json
import re
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def debug_print(title: str, data: any, indent: int = 2):
    """Helper function to print debug information"""
    print(f"\n🔍 DEBUG: {title}")
    if isinstance(data, (dict, list)):
        import json
        print(json.dumps(data, indent=indent, default=str))
    else:
        print(data)
    print("-" * 50)

class InvoicePaymentProcessor:
    def __init__(self, download_dir="downloads", debug=True):
        """Initialize the invoice payment processor
        
        Args:
            download_dir (str): Directory to save downloaded attachments
            debug (bool): Enable debug output
        """
        self.debug = debug
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True)
        
        # Initialize PDF processor
        self.pdf_processor = EmailPDFProcessor(download_dir=download_dir, debug=debug)
        
        if self.debug:
            debug_print("Invoice Payment Processor Initialized", {
                "download_dir": str(self.download_dir),
                "debug_mode": debug
            })
    
    def extract_payment_info_from_text(self, text: str) -> Dict:
        """Extract payment information from text using flexible patterns
        
        Args:
            text (str): Text content from PDF
            
        Returns:
            dict: Extracted payment information
        """
        try:
            # Multiple patterns for each field to handle different formats
            patterns = {
                'invoice_number': [
                    r'INVOICE\s*(?:NO\.?|NUMBER:?|#)\s*[#]?([A-Z0-9][-A-Z0-9]*)',
                    r'INV[:\s.-]*([A-Z0-9][-A-Z0-9]*)',
                    r'INVOICE\s*ID[:\s]*([A-Z0-9][-A-Z0-9]*)',
                    r'#\s*([A-Z0-9][-A-Z0-9]*)'
                ],
                'amount': [
                    r'Balance\s*Due\s*[\$]?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',
                    r'(?:TOTAL|SUBTOTAL)\s*(?:USD|\$)?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',
                    r'(?:Amount|Sum)\s*(?:Due|Payable|:)?\s*(?:USD|\$)?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',
                    r'(?:USD|\$)\s*(\d+(?:,\d{3})*(?:\.\d{2})?)'
                ],
                'recipient_name': [
                    r'BILL\s*TO\s*(?:.*?\n){0,2}([A-Z][a-zA-Z\s]+)(?:\n|$)',  # Only first line
                    r'(?:PAYEE|VENDOR|SUPPLIER)[:\s]*(?:.*?\n){0,2}([A-Z][a-zA-Z\s]+)(?:\n|$)',
                    r'(?:COMPANY|BUSINESS)[:\s]*(?:.*?\n){0,2}([A-Z][a-zA-Z\s]+)(?:\n|$)'
                ],
                'company_name': [  # Added to capture company name separately
                    r'BILL\s*TO\s*(?:.*?\n){1,3}(?:[A-Z][a-zA-Z\s]+\n)([A-Z][a-zA-Z\s]+)(?:\n|$)',
                    r'(?:PAYEE|VENDOR|SUPPLIER)[:\s]*(?:.*?\n){1,3}(?:[A-Z][a-zA-Z\s]+\n)([A-Z][a-zA-Z\s]+)(?:\n|$)'
                ],
                'memo': [
                    r'(?:PROJECT\s+DETAILS?)[:\s]*\n+([^\n]+)(?:\n|$)',  # Project details first
                    r'(?:DESCRIPTION|DETAILS)[:\s]*\n+([^\n]+)(?:\n|$)',
                    r'(?:SERVICE|WORK)\s*DESCRIPTION[:\s]*\n+([^\n]+)(?:\n|$)',
                    r'(?:ITEM|PRODUCT)[:\s]*\n+([^\n]+)(?:\n|$)'
                ]
            }
            
            extracted = {}
            
            # Try each pattern for each field
            for field, field_patterns in patterns.items():
                for pattern in field_patterns:
                    match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
                    if match:
                        value = match.group(1).strip()
                        # Basic validation
                        if field == 'amount':
                            # Remove any currency symbols and commas
                            value = re.sub(r'[^\d.]', '', value)
                            if value and float(value) > 0:
                                extracted[field] = value
                                break
                        elif field == 'invoice_number':
                            # Ensure it's a valid invoice number format
                            if len(value) >= 1 and not value.isalpha():
                                extracted[field] = value
                                break
                        elif value and len(value) > 1:  # Avoid single character matches
                            extracted[field] = value
                            break
            
            if self.debug:
                debug_print("Extracted Fields", extracted)
            
            # If no invoice number found, try to find any alphanumeric sequence that looks like an invoice number
            if 'invoice_number' not in extracted:
                # Look for patterns like "123", "A123", "INV-123", etc.
                number_matches = re.findall(r'(?:^|\s)([A-Z0-9][-A-Z0-9]{2,})', text)
                if number_matches:
                    extracted['invoice_number'] = number_matches[0]
                else:
                    # Generate a unique one if nothing found
                    from datetime import datetime
                    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                    extracted['invoice_number'] = f"AUTO-{timestamp}"
            
            # Make invoice number more unique by adding prefix if it's too simple
            if extracted.get('invoice_number', '').isdigit():
                # Get company initials if available
                company = extracted.get('company_name', '')
                if company:
                    initials = ''.join(word[0].upper() for word in company.split() if word)
                    if initials:
                        extracted['invoice_number'] = f"{initials}-{extracted['invoice_number']}"
                else:
                    # Use date-based prefix
                    from datetime import datetime
                    date_prefix = datetime.now().strftime('%Y%m')
                    extracted['invoice_number'] = f"INV-{date_prefix}-{extracted['invoice_number']}"
            
            # If no amount found, look for any number that could be the total
            if 'amount' not in extracted:
                # Look for numbers with decimal points near keywords
                amount_matches = []
                for line in text.split('\n'):
                    if any(keyword in line.upper() for keyword in ['TOTAL', 'AMOUNT', 'DUE', 'BALANCE']):
                        matches = re.findall(r'\$?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)', line)
                        amount_matches.extend(matches)
                
                if amount_matches:
                    # Take the largest number as it's likely the total
                    amounts = [float(amt.replace(',', '')) for amt in amount_matches]
                    extracted['amount'] = str(max(amounts))
            
            # If no recipient name, try to find any name-like text
            if 'recipient_name' not in extracted:
                # Look for capitalized words that might be names
                name_matches = re.findall(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})(?:\n|$)', text)
                if name_matches:
                    # Take the first name-like match that's not a common header
                    common_headers = ['INVOICE', 'BILL', 'TOTAL', 'DESCRIPTION']
                    for name in name_matches:
                        if not any(header in name.upper() for header in common_headers):
                            extracted['recipient_name'] = name
                            break
            
            # If no memo found, try to extract meaningful description
            if 'memo' not in extracted:
                # Look for lines with potential descriptions
                lines = text.split('\n')
                description_found = False
                for i, line in enumerate(lines):
                    line = line.strip()
                    if any(keyword in line.upper() for keyword in ['DESCRIPTION', 'PROJECT', 'DETAILS']):
                        # Take the next non-empty line as memo
                        for next_line in lines[i+1:]:
                            next_line = next_line.strip()
                            if next_line and not any(word in next_line.upper() for word in ['INVOICE', 'TOTAL', 'BALANCE', 'DATE']):
                                extracted['memo'] = next_line
                                description_found = True
                                break
                    if description_found:
                        break
            
            # Convert to payment format with defaults
            payment = {
                "id": extracted.get('invoice_number'),
                "amount": float(extracted.get('amount', '0').replace(',', '')),
                "currency": "USD",  # Default to USD
                "recipientName": extracted.get('recipient_name', 'UNKNOWN RECIPIENT'),
                "memo": extracted.get('memo', "Software Development Services")  # Better default memo
            }
            
            # Validate the extracted data
            if payment["amount"] <= 0:
                if self.debug:
                    debug_print("Validation Error", "Invalid amount: must be greater than 0")
                return None
                
            if payment["recipientName"] == 'UNKNOWN RECIPIENT':
                if self.debug:
                    debug_print("Warning", "No recipient name found in invoice")
            
            return payment
            
        except Exception as e:
            if self.debug:
                debug_print("Extraction Error", str(e))
            return None
    
    def process_pdf_payments(self, attachments_info: list) -> Dict:
        """Process payments from PDF attachments
        
        Args:
            attachments_info (list): List of attachment information
            
        Returns:
            dict: Processing results
        """
        try:
            if self.debug:
                debug_print("Processing PDF Payments", attachments_info)
            
            # Process PDF attachments
            pdf_results = self.pdf_processor.process_email_attachments(attachments_info)
            
            if not pdf_results["success"]:
                return pdf_results
            
            # Extract payment information from each PDF
            payments = []
            for result in pdf_results["results"]:
                if not result["success"] or not result["is_pdf"]:
                    continue
                
                # Get text content from first page
                pages = result["extraction_info"]["pages"]
                if not pages:
                    continue
                
                text = pages[0]["text"]
                payment_info = self.extract_payment_info_from_text(text)
                
                if payment_info:
                    payments.append(payment_info)
            
            if not payments:
                return {
                    "success": False,
                    "error": "No valid payment information found in PDFs"
                }
            
            # Process payments using payment agent
            payment_request = {"payments": payments}
            if self.debug:
                debug_print("Payment Request", payment_request)
            
            response = process_payment_request(json.dumps(payment_request))
            
            return {
                "success": True,
                "pdf_results": pdf_results,
                "payments_processed": len(payments),
                "payment_response": response
            }
            
        except Exception as e:
            error_msg = str(e)
            if self.debug:
                import traceback
                debug_print("Processing Error", {
                    "error": error_msg,
                    "traceback": traceback.format_exc()
                })
            return {"success": False, "error": error_msg}

def main():
    # Initialize the processor
    processor = InvoicePaymentProcessor(debug=True)
    
    # Example attachment information
    attachments = [
        {
            "message_id": "1946aaf0de7d93b8",
            "attachment_id": "attachment-0f0edf62",
            "filename": "Invoice-SlingshotAI-sept-21.pdf"
        }
    ]
    
    # Process payments from PDFs
    print("\nProcessing payments from PDF attachments...")
    results = processor.process_pdf_payments(attachments)
    
    if results["success"]:
        print("\n✅ Payment Processing Results:")
        print(f"PDFs Processed: {results['pdf_results']['processed_files']}")
        print(f"Payments Processed: {results['payments_processed']}")
        print("\nPayment Response:")
        print(results["payment_response"])
    else:
        print(f"\n❌ Error: {results['error']}")

if __name__ == "__main__":
    main() 