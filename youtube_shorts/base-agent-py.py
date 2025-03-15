"""
Base agent class for YouTube Shorts Automation Framework.
"""

import datetime
from abc import ABC, abstractmethod
from typing import Dict, Any
import logging

class Agent(ABC):
    """Base agent class that all specialized agents inherit from."""
    
    def __init__(self, config: Dict[str, Any], workspace: Dict[str, Any], name: str):
        """
        Initialize the agent.
        
        Args:
            config: The global configuration
            workspace: Shared workspace for agents to communicate
            name: The name of this agent
        """
        self.config = config
        self.workspace = workspace
        self.name = name
        self.logger = logging.getLogger(f"youtube_shorts.{name}")
        self.setup()
    
    def setup(self):
        """Set up the agent. Override this method to add initialization logic."""
        pass
    
    @abstractmethod
    async def execute(self) -> bool:
        """
        Execute the agent's task.
        
        Returns:
            bool: True if successful, False otherwise
        """
        pass
    
    def report(self, message: str, level: str = "info"):
        """
        Log a message and update the workspace with the agent's progress.
        
        Args:
            message: The message to log
            level: The logging level (debug, info, warning, error, critical)
        """
        if level == "debug":
            self.logger.debug(message)
        elif level == "info":
            self.logger.info(message)
        elif level == "warning":
            self.logger.warning(message)
        elif level == "error":
            self.logger.error(message)
        elif level == "critical":
            self.logger.critical(message)
        
        # Update workspace with progress
        if "progress" not in self.workspace:
            self.workspace["progress"] = {}
        
        if self.name not in self.workspace["progress"]:
            self.workspace["progress"][self.name] = []
        
        self.workspace["progress"][self.name].append({
            "timestamp": datetime.datetime.now().isoformat(),
            "message": message,
            "level": level
        })
