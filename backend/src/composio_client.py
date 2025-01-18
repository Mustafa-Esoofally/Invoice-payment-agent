"""Composio client initialization and configuration."""

from composio_langchain import ComposioToolSet
from dotenv import load_dotenv
import os
from typing import List, Optional, Dict
import json

# Load environment variables
load_dotenv()

# Global cache for tools
_tools_cache: Dict[str, List] = {}

def debug_print(title: str, data: any, indent: int = 2) -> None:
    """Print debug information in a structured format
    
    Args:
        title (str): Title of the debug message
        data (any): Data to print
        indent (int): Indentation level for JSON formatting
    """
    print(f"\n🔍 DEBUG: {title}")
    if isinstance(data, (dict, list)):
        print(json.dumps(data, indent=indent, default=str))
    else:
        print(data)
    print("-" * 50)

def get_api_key(debug: bool = False) -> str:
    """Get Composio API key from environment variables
    
    Args:
        debug (bool): Enable debug output
        
    Returns:
        str: API key
        
    Raises:
        ValueError: If API key is not found in environment variables
    """
    api_key = os.getenv("COMPOSIO_API_KEY")
    if not api_key:
        error = "COMPOSIO_API_KEY environment variable not found"
        if debug:
            debug_print("API Key Error", error)
        raise ValueError(error)
    
    if debug:
        debug_print("API Key", {"exists": bool(api_key)})
    
    return api_key

def get_tools(actions: Optional[List[str]] = None, debug: bool = False, **kwargs) -> List:
    """Get Composio tools for specific actions
    
    Args:
        actions (List[str], optional): List of action names to get tools for.
                                     If None, returns all available tools.
        debug (bool): Enable debug output
        **kwargs: Additional arguments to pass to get_tools
        
    Returns:
        List: List of tools for the specified actions
    """
    try:
        # Create a cache key from the actions and kwargs
        cache_key = str(sorted(actions or [])) + str(sorted(kwargs.items()))
        
        # Check if tools are already cached
        if cache_key in _tools_cache:
            if debug:
                debug_print("Using Cached Tools", {
                    "actions": actions,
                    "cache_key": cache_key
                })
            return _tools_cache[cache_key]
        
        # Initialize Composio with API key
        api_key = get_api_key(debug=debug)
        composio = ComposioToolSet(api_key=api_key)
        
        # Get and cache the tools
        tools = composio.get_tools(actions=actions, **kwargs)
        _tools_cache[cache_key] = tools
        
        if debug:
            debug_print("Got New Tools", {
                "actions": actions,
                "num_tools": len(tools),
                "tool_names": [t.name for t in tools]
            })
        
        return tools
        
    except Exception as e:
        if debug:
            debug_print("Error Getting Tools", {
                "error": str(e),
                "actions": actions,
                "kwargs": kwargs
            })
        raise

def get_tool(action_name: str, debug: bool = False, **kwargs) -> Optional[object]:
    """Get a specific Composio tool by action name
    
    Args:
        action_name (str): Name of the action to get tool for
        debug (bool): Enable debug output
        **kwargs: Additional arguments to pass to get_tools
        
    Returns:
        object: Tool for the specified action, or None if not found
    """
    try:
        tools = get_tools(actions=[action_name], debug=debug, **kwargs)
        tool = next((tool for tool in tools if tool.name == action_name), None)
        
        if debug:
            debug_print("Got Tool", {
                "action_name": action_name,
                "found": bool(tool)
            })
        
        return tool
        
    except Exception as e:
        if debug:
            debug_print("Error Getting Tool", {
                "error": str(e),
                "action_name": action_name
            })
        raise

def clear_cache(debug: bool = False) -> None:
    """Clear the cached tools
    
    Args:
        debug (bool): Enable debug output
    """
    _tools_cache.clear()
    if debug:
        debug_print("Cache Cleared", {"cache_size": len(_tools_cache)})

def main():
    debug = True
    
    try:
        # Get Gmail tools
        gmail_tools = get_tools(
            actions=['GMAIL_FETCH_EMAILS', 'GMAIL_GET_ATTACHMENT'],
            debug=debug
        )
        print(f"\n✅ Successfully initialized with {len(gmail_tools)} Gmail tools")
        
        # Get specific tool
        fetch_tool = get_tool('GMAIL_FETCH_EMAILS', debug=debug)
        if fetch_tool:
            print(f"✅ Successfully got Gmail fetch tool: {fetch_tool.name}")
        
        # Clear cache example
        clear_cache(debug=debug)
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    main() 