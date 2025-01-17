"""Payment agent for processing payments from JSON input."""

from typing import List, Dict, Union, TypedDict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, FunctionMessage
from langgraph.graph import StateGraph, END
from langchain_core.utils.function_calling import convert_to_openai_function
import json
import os
from dotenv import load_dotenv
from payment_tools import tools, PaymentItem, BatchPaymentSchema

# Load environment variables
load_dotenv()

# Check for OpenAI API key
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError(
        "OpenAI API key not found. Please set the OPENAI_API_KEY environment variable."
    )

# Define the agent state
class AgentState(TypedDict):
    messages: List[BaseMessage]
    next: str

# Convert tools to OpenAI functions
functions = [convert_to_openai_function(t) for t in tools]

# Create the LLM
llm = ChatOpenAI(temperature=0, model="gpt-4", streaming=True)

def process_payments_from_json(json_data: Union[str, Dict, List]) -> List[PaymentItem]:
    """Process payments from JSON input."""
    try:
        # Handle string input
        if isinstance(json_data, str):
            try:
                data = json.loads(json_data)
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON format")
        else:
            data = json_data
        
        # Handle different JSON structures
        if isinstance(data, dict) and 'payments' in data:
            payments = data['payments']
        elif isinstance(data, list):
            payments = data
        else:
            raise ValueError("JSON must contain a list of payments or a 'payments' key with a list")
        
        # Convert to PaymentItem objects
        return [PaymentItem(**payment) for payment in payments]
    except Exception as e:
        raise ValueError(f"Failed to process payment data: {str(e)}")

def agent(state: AgentState) -> Union[AgentState, str]:
    """Process payments using the payment agent."""
    messages = state["messages"]
    last_user_msg = next((m.content for m in reversed(messages) if isinstance(m, HumanMessage)), "")
    
    try:
        # Extract JSON from the message
        json_start = last_user_msg.find('{')
        json_end = last_user_msg.rfind('}') + 1
        if json_start == -1 or json_end == 0:
            # Try list format
            json_start = last_user_msg.find('[')
            json_end = last_user_msg.rfind(']') + 1
        
        if json_start == -1 or json_end == 0:
            messages.append(AIMessage(content="""Please provide payment details in JSON format. Example:
{
    "payments": [
        {
            "id": "PAY001",
            "amount": 100.00,
            "currency": "USD",
            "recipientName": "John Doe",
            "memo": "Service payment"
        }
    ]
}
Or as a list:
[
    {
        "id": "PAY001",
        "amount": 100.00,
        "currency": "USD",
        "recipientName": "John Doe",
        "memo": "Service payment"
    }
]"""))
            return {"messages": messages, "next": END}
        
        # Extract and parse JSON
        json_str = last_user_msg[json_start:json_end]
        payments = process_payments_from_json(json_str)
        
        # First check balance
        balance_tool = next(t for t in tools if t.name == "get_balance")
        balance_result = balance_tool.invoke({})
        messages.append(FunctionMessage(content=balance_result, name="get_balance"))
        
        # Process batch payments
        batch_tool = next(t for t in tools if t.name == "process_batch_payments")
        batch_result = batch_tool.invoke({"payments": payments})
        messages.append(FunctionMessage(content=batch_result, name="process_batch_payments"))
        
        # Add final summary
        if "Error: Insufficient funds" in batch_result:
            messages.append(AIMessage(content=f"""Unable to process payments due to insufficient funds.
{batch_result}

Would you like me to generate a checkout URL to add more funds?"""))
        else:
            messages.append(AIMessage(content=f"""I've processed your payment request:
{batch_result}

Would you like to process any other payments?"""))
    except Exception as e:
        error_msg = f"""❌ Error processing payments: {str(e)}

Please ensure your payment data is in the correct format and try again."""
        messages.append(AIMessage(content=error_msg))
    
    return {"messages": messages, "next": END}

# Create the graph
workflow = StateGraph(AgentState)
workflow.add_node("agent", agent)
workflow.set_entry_point("agent")
app = workflow.compile()

def process_payment_request(request: str) -> str:
    """Process a payment request using the LangGraph agent."""
    try:
        state = {
            "messages": [HumanMessage(content=request)],
            "next": "agent"
        }
        
        result = app.invoke(state)
        messages = result["messages"]
        
        # Return the last non-empty message
        for message in reversed(messages):
            if message.content.strip():
                return message.content
        return "No response generated."
    except Exception as e:
        return f"""❌ Error processing request: {str(e)}

Please try again with valid payment details."""

def main():
    """Main function to test the payment agent."""
    print("\n🤖 Payment Agent Test\n")
    
    # Test with sample payments
    sample_payments = {
        "payments": [
            {
                "id": "TEST001",
                "amount": 50.00,
                "currency": "USD",
                "recipientName": "Tech Consulting Services",
                "memo": "Test payment 1"
            },
            {
                "id": "TEST002",
                "amount": 75.00,
                "currency": "USD",
                "recipientName": "Tech Solutions LLC",
                "memo": "Test payment 2"
            }
        ]
    }
    
    print("Processing sample payments...")
    response = process_payment_request(json.dumps(sample_payments))
    print(f"✅ Response: {response}\n")
    print("-" * 80)

if __name__ == "__main__":
    main() 