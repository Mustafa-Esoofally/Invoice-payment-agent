"""Composio client initialization and configuration."""

from composio_langchain import ComposioToolSet
from dotenv import load_dotenv
import os
from typing import List, Optional

# Load environment variables
load_dotenv()

class ComposioClient:
    _instance = None
    _tools = {}

    def __new__(cls):
        """Singleton pattern to ensure only one instance of the client exists."""
        if cls._instance is None:
            cls._instance = super(ComposioClient, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the Composio client if not already initialized."""
        if not self._initialized:
            self.api_key = os.getenv("COMPOSIO_API_KEY")
            if not self.api_key:
                raise ValueError("COMPOSIO_API_KEY environment variable not found")
            
            self.composio = ComposioToolSet(api_key=self.api_key)
            self._initialized = True

    def get_tools(self, actions: Optional[List[str]] = None, **kwargs) -> List:
        """Get Composio tools for specific actions.
        
        Args:
            actions (List[str], optional): List of action names to get tools for.
                                         If None, returns all available tools.
            **kwargs: Additional arguments to pass to get_tools.
        
        Returns:
            List: List of tools for the specified actions.
        """
        # Create a cache key from the actions and kwargs
        cache_key = str(sorted(actions or [])) + str(sorted(kwargs.items()))
        
        # Check if tools are already cached
        if cache_key in self._tools:
            return self._tools[cache_key]
        
        # Get and cache the tools
        tools = self.composio.get_tools(actions=actions, **kwargs)
        self._tools[cache_key] = tools
        return tools

    def get_tool(self, action_name: str, **kwargs) -> Optional[object]:
        """Get a specific Composio tool by action name.
        
        Args:
            action_name (str): Name of the action to get tool for.
            **kwargs: Additional arguments to pass to get_tools.
        
        Returns:
            object: Tool for the specified action, or None if not found.
        """
        tools = self.get_tools(actions=[action_name], **kwargs)
        return next((tool for tool in tools if tool.name == action_name), None)

    def clear_cache(self):
        """Clear the cached tools."""
        self._tools.clear()

def get_composio_client() -> ComposioClient:
    """Get the singleton instance of ComposioClient.
    
    Returns:
        ComposioClient: The singleton instance.
    """
    return ComposioClient()

# Example usage
if __name__ == "__main__":
    try:
        # Get client instance
        client = get_composio_client()
        
        # Get Gmail tools
        gmail_tools = client.get_tools(actions=['GMAIL_FETCH_EMAILS', 'GMAIL_GET_ATTACHMENT'])
        print(f"\n✅ Successfully initialized with {len(gmail_tools)} Gmail tools")
        
        # Get specific tool
        fetch_tool = client.get_tool('GMAIL_FETCH_EMAILS')
        if fetch_tool:
            print(f"✅ Successfully got Gmail fetch tool: {fetch_tool.name}")
        
    except Exception as e:
        print(f"❌ Error initializing Composio client: {str(e)}") 