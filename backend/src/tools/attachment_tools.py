from composio_client import get_composio_client
from pathlib import Path
import os
import shutil
from typing import Dict, List, Optional

def debug_print(title: str, data: any, indent: int = 2):
    """Helper function to print debug information"""
    print(f"\n🔍 DEBUG: {title}")
    if isinstance(data, (dict, list)):
        import json
        print(json.dumps(data, indent=indent, default=str))
    else:
        print(data)
    print("-" * 50)

class AttachmentAgent:
    def __init__(self, download_dir: str = "downloads", debug: bool = False):
        """Initialize the attachment agent
        
        Args:
            download_dir (str): Directory to save downloaded attachments
            debug (bool): Enable debug output
        """
        self.debug = debug
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True)
        
        # Get Composio client and tool
        client = get_composio_client()
        self.attachment_tool = client.get_tool('GMAIL_GET_ATTACHMENT')
        
        if not self.attachment_tool:
            raise ValueError("Failed to initialize Gmail attachment tool")
        
        if self.debug:
            debug_print("Attachment Agent Initialized", {
                "download_dir": str(self.download_dir),
                "composio_api_key": bool(client.api_key),
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
            
            print(f"Downloading attachment: {filename}")
            
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
                target_path = self._get_safe_filename(filename)
                
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
                debug_print("Download Error", error_msg)
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
                debug_print("Multiple Download Error", error_msg)
            return [{
                'success': False,
                'error': error_msg,
                'filename': att.get('filename', 'Unknown')
            } for att in attachments]
    
    def _get_safe_filename(self, filename: str) -> Path:
        """Create a safe filename that doesn't overwrite existing files
        
        Args:
            filename (str): Original filename
            
        Returns:
            Path: Safe file path
        """
        name = Path(filename).stem
        suffix = Path(filename).suffix
        counter = 1
        
        while True:
            if counter == 1:
                new_path = self.download_dir / filename
            else:
                new_path = self.download_dir / f"{name}_{counter}{suffix}"
            
            if not new_path.exists():
                return new_path
            counter += 1

def main():
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
    print("\nDownloading attachments...")
    results = agent.download_multiple_attachments(attachments)
    
    # Print results
    for result in results:
        if result['success']:
            print(f"\n✅ Downloaded: {result['original_name']}")
            print(f"Saved as: {result['file_path']}")
            print(f"Size: {result['size']} bytes")
        else:
            print(f"\n❌ Failed to download {result['filename']}")
            print(f"Error: {result['error']}")

if __name__ == "__main__":
    main() 