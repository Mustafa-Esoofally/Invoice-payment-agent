"""Tools for handling email operations."""

from langchain.agents import create_openai_functions_agent, AgentExecutor
from langchain import hub
from composio_langchain import ComposioToolSet
from pathlib import Path
import os
from typing import Dict, List, Optional
import json
from datetime import datetime

from tools.shared_tools import get_composio_tool, debug_print
from tools.attachment_tools import AttachmentAgent

# Initialize Composio toolset with API key
COMPOSIO_API_KEY = os.getenv("COMPOSIO_API_KEY")
composio_tools = ComposioToolSet(api_key=COMPOSIO_API_KEY)

def debug_print(title: str, data: any, indent: int = 2):
    """Print debug information with consistent formatting"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n[{timestamp}] [EMAIL] {title}:")
    if isinstance(data, (dict, list)):
        print(json.dumps(data, indent=indent, default=str))
    else:
        print(data)
    print("-" * 50)

class GmailAgent:
    """Agent for handling Gmail operations using Composio."""
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.gmail_tool = composio_tools.get_tool("GMAIL_REPLY_TO_THREAD")
        if not self.gmail_tool:
            raise ValueError("Failed to initialize Gmail reply tool")
        
    def reply_to_thread(self, thread_id: str, message: str, recipient_email: str, is_html: bool = False) -> Dict:
        """Reply to an email thread using Composio's Gmail API.
        
        Args:
            thread_id: ID of the thread to reply to
            message: Body of the reply message  
            recipient_email: Email address of the recipient
            is_html: Set to True if the body content is HTML
            
        Returns:
            Dict with response data and success status
        """
        try:
            # Prepare request parameters based on Composio schema
            params = {
                "thread_id": thread_id,
                "message_body": message,
                "recipient_email": recipient_email,
                "user_id": "me",
                "is_html": is_html
            }
            
            if self.debug:
                debug_print("Gmail Reply Parameters", {
                    "thread_id": thread_id,
                    "recipient": recipient_email,
                    "is_html": is_html
                })
            
            # Call Composio Gmail reply API
            response = self.gmail_tool.run(params)
            
            if self.debug:
                debug_print("Gmail API Response", response)
            
            return {
                "success": response.get("successful", False),
                "error": response.get("error"),
                "response": response
            }
            
        except Exception as e:
            error_msg = str(e)
            if self.debug:
                debug_print("Gmail Reply Error", {
                    "error": error_msg,
                    "type": type(e).__name__
                })
            return {
                "success": False,
                "error": error_msg
            }

def main():
    # Example usage
    try:
        # Initialize agents
        gmail_agent = GmailAgent(debug=True)
        attachment_agent = AttachmentAgent(debug=True)
        
        # Example attachment information
        attachments = [
            {
                "message_id": "1946aaf0de7d93b8",
                "attachment_id": "attachment-0f0edf62",
                "filename": "Invoice-SlingshotAI-sept-21.pdf"
            }
        ]
        
        # Download attachments
        print("\n📥 Downloading attachments...")
        results = attachment_agent.download_multiple_attachments(attachments)
        
        # Print results
        for result in results:
            if result['success']:
                print(f"\n✅ Downloaded successfully:")
                print(f"  • Original name: {result['original_name']}")
                print(f"  • Saved as: {result['file_path']}")
                print(f"  • Size: {result['size']} bytes")
            else:
                print(f"\n❌ Download failed:")
                print(f"  • Filename: {result['filename']}")
                print(f"  • Error: {result['error']}")
        
        # Example email reply
        thread_id = "thread_123"
        message = "Thank you for your email. We have received your invoice."
        recipient = "sender@example.com"
        
        reply_result = gmail_agent.reply_to_thread(thread_id, message, recipient)
        if reply_result["success"]:
            print("\n✅ Email reply sent successfully")
        else:
            print(f"\n❌ Failed to send reply: {reply_result['error']}")
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")

if __name__ == "__main__":
    main() 