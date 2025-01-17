from pathlib import Path
import os
from typing import Dict, List, Optional
from langchain_community.document_loaders import PyPDFLoader

def debug_print(title: str, data: any, indent: int = 2):
    """Helper function to print debug information"""
    print(f"\n🔍 DEBUG: {title}")
    if isinstance(data, (dict, list)):
        import json
        print(json.dumps(data, indent=indent, default=str))
    else:
        print(data)
    print("-" * 50)

class PDFExtractionAgent:
    def __init__(self, debug: bool = True):
        """Initialize the PDF extraction agent
        
        Args:
            debug (bool): Enable debug output
        """
        self.debug = debug
        
        if self.debug:
            debug_print("PDF Extraction Agent Initialized", {
                "debug_mode": debug
            })
    
    def extract_text(self, pdf_path: str, extract_metadata: bool = True) -> Dict:
        """Extract text from a PDF file
        
        Args:
            pdf_path (str): Path to the PDF file
            extract_metadata (bool): Whether to extract metadata
            
        Returns:
            dict: Dictionary containing extraction results
        """
        try:
            if self.debug:
                debug_print("Extraction Request", {
                    "pdf_path": pdf_path,
                    "extract_metadata": extract_metadata
                })
            
            # Check if file exists
            if not os.path.exists(pdf_path):
                error_msg = f"PDF file not found: {pdf_path}"
                if self.debug:
                    debug_print("Error", error_msg)
                return {"success": False, "error": error_msg}
            
            # Load PDF using PyPDFLoader
            loader = PyPDFLoader(pdf_path)
            pages = loader.load()
            
            if self.debug:
                debug_print("Extracted Pages", {
                    "num_pages": len(pages),
                    "first_page_metadata": pages[0].metadata if pages else None
                })
            
            # Process extracted pages
            processed_pages = []
            for page in pages:
                page_data = {
                    "page_number": page.metadata.get("page", 0) + 1,  # Convert 0-based to 1-based
                    "text": page.page_content
                }
                if extract_metadata:
                    page_data["metadata"] = page.metadata
                processed_pages.append(page_data)
            
            result = {
                "success": True,
                "filename": os.path.basename(pdf_path),
                "file_path": pdf_path,
                "total_pages": len(processed_pages),
                "pages": processed_pages,
                "file_size": os.path.getsize(pdf_path)
            }
            
            if self.debug:
                debug_print("Extraction Success", {
                    "filename": result["filename"],
                    "total_pages": result["total_pages"],
                    "file_size": result["file_size"]
                })
            
            return result
            
        except Exception as e:
            error_msg = str(e)
            if self.debug:
                import traceback
                debug_print("Extraction Error", {
                    "error": error_msg,
                    "traceback": traceback.format_exc()
                })
            return {
                "success": False, 
                "error": error_msg,
                "filename": os.path.basename(pdf_path) if pdf_path else None
            }
    
    def extract_text_from_directory(self, directory: str, file_pattern: str = "*.pdf", extract_metadata: bool = True) -> Dict:
        """Extract text from all PDF files in a directory
        
        Args:
            directory (str): Directory containing PDF files
            file_pattern (str): Pattern to match PDF files (default: "*.pdf")
            extract_metadata (bool): Whether to extract metadata
            
        Returns:
            dict: Dictionary containing extraction results for all PDFs
        """
        try:
            if self.debug:
                debug_print("Directory Extraction Request", {
                    "directory": directory,
                    "file_pattern": file_pattern,
                    "extract_metadata": extract_metadata
                })
            
            # Check if directory exists
            if not os.path.exists(directory):
                error_msg = f"Directory not found: {directory}"
                if self.debug:
                    debug_print("Error", error_msg)
                return {"success": False, "error": error_msg}
            
            # Get list of PDF files
            pdf_files = list(Path(directory).glob(file_pattern))
            
            if self.debug:
                debug_print("Found PDF Files", {
                    "count": len(pdf_files),
                    "files": [str(f) for f in pdf_files]
                })
            
            # Process each PDF file
            results = []
            for pdf_file in pdf_files:
                result = self.extract_text(str(pdf_file), extract_metadata=extract_metadata)
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
            error_msg = str(e)
            if self.debug:
                import traceback
                debug_print("Directory Extraction Error", {
                    "error": error_msg,
                    "traceback": traceback.format_exc()
                })
            return {"success": False, "error": error_msg}

def main():
    # Initialize the PDF extraction agent
    agent = PDFExtractionAgent(debug=True)
    
    # Example: Extract text from a single PDF
    pdf_path = "downloads/Invoice-SlingshotAI-sept-21.pdf"
    if os.path.exists(pdf_path):
        print("\nExtracting text from single PDF...")
        result = agent.extract_text(pdf_path)
        
        if result["success"]:
            print(f"\n✅ Successfully extracted text from: {result['filename']}")
            print(f"Total pages: {result['total_pages']}")
            print(f"File size: {result['file_size']} bytes")
            
            for page in result["pages"]:
                print(f"\n📄 Page {page['page_number']}:")
                print(f"{page['text'][:500]}...")  # Print first 500 chars of each page
        else:
            print(f"\n❌ Failed to extract text: {result['error']}")
    
    # Example: Extract text from all PDFs in downloads directory
    print("\nExtracting text from all PDFs in downloads directory...")
    results = agent.extract_text_from_directory("downloads")
    
    if results["success"]:
        print(f"\n✅ Processed {results['total_files']} PDF files")
        print(f"Successful: {results['successful_files']}")
        print(f"Failed: {results['failed_files']}")
        
        for result in results["results"]:
            if result["success"]:
                print(f"\n📑 {result['filename']}:")
                print(f"Total pages: {result['total_pages']}")
                print(f"File size: {result['file_size']} bytes")
                
                # Print first page preview
                if result["pages"]:
                    first_page = result["pages"][0]
                    print(f"\nFirst page preview:")
                    print(f"{first_page['text'][:300]}...")
            else:
                print(f"\n❌ Failed to process {result.get('filename', 'unknown')}")
                print(f"   Error: {result['error']}")
    else:
        print(f"\n❌ Error processing directory: {results['error']}")

if __name__ == "__main__":
    main() 