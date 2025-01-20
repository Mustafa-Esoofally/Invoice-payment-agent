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

# Initialize Gmail tools globally
FETCH_TOOL = get_tool('GMAIL_FETCH_EMAILS')
ATTACHMENT_TOOL = get_tool('GMAIL_GET_ATTACHMENT')

def fetch_emails(
    query: str = "has:attachment newer_than:7d",
    max_results: int = 15,
    include_spam_trash: bool = False,
    debug: bool = False
) -> Dict:
    """Fetch emails from Gmail using search criteria
    
    Args:
        query (str): Gmail search query
        max_results (int): Maximum number of results
        include_spam_trash (bool): Include spam/trash folders
        debug (bool): Enable debug output
        
    Returns:
        dict: Processed email results
    """
    try:
        if debug:
            debug_print("Fetch Request", {
                "query": query,
                "max_results": max_results,
                "include_spam_trash": include_spam_trash
            })
        
        # Call Gmail fetch tool
        result = FETCH_TOOL.run({
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
        
        if debug:
            debug_print("Fetched Emails", response)
            
        return response
        
    except Exception as e:
        error = format_error(e)
        if debug:
            debug_print("Fetch Error", error)
        return {"success": False, "error": str(e)}

def download_attachment(
    message_id: str,
    attachment_id: str,
    filename: str,
    download_dir: str = "downloads",
    debug: bool = False
) -> Dict:
    """Download an attachment from a Gmail message
    
    Args:
        message_id (str): Gmail message ID
        attachment_id (str): Attachment ID
        filename (str): Original filename
        download_dir (str): Directory to save attachments
        debug (bool): Enable debug output
        
    Returns:
        dict: Download result with file info
    """
    try:
        if debug:
            debug_print("Download Request", {
                "message_id": message_id,
                "attachment_id": attachment_id,
                "filename": filename
            })
        
        # Ensure download directory exists
        download_dir = ensure_directory(download_dir)
        
        # Call Gmail attachment tool
        result = ATTACHMENT_TOOL.run({
            'message_id': message_id,
            'attachment_id': attachment_id,
            'file_name': filename,
            'user_id': 'me'
        })
        
        if result.get('successfull') and result.get('data', {}).get('file'):
            file_path = result['data']['file']
            
            # Create unique filename
            target_path = get_safe_filename(download_dir, filename)
            
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
                
                if debug:
                    debug_print("Download Success", response)
                    
                return response
                
            except Exception as e:
                error = {
                    'success': False,
                    'error': f"Failed to copy file: {str(e)}",
                    'filename': filename
                }
                if debug:
                    debug_print("Copy Error", error)
                return error
        else:
            error = {
                'success': False,
                'error': result.get('error', 'No file data in response'),
                'filename': filename
            }
            if debug:
                debug_print("Download Error", error)
            return error
            
    except Exception as e:
        error = format_error(e)
        if debug:
            debug_print("Download Error", error)
        return {"success": False, "error": str(e)}

def main():
    """Example usage of email functions"""
    try:
        # Fetch emails with attachments
        result = fetch_emails(max_results=5, debug=True)
        
        if result["success"] and result["emails"]:
            # Download first attachment from first email
            email = result["emails"][0]
            if email["attachments"]:
                attachment = email["attachments"][0]
                download_attachment(
                    message_id=email["message_id"],
                    attachment_id=attachment["attachment_id"],
                    filename=attachment["filename"],
                    debug=True
                )
                
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    main() 