#!/usr/bin/env python3
"""
YouTube Shorts Automation Agent Framework
=========================================
A modular, agent-based framework for automating the creation and upload of YouTube Shorts.
Each agent specializes in a specific part of the workflow, with a coordinator orchestrating
the entire process.

This version uses Ollama with Deepseek for content generation and GPU acceleration for video encoding.
"""

import asyncio
import argparse
import sys
import os
import multiprocessing

# Add the parent directory to the Python path to allow imports to work
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import from the modules, adjusting the imports to match the actual file locations
from agents.upload_agent import UploadAgent
from framework import YouTubeShortsFramework


async def main_async():
    """Async main function."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="YouTube Shorts Automation Framework")
    parser.add_argument("-c", "--config", help="Path to configuration file (JSON or YAML)")
    parser.add_argument("-b", "--background", help="Path to background image")
    parser.add_argument("-m", "--music", help="Path to background music")
    parser.add_argument("-u", "--upload", action="store_true", help="Enable auto-upload to YouTube")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("--setup", action="store_true", help="Run first-time setup for YouTube API")
    parser.add_argument("--model", help="Specify LLM model to use (e.g. deepseek-r1:latest)")
    parser.add_argument("--debug-llm", action="store_true", help="Print raw LLM output for debugging")
    
    args = parser.parse_args()
    
    # Create custom config from command-line arguments
    config = {}
    
    if args.background:
        config["default_background"] = args.background
    
    if args.music:
        config["default_music"] = args.music
    
    if args.upload:
        config["auto_upload"] = True
    
    if args.verbose:
        config["logging_level"] = "DEBUG"
        
    if args.model:
        config["llm_model"] = args.model
    
    if args.debug_llm:
        config["debug_llm_output"] = True
    
    # Create framework instance
    framework = YouTubeShortsFramework(config)
    
    # Load config file if specified
    if args.config:
        if not framework.load_config_file(args.config):
            return 1
    
    # If setup flag is specified, run OAuth setup
    if args.setup:
        upload_agent = UploadAgent(framework.config, framework.workspace, "upload_setup")
        await upload_agent.setup_youtube_oauth(save_creds=True)
        print("YouTube API setup complete.")
        return 0
    
    # Run the pipeline
    success = await framework.run()
    
    return 0 if success else 1


def main():
    """Synchronous entry point."""
    try:
        # Import multiprocessing here to ensure it's accessible
        import multiprocessing
        
        # Handle platform-specific event loop settings
        if sys.platform == 'win32':
            # On Windows, we need to use a different event loop policy
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        elif sys.platform == 'darwin':
            # On macOS, use spawn method for multiprocessing
            multiprocessing.set_start_method('spawn', force=True)
        
        return asyncio.run(main_async())
    except KeyboardInterrupt:
        from youtube_shorts.config import logger
        logger.info("Process interrupted by user")
        return 1


if __name__ == "__main__":
    print("\n===== YOUTUBE SHORTS AUTOMATION FRAMEWORK =====")
    print("Version: 2.0 - Using Ollama with Deepseek and GPU acceleration")
    print("====================================================\n")
    sys.exit(main())
