"""Email agent for handling Gmail operations using Langchain."""

import json
import os
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

from composio_langchain import ComposioToolSet

# Initialize Composio toolset
composio_tools = ComposioToolSet(api_key=os.getenv("COMPOSIO_API_KEY"))

def get_gmail_tools():
    """Get Gmail tools from ComposioToolSet."""
    return composio_tools.get_tools(actions=['GMAIL_FETCH_EMAILS', 'GMAIL_SEND_EMAIL'])

def process_email_response(response_data: Dict) -> Dict:
    """Process email response to extract only essential information."""
    try:
        if not response_data or not isinstance(response_data, dict):
            return {"success": False, "error": "Invalid response data"}
            
        if not response_data.get('successfull'):
            error = response_data.get('error', 'Failed to fetch emails')
            return {"success": False, "error": error}
            
        response_data = response_data.get('data', {}).get('response_data', {})
        if not response_data:
            return {"success": True, "data": []}
            
        messages = response_data.get('messages', [])
        if not messages:
            return {"success": True, "data": []}
            
        processed_messages = []
        for msg in messages:
            try:
                # Extract only essential fields
                processed_msg = {
                    'messageId': msg.get('messageId'),
                    'threadId': msg.get('threadId'),
                    'subject': msg.get('subject', '').strip(),
                    'sender': msg.get('sender', '').strip(),
                    'date': msg.get('messageTimestamp'),
                    'attachments': []
                }
                
                # Process attachments if present
                attachments = msg.get('attachmentList', [])
                for att in attachments:
                    if att.get('filename', '').lower().endswith('.pdf'):
                        processed_msg['attachments'].append({
                            'filename': att.get('filename'),
                            'attachmentId': att.get('attachmentId'),
                            'size': att.get('size', 0)
                        })
                        
                # Only include messages with PDF attachments
                if processed_msg['attachments']:
                    processed_messages.append(processed_msg)
            except Exception as e:
                print(f"\n[EMAIL] ⚠️ Error processing message: {str(e)}")
                continue
                
        return {"success": True, "data": processed_messages}
        
    except Exception as e:
        return {"success": False, "error": f"Failed to process email response: {str(e)}"}

async def process_emails(query: str = "subject:invoice has:attachment newer_than:7d", max_results: int = 10) -> Dict:
    """Process invoice emails using Gmail tools."""
    try:
        print("\n[EMAIL] 📧 Fetching emails...")
        
        # Get Gmail tools
        gmail_tools = get_gmail_tools()
        if not gmail_tools:
            return {"success": False, "error": "Failed to initialize Gmail tools"}
            
        # Find fetch emails tool
        fetch_tool = None
        for tool in gmail_tools:
            if tool.name == "GMAIL_FETCH_EMAILS":
                fetch_tool = tool
                break
                
        if not fetch_tool:
            return {"success": False, "error": "Gmail fetch tool not found"}
        
        # Execute the fetch emails action
        response = await fetch_tool.ainvoke({
            "user_id": "me",
            "query": query,
            "max_results": max_results,
            "include_spam_trash": False
        })
        
        print(f"\n[EMAIL] 📨 Processing response...")
        if not response:
            return {"success": False, "error": "No response from Gmail API"}
            
        result = process_email_response(response)
        
        if not result["success"]:
            print(f"\n[EMAIL] ❌ {result['error']}")
            return result
            
        emails = result["data"]
        print(f"\n[EMAIL] ✅ Found {len(emails)} invoice emails with PDF attachments")
        return result
        
    except Exception as e:
        error_msg = f"Error in email processing: {str(e)}"
        print(f"\n[EMAIL] ❌ {error_msg}")
        return {"success": False, "error": error_msg}

async def send_reply(to: str, subject: str, body: str, thread_id: Optional[str] = None) -> Dict:
    """Send email reply using Gmail tools."""
    try:
        print(f"\n[EMAIL] 📤 Sending reply to: {to}")
        
        # Get Gmail tools
        gmail_tools = get_gmail_tools()
        if not gmail_tools:
            return {"success": False, "error": "Failed to initialize Gmail tools"}
            
        # Find send email tool
        send_tool = None
        for tool in gmail_tools:
            if tool.name == "GMAIL_SEND_EMAIL":
                send_tool = tool
                break
                
        if not send_tool:
            return {"success": False, "error": "Gmail send tool not found"}
        
        # Create message data
        message_data = {
            "to": to,
            "subject": subject,
            "body": body,
            "thread_id": thread_id
        }
        
        # Execute send action
        response = await send_tool.ainvoke(message_data)
        
        if response.get('successful'):
            print(f"\n[EMAIL] ✅ Reply sent successfully")
            return {"success": True, "data": response.get('response_data')}
        else:
            error_msg = "Failed to send email reply"
            print(f"\n[EMAIL] ❌ {error_msg}")
            return {"success": False, "error": error_msg}
            
    except Exception as e:
        error_msg = f"Error sending reply: {str(e)}"
        print(f"\n[EMAIL] ❌ {error_msg}")
        return {"success": False, "error": error_msg} 