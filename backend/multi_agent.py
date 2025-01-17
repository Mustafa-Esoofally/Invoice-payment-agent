from email_agent import EmailAgent
from attachment_agent import AttachmentAgent, debug_print
from langchain.agents import AgentType, initialize_agent
from langchain.chat_models import ChatOpenAI
from langchain.tools import Tool
from langchain.memory import ConversationBufferMemory
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class EmailProcessingAgent:
    def __init__(self, debug=True):
        """Initialize the multi-agent system
        
        Args:
            debug (bool): Enable debug output
        """
        self.debug = debug
        
        # Initialize sub-agents
        self.email_agent = EmailAgent()
        self.attachment_agent = AttachmentAgent(debug=debug)
        
        if self.debug:
            debug_print("Multi-Agent System Initialized", {
                "email_agent": bool(self.email_agent),
                "attachment_agent": bool(self.attachment_agent),
                "debug_mode": debug
            })
    
    def process_emails(self, query=None, days=7, max_results=10):
        """Process emails and download attachments based on criteria"""
        try:
            if self.debug:
                debug_print("Process Request", {
                    "query": query,
                    "days": days,
                    "max_results": max_results
                })
            
            # Build the query string
            if query:
                full_query = f"{query} newer_than:{days}d"
            else:
                full_query = f"has:attachment newer_than:{days}d"
            
            if self.debug:
                debug_print("Search Query", full_query)
            
            # Fetch emails with attachments
            emails = self.email_agent.fetch_emails(
                query=full_query,
                max_results=max_results
            )
            
            if self.debug:
                debug_print("Fetched Emails", emails)
            
            if not emails or not isinstance(emails, list):
                error_msg = "No emails found or invalid response"
                if self.debug:
                    debug_print("Error", error_msg)
                return {"success": False, "error": error_msg}
            
            # Process each email's attachments
            results = []
            for email in emails:
                if self.debug:
                    debug_print("Processing Email", {
                        "subject": email.get("subject"),
                        "message_id": email.get("message_id"),
                        "attachments": email.get("attachments", [])
                    })
                
                attachments = email.get("attachments", [])
                if not attachments:
                    continue
                
                # Download attachments
                download_info = [{
                    "message_id": email["message_id"],
                    "attachment_id": att["attachment_id"],
                    "filename": att["filename"]
                } for att in attachments]
                
                download_results = self.attachment_agent.download_multiple_attachments(download_info)
                
                results.append({
                    "email": {
                        "subject": email.get("subject"),
                        "sender": email.get("sender"),
                        "date": email.get("timestamp")  # Updated to match email_agent's field name
                    },
                    "attachments": download_results
                })
            
            if self.debug:
                debug_print("Final Results", results)
            
            return {
                "success": True,
                "processed_emails": len(emails),
                "downloaded_attachments": sum(len(r["attachments"]) for r in results),
                "results": results
            }
            
        except Exception as e:
            error_msg = str(e)
            if self.debug:
                import traceback
                debug_print("Process Error", {
                    "error": error_msg,
                    "traceback": traceback.format_exc()
                })
            return {"success": False, "error": error_msg}

def main():
    # Initialize the multi-agent system with debug mode
    agent = EmailProcessingAgent(debug=True)
    
    # Process emails with attachments from the last 7 days
    results = agent.process_emails(
        query="has:attachment",
        days=7,
        max_results=10
    )
    
    # Print results
    if results["success"]:
        print("\n✅ Email Processing Complete")
        print(f"Processed {results['processed_emails']} emails")
        print(f"Downloaded {results['downloaded_attachments']} attachments")
        
        for result in results["results"]:
            print(f"\n📧 Email: {result['email']['subject']}")
            print(f"   From: {result['email']['sender']}")
            print(f"   Date: {result['email']['date']}")
            
            for att in result["attachments"]:
                if att["success"]:
                    print(f"\n   📎 Downloaded: {att['filename']}")
                    print(f"      Saved as: {att['file_path']}")
                    print(f"      Size: {att['size']} bytes")
                else:
                    print(f"\n   ❌ Failed to download {att['filename']}")
                    print(f"      Error: {att['error']}")
    else:
        print(f"\n❌ Error: {results['error']}")

if __name__ == "__main__":
    main() 