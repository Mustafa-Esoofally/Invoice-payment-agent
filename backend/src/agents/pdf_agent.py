"""PDF agent for extracting and processing text from PDF files."""

from typing import Dict, List, Optional
from pathlib import Path
import os
from langchain_community.document_loaders import PyPDFLoader
import json
import traceback

from tools.shared_tools import (
    debug_print,
    format_error,
    ensure_directory
)

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
        for page in pages:
            page_data = {
                "page_number": page.metadata.get("page", 0) + 1,
                "text": page.page_content
            }
            if extract_metadata:
                page_data["metadata"] = page.metadata
            processed_pages.append(page_data)
        
        response = {
            "success": True,
            "filename": os.path.basename(pdf_path),
            "file_path": pdf_path,
            "total_pages": len(processed_pages),
            "pages": processed_pages,
            "file_size": os.path.getsize(pdf_path)
        }
        
        if debug:
            debug_print("Extract Success", {
                "filename": response["filename"],
                "total_pages": response["total_pages"],
                "file_size": response["file_size"]
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