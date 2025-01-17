from composio_langchain import ComposioToolSet
from dotenv import load_dotenv
import os
import base64
import json
from pathlib import Path

# Load environment variables
load_dotenv()

def debug_print(title: str, data: any, indent: int = 2):
    """Helper function to print debug information"""
    print(f"\n🔍 DEBUG: {title}")
    if isinstance(data, (dict, list)):
        print(json.dumps(data, indent=indent, default=str))
    else:
        print(data)
    print("-" * 50)

class AttachmentAgent:
    def __init__(self, download_dir="downloads", debug=True):
        """Initialize the attachment agent
        
        Args:
            download_dir (str): Directory to save downloaded attachments
            debug (bool): Enable debug output
        """
        self.debug = debug
        
        # Initialize Composio toolset
        self.composio = ComposioToolSet(api_key=os.getenv("COMPOSIO_API_KEY"))
        self.tools = self.composio.get_tools(actions=['GMAIL_GET_ATTACHMENT'])
        self.attachment_tool = next(tool for tool in self.tools if tool.name == 'GMAIL_GET_ATTACHMENT')
        
        # Setup download directory
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True)
        
        if self.debug:
            debug_print("Attachment Agent Initialized", {
                "download_dir": str(self.download_dir),
                "composio_api_key": bool(os.getenv("COMPOSIO_API_KEY")),
                "tool_name": self.attachment_tool.name if self.attachment_tool else None
            })
    
    def download_attachment(self, message_id: str, attachment_id: str, filename: str):
        """Download a specific attachment from an email"""
        try:
            if self.debug:
                debug_print("Download Request", {
                    "message_id": message_id,
                    "attachment_id": attachment_id,
                    "filename": filename
                })
            
            print(f"Downloading attachment: {filename}")
            
            # Call the Gmail attachment tool
            request_params = {
                'message_id': message_id,
                'attachment_id': attachment_id,
                'file_name': filename,
                'user_id': 'me'
            }
            
            if self.debug:
                debug_print("API Request Parameters", request_params)
            
            result = self.attachment_tool.run(request_params)
            
            if self.debug:
                debug_print("API Response", result)
            
            if not result or not isinstance(result, dict):
                error_msg = 'Invalid response from Gmail API'
                if self.debug:
                    debug_print("Error", error_msg)
                return {'success': False, 'error': error_msg}
            
            # Check if the response contains a file path
            if result.get('successfull') and result.get('data', {}).get('file'):
                file_path = result['data']['file']
                if self.debug:
                    debug_print("File Path from API", file_path)
                
                try:
                    # Create a safe filename in our download directory
                    safe_filename = self._get_safe_filename(filename)
                    target_path = self.download_dir / safe_filename
                    
                    # Copy the file from the API's location to our download directory
                    import shutil
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
                    error_msg = f'Failed to copy file: {str(e)}'
                    if self.debug:
                        import traceback
                        debug_print("Copy Error", {
                            "error": error_msg,
                            "traceback": traceback.format_exc()
                        })
                    return {'success': False, 'error': error_msg}
            
            # Extract file data from response (legacy format)
            file_data = result.get('file', {})
            if not file_data:
                error_msg = 'No file data in response'
                if self.debug:
                    debug_print("Error", error_msg)
                return {'success': False, 'error': error_msg}
            
            # Get file content and name
            content = file_data.get('content')
            name = file_data.get('name', filename)
            
            if self.debug:
                debug_print("File Info", {
                    "name": name,
                    "has_content": bool(content),
                    "content_length": len(content) if content else 0
                })
            
            if not content:
                error_msg = 'No file content in response'
                if self.debug:
                    debug_print("Error", error_msg)
                return {'success': False, 'error': error_msg}
            
            # Create a safe filename
            safe_filename = self._get_safe_filename(name)
            file_path = self.download_dir / safe_filename
            
            if self.debug:
                debug_print("File Path", str(file_path))
            
            # Save the file
            try:
                # Decode base64 content and write to file
                file_content = base64.b64decode(content)
                with open(file_path, 'wb') as f:
                    f.write(file_content)
                
                result = {
                    'success': True,
                    'file_path': str(file_path),
                    'original_name': name,
                    'size': len(file_content)
                }
                
                if self.debug:
                    debug_print("Download Success", result)
                
                return result
            
            except Exception as e:
                error_msg = f'Failed to save file: {str(e)}'
                if self.debug:
                    import traceback
                    debug_print("Save Error", {
                        "error": error_msg,
                        "traceback": traceback.format_exc()
                    })
                return {'success': False, 'error': error_msg}
            
        except Exception as e:
            error_msg = str(e)
            if self.debug:
                import traceback
                debug_print("Download Error", {
                    "error": error_msg,
                    "traceback": traceback.format_exc()
                })
            return {'success': False, 'error': error_msg}
    
    def download_multiple_attachments(self, attachments_info: list):
        """Download multiple attachments"""
        if self.debug:
            debug_print("Multiple Download Request", attachments_info)
        
        results = []
        for att in attachments_info:
            result = self.download_attachment(
                message_id=att['message_id'],
                attachment_id=att['attachment_id'],
                filename=att['filename']
            )
            results.append({
                'filename': att['filename'],
                **result
            })
        
        if self.debug:
            debug_print("Multiple Download Results", results)
        
        return results
    
    def _get_safe_filename(self, filename: str) -> str:
        """Create a safe version of the filename"""
        # Remove any path components
        filename = os.path.basename(filename)
        
        # If file exists, add a number to the filename
        base, ext = os.path.splitext(filename)
        counter = 1
        new_filename = filename
        
        while (self.download_dir / new_filename).exists():
            new_filename = f"{base}_{counter}{ext}"
            counter += 1
        
        return new_filename

def main():
    # Initialize the attachment agent with debug mode
    agent = AttachmentAgent(debug=True)
    
    # Example attachments to download
    attachments = [
        {
            'message_id': 'your_message_id',
            'attachment_id': 'your_attachment_id',
            'filename': 'example.pdf'
        }
    ]
    
    # Download attachments
    results = agent.download_multiple_attachments(attachments)
    
    # Print results
    for result in results:
        if result['success']:
            print(f"\n✅ Successfully downloaded: {result['filename']}")
            print(f"   Saved as: {result['file_path']}")
            print(f"   Size: {result['size']} bytes")
        else:
            print(f"\n❌ Failed to download {result['filename']}")
            print(f"   Error: {result['error']}")

if __name__ == "__main__":
    main() 