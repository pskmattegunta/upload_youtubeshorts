"""
Coordinator agent for orchestrating the entire workflow in YouTube Shorts Automation.
"""

import os
import sys
import time
import subprocess
from typing import Dict, Any, List

from agents.base_agent import Agent
from agents.content_agent import ContentAgent
from agents.audio_agent import AudioAgent
from agents.visual_agent import VisualAgent
from agents.video_agent import VideoAgent
from agents.upload_agent import UploadAgent
import datetime


class CoordinatorAgent(Agent):
    """Coordinator agent responsible for orchestrating the entire workflow."""
    
    def setup(self):
        """Set up the coordinator agent."""
        self.agents = {}
        self.current_step = 0
        self.pipeline_steps = [
            {
                "name": "content",
                "description": "Generate health tip and script",
                "agent_class": ContentAgent
            },
            {
                "name": "audio",
                "description": "Generate audio from script",
                "agent_class": AudioAgent
            },
            {
                "name": "visual",
                "description": "Generate video frames",
                "agent_class": VisualAgent
            },
            {
                "name": "video",
                "description": "Create final video",
                "agent_class": VideoAgent
            },
            {
                "name": "upload",
                "description": "Upload to YouTube (if enabled)",
                "agent_class": UploadAgent
            }
        ]
        
        # Create run directory with timestamp
        self.run_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_dir = f"youtube_short_{self.run_timestamp}"
        os.makedirs(self.run_dir, exist_ok=True)
        self.workspace["run_dir"] = self.run_dir
        
        # Detect system capabilities
        self.detect_system_capabilities()
        
        self.report(f"Created run directory: {self.run_dir}", "info")
        
        # Create required subdirectories
        for subdir in ["frames", "audio", "output", "assets"]:
            os.makedirs(os.path.join(self.run_dir, subdir), exist_ok=True)
    
    def detect_system_capabilities(self):
        """Detect system capabilities and update config accordingly."""
        # Detect CPU cores
        cpu_count = os.cpu_count()
        self.report(f"Detected {cpu_count} CPU cores", "info")
        
        # If parallel_processes not specified, use CPU count - 1 (leave one for system)
        if not self.config.get("parallel_processes"):
            self.config["parallel_processes"] = max(1, cpu_count - 1)
            self.report(f"Setting parallel processes to {self.config['parallel_processes']}", "info")
        
        # Detect platform
        platform = sys.platform
        self.report(f"Detected platform: {platform}", "info")
        
        # Check for GPU acceleration on macOS
        if platform == 'darwin':
            self.report("Detecting macOS GPU capabilities...", "info")
            try:
                # Check for videotoolbox support
                result = subprocess.run(
                    ["ffmpeg", "-hide_banner", "-hwaccels"],
                    capture_output=True,
                    text=True,
                    check=False  # Don't raise exception on non-zero exit
                )
                
                if "videotoolbox" in result.stdout.lower():
                    self.report("VideoToolbox GPU acceleration is available", "info")
                    self.config["use_gpu"] = True
                else:
                    self.report("VideoToolbox GPU acceleration not detected", "info")
                    self.config["use_gpu"] = False
            except Exception as e:
                self.report(f"Error detecting GPU capabilities: {e}", "warning")
                self.config["use_gpu"] = False
        else:
            # No GPU acceleration on other platforms (for simplicity)
            self.config["use_gpu"] = False
        
        # Check for AMD/Intel hardware acceleration
        if platform == 'darwin':
            # Check for hardware vendor
            try:
                result = subprocess.run(
                    ["system_profiler", "SPDisplaysDataType"],
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                output = result.stdout.lower()
                if "amd" in output:
                    self.report("Detected AMD GPU", "info")
                    self.config["gpu_vendor"] = "amd"
                elif "intel" in output:
                    self.report("Detected Intel GPU", "info")
                    self.config["gpu_vendor"] = "intel"
                elif "nvidia" in output:
                    self.report("Detected NVIDIA GPU", "info")
                    self.config["gpu_vendor"] = "nvidia"
                else:
                    self.report("Unknown GPU vendor", "info")
                    self.config["gpu_vendor"] = "unknown"
            except Exception as e:
                self.report(f"Error detecting GPU vendor: {e}", "warning")
                self.config["gpu_vendor"] = "unknown"
    
    def create_agents(self):
        """Create all agents in the pipeline."""
        for step in self.pipeline_steps:
            agent_name = step["name"]
            agent_class = step["agent_class"]
            self.agents[agent_name] = agent_class(self.config, self.workspace, agent_name)
            self.report(f"Created {agent_name} agent", "debug")
    
    async def execute(self) -> bool:
        """
        Execute the full pipeline.
        
        Returns:
            bool: True if all steps succeeded, False otherwise
        """
        self.report("Starting YouTube Shorts generation pipeline", "info")
        self.report(f"System configuration: {self.config['parallel_processes']} cores, GPU acceleration: {'enabled' if self.config.get('use_gpu') else 'disabled'}", "info")
        
        # Create all agents
        self.create_agents()
        
        # Record start time
        start_time = time.time()
        
        # Run each agent in sequence
        for i, step in enumerate(self.pipeline_steps):
            agent_name = step["name"]
            description = step["description"]
            
            self.current_step = i + 1
            progress_msg = f"Step {self.current_step}/{len(self.pipeline_steps)}: {description}"
            separator = "=" * len(progress_msg)
            
            self.report(separator, "info")
            self.report(progress_msg, "info")
            self.report(separator, "info")
            
            # Record step start time
            step_start_time = time.time()
            
            agent = self.agents[agent_name]
            success = await agent.execute()
            
            # Record step end time and calculate duration
            step_end_time = time.time()
            step_duration = step_end_time - step_start_time
            self.report(f"Completed step in {step_duration:.2f} seconds", "info")
            
            if not success:
                self.report(f"Pipeline failed at step {self.current_step}: {agent_name}", "error")
                return False
        
        # Record end time and calculate total duration
        end_time = time.time()
        total_duration = end_time - start_time
        
        # All steps completed successfully
        self.report(f"YouTube Shorts generation pipeline completed successfully in {total_duration:.2f} seconds!", "info")
        
        # Print final output paths
        if "final_video" in self.workspace:
            self.report(f"Final video saved to: {self.workspace['final_video']}", "info")
        
        if "youtube_video_url" in self.workspace:
            self.report(f"Video uploaded to YouTube: {self.workspace['youtube_video_url']}", "info")
        
        return True
