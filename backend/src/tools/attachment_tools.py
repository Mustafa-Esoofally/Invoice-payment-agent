"""Tools for handling email attachments."""

from typing import Dict, List, Optional
import os
import shutil
from pathlib import Path
import json
from datetime import datetime

from tools.shared_tools import (
    debug_print,
    get_composio_tool,
    get_safe_filename,
    ensure_directory
)

class AttachmentAgent:
    def __init__(self, download_dir: str = "downloads", debug: bool = False):
        """Initialize the attachment agent
        
        Args:
            download_dir (str): Directory to save downloaded attachments
            debug (bool): Enable debug output
        """
        self.debug = debug
        self.download_dir = ensure_directory(download_dir)
        
        # Get attachment tool using composio client
        self.attachment_tool = get_composio_tool('GMAIL_GET_ATTACHMENT', debug=debug)
        
        if not self.attachment_tool:
            raise ValueError("Failed to initialize Gmail attachment tool")
        
        if self.debug:
            debug_print("Attachment Agent Initialized", {
                "download_dir": str(self.download_dir),
                "tool_name": self.attachment_tool.name
            })
    
    def download_attachment(self, message_id: str, attachment_id: str, filename: str) -> Dict:
        """Download a specific attachment
        
        Args:
            message_id (str): Gmail message ID
            attachment_id (str): Attachment ID
            filename (str): Original filename
            
        Returns:
            dict: Download result with success status and file details
        """
        try:
            if self.debug:
                debug_print("Download Request", {
                    "message_id": message_id,
                    "attachment_id": attachment_id,
                    "filename": filename
                })
            
            print(f"\n📥 Downloading: {filename}")
            
            # Prepare API request
            params = {
                'message_id': message_id,
                'attachment_id': attachment_id,
                'file_name': filename,
                'user_id': 'me'
            }
            
            if self.debug:
                debug_print("API Request Parameters", params)
            
            # Call the API
            result = self.attachment_tool.run(params)
            
            if self.debug:
                debug_print("API Response", result)
            
            if result.get('successfull') and result.get('data', {}).get('file'):
                file_path = result['data']['file']
                
                if self.debug:
                    debug_print("File Path from API", file_path)
                
                # Create a unique filename to avoid overwrites
                target_path = get_safe_filename(self.download_dir, filename)
                
                try:
                    # Copy file to download directory
                    shutil.copy2(file_path, target_path)
                    result = {
                        'success': True,
                        'file_path': str(target_path),
                        'original_name': filename,
                        'size': os.path.getsize(target_path)
                    }
                    
                    if self.debug:
                        debug_print("Download Success", result)
                    
                    return result
                    
                except Exception as e:
                    error_msg = f"Failed to copy file: {str(e)}"
                    if self.debug:
                        debug_print("File Copy Error", error_msg)
                    return {
                        'success': False,
                        'error': error_msg,
                        'filename': filename
                    }
            else:
                error_msg = result.get('error', 'No file data in response')
                if self.debug:
                    debug_print("API Error", error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'filename': filename
                }
                
        except Exception as e:
            error_msg = str(e)
            if self.debug:
                debug_print("Download Error", {
                    "error": error_msg,
                    "type": type(e).__name__
                })
            return {
                'success': False,
                'error': error_msg,
                'filename': filename
            }
    
    def download_multiple_attachments(self, attachments: List[Dict]) -> List[Dict]:
        """Download multiple attachments
        
        Args:
            attachments (list): List of attachment information dictionaries
            
        Returns:
            list: List of download results
        """
        try:
            if self.debug:
                debug_print("Multiple Download Request", attachments)
            
            results = []
            print("\n📥 Processing attachments...")
            for attachment in attachments:
                result = self.download_attachment(
                    message_id=attachment['message_id'],
                    attachment_id=attachment['attachment_id'],
                    filename=attachment['filename']
                )
                results.append(result)
            
            if self.debug:
                debug_print("Multiple Download Results", results)
            
            return results
            
        except Exception as e:
            error_msg = str(e)
            if self.debug:
                debug_print("Multiple Download Error", {
                    "error": error_msg,
                    "type": type(e).__name__
                })
            return [{
                'success': False,
                'error': error_msg,
                'filename': att.get('filename', 'Unknown')
            } for att in attachments]

def main():
    # Example usage
    try:
        # Initialize the attachment agent
        agent = AttachmentAgent(debug=True)
        
        # Example attachment information
        attachments = [
            {
                "message_id": "1946aaf0de7d93b8",
                "attachment_id": "attachment-0f0edf62",
                "filename": "Invoice-SlingshotAI-sept-21.pdf"
            }
        ]
        
        # Download attachments
        results = agent.download_multiple_attachments(attachments)
        
        # Print results
        for result in results:
            if result.get('success', False):
                print(f"\n✅ Downloaded successfully:")
                print(f"  • Original name: {result['original_name']}")
                print(f"  • Saved as: {result['file_path']}")
                print(f"  • Size: {result['size']} bytes")
            else:
                print(f"\n❌ Download failed:")
                print(f"  • Filename: {result['filename']}")
                print(f"  • Error: {result['error']}")
                
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")

if __name__ == "__main__":
    main() 