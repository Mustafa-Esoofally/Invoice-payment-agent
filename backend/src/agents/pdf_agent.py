"""PDF agent for extracting and processing text from PDF files."""

from typing import Dict, List, Optional
from pathlib import Path
import os
from langchain_community.document_loaders import PyPDFLoader
import json
import traceback
import re

from tools.shared_tools import (
    debug_print,
    format_error,
    ensure_directory
)

def extract_payment_info(text: str) -> Dict:
    """Extract payment information from text.
    
    Args:
        text (str): Text to extract from
        
    Returns:
        dict: Extracted payment information
    """
    # Remove extra whitespace and normalize
    text = ' '.join(text.split())
    
    # Initialize result
    result = {
        "invoice_number": None,
        "paid_amount": None,
        "recipient": None,
        "date": None,
        "due_date": None,
        "description": None
    }
    
    # Extract invoice number
    invoice_patterns = [
        r'Invoice\s*#?\s*(\w+[-/]?\w+)',
        r'Invoice Number:?\s*(\w+[-/]?\w+)',
        r'Invoice ID:?\s*(\w+[-/]?\w+)',
        r'#\s*(\w+[-/]?\w+)',
        r'NO\.?\s*(\w+[-/]?\w+)'
    ]
    
    for pattern in invoice_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result["invoice_number"] = match.group(1)
            break
    
    # Extract amount
    amount_patterns = [
        r'Total:?\s*\$?([\d,]+\.?\d*)',
        r'Amount Due:?\s*\$?([\d,]+\.?\d*)',
        r'Balance Due:?\s*\$?([\d,]+\.?\d*)',
        r'Due:?\s*\$?([\d,]+\.?\d*)',
        r'TOTAL:?\s*\$?([\d,]+\.?\d*)',
        r'SUBTOTAL:?\s*\$?([\d,]+\.?\d*)',
        r'\$\s*([\d,]+\.?\d*)'
    ]
    
    for pattern in amount_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                amount_str = match.group(1).replace(',', '')
                result["paid_amount"] = float(amount_str)
                break
            except ValueError:
                continue
    
    # Extract recipient
    recipient_patterns = [
        r'Bill To:?\s*([^$\n\.]+?)(?=\s*\$|\s*\n|\s*\.|\s*@|$)',
        r'To:?\s*([^$\n\.]+?)(?=\s*\$|\s*\n|\s*\.|\s*@|$)',
        r'Recipient:?\s*([^$\n\.]+?)(?=\s*\$|\s*\n|\s*\.|\s*@|$)',
        r'Company:?\s*([^$\n\.]+?)(?=\s*\$|\s*\n|\s*\.|\s*@|$)',
        r'Client:?\s*([^$\n\.]+?)(?=\s*\$|\s*\n|\s*\.|\s*@|$)',
        r'Customer:?\s*([^$\n\.]+?)(?=\s*\$|\s*\n|\s*\.|\s*@|$)'
    ]
    
    # Try to find recipient name
    recipient_name = None
    for pattern in recipient_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            recipient_name = match.group(1).strip()
            # Clean up recipient name
            recipient_name = re.sub(r'\s+', ' ', recipient_name)
            recipient_name = re.sub(r'[^\w\s\-\.,]', '', recipient_name)
            recipient_name = recipient_name.strip()
            if recipient_name and len(recipient_name) > 2:
                result["recipient"] = recipient_name
                break
    
    # If no recipient found, try to find a business name
    if not result["recipient"]:
        business_patterns = [
            r'([A-Z][A-Za-z\s\.,]+(?:LLC|Inc|Corp|Ltd|Limited|Company|Co\.))',
            r'([A-Z][A-Za-z\s\.,]+(?:Technologies|Solutions|Services|Systems))',
            r'([A-Z][A-Za-z\s\.,]+(?:Group|Partners|Associates))',
            r'(?:To|For|By):\s*([A-Z][A-Za-z\s\.,]+)',
            r'(?:Project|Client):\s*([A-Z][A-Za-z\s\.,]+)'
        ]
        for pattern in business_patterns:
            match = re.search(pattern, text)
            if match:
                business_name = match.group(1).strip()
                # Clean up business name
                business_name = re.sub(r'\s+', ' ', business_name)
                business_name = re.sub(r'[^\w\s\-\.,]', '', business_name)
                business_name = business_name.strip()
                if business_name and len(business_name) > 2:
                    # Extract just the company name without address
                    name_parts = business_name.split(',')[0].split('\n')[0].split('@')[0]
                    result["recipient"] = name_parts.strip()
                    break
    
    # Extract dates
    date_patterns = [
        r'Date:?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
        r'Invoice Date:?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
        r'Due Date:?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
        r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})'
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match and not result["date"]:
            result["date"] = match.group(1)
        elif match and not result["due_date"]:
            result["due_date"] = match.group(1)
    
    # Extract description
    description_patterns = [
        r'Description:?\s*([^\n]+)',
        r'Details:?\s*([^\n]+)',
        r'Services:?\s*([^\n]+)',
        r'Items:?\s*([^\n]+)',
        r'Project Details:?\s*([^\n]+)',
        r'Work Description:?\s*([^\n]+)'
    ]
    
    for pattern in description_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            description = match.group(1).strip()
            # Clean up description
            description = re.sub(r'\s+', ' ', description)
            description = description.strip()
            if description and len(description) > 2:
                result["description"] = description
                break
    
    # If no description found, try to find itemized entries
    if not result["description"]:
        lines = text.split('\n')
        items = []
        for line in lines:
            if re.search(r'\$\s*[\d,]+\.?\d*', line):  # Line contains a price
                item = re.sub(r'\$\s*[\d,]+\.?\d*', '', line).strip()
                if item and len(item) > 2:
                    items.append(item)
        if items:
            result["description"] = "; ".join(items[:3])  # Take first 3 items
    
    return result

