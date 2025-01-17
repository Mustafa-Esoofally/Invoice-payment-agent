from composio_client import get_composio_client
from datetime import datetime
from typing import Dict, List, Optional

class EmailAgent:
    def __init__(self):
        """Initialize the email agent with Composio tools."""
        # Get Composio client
        client = get_composio_client()
        
        # Get required tools
        self.gmail_tool = client.get_tool('GMAIL_FETCH_EMAILS')
        self.attachment_tool = client.get_tool('GMAIL_GET_ATTACHMENT')
        
        if not self.gmail_tool or not self.attachment_tool:
            raise ValueError("Failed to initialize required Gmail tools")
    
    def fetch_emails(self, query: str = None, max_results: int = 15) -> List[Dict]:
        """Fetch emails using Composio's Gmail integration"""
        try:
            # Add specific filters to reduce response size
            base_query = "newer_than:7d"  # Only fetch emails from last 7 days
            if query:
                full_query = f"{base_query} {query}"
            else:
                full_query = base_query
            
            # Call the tool directly with parameters
            result = self.gmail_tool.run({
                'query': full_query,
                'max_results': max_results,
                'user_id': 'me',
                'include_spam_trash': False
            })
            
            return self._process_email_response(result)
        except Exception as e:
            print(f"Error fetching emails: {e}")
            return []
    
    def get_attachment(self, message_id: str, attachment_id: str, file_name: str) -> Optional[Dict]:
        """Get a specific attachment from an email"""
        try:
            # Call the tool directly with parameters
            result = self.attachment_tool.run({
                'message_id': message_id,
                'attachment_id': attachment_id,
                'file_name': file_name,
                'user_id': 'me'
            })
            
            return result
        except Exception as e:
            print(f"Error getting attachment: {e}")
            return None
    
    def _process_email_response(self, response: Dict) -> List[Dict]:
        """Process the email response and extract relevant details"""
        if not response or not isinstance(response, dict):
            return []
        
        try:
            data = response.get('data', {})
            response_data = data.get('response_data', {})
            messages = response_data.get('messages', [])
            if not messages:
                return []
                
            processed_emails = []
            for msg in messages:
                # Extract basic email info
                email_data = {
                    'message_id': msg.get('messageId'),
                    'thread_id': msg.get('threadId'),
                    'timestamp': self._format_timestamp(msg.get('messageTimestamp')),
                    'subject': msg.get('subject', ''),
                    'sender': msg.get('sender', ''),
                    'labels': msg.get('labelIds', []),
                    'preview': msg.get('preview', {}).get('body', ''),
                    'attachments': []
                }
                
                # Process attachments if any
                attachments = msg.get('attachmentList', [])
                if attachments:
                    email_data['attachments'] = [{
                        'filename': att.get('filename', ''),
                        'attachment_id': att.get('attachmentId', ''),
                        'mime_type': att.get('mimeType', '')
                    } for att in attachments]
                
                processed_emails.append(email_data)
            
            return processed_emails
            
        except Exception as e:
            print(f"Error processing response: {e}")
            return []
    
    def _format_timestamp(self, timestamp_str: str) -> Optional[str]:
        """Format timestamp to readable date"""
        if not timestamp_str:
            return None
        try:
            dt = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%SZ")
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return timestamp_str

def main():
    # Initialize the email agent
    agent = EmailAgent()
    
    try:
        # Fetch emails with attachments from last 7 days
        print("Fetching emails...")
        emails = agent.fetch_emails(query="has:attachment", max_results=15)
        
        if not emails:
            print("No emails found.")
            return
            
        # Print email details
        for idx, email in enumerate(emails, 1):
            print(f"\n📧 Email {idx}")
            print(f"Subject: {email['subject']}")
            print(f"From: {email['sender']}")
            print(f"Date: {email['timestamp']}")
            print(f"Labels: {', '.join(email['labels'])}")
            print(f"Preview: {email['preview'][:100]}...")
            
            if email['attachments']:
                print("📎 Attachments:")
                for att in email['attachments']:
                    print(f"  - {att['filename']} ({att['mime_type']})")
            print("-" * 50)
    
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main() 