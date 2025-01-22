"""Shared utilities and tools for all agents."""

from typing import Dict, List, Optional, Any
import json
import traceback
from pathlib import Path
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get debug mode from environment
DEBUG = os.getenv("DEBUG", "FALSE").upper() == "TRUE"

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

__all__ = [
    'DEBUG',
    'debug_print',
    'format_error',
    'get_safe_filename',
    'format_timestamp',
    'ensure_directory',
    'format_currency'
] 