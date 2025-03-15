"""
Visual agent for generating frames in YouTube Shorts Automation Framework.
"""

import os
import sys
import time
from typing import List, Dict, Any, Optional

from agents.base_agent import Agent
from utils.visual_helpers import generate_frame_chunk


class VisualAgent(Agent):
    """Agent responsible for visual processing: frames, images, etc."""
    
    def setup(self):
        """Set up visual processing tools."""
        try:
            from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
            self.pil_available = True
        except ImportError:
            self.pil_available = False
            self.report("PIL package not installed. Running pip install pillow...", "warning")
            try:
                import subprocess
                subprocess.check_call([sys.executable, "-m", "pip", "install", "pillow"])
                from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
                self.pil_available = True
            except Exception as e:
                self.report(f"Failed to install PIL package: {e}", "error")
        
        # Create frames directory
        self.frames_dir = os.path.join(self.workspace["run_dir"], "frames")
        os.makedirs(self.frames_dir, exist_ok=True)
        
        # Set up rendering parameters
        self.width = self.config.get("video_width", 1080)
        self.height = self.config.get("video_height", 1920)
        self.fps = self.config.get("fps", 30)
        
        # Number of CPU cores to use for parallel processing
        if self.config.get("parallel_processes"):
            self.num_processes = self.config["parallel_processes"]
        else:
            self.num_processes = max(1, os.cpu_count() - 1) 
    
    async def prepare_background(self, background_image: Optional[str] = None) -> 'Image.Image':
        """
        Prepare the background image for the video.
        
        Args:
            background_image: Path to background image file (optional)
            
        Returns:
            PIL.Image: Processed background image
        """
        if not self.pil_available:
            self.report("PIL not available, cannot process background image", "error")
            return None
            
        from PIL import Image, ImageFilter, ImageEnhance
        
        # If image path is relative, check current directory
        if background_image and not os.path.isabs(background_image):
            current_dir_image = os.path.join(os.getcwd(), background_image)
            if os.path.exists(current_dir_image):
                background_image = current_dir_image
                self.report(f"Using background image from current directory: {background_image}", "info")
        
        # Try to load specified background image
        if background_image and os.path.exists(background_image):
            try:
                self.report(f"Loading background image: {background_image}", "info")
                bg_img = Image.open(background_image)
                
                # Resize to target dimensions
                bg_img = bg_img.resize((self.width, self.height), Image.LANCZOS)
                
                # Apply slight blur to make text more readable
                bg_img = bg_img.filter(ImageFilter.GaussianBlur(radius=1.5))
                
                # Darken the image slightly to make text stand out more
                enhancer = ImageEnhance.Brightness(bg_img)
                bg_img = enhancer.enhance(0.8)
                
                return bg_img
            
            except Exception as e:
                self.report(f"Error loading background image: {e}", "error")
                # Fall through to default background
        
        # Create default gradient background
        self.report("Creating default gradient background", "info")
        return self._create_gradient_background()
    
    def _create_gradient_background(self) -> 'Image.Image':
        """
        Create a nice gradient background if no image is available.
        
        Returns:
            PIL.Image: Gradient background image
        """
        from PIL import Image, ImageDraw
        
        bg_img = Image.new('RGB', (self.width, self.height), (0, 0, 0))
        draw = ImageDraw.Draw(bg_img)
        
        for y in range(self.height):
            # Create a blue to purple gradient
            r = int(25 + (y / self.height * 40))
            g = int(25 + (y / self.height * 30))
            b = int(50 + (y / self.height * 150))
            draw.line([(0, y), (self.width, y)], fill=(r, g, b))
        
        return bg_img
    
    def _get_available_font_paths(self):
        """Get a list of available font paths based on platform."""
        font_paths = []
        
        # macOS fonts
        if 'darwin' in sys.platform:
            font_paths.extend([
                "/System/Library/Fonts/Supplemental/Impact.ttf",
                "/System/Library/Fonts/Supplemental/Verdana Bold.ttf",
                "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                "/System/Library/Fonts/Helvetica.ttc",
                "/Library/Fonts/Arial Bold.ttf"
            ])
        
        # Linux fonts
        if 'linux' in sys.platform:
            font_paths.extend([
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
                "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/TTF/Arial.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
            ])
        
        # Windows fonts
        if 'win32' in sys.platform:
            font_paths.extend([
                "C:\\Windows\\Fonts\\Arial.ttf",
                "C:\\Windows\\Fonts\\ArialBD.ttf",
                "C:\\Windows\\Fonts\\Impact.ttf",
                "C:\\Windows\\Fonts\\Verdana.ttf",
                "C:\\Windows\\Fonts\\VerdanaBD.ttf"
            ])
        
        # Return only paths that exist
        return [path for path in font_paths if os.path.exists(path)]
    
    async def generate_frames(self, bg_image: Optional[str] = None) -> int:
        """
        Generate all video frames using parallel processing for faster generation.
        
        Args:
            bg_image: Path to background image file (optional)
            
        Returns:
            int: Number of frames generated
        """
        if not self.pil_available:
            self.report("PIL not available, cannot generate frames", "error")
            return 0
            
        if "audio_timings" not in self.workspace:
            self.report("Error: audio_timings not found in workspace", "error")
            return 0
        
        self.is_mac = 'darwin' in sys.platform
        timings = self.workspace["audio_timings"]
        
        if not timings:
            self.report("No audio timings provided for frame generation.", "error")
            return 0
        
        # Determine video duration
        total_duration = timings[-1]['end_time']
        total_frames = int(total_duration * self.fps) + 10  # Add 10 frames buffer
        
        # Get number of processes to use
        num_processes = self.num_processes
        self.report(f"Generating {total_frames} frames for {total_duration:.2f} seconds at {self.fps} fps using {num_processes} processes", "info")
        
        try:
            # Prepare background image
            bg_img = await self.prepare_background(bg_image or self.config["default_background"])
            
            # Save background image to a temporary file for multiprocessing
            bg_temp_path = os.path.join(self.workspace["run_dir"], "temp_bg.jpg")
            bg_img.save(bg_temp_path, quality=95)
            
            # Create frames directory if it doesn't exist
            os.makedirs(self.frames_dir, exist_ok=True)
            
            # Import necessary modules for multiprocessing
            import multiprocessing
            from functools import partial
            
            # Record start time
            start_time = time.time()
            
            # Split frames into chunks for parallel processing
            chunk_size = max(1, total_frames // num_processes)
            chunks = []
            
            # Get a font path
            font_paths = self._get_available_font_paths()
            font_path = font_paths[0] if font_paths else None
            
            for i in range(0, total_frames, chunk_size):
                end = min(i + chunk_size, total_frames)
                # Include all necessary data in the chunk
                chunks.append((
                    i, end, font_path, self.width, self.height, 
                    self.fps, self.frames_dir, bg_temp_path, timings
                ))
            
            self.report(f"Splitting work into {len(chunks)} chunks", "info")
            
            # Create process pool
            # Use 'spawn' method on macOS to avoid issues with forking
            ctx = multiprocessing.get_context('spawn')
            with ctx.Pool(processes=num_processes) as pool:
                # Process chunks in parallel using the external helper function
                results = []
                for i, result in enumerate(pool.imap_unordered(generate_frame_chunk, chunks)):
                    results.append(result)
                    self.report(f"Completed chunk {i+1}/{len(chunks)} - Generated {result} frames", "info")
            
            # Clean up temporary files
            if os.path.exists(bg_temp_path):
                os.remove(bg_temp_path)
            
            # Verify frames were created
            frame_count = len([f for f in os.listdir(self.frames_dir) if f.startswith('frame_') and f.endswith('.jpg')])
            
            # Report final statistics
            end_time = time.time()
            elapsed = end_time - start_time
            frames_per_second = total_frames / max(elapsed, 0.1)
            self.report(f"Generated {frame_count} frames in {elapsed:.2f} seconds ({frames_per_second:.2f} frames/second)", "info")
            
            return total_frames
            
        except Exception as e:
            self.report(f"Error generating frames: {e}", "error")
            import traceback
            self.report(f"Traceback: {traceback.format_exc()}", "debug")
            return 0
    
    async def execute(self) -> bool:
        """
        Execute the visual processing workflow.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Generate frames
            num_frames = await self.generate_frames(self.config["default_background"])
            
            if num_frames == 0:
                self.report("Failed to generate frames", "error")
                return False
            
            self.workspace["num_frames"] = num_frames
            self.workspace["frames_dir"] = self.frames_dir
            self.workspace["frame_rate"] = self.fps
            
            # Success
            self.report("Visual processing completed successfully.", "info")
            return True
            
        except Exception as e:
            self.report(f"Error in visual processing: {e}", "error")
            return False
