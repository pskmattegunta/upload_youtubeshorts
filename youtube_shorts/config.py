"""
Configuration settings for YouTube Shorts Automation Framework.
"""

import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("youtube_shorts.log")
    ]
)

logger = logging.getLogger("youtube_shorts")

# Constants
MAX_DURATION = 45  # Max video duration in seconds (Shorts must be < 60s)

# Default configuration
DEFAULT_CONFIG = {
    "llm_model": "deepseek-r1:latest",
    "max_duration": 45,
    "video_width": 1080,
    "video_height": 1920,
    "fps": 30,
    "parallel_processes": None,  # None = auto-detect
    "output_dir": "output",
    "youtube_token_path": os.path.join(os.path.expanduser("~"), ".youtube_tokens", "token.pickle"),
    "default_background": "background.jpg",  # Default background image
    "default_music": "background.mp3",       # Default background music
    "auto_upload": False,
    "use_gpu": True,  # Use GPU acceleration when available
    "quality": "medium",  # low, medium, high
    "logging_level": "INFO",
    "debug_llm_output": False  # Set to True to print raw LLM output for debugging
}
