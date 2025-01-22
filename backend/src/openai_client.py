"""Shared OpenAI client configuration."""

import os
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
from langchain_openai import ChatOpenAI

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
    
    # print("\n🤖 Agent Configuration:")
    # print(f"Model: {model_name}")
    # print(f"Temperature: {temperature}")
    # print("✅ LLM initialized and ready")
    
    return client

# Create default shared client instance
openai_client = get_openai_client() 