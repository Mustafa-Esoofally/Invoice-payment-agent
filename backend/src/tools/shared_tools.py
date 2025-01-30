"""Shared utilities and tools for all agents."""

from typing import Dict, List, Optional, Any
import json
import traceback
from pathlib import Path
import os
from datetime import datetime
from dotenv import load_dotenv, find_dotenv
from langchain_openai import ChatOpenAI
from composio_langchain import ComposioToolSet

# Load environment variables
load_dotenv()

# Get debug mode from environment
DEBUG = os.getenv("DEBUG", "FALSE").upper() == "TRUE"

# Global cache for Composio tools
_tools_cache: Dict[str, List] = {}
_composio_client: Optional[ComposioToolSet] = None

def debug_print(*args: Any, **kwargs: Any) -> None:
    """Enhanced debug print function with timestamp and formatting"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n[{timestamp}] 🔍 DEBUG:", *args, **kwargs)
    print("-" * 50)

def format_error(error: Exception, include_traceback: bool = True) -> Dict:
    """Format error information consistently
    
    Args:
        error (Exception): The error to format
        include_traceback (bool): Whether to include the traceback
        
    Returns:
        dict: Formatted error information
    """
    error_info = {
        "error": str(error),
        "type": error.__class__.__name__
    }
    
    if include_traceback:
        error_info["traceback"] = traceback.format_exc()
    
    return error_info

def get_safe_filename(directory: str, filename: str) -> Path:
    """Create a safe filename that doesn't overwrite existing files
    
    Args:
        directory (str): Directory to save file in
        filename (str): Original filename
        
    Returns:
        Path: Safe file path
    """
    name = Path(filename).stem
    suffix = Path(filename).suffix
    counter = 1
    
    while True:
        if counter == 1:
            new_path = Path(directory) / filename
        else:
            new_path = Path(directory) / f"{name}_{counter}{suffix}"
        
        if not new_path.exists():
            return new_path
        counter += 1

def format_timestamp(timestamp_str: str) -> Optional[str]:
    """Format timestamp to readable date
    
    Args:
        timestamp_str (str): Timestamp string
        
    Returns:
        str: Formatted date string
    """
    if not timestamp_str:
        return None
    try:
        dt = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%SZ")
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return timestamp_str

def ensure_directory(path: str) -> Path:
    """Ensure a directory exists and create it if it doesn't
    
    Args:
        path (str): Directory path
        
    Returns:
        Path: Path object for the directory
    """
    directory = Path(path)
    directory.mkdir(exist_ok=True, parents=True)
    return directory

def format_currency(amount: float, currency: str = "USD") -> str:
    """Format currency amount
    
    Args:
        amount (float): Amount to format
        currency (str): Currency code
        
    Returns:
        str: Formatted currency string
    """
    if currency == "USD":
        return f"${amount:,.2f}"
    return f"{amount:,.2f} {currency}"

def get_env_file_path() -> Path:
    """Get the correct .env file path.
    
    Returns:
        Path: Path to the .env file
    """
    # Try different possible locations
    possible_paths = [
        Path.cwd() / '.env',  # Current working directory
        Path(__file__).parent.parent / '.env',  # Backend root directory
        Path(__file__).parent / '.env',  # src directory
    ]
    
    for path in possible_paths:
        if path.exists():
            return path
            
    # Try using find_dotenv as a fallback
    dotenv_path = find_dotenv()
    if dotenv_path:
        return Path(dotenv_path)
            
    raise FileNotFoundError("Could not find .env file in any expected location")

def get_openai_client(model_name: str = None, temperature: float = 0) -> ChatOpenAI:
    """Get shared OpenAI client instance.
    
    Args:
        model_name (str, optional): OpenAI model to use. Defaults to env var or gpt-4
        temperature (float, optional): Model temperature. Defaults to 0
        
    Returns:
        ChatOpenAI: Configured OpenAI client
        
    Raises:
        ValueError: If OPENAI_API_KEY is not set
    """
    # Force reload environment variables
    env_path = get_env_file_path()
    load_dotenv(dotenv_path=env_path, override=True)
    
    # Get API key from environment
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not found")
    
    # Validate API key format
    if not api_key.startswith('sk-'):
        raise ValueError("Invalid OpenAI API key format. Key should start with 'sk-'")
        
    # Get model name with default
    if not model_name:
        model_name = os.getenv("OPENAI_MODEL", "gpt-4")
    
    # Initialize client with proper configuration
    client = ChatOpenAI(
        api_key=api_key,
        model=model_name,
        temperature=temperature
    )
    
    return client

def init_composio(debug: bool = False) -> None:
    """Initialize Composio client with API key
    
    Args:
        debug (bool): Enable debug output
    """
    global _composio_client
    
    try:
        # Get API key from environment
        api_key = os.getenv("COMPOSIO_API_KEY")
        if not api_key:
            raise ValueError("COMPOSIO_API_KEY environment variable not found")
        
        # Initialize client
        _composio_client = ComposioToolSet(api_key=api_key)
        
        # Test connection by getting basic tools
        tools = _composio_client.get_tools(actions=['GMAIL_FETCH_EMAILS'])
        
        if debug:
            debug_print("Composio Client Initialized", {
                "api_key_exists": bool(api_key),
                "client_initialized": bool(_composio_client),
                "test_tools": len(tools)
            })
            
    except Exception as e:
        error_msg = f"Failed to initialize Composio client: {str(e)}"
        if debug:
            debug_print("Initialization Error", error_msg)
        raise RuntimeError(error_msg)

def get_composio_tools(actions: Optional[List[str]] = None, debug: bool = False, **kwargs) -> List:
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
        global _composio_client
        
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
        
        # Initialize client if not already initialized
        if not _composio_client:
            init_composio(debug=debug)
        
        # Get and cache the tools
        tools = _composio_client.get_tools(actions=actions, **kwargs)
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

def get_composio_tool(action: str, debug: bool = False) -> Optional[Any]:
    """Get a specific Composio tool by action name
    
    Args:
        action (str): Action name to get tool for
        debug (bool): Enable debug output
        
    Returns:
        Any: Tool for the specified action, or None if not found
    """
    tools = get_composio_tools(actions=[action], debug=debug)
    return tools[0] if tools else None

def clear_composio_cache(debug: bool = False) -> None:
    """Clear the Composio tools cache
    
    Args:
        debug (bool): Enable debug output
    """
    global _tools_cache
    if debug:
        debug_print("Clearing Tools Cache", {
            "num_cached": len(_tools_cache)
        })
    _tools_cache.clear()

# Create default shared OpenAI client instance
openai_client = get_openai_client()

__all__ = [
    'DEBUG',
    'debug_print',
    'format_error',
    'get_safe_filename',
    'format_timestamp',
    'ensure_directory',
    'format_currency',
    'get_env_file_path',
    'get_openai_client',
    'openai_client',
    'init_composio',
    'get_composio_tools',
    'get_composio_tool',
    'clear_composio_cache'
] 