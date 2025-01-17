from attachment_agent import AttachmentAgent
from pdf_extraction_agent import PDFExtractionAgent
from typing import Dict, List, Optional
import os
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

class EmailPDFProcessor:
    def __init__(self, download_dir="downloads", debug=True):
        """Initialize the email PDF processor
        
        Args:
            download_dir (str): Directory to save downloaded attachments
            debug (bool): Enable debug output
        """
        self.debug = debug
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True)
        
        # Initialize sub-agents
        self.attachment_agent = AttachmentAgent(download_dir=download_dir, debug=debug)
        self.pdf_agent = PDFExtractionAgent(debug=debug)
        
        if self.debug:
            debug_print("Email PDF Processor Initialized", {
                "download_dir": str(self.download_dir),
                "debug_mode": debug
            })
    
    def process_email_attachments(self, attachments_info: list) -> Dict:
        """Process email attachments - download and extract text from PDFs
        
        Args:
            attachments_info (list): List of attachment information from email agent
            
        Returns:
            dict: Processing results including downloaded files and extracted text
        """
        try:
            if self.debug:
                debug_print("Processing Attachments", attachments_info)
            
            # Download attachments
            download_results = self.attachment_agent.download_multiple_attachments(attachments_info)
            
            if self.debug:
                debug_print("Download Results", download_results)
            
            # Process downloaded PDFs
            processed_pdfs = []
            for result in download_results:
                if not result["success"]:
                    processed_pdfs.append({
                        "filename": result["filename"],
                        "success": False,
                        "error": result["error"]
                    })
                    continue
                
                # Check if file is a PDF
                file_path = result["file_path"]
                if not file_path.lower().endswith(".pdf"):
                    processed_pdfs.append({
                        "filename": result["filename"],
                        "success": True,
                        "is_pdf": False,
                        "download_info": result
                    })
                    continue
                
                # Extract text from PDF
                extraction_result = self.pdf_agent.extract_text(file_path)
                processed_pdfs.append({
                    "filename": result["filename"],
                    "success": extraction_result["success"],
                    "is_pdf": True,
                    "download_info": result,
                    "extraction_info": extraction_result
                })
            
            return {
                "success": True,
                "processed_files": len(processed_pdfs),
                "results": processed_pdfs
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
    
    def summarize_pdf_content(self, extraction_result: Dict) -> str:
        """Create a summary of the extracted PDF content
        
        Args:
            extraction_result (dict): PDF extraction result
            
        Returns:
            str: Summary of the PDF content
        """
        if not extraction_result["success"]:
            return f"❌ Failed to extract text: {extraction_result.get('error', 'Unknown error')}"
        
        summary = []
        summary.append(f"📑 {extraction_result['filename']}")
        summary.append(f"Pages: {extraction_result['total_pages']}")
        
        for page in extraction_result["pages"]:
            text = page["text"].strip()
            if text:
                preview = text[:300] + "..." if len(text) > 300 else text
                summary.append(f"\nPage {page['page_number']}:")
                summary.append(preview)
        
        return "\n".join(summary)

def main():
    # Initialize the processor
    processor = EmailPDFProcessor(debug=True)
    
    # Example attachment information
    attachments = [
        {
            "message_id": "1946aaf0de7d93b8",
            "attachment_id": "attachment-0f0edf62",
            "filename": "Invoice-SlingshotAI-sept-21.pdf"
        }
    ]
    
    # Process attachments
    print("\nProcessing email attachments...")
    results = processor.process_email_attachments(attachments)
    
    if results["success"]:
        print(f"\n✅ Processed {results['processed_files']} attachments")
        
        for result in results["results"]:
            print(f"\n{'=' * 50}")
            print(f"📎 {result['filename']}")
            
            if not result["success"]:
                print(f"❌ Error: {result['error']}")
                continue
            
            if result["is_pdf"]:
                print("\n📄 PDF Content:")
                print(processor.summarize_pdf_content(result["extraction_info"]))
            else:
                print("📁 Non-PDF file downloaded successfully")
                print(f"Saved as: {result['download_info']['file_path']}")
                print(f"Size: {result['download_info']['size']} bytes")
    else:
        print(f"\n❌ Error: {results['error']}")

if __name__ == "__main__":
    main() 