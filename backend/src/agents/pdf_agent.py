"""PDF agent for extracting and processing text from PDF files."""

from typing import Dict, List, Optional
from pathlib import Path
import os
from langchain_community.document_loaders import PyPDFLoader
import json
import traceback
import re
from datetime import datetime
from dotenv import load_dotenv
from langchain_core.messages import SystemMessage, HumanMessage

from tools.shared_tools import (
    debug_print,
    format_error,
    ensure_directory
)
from openai_client import get_openai_client

class PaymentExtractor:
    """Extract and validate payment information from invoices."""
    
    def __init__(self, debug: bool = False):
        """Initialize payment extractor."""
        self.debug = debug
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
                    extracted = json.loads(func_call['arguments'])
                    
                    # Convert to our standard format
                    result = {
                        "invoice_number": extracted["invoice"]["number"],
                        "paid_amount": extracted["payment"]["amount"],
                        "recipient": extracted["payee"]["name"],
                        "date": extracted["invoice"]["date"],
                        "due_date": extracted["invoice"].get("due_date"),
                        "description": extracted["payment"].get("description"),
                        "bank_details": extracted.get("bank_details", {}),
                        "customer": extracted.get("customer", {}),
                        "payee_details": {
                            "contact_type": extracted["payee"]["contact_type"],
                            "email": extracted["payee"].get("email"),
                            "phone": extracted["payee"].get("phone"),
                            "address": extracted["payee"].get("address"),
                            "tax_id": extracted["payee"].get("tax_id")
                        }
                    }
                    
                    if self.debug:
                        debug_print("Extracted Payment Info", result)
                        
                    return result
            
            return {"error": "No valid extraction"}
            
        except Exception as e:
            error_msg = str(e)
            if self.debug:
                debug_print("Extraction Error", error_msg)
                traceback.print_exc()
            return {"error": f"Extraction failed: {error_msg}"}
    
    def validate(self, data: dict) -> list:
        """Validate extracted payment information."""
        issues = []
        
        # Check payee information
        if not data.get("recipient"):
            issues.append("Missing recipient name")
        if not data.get("payee_details", {}).get("contact_type"):
            issues.append("Missing contact type (individual/business)")
        
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
        if not data.get("paid_amount"):
            issues.append("Missing payment amount")
        elif data["paid_amount"] <= 0:
            issues.append("Invalid payment amount")
        
        # Check invoice information
        if not data.get("invoice_number"):
            issues.append("Missing invoice number")
        
        return issues

def extract_text(pdf_path: str, extract_metadata: bool = True, debug: bool = False) -> Dict:
    """Extract text from a PDF file"""
    try:
        print("\n📄 PDF EXTRACTION WORKFLOW")
        print("=" * 50)
        
        # Check if file exists
        if not os.path.exists(pdf_path):
            error = {
                "success": False,
                "error": f"PDF file not found: {pdf_path}"
            }
            print("❌ File not found")
            return error
        
        # Load and process PDF
        print("📖 Loading PDF...")
        loader = PyPDFLoader(pdf_path)
        pages = loader.load()
        
        # Process pages
        processed_pages = []
        combined_text = ""
        
        print(f"📑 Processing {len(pages)} pages...")
        for idx, page in enumerate(pages, 1):
            page_data = {
                "page_number": page.metadata.get("page", 0) + 1,
                "text_length": len(page.page_content)
            }
            if extract_metadata:
                page_data["metadata"] = page.metadata
            processed_pages.append(page_data)
            combined_text += page.page_content + "\n"
            
            # Print extracted text for each page
            # print(f"\n📝 Page {idx} Content:")
            # print("-" * 50)
            # print(page.page_content.strip())
            # print("-" * 50)
        
        print("\n🔍 Extracting payment information...")
        
        # Extract payment information
        extractor = PaymentExtractor(debug=debug)
        payment_info = extractor.extract(combined_text)
        
        if "error" in payment_info:
            print("\n⚠️ Extraction Issues:")
            print(json.dumps(payment_info, indent=2))
        else:
            print("\n📋 Extracted JSON Data:")
            print("-" * 50)
            print(json.dumps(payment_info, indent=2))
            print("-" * 50)
            
            print("\n✅ Payment Info Summary:")
            print("-" * 30)
            print(f"Invoice Number: {payment_info.get('invoice_number', 'Not found')}")
            print(f"Amount: ${payment_info.get('paid_amount', 0):,.2f}")
            print(f"Recipient: {payment_info.get('recipient', 'Not found')}")
            print(f"Date: {payment_info.get('date', 'Not found')}")
            
            # Validate extracted data
            issues = extractor.validate(payment_info)
            if issues:
                print("\n⚠️ Validation Issues:")
                for issue in issues:
                    print(f"- {issue}")
                payment_info["validation_issues"] = issues
        
        response = {
            "success": True,
            "filename": os.path.basename(pdf_path),
            "total_pages": len(processed_pages),
            "pages": processed_pages,
            "payment_info": payment_info
        }
        
        print("\n" + "="*50)
        print("📄 EXTRACTION COMPLETE")
        print("="*50)
        
        return response
        
    except Exception as e:
        error_details = {
            "success": False,
            "error": str(e),
            "type": type(e).__name__
        }
        print("\n❌ EXTRACTION ERROR:")
        print(str(e))
        return error_details

