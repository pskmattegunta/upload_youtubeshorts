"""
Main framework class for YouTube Shorts Automation.
"""

import os
import logging
from typing import Dict, Any, Optional
from config import DEFAULT_CONFIG, logger

class YouTubeShortsFramework:
    """Main framework class for YouTube Shorts automation."""
    
    def __init__(self, config=None):
        """
        Initialize the framework.
        
        Args:
            config: Configuration dictionary (optional)
        """
        # Import coordinator here to avoid circular imports
        from coordinator import CoordinatorAgent
        
        # Load default config
        self.config = DEFAULT_CONFIG.copy()
        
        # Update with custom config if provided
        if config is not None:
            self.config.update(config)
        
        # Create workspace for agents to share data
        self.workspace = {}
        
        # Set up logging level
        level = getattr(logging, self.config.get("logging_level", "INFO").upper())
        logger.setLevel(level)
        
        # Create coordinator agent
        self.coordinator = CoordinatorAgent(self.config, self.workspace, "coordinator")
    
    def load_config_file(self, config_file: str) -> bool:
        """
        Load configuration from a file.
        
        Args:
            config_file: Path to JSON or YAML config file
            
        Returns:
            bool: True if loaded successfully, False otherwise
        """
        if not os.path.exists(config_file):
            logger.error(f"Config file not found: {config_file}")
            return False
        
        try:
            with open(config_file, 'r') as f:
                if config_file.endswith('.json'):
                    import json
                    custom_config = json.load(f)
                elif config_file.endswith(('.yaml', '.yml')):
                    try:
                        import yaml
                        custom_config = yaml.safe_load(f)
                    except ImportError:
                        logger.error("PyYAML is required to load YAML config files")
                        return False
                else:
                    logger.error("Config file must be JSON or YAML format")
                    return False
            
            # Update config
            self.config.update(custom_config)
            logger.info(f"Loaded configuration from {config_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading config file: {e}")
            return False
    
    async def run(self) -> bool:
        """
        Run the YouTube Shorts generation pipeline.
        
        Returns:
            bool: True if successful, False otherwise
        """
        return await self.coordinator.execute()