def extract_text(pdf_path: str, extract_metadata: bool = True, debug: bool = False) -> Dict:
    """Extract text from a PDF file
    
    Args:
        pdf_path (str): Path to PDF file
        extract_metadata (bool): Whether to extract metadata
        debug (bool): Enable debug output
        
    Returns:
        dict: Extracted text and metadata
    """
    try:
        if debug:
            debug_print("Extract Request", {
                "pdf_path": pdf_path,
                "extract_metadata": extract_metadata
            })
        
        # Check if file exists
        if not os.path.exists(pdf_path):
            error = {"success": False, "error": f"PDF file not found: {pdf_path}"}
            if debug:
                debug_print("Extract Error", error)
            return error
        
        # Load and process PDF
        loader = PyPDFLoader(pdf_path)
        pages = loader.load()
        
        if debug:
            debug_print("Extracted Pages", {
                "num_pages": len(pages),
                "first_page_metadata": pages[0].metadata if pages else None
            })
        
        # Process pages
        processed_pages = []
        combined_text = ""
        
        for page in pages:
            page_data = {
                "page_number": page.metadata.get("page", 0) + 1,
                "text": page.page_content
            }
            if extract_metadata:
                page_data["metadata"] = page.metadata
            processed_pages.append(page_data)
            combined_text += page.page_content + "\n"
        
        # Extract payment information
        payment_info = extract_payment_info(combined_text)
        
        response = {
            "success": True,
            "filename": os.path.basename(pdf_path),
            "file_path": pdf_path,
            "total_pages": len(processed_pages),
            "pages": processed_pages,
            "file_size": os.path.getsize(pdf_path),
            "payment_info": payment_info
        }
        
        if debug:
            debug_print("Extract Success", {
                "filename": response["filename"],
                "total_pages": response["total_pages"],
                "file_size": response["file_size"],
                "payment_info": payment_info
            })
            
        return response
        
    except Exception as e:
        error = format_error(e)
        if debug:
            debug_print("Extract Error", error)
        return {"success": False, "error": str(e)}

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