def extract_from_directory(
    directory: str,
    file_pattern: str = "*.pdf",
    extract_metadata: bool = True,
    debug: bool = False
) -> Dict:
    """Extract text from all PDFs in a directory
    
    Args:
        directory (str): Directory containing PDFs
        file_pattern (str): Pattern to match PDF files
        extract_metadata (bool): Whether to extract metadata
        debug (bool): Enable debug output
        
    Returns:
        dict: Results for each PDF
    """
    try:
        if debug:
            debug_print("Directory Extract Request", {
                "directory": directory,
                "file_pattern": file_pattern,
                "extract_metadata": extract_metadata
            })
        
        # Check if directory exists
        if not os.path.exists(directory):
            error = {"success": False, "error": f"Directory not found: {directory}"}
            if debug:
                debug_print("Directory Error", error)
            return error
        
        # Get all PDF files
        pdf_files = list(Path(directory).glob(file_pattern))
        
        if not pdf_files:
            response = {
                "success": True,
                "total_files": 0,
                "message": f"No PDF files found in {directory}"
            }
            if debug:
                debug_print("Directory Result", response)
            return response
        
        # Process each PDF
        results = []
        for pdf_file in pdf_files:
            result = extract_text(
                pdf_path=str(pdf_file),
                extract_metadata=extract_metadata,
                debug=debug
            )
            results.append(result)
        
        successful = [r for r in results if r["success"]]
        failed = [r for r in results if not r["success"]]
        
        response = {
            "success": True,
            "total_files": len(results),
            "successful_files": len(successful),
            "failed_files": len(failed),
            "results": results
        }
        
        if debug:
            debug_print("Directory Success", {
                "total_files": response["total_files"],
                "successful": len(successful),
                "failed": len(failed)
            })
            
        return response
        
    except Exception as e:
        error = format_error(e)
        if debug:
            debug_print("Directory Error", error)
        return {"success": False, "error": str(e)}

def main():
    """Example usage of PDF functions"""
    try:
        print("\n🚀 Starting PDF Processing Test")
        print("=" * 50)
        
        # Example PDF path
        pdf_path = "downloads/Invoice-SlingshotAI-sept-21.pdf"
        
        # Extract text from single PDF
        result = extract_text(pdf_path, debug=True)
        
        if result["success"]:
            print(f"\n✅ Successfully extracted text from: {result['filename']}")
            print(f"Total pages: {result['total_pages']}")
            print(f"File size: {result['file_size']} bytes")
            
            # Print first page preview
            if result["pages"]:
                first_page = result["pages"][0]
                print(f"\nFirst page preview:")
                print(f"{first_page['text'][:300]}...")
            
            # Extract from directory
            dir_result = extract_from_directory("downloads", debug=True)
            if dir_result["success"]:
                print(f"\n✅ Processed {dir_result['total_files']} PDF files")
                print(f"Successful: {dir_result['successful_files']}")
                print(f"Failed: {dir_result['failed_files']}")
                
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")

if __name__ == "__main__":
    main() 