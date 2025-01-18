"""Email agent for handling Gmail interactions and attachments."""

from typing import Dict, List, Optional
from pathlib import Path
import os

from tools.shared_tools import (
    debug_print,
    format_error,
    get_safe_filename,
    format_timestamp,
    ensure_directory
)
from composio_client import get_tool

class EmailAgent:
    """Agent for handling Gmail interactions and attachments."""
    
    def __init__(self, download_dir: str = "downloads", debug: bool = False):
        """Initialize the email agent
        
        Args:
            download_dir (str): Directory to save attachments
            debug (bool): Enable debug output
        """
        self.download_dir = ensure_directory(download_dir)
        self.debug = debug
        
        # Initialize Gmail tools
        self.fetch_tool = get_tool('GMAIL_FETCH_EMAILS')
        self.attachment_tool = get_tool('GMAIL_GET_ATTACHMENT')
        
        if not self.fetch_tool or not self.attachment_tool:
            raise ValueError("Failed to initialize Gmail tools")
            
        if self.debug:
            debug_print("Email Agent Initialized", {
                "download_dir": str(self.download_dir),
                "fetch_tool": bool(self.fetch_tool),
                "attachment_tool": bool(self.attachment_tool)
            })
    
    def fetch_emails(
        self, 
        query: str = "has:attachment newer_than:7d",
        max_results: int = 15,
        include_spam_trash: bool = False
    ) -> Dict:
        """Fetch emails from Gmail using search criteria
        
        Args:
            query (str): Gmail search query
            max_results (int): Maximum number of results
            include_spam_trash (bool): Include spam/trash folders
            
        Returns:
            dict: Processed email results
        """
        try:
            if self.debug:
                debug_print("Fetch Request", {
                    "query": query,
                    "max_results": max_results,
                    "include_spam_trash": include_spam_trash
                })
            
            # Call Gmail fetch tool
            result = self.fetch_tool.run({
                'query': query,
                'max_results': max_results,
                'user_id': 'me',
                'include_spam_trash': include_spam_trash
            })
            
            if not result or not isinstance(result, dict):
                return {"success": False, "error": "Invalid response from Gmail API"}
            
            # Process response
            data = result.get('data', {})
            response_data = data.get('response_data', {})
            messages = response_data.get('messages', [])
            
            processed_emails = []
            for msg in messages:
                email_data = {
                    'message_id': msg.get('messageId'),
                    'thread_id': msg.get('threadId'),
                    'timestamp': format_timestamp(msg.get('messageTimestamp')),
                    'subject': msg.get('subject', ''),
                    'sender': msg.get('sender', ''),
                    'labels': msg.get('labelIds', []),
                    'preview': msg.get('preview', {}).get('body', ''),
                    'attachments': [{
                        'filename': att.get('filename', ''),
                        'attachment_id': att.get('attachmentId', ''),
                        'mime_type': att.get('mimeType', '')
                    } for att in msg.get('attachmentList', [])]
                }
                processed_emails.append(email_data)
            
            response = {
                "success": True,
                "total_emails": len(processed_emails),
                "emails": processed_emails
            }
            
            if self.debug:
                debug_print("Fetched Emails", response)
                
            return response
            
        except Exception as e:
            error = format_error(e)
            if self.debug:
                debug_print("Fetch Error", error)
            return {"success": False, "error": str(e)}
    
    def download_attachment(
        self,
        message_id: str,
        attachment_id: str,
        filename: str
    ) -> Dict:
        """Download an attachment from a Gmail message
        
        Args:
            message_id (str): Gmail message ID
            attachment_id (str): Attachment ID
            filename (str): Original filename
            
        Returns:
            dict: Download result with file info
        """
        try:
            if self.debug:
                debug_print("Download Request", {
                    "message_id": message_id,
                    "attachment_id": attachment_id,
                    "filename": filename
                })
            
            # Call Gmail attachment tool
            result = self.attachment_tool.run({
                'message_id': message_id,
                'attachment_id': attachment_id,
                'file_name': filename,
                'user_id': 'me'
            })
            
            if result.get('successfull') and result.get('data', {}).get('file'):
                file_path = result['data']['file']
                
                # Create unique filename
                target_path = get_safe_filename(self.download_dir, filename)
                
                try:
                    # Copy file to download directory
                    import shutil
                    shutil.copy2(file_path, target_path)
                    
                    response = {
                        'success': True,
                        'file_path': str(target_path),
                        'original_name': filename,
                        'size': os.path.getsize(target_path)
                    }
                    
                    if self.debug:
                        debug_print("Download Success", response)
                        
                    return response
                    
                except Exception as e:
                    error = {
                        'success': False,
                        'error': f"Failed to copy file: {str(e)}",
                        'filename': filename
                    }
                    if self.debug:
                        debug_print("Copy Error", error)
                    return error
            else:
                error = {
                    'success': False,
                    'error': result.get('error', 'No file data in response'),
                    'filename': filename
                }
                if self.debug:
                    debug_print("Download Error", error)
                return error
                
        except Exception as e:
            error = format_error(e)
            if self.debug:
                debug_print("Download Error", error)
            return {"success": False, "error": str(e)}

def main():
    """Example usage of EmailAgent"""
    try:
        # Initialize agent
        agent = EmailAgent(debug=True)
        
        # Fetch emails with attachments
        result = agent.fetch_emails(max_results=5)
        
        if result["success"] and result["emails"]:
            # Download first attachment from first email
            email = result["emails"][0]
            if email["attachments"]:
                attachment = email["attachments"][0]
                agent.download_attachment(
                    message_id=email["message_id"],
                    attachment_id=attachment["attachment_id"],
                    filename=attachment["filename"]
                )
                
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    main() 