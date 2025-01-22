"""Payment agent for processing invoice payments using Langchain."""

from langchain.agents import create_openai_functions_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from typing import Dict, List, Optional
import os
import json
from datetime import datetime

from src.tools.payment_tools import (
    BalanceTool,
    SearchPayeesTool,
    SendPaymentTool,
    CheckoutUrlTool
)
from src.openai_client import get_openai_client

# Initialize payment tools
tools = [
    BalanceTool(),
    SearchPayeesTool(),
    SendPaymentTool(),
    CheckoutUrlTool()
]

# Create agent prompt
prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a helpful AI assistant that processes invoice payments.
Your main tasks are:
1. Check available balance before processing payments
2. Search for and verify payee information
3. Send payments or generate checkout URLs as needed
4. Track and report payment status

Use the provided tools to accomplish these tasks efficiently and accurately.
If you encounter any issues, explain them clearly and suggest next steps."""),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

# Create agent with tools
agent = create_openai_functions_agent(get_openai_client(), tools, prompt)
agent_executor = AgentExecutor(
    agent=agent, 
    tools=tools, 
    verbose=True,
    tags=["payment-agent"],
    metadata={
        "agent_type": "payment_processing",
        "agent_version": "1.0.0"
    }
)

async def process_payment(invoice_data: Dict) -> Dict:
    """Process invoice payment using LangChain agent."""
    
    try:
        print(f"\n[PAYMENT] 💸 Processing invoice: {invoice_data.get('invoice_number')}")
        
        # Create agent task
        task = f"""Process this invoice payment with these requirements:
        1. Check current balance
        2. Search for payee: {invoice_data.get('recipient')}
        3. If payee found:
           - Send payment of ${invoice_data.get('paid_amount')} 
           - Use invoice number as payment reference
        4. If payee not found:
           - Generate checkout URL for manual payment
        5. Return payment status and details
        
        Invoice Data:
        {invoice_data}
        """
        
        # Execute agent
        result = await agent_executor.ainvoke({
            "input": task,
            "chat_history": []
        })
        
        print(f"\n[PAYMENT] ✅ Processing complete")
        return result
            
    except Exception as e:
        print(f"\n[PAYMENT] ❌ Error: {str(e)}")
        return {"success": False, "error": str(e)}

async def get_payment_history() -> Dict[str, List]:
    """Get payment history.
    
    Returns:
        Dict[str, List]: List of payment records
    """
    try:
        history_file = os.path.join("invoice data", "payment_history.json")
        if not os.path.exists(history_file):
            return {"payments": []}
            
        with open(history_file, 'r') as f:
            history = json.load(f)
            
        # Transform data to match frontend expectations
        transformed_history = []
        for record in history:
            email_data = record.get("email_data", {})
            invoice_data = record.get("invoice_data", {})
            result = record.get("result", {})

            transformed_record = {
                "timestamp": record["timestamp"],
                "email": {
                    "subject": email_data.get("subject"),
                    "sender": email_data.get("sender"),
                    "timestamp": invoice_data.get("date")
                },
                "invoice": {
            "invoice_number": invoice_data.get("invoice_number"),
                    "paid_amount": invoice_data.get("paid_amount"),
            "recipient": invoice_data.get("recipient"),
                    "date": invoice_data.get("date"),
                    "due_date": invoice_data.get("due_date"),
                    "description": invoice_data.get("description")
                },
                "payment": {
                    "success": result.get("success", False),
            "amount": invoice_data.get("paid_amount"),
                    "recipient": invoice_data.get("recipient"),
                    "reference": result.get("payment_id"),
                    "error": result.get("error")
                }
            }
            transformed_history.append(transformed_record)
            
        return {"payments": transformed_history}
            
    except Exception as e:
        return {"error": f"Error reading payment history: {str(e)}"} 