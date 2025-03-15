"""
Common utility functions for YouTube Shorts Automation Framework.
"""

import os
import asyncio
from typing import List, Dict, Any


async def run_process(cmd: List[str], **kwargs) -> str:
    """
    Run a subprocess asynchronously and return stdout as string.
    
    Args:
        cmd: Command to run
        kwargs: Additional arguments for subprocess
        
    Returns:
        str: Output from process
    """
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        **kwargs
    )
    stdout, stderr = await process.communicate()
    
    if process.returncode != 0:
        raise Exception(f"Process error: {stderr.decode()}")
    
    return stdout.decode()


def find_file_in_paths(filename: str, paths: List[str] = None) -> str:
    """
    Find a file in a list of paths.
    
    Args:
        filename: Name of file to find
        paths: List of paths to search (defaults to current directory and common system paths)
        
    Returns:
        str: Full path to file if found, empty string otherwise
    """
    if paths is None:
        # Default search paths
        paths = [
            os.getcwd(),  # Current directory
            os.path.expanduser("~"),  # User home directory
            os.path.join(os.path.expanduser("~"), "Downloads"),  # Downloads folder
            "/usr/local/bin",  # Common Linux/macOS path
        ]
    
    for path in paths:
        full_path = os.path.join(path, filename)
        if os.path.exists(full_path):
            return full_path
    
    return ""
