"""PDF agent for extracting invoice information using Langchain."""

from langchain.agents import create_openai_functions_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_community.document_loaders import PyPDFLoader
from typing import Dict
import os

from src.openai_client import get_openai_client

# Create tools list for PDF processing
tools = [
    # Add any specific PDF processing tools here
]

# Create agent prompt
prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a helpful AI assistant that extracts information from PDF files.
Your main tasks are:
1. Extract payment-related information from invoice PDFs
2. Identify and structure key details like amounts, dates, and recipient information
3. Format the extracted data in a consistent way

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
    tags=["pdf-agent"],
    metadata={
        "agent_type": "pdf_extraction",
        "agent_version": "1.0.0"
    }
)

async def extract_invoice_data(pdf_path: str) -> Dict:
    """Extract invoice information using LangChain agent."""
    
    try:
        print(f"\n[PDF] 📄 Processing: {pdf_path}")
        
        # Load PDF content
        loader = PyPDFLoader(pdf_path)
        pages = loader.load()
        content = "\n".join(page.page_content for page in pages)
        
        # Create agent task
        task = f"""Extract invoice information from this PDF with these requirements:
        1. Find all payment-related information:
           - Invoice number
           - Amount and currency
           - Due date
           - Description/memo
        2. Extract recipient details:
           - Full name
           - Email
           - Phone
           - Address
           - Tax ID if present
        3. Look for bank account details:
           - Account holder name
           - Account number
           - Account type
           - Routing number
           - Bank name
        4. Format the response as a structured JSON
        
        PDF Content:
        {content}
        """
        
        # Execute agent
        result = await agent_executor.ainvoke({
            "input": task,
            "chat_history": []
        })
        
        print(f"\n[PDF] ✅ Extraction complete")
        return result
        
    except Exception as e:
        print(f"\n[PDF] ❌ Error: {str(e)}")
        return {"success": False, "error": str(e)}