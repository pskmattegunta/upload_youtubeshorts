"""
Content agent for health tips and script generation.
"""

import os
import sys
import random
import re
import subprocess
import traceback
from typing import List, Dict, Any, Optional

from agents.base_agent import Agent


class ContentAgent(Agent):
    """Agent responsible for content generation: health tip and script."""
    
    def setup(self):
        """Set up the Ollama client."""
        # Add debug output flag to configuration with default value
        self.debug_llm_output = self.config.get("debug_llm_output", False)
        self.report(f"Debug LLM output: {'enabled' if self.debug_llm_output else 'disabled'}", "info")
        
        try:
            import ollama
            self.ollama_available = True
            self.report("Ollama module loaded successfully.", "debug")
        except ImportError:
            self.ollama_available = False
            self.report("Ollama module not installed. Running pip install ollama...", "warning")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "ollama"])
                import ollama
                self.ollama_available = True
                self.report("Successfully installed Ollama module.", "info")
            except Exception as e:
                self.report(f"Failed to install Ollama package: {e}", "error")
                return
                
        # Check if requests is available for API calls
        try:
            import requests
            self.requests_available = True
        except ImportError:
            self.requests_available = False
            self.report("Requests package not installed. Running pip install requests...", "warning")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
                import requests
                self.requests_available = True
            except Exception as e:
                self.report(f"Failed to install requests package: {e}", "error")
        
        # Set up model configuration
        self.model_name = self.config.get("llm_model", "deepseek-r1:latest")
        self.report(f"Using LLM model: {self.model_name}", "info")
        
        # Test ollama connection
        if self.ollama_available:
            try:
                import ollama
                # Direct test to see if Ollama service is running
                try:
                    # Check if Ollama service is running by trying a simple operation
                    test_response = ollama.list()
                    self.report("Successfully connected to Ollama service", "debug")
                    
                    # Check if our model is available directly with a test prompt
                    try:
                        self.report(f"Testing model {self.model_name} availability...", "info")
                        test_gen = ollama.generate(
                            model=self.model_name, 
                            prompt="Hello",
                            options={"num_predict": 1}  # Minimal generation to test
                        )
                        self.report(f"Model {self.model_name} is available and working.", "info")
                        self.model_available = True
                    except Exception as model_err:
                        if "model not found" in str(model_err).lower():
                            self.report(f"ERROR: Model {self.model_name} not found. You must pull it first.", "error")
                            self.report(f"Run this command: ollama pull {self.model_name}", "error")
                            self.model_available = False
                        else:
                            self.report(f"Error testing model: {model_err}", "error")
                            self.model_available = False
                except Exception as e:
                    self.report(f"Error connecting to Ollama service: {e}", "error")
                    self.report("Make sure Ollama service is running with 'ollama serve'", "error")
                    self.model_available = False
            except Exception as e:
                self.report(f"Error with Ollama: {e}", "error")
                self.model_available = False
        else:
            self.model_available = False
    
    async def fetch_health_tip(self) -> str:
        """
        Fetch a random health tip from the health.gov API.
        
        Returns:
            str: A health tip
        """
        self.report("Fetching health tip from health.gov API...", "info")
        url = "https://health.gov/myhealthfinder/api/v3/topicsearch.json?lang=en"
        
        try:
            import requests
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if "Result" in data and "Resources" in data["Result"]:
                resources = data["Result"]["Resources"]["Resource"]
                
                if resources:
                    random_tip = random.choice(resources)
                    tip = random_tip.get("Title", "Stay hydrated and drink 8 glasses of water daily!")
                    self.report(f"Fetched health tip: {tip}", "info")
                    return tip
            
            default_tip = "Stay hydrated and drink 8 glasses of water daily!"
            self.report(f"No health tips found from API. Using default: {default_tip}", "warning")
            return default_tip
            
        except Exception as e:
            default_tip = "Stay hydrated and drink 8 glasses of water daily!"
            self.report(f"Error fetching health tips: {e}. Using default: {default_tip}", "error")
            return default_tip
    
    async def generate_script(self, health_tip: str) -> str:
        """
        Generate a script for the YouTube short using Ollama with Deepseek model.
        
        Args:
            health_tip: The health tip to create a script for
            
        Returns:
            str: The generated script
        """
        self.report(f"Generating script for health tip: {health_tip}", "info")
        
        # Check if Ollama is available
        if not getattr(self, 'model_available', False):
            mock_script = (
                "Narrator: Did you know that staying hydrated is key to your health?\n\n"
                f"Narrator: {health_tip}\n\n"
                "Narrator: This simple tip can boost your energy, improve your focus, and help your body function at its best.\n\n"
                "Narrator: Make this small change today for a healthier tomorrow!"
            )
            self.report("Ollama model not available. Using mock script.", "warning")
            return mock_script
        
        # Create prompt for script generation
        prompt = f"""
        Create a 40-45 second YouTube Shorts script about this health tip: "{health_tip}".
        
        Format the script as 6-8 separate, numbered points (1-8) that explain key aspects of this health topic.
        Each point should start with a number and title in bold (**Title**) followed by a brief explanation.
        
        For example:
        1. **Introduction**: Brief explanation here...
        2. **Symptoms**: Brief explanation here...
        
        Make the points concise and informative, suitable for creating separate frames in a YouTube Short.
        Focus on providing practical, useful information for viewers.
        """
        
        try:
            import ollama
            self.report("Sending request to Ollama...", "debug")
            
            # Use Ollama to generate the script
            response = ollama.generate(
                model=self.model_name,
                prompt=prompt,
                system="You are a professional health educator creating concise, informative YouTube Shorts scripts.",
                options={"temperature": 0.7}
            )
            
            # Extract the response text
            script = response.get('response', '').strip()
            
            # Print raw model output if debug is enabled
            if self.debug_llm_output:
                print("\n" + "=" * 80)
                print("DEEPSEEK RAW OUTPUT:")
                print("=" * 80)
                print(script)
                print("=" * 80 + "\n")
                self.report("Printed raw Deepseek output to console", "info")
            else:
                # Just log a shorter version to debug
                self.report(f"Raw model output (first 100 chars): {script[:100]}...", "debug")
            
            # Clean up the script
            # Remove <think> section if present
            if "<think>" in script and "</think>" in script:
                think_start = script.find("<think>")
                think_end = script.find("</think>") + len("</think>")
                script = script[:think_start] + script[think_end:]
                script = script.strip()
                self.report("Removed <think> section from Deepseek output", "debug")
            
            # Format the script for our video frames - convert numbered points into narrator format
            formatted_lines = []
            lines = script.split('\n')
            current_point = ""
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # Check if line starts with a number (1-8 followed by a period or colon)
                if re.match(r'^[1-8][.:]\s', line) or re.match(r'^[1-8]\.\s\*\*', line):
                    # If we have accumulated text for the previous point, add it
                    if current_point:
                        formatted_lines.append(f"Narrator: {current_point}")
                        self.report(f"Added point: {current_point[:30]}...", "debug")
                    
                    # Start a new point
                    current_point = line
                else:
                    # Continue the current point
                    if current_point:
                        current_point += " " + line
                    else:
                        current_point = line
            
            # Add the last point
            if current_point:
                formatted_lines.append(f"Narrator: {current_point}")
                self.report(f"Added final point: {current_point[:30]}...", "debug")
            
            # Join all formatted lines with newlines
            script = "\n\n".join(formatted_lines)
            
            self.report("Successfully generated script with Ollama.", "info")
            return script
        except Exception as e:
            self.report(f"Error generating script with Ollama: {e}", "error")
            self.report(f"Traceback: {traceback.format_exc()}", "debug")
            
            # Fallback script if API fails
            mock_script = (
                "Narrator: 1. **Introduction**: Understanding this health topic is crucial.\n\n"
                f"Narrator: 2. **What is {health_tip}**: This is an important aspect of your health.\n\n"
                "Narrator: 3. **Risk Factors**: Several factors can increase your risk.\n\n"
                "Narrator: 4. **Symptoms**: Watch for these important signs.\n\n"
                "Narrator: 5. **Prevention**: Take these steps to protect your health.\n\n"
                "Narrator: 6. **When to See a Doctor**: Don't ignore these warning signs."
            )
            self.report("Using fallback script due to API error.", "warning")
            return mock_script
    
    def extract_narration_lines(self, script_text: str) -> List[str]:
        """
        Extract clean narration lines from the script.
        
        Args:
            script_text: The raw script text
            
        Returns:
            List[str]: List of clean narration lines
        """
        self.report("Extracting narration lines from script...", "debug")
        narration_lines = []
        
        for line in script_text.split('\n'):
            if 'Narrator:' in line:
                # Extract the text after "Narrator:"
                narration_text = line.split('Narrator:', 1)[1].strip()
                
                # Clean the text (remove stage directions, quotes, etc)
                cleaned_text = self._clean_narration_text(narration_text)
                
                # Only add non-empty lines
                if cleaned_text:
                    narration_lines.append(cleaned_text)
        
        # If no lines with "Narrator:" were found, split by sentences
        if not narration_lines:
            # Split by sentence endings (., !, ?)
            sentences = re.split(r'(?<=[.!?])\s+', script_text)
            narration_lines = [self._clean_narration_text(s.strip()) for s in sentences if s.strip()]
            narration_lines = [s for s in narration_lines if s]  # Remove empty strings
        
        self.report(f"Extracted {len(narration_lines)} narration lines.", "info")
        return narration_lines
    
    def _clean_narration_text(self, text: str) -> str:
        """
        Clean narration text by removing stage directions, quotes, etc.
        
        Args:
            text: The text to clean
            
        Returns:
            str: Cleaned text
        """
        # Remove text in square brackets
        cleaned_text = re.sub(r'\[.*?\]', '', text)
        # Remove text in parentheses
        cleaned_text = re.sub(r'\(.*?\)', '', cleaned_text)
        # Remove quotes around text
        cleaned_text = re.sub(r'^"|"$', '', cleaned_text)
        # Remove excess whitespace
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
        return cleaned_text
    
    async def execute(self) -> bool:
        """
        Execute the content generation process.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # First, verify that model is available
            if not getattr(self, 'model_available', False) and self.ollama_available:
                self.report(f"ERROR: Required model '{self.model_name}' is not available.", "error")
                self.report(f"Please run: ollama pull {self.model_name}", "error")
                self.report("Pipeline cannot continue without the required model.", "error")
                return False
            
            # Step 1: Fetch health tip
            health_tip = await self.fetch_health_tip()
            self.workspace["health_tip"] = health_tip
            
            # Step 2: Generate script
            script = await self.generate_script(health_tip)
            self.workspace["script"] = script
            
            # Step 3: Extract narration lines
            narration_lines = self.extract_narration_lines(script)
            self.workspace["narration_lines"] = narration_lines
            
            # Success
            self.report("Content generation completed successfully.", "info")
            return True
            
        except Exception as e:
            self.report(f"Error in content generation: {e}", "error")
            self.report(f"Traceback: {traceback.format_exc()}", "debug")
            return False
