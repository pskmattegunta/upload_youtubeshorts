"""
Video agent for combining frames and audio in YouTube Shorts Automation Framework.
"""

import os
import sys
import shutil
import asyncio
from typing import List, Dict, Any, Optional

from agents.base_agent import Agent
from utils.common import run_process


class VideoAgent(Agent):
    """Agent responsible for video encoding: combining frames and audio."""
    
    def setup(self):
        """Set up video processing directories."""
        # Create output directory
        self.output_dir = os.path.join(self.workspace["run_dir"], "output")
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Set output video path
        self.output_video = os.path.join(self.output_dir, "health_tip_short.mp4")
        
        # Final copy that will be created in current directory
        self.final_video = os.path.join(os.getcwd(), "latest_health_tip.mp4")
    
    async def _get_video_duration(self, video_file: str) -> float:
        """
        Get the duration of a video file.
        
        Args:
            video_file: Path to the video file
            
        Returns:
            float: Duration in seconds
        """
        cmd = [
            "ffprobe", 
            "-v", "error", 
            "-show_entries", "format=duration", 
            "-of", "default=noprint_wrappers=1:nokey=1", 
            video_file
        ]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                self.report(f"Error getting video duration: {stderr.decode()}", "error")
                return 0
            
            duration = float(stdout.decode().strip())
            return duration
        except Exception as e:
            self.report(f"Error getting video duration: {e}", "error")
            return 0
    
    async def _get_audio_duration(self, audio_file):
        """Get audio duration using ffprobe."""
        cmd = [
            "ffprobe", 
            "-v", "error", 
            "-show_entries", "format=duration", 
            "-of", "default=noprint_wrappers=1:nokey=1", 
            audio_file
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            return float(stdout.decode().strip())
        else:
            self.report(f"Error getting audio duration: {stderr.decode()}", "error")
            return 30.0  # Default fallback duration
    
    async def create_video(self) -> bool:
        """
        Create a video from frames and audio using FFmpeg with GPU acceleration when available.
        
        Returns:
            bool: True if successful, False otherwise
        """
        if ("frames_dir" not in self.workspace or
            "combined_audio_file" not in self.workspace or
            "frame_rate" not in self.workspace):
            self.report("Error: missing required workspace variables", "error")
            return False
        
        frames_dir = self.workspace["frames_dir"]
        audio_file = self.workspace["combined_audio_file"]
        fps = self.workspace["frame_rate"]
        
        # Ensure audio file exists
        if not os.path.exists(audio_file):
            self.report(f"Error: Audio file {audio_file} not found", "error")
            return False
        
        # Verify frames exist
        frame_files = [f for f in os.listdir(frames_dir) if f.startswith('frame_') and f.endswith('.jpg')]
        if not frame_files:
            self.report(f"Error: No frame files found in {frames_dir}", "error")
            return False
        
        # Sort frames to ensure proper order
        frame_files.sort()
        self.report(f"Found {len(frame_files)} frame files. First frame: {frame_files[0]}, Last frame: {frame_files[-1]}", "info")
        
        self.report(f"Creating video with frames from {frames_dir} and audio from {audio_file}", "info")
        
        try:
            # Get audio duration
            audio_duration_cmd = [
                "ffprobe", 
                "-v", "error", 
                "-show_entries", "format=duration", 
                "-of", "default=noprint_wrappers=1:nokey=1", 
                audio_file
            ]
            
            process = await asyncio.create_subprocess_exec(
                *audio_duration_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                self.report(f"Error getting audio duration: {stderr.decode()}", "error")
                audio_duration = 0
            else:
                audio_duration = float(stdout.decode().strip())
            
            self.report(f"Audio duration: {audio_duration} seconds", "info")
            
            # Check if GPU acceleration is available on macOS
            is_mac = 'darwin' in sys.platform
            use_gpu = is_mac and self.config.get("use_gpu", True)
            
            if use_gpu:
                self.report("Attempting to use GPU acceleration with VideoToolbox", "info")
                
                # Test if VideoToolbox is available
                videotoolbox_test = [
                    "ffmpeg",
                    "-hide_banner",
                    "-hwaccel", "help"
                ]
                
                process = await asyncio.create_subprocess_exec(
                    *videotoolbox_test,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                output = stdout.decode() + stderr.decode()
                
                if "videotoolbox" in output.lower():
                    self.report("VideoToolbox hardware acceleration is available", "info")
                    use_gpu = True
                else:
                    self.report("VideoToolbox hardware acceleration not found, falling back to CPU", "warning")
                    use_gpu = False
            
            # Prepare FFmpeg command with potential GPU acceleration
            cmd = [
                "ffmpeg",
                "-y"  # Overwrite output file if it exists
            ]
            
            # Add GPU acceleration for macOS if available
            if use_gpu:
                cmd.extend([
                    "-hwaccel", "videotoolbox",
                    "-hwaccel_output_format", "videotoolbox_vld"
                ])
            
            # Add input frames and settings
            cmd.extend([
                "-framerate", str(fps),    # Frame rate
                "-i", f"{frames_dir}/frame_%04d.jpg",  # Input frames pattern
                "-i", audio_file           # Input audio
            ])
            
            # Add video codec settings with GPU acceleration if available
            if use_gpu:
                cmd.extend([
                    "-c:v", "h264_videotoolbox",  # Use VideoToolbox H.264 encoder
                    "-b:v", "5M",                 # Video bitrate
                    "-allow_sw", "1"              # Allow software fallback
                ])
            else:
                cmd.extend([
                    "-c:v", "libx264",     # Video codec
                    "-profile:v", "main",  # Video profile
                    "-preset", "medium",   # Balance between speed and quality
                    "-crf", "23"           # Reasonable quality (lower is better)
                ])
            
            # Add common settings
            cmd.extend([
                "-pix_fmt", "yuv420p",     # Pixel format for compatibility
                "-c:a", "aac",             # Audio codec
                "-b:a", "192k",            # Audio bitrate
                "-shortest",               # End when shortest input ends (likely audio)
                self.output_video
            ])
            
            # Execute the command
            self.report(f"Running FFmpeg command to generate video{' with GPU acceleration' if use_gpu else ''}...", "info")
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            stderr_text = stderr.decode() if stderr else ""
            
            if process.returncode != 0:
                self.report(f"Error creating video with standard pattern: {stderr_text}", "error")
                
                # If GPU acceleration failed, try again without it
                if use_gpu:
                    self.report("GPU acceleration failed, trying again without GPU...", "warning")
                    return await self._create_video_fallback(frames_dir, audio_file, fps, frame_files)
                else:
                    # Try with a direct file list approach instead
                    return await self._create_video_fallback(frames_dir, audio_file, fps, frame_files)
            
            # Verify the file was created
            if not os.path.exists(self.output_video):
                self.report(f"Error: Output video file {self.output_video} was not created", "error")
                return await self._create_video_fallback(frames_dir, audio_file, fps, frame_files)
            
            # Verify video duration
            video_duration = await self._get_video_duration(self.output_video)
            self.report(f"Video created successfully: {self.output_video} (Duration: {video_duration:.2f}s)", "info")
            
            # Ensure it's under 50 seconds for a YouTube Short
            if video_duration > 50:
                self.report(f"WARNING: Video duration ({video_duration:.2f}s) exceeds 50 seconds for a YouTube Short!", "warning")
            else:
                self.report(f"Video duration is under 50 seconds as required for a YouTube Short: {video_duration:.2f}s", "info")
            
            # Create a copy in the current directory for easier access
            shutil.copy(self.output_video, self.final_video)
            self.report(f"Copied video to current directory: {self.final_video}", "info")
            
            # Update workspace
            self.workspace["output_video"] = self.output_video
            self.workspace["final_video"] = self.final_video
            self.workspace["video_duration"] = video_duration
            
            return True
            
        except Exception as e:
            self.report(f"Error creating video: {e}", "error")
            import traceback
            self.report(f"Traceback: {traceback.format_exc()}", "debug")
            return False
    
    async def _create_video_fallback(self, frames_dir, audio_file, fps, frame_files):
        """Fallback method for video creation without GPU acceleration."""
        self.report("Trying with a direct file list approach...", "warning")
        
        # Create a temporary file list for ffmpeg
        file_list_path = os.path.join(self.output_dir, "frames.txt")
        with open(file_list_path, 'w') as file_list:
            for frame_file in frame_files:
                file_list.write(f"file '{os.path.join(frames_dir, frame_file)}'\n")
        
        # Use the file list as input
        concat_cmd = [
            "ffmpeg",
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", file_list_path,
            "-i", audio_file,
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-crf", "23",
            "-preset", "medium",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            self.output_video
        ]
        
        process = await asyncio.create_subprocess_exec(
            *concat_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        stderr_text = stderr.decode() if stderr else ""
        
        if process.returncode != 0:
            self.report(f"Error with concat approach: {stderr_text}", "error")
            
            # One more fallback approach - use the first frame directly
            self.report("Trying one more fallback approach...", "warning")
            first_frame = os.path.join(frames_dir, frame_files[0])
            
            fallback_cmd = [
                "ffmpeg",
                "-y",
                "-loop", "1",  # Loop the image
                "-i", first_frame,  # First frame as static image
                "-i", audio_file,
                "-c:v", "libx264",
                "-tune", "stillimage",
                "-c:a", "aac",
                "-b:a", "192k",
                "-pix_fmt", "yuv420p",
                "-shortest",
                "-t", str(await self._get_audio_duration(audio_file)),  # Use audio duration
                self.output_video
            ]
            
            process = await asyncio.create_subprocess_exec(
                *fallback_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                self.report(f"All video creation attempts failed: {stderr.decode()}", "error")
                return False
        
        # If we got here, one of the fallbacks worked
        # Verify the file was created
        if not os.path.exists(self.output_video):
            self.report(f"Error: Output video file {self.output_video} was not created", "error")
            return False
        
        # Verify video duration
        video_duration = await self._get_video_duration(self.output_video)
        self.report(f"Video created successfully using fallback method: {self.output_video} (Duration: {video_duration:.2f}s)", "info")
        
        # Create a copy in the current directory for easier access
        shutil.copy(self.output_video, self.final_video)
        self.report(f"Copied video to current directory: {self.final_video}", "info")
        
        # Update workspace
        self.workspace["output_video"] = self.output_video
        self.workspace["final_video"] = self.final_video
        self.workspace["video_duration"] = video_duration
        
        return True
    
    async def execute(self) -> bool:
        """
        Execute the video creation workflow.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create video from frames and audio
            success = await self.create_video()
            
            if not success:
                self.report("Failed to create video", "error")
                return False
            
            # Success
            self.report("Video creation completed successfully.", "info")
            return True
            
        except Exception as e:
            self.report(f"Error in video creation: {e}", "error")
            return False
