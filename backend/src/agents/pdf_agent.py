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
from openai_client import get_openai_client

class PaymentExtractor:
    """Extract and validate payment information from invoices."""
    
    def __init__(self):
        """Initialize payment extractor."""
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
                    return {
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
            
            return {"error": "No valid extraction"}
            
        except Exception as e:
            return {"error": f"Extraction failed: {str(e)}"}

def extract_text(pdf_path: str, extract_metadata: bool = True) -> Dict:
    """Extract text from a PDF file"""
    try:
        # Check if file exists
        if not os.path.exists(pdf_path):
            return {
                "success": False,
                "error": f"PDF file not found: {pdf_path}"
            }
        
        # Load and process PDF
        loader = PyPDFLoader(pdf_path)
        pages = loader.load()
        
        # Process pages
        processed_pages = []
        combined_text = ""
        
        for page in pages:
            page_data = {
                "page_number": page.metadata.get("page", 0) + 1,
                "text_length": len(page.page_content)
            }
            if extract_metadata:
                page_data["metadata"] = page.metadata
            processed_pages.append(page_data)
            combined_text += page.page_content + "\n"
        
        # Extract payment information
        extractor = PaymentExtractor()
        payment_info = extractor.extract(combined_text)
        
        if "error" in payment_info:
            return payment_info
            
        return payment_info
            
    except Exception as e:
        return {"error": str(e)}

def extract_from_directory(
    directory: str,
    file_pattern: str = "*.pdf",
    extract_metadata: bool = True
) -> Dict:
    """Extract text from all PDFs in a directory
    
    Args:
        directory (str): Directory containing PDFs
        file_pattern (str): Pattern to match PDF files
        extract_metadata (bool): Whether to extract metadata
        
    Returns:
        dict: Results for each PDF
    """
    try:
        # Check if directory exists
        if not os.path.exists(directory):
            return {
                "success": False,
                "error": f"Directory not found: {directory}"
            }
        
        # Get all PDF files
        pdf_files = list(Path(directory).glob(file_pattern))
        
        if not pdf_files:
            return {
                "success": True,
                "total_files": 0,
                "message": f"No PDF files found in {directory}"
            }
        
        # Process each PDF
        results = []
        for pdf_file in pdf_files:
            result = extract_text(
                pdf_path=str(pdf_file),
                extract_metadata=extract_metadata
            )
            results.append(result)
        
        successful = [r for r in results if r["success"]]
        failed = [r for r in results if not r["success"]]
        
        return {
            "success": True,
            "total_files": len(results),
            "successful_files": len(successful),
            "failed_files": len(failed),
            "results": results
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

def main():
    """Example usage of PDF functions"""
    try:
        # Example PDF path
        pdf_path = "downloads/Invoice-SlingshotAI-sept-21.pdf"
        
        # Extract text from single PDF
        result = extract_text(pdf_path)
        
        if result["success"]:
            print(f"Successfully extracted text from: {result['filename']}")
            print(f"Total pages: {result['total_pages']}")
            print(f"File size: {result['file_size']} bytes")
            
            # Print first page preview
            if result["pages"]:
                first_page = result["pages"][0]
                print(f"First page preview:")
                print(f"{first_page['text'][:300]}...")
            
            # Extract from directory
            dir_result = extract_from_directory("downloads")
            if dir_result["success"]:
                print(f"Processed {dir_result['total_files']} PDF files")
                print(f"Successful: {dir_result['successful_files']}")
                print(f"Failed: {dir_result['failed_files']}")
                
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main() 