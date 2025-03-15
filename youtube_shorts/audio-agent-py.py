"""
Audio agent for speech synthesis and audio processing.
"""

import os
import sys
import math
import subprocess
import asyncio
from typing import List, Dict, Any, Optional

from agents.base_agent import Agent
from utils.common import run_process


class AudioAgent(Agent):
    """Agent responsible for audio processing: TTS, audio mixing, etc."""
    
    def setup(self):
        """Set up audio processing tools."""
        try:
            from gtts import gTTS
            self.gtts_available = True
        except ImportError:
            self.gtts_available = False
            self.report("gTTS package not installed. Running pip install gtts...", "warning")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "gtts"])
                from gtts import gTTS
                self.gtts_available = True
            except Exception as e:
                self.report(f"Failed to install gTTS package: {e}", "error")
        
        try:
            from pydub import AudioSegment
            self.pydub_available = True
        except ImportError:
            self.pydub_available = False
            self.report("pydub package not installed. Running pip install pydub...", "warning")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "pydub"])
                from pydub import AudioSegment
                self.pydub_available = True
            except Exception as e:
                self.report(f"Failed to install pydub package: {e}", "error")
        
        # Detect platform for audio format compatibility
        self.is_mac = 'darwin' in sys.platform
        if self.is_mac:
            self.report("macOS detected - adapting audio formats for compatibility", "info")
        
        # Create audio directory
        self.audio_dir = os.path.join(self.workspace["run_dir"], "audio")
        os.makedirs(self.audio_dir, exist_ok=True)
    
    async def text_to_speech(self, narration_lines: List[str]) -> List[Dict[str, Any]]:
        """
        Convert narration lines to speech with timing information.
        
        Args:
            narration_lines: List of text lines for narration
            
        Returns:
            List[Dict]: List of timing dicts with file, start_time, end_time, etc.
        """
        self.report("Converting narration lines to speech...", "info")
        
        if not self.gtts_available:
            self.report("gTTS not available, cannot generate speech", "error")
            return []
        
        from gtts import gTTS
        
        # List to store timing information
        timings = []
        total_duration = 0
        
        # Process each line individually to get accurate timing
        for i, line in enumerate(narration_lines):
            output_file = os.path.join(self.audio_dir, f"segment_{i}.mp3")
            
            try:
                # Generate speech for this line
                tts = gTTS(text=line, lang='en')
                tts.save(output_file)
                
                # Get duration using ffprobe
                duration = await self._get_audio_duration(output_file)
                
                timings.append({
                    'line': line,
                    'file': output_file,
                    'start_time': total_duration,
                    'duration': duration,
                    'end_time': total_duration + duration
                })
                
                total_duration += duration
                self.report(f"Generated audio for line {i+1}: {line[:30]}... ({duration:.2f}s)", "debug")
                
            except Exception as e:
                self.report(f"Error generating speech for line {i+1}: {e}", "error")
                return []
        
        # Check if total duration exceeds MAX_DURATION
        if total_duration > self.config["max_duration"]:
            self.report(f"WARNING: Audio duration ({total_duration:.2f}s) exceeds target of {self.config['max_duration']}s.", "warning")
            self.report("Audio will be slightly sped up to fit within the target duration.", "warning")
        
        self.report(f"Successfully generated {len(timings)} audio segments. Total duration: {total_duration:.2f}s", "info")
        return timings
    
    async def _get_audio_duration(self, audio_file: str) -> float:
        """
        Get the duration of an audio file using ffprobe.
        
        Args:
            audio_file: Path to the audio file
            
        Returns:
            float: Duration in seconds
        """
        cmd = [
            "ffprobe", 
            "-v", "error", 
            "-show_entries", "format=duration", 
            "-of", "default=noprint_wrappers=1:nokey=1", 
            audio_file
        ]
        
        try:
            result = await run_process(cmd)
            duration = float(result.strip())
            return duration
        except Exception as e:
            self.report(f"Error getting audio duration: {e}", "error")
            # Return an approximation based on file size
            try:
                return os.path.getsize(audio_file) / 15000  # Rough estimate
            except:
                return 3.0  # Default fallback
    
    async def combine_audio(self, timings: List[Dict[str, Any]], bg_music_file: Optional[str] = None) -> str:
        """
        Combine audio segments and add background music.
        
        Args:
            timings: List of timing dicts with audio file info
            bg_music_file: Path to background music file (optional)
            
        Returns:
            str: Path to combined audio file
        """
        if not timings:
            self.report("No audio timings provided for combining.", "error")
            return ""
        
        if not self.pydub_available:
            self.report("pydub not available, cannot combine audio", "error")
            return ""
        
        # Set output file path based on platform
        output_ext = '.m4a' if self.is_mac else '.mp3'
        output_file = os.path.join(self.workspace["run_dir"], "output", f"combined_audio{output_ext}")
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        self.report(f"Combining {len(timings)} audio segments...", "info")
        
        try:
            # Import AudioSegment
            from pydub import AudioSegment
            
            # Start with an empty audio segment
            combined = AudioSegment.silent(duration=0)
            
            # Add each segment
            for timing in timings:
                segment = AudioSegment.from_file(timing['file'])
                combined += segment
            
            # Check combined duration
            total_duration = len(combined) / 1000.0  # Convert milliseconds to seconds
            
            # Speed up audio if it's too long
            if total_duration > self.config["max_duration"]:
                speed_factor = self.config["max_duration"] / total_duration
                
                # Check if speed_factor is within FFmpeg's atempo filter range (0.5 to 100)
                if speed_factor < 0.5:
                    self.report(f"Speed factor {speed_factor:.2f} is below minimum allowed value (0.5)", "warning")
                    self.report("Applying multiple atempo filters to achieve the desired speed", "info")
                    
                    # For very slow speeds, we need to apply the filter multiple times
                    # Each application can go down to 0.5, so we calculate how many times to apply it
                    num_applications = math.ceil(math.log(speed_factor) / math.log(0.5))
                    per_application_factor = speed_factor ** (1 / num_applications)
                    
                    self.report(f"Applying atempo filter {num_applications} times with factor {per_application_factor:.4f}", "debug")
                    
                    # Create filter string with multiple atempo applications
                    filter_chain = []
                    for _ in range(num_applications):
                        filter_chain.append(f"atempo={per_application_factor}")
                    filter_str = ','.join(filter_chain)
                    
                    # Use ffmpeg for speedup with multiple atempo filters
                    temp_file = os.path.join(self.audio_dir, "temp_audio.wav")
                    combined.export(temp_file, format="wav")
                    
                    speedup_file = os.path.join(self.audio_dir, "speedup_audio.wav")
                    speedup_cmd = [
                        "ffmpeg",
                        "-y",
                        "-i", temp_file,
                        "-filter:a", filter_str,
                        speedup_file
                    ]
                    
                    await run_process(speedup_cmd)
                    
                    # Load the sped-up audio
                    combined = AudioSegment.from_file(speedup_file)
                else:
                    # Original code for speed factors within range
                    self.report(f"Speeding up audio by factor of {speed_factor:.2f} to fit within {self.config['max_duration']}s", "warning")
                    
                    # Use ffmpeg for speedup
                    temp_file = os.path.join(self.audio_dir, "temp_audio.wav")
                    combined.export(temp_file, format="wav")
                    
                    speedup_file = os.path.join(self.audio_dir, "speedup_audio.wav")
                    speedup_cmd = [
                        "ffmpeg",
                        "-y",
                        "-i", temp_file,
                        "-filter:a", f"atempo={speed_factor}",
                        speedup_file
                    ]
                    
                    await run_process(speedup_cmd)
                    
                    # Load the sped-up audio
                    combined = AudioSegment.from_file(speedup_file)
                
                # Update total duration
                total_duration = len(combined) / 1000.0
                self.report(f"Audio speed adjustment completed. New duration: {total_duration:.2f}s", "info")
            
            # Export voice only audio directly
            voice_only_file = os.path.join(self.audio_dir, f"voice_only.wav")
            combined.export(voice_only_file, format="wav")
            
            # If background music is provided, mix it
            if bg_music_file and os.path.exists(bg_music_file):
                self.report(f"Mixing voice with background music: {bg_music_file}", "info")
                try:
                    # Load voice audio
                    voice_audio = AudioSegment.from_file(voice_only_file)
                    
                    # Try to load background music
                    try:
                        bg_music = AudioSegment.from_file(bg_music_file)
                    except:
                        # If loading fails, convert with ffmpeg first
                        bg_wav_file = os.path.join(self.audio_dir, "bg_music.wav")
                        await run_process(["ffmpeg", "-y", "-i", bg_music_file, bg_wav_file])
                        bg_music = AudioSegment.from_file(bg_wav_file)
                    
                    # Make sure background music is long enough
                    if len(bg_music) < len(voice_audio):
                        repeats = math.ceil(len(voice_audio) / len(bg_music))
                        bg_music = bg_music * repeats
                    
                    # Trim to match voice audio length
                    bg_music = bg_music[:len(voice_audio)]
                    
                    # Lower the volume of background music
                    bg_music = bg_music - 14  # Reduce by ~14dB
                    
                    # Mix audio
                    mixed_audio = voice_audio.overlay(bg_music)
                    
                    # Export format depends on platform
                    export_format = "ipod" if self.is_mac else "mp3"
                    mixed_audio.export(output_file, format=export_format)
                    
                    self.report(f"Successfully created mixed audio: {output_file}", "info")
                except Exception as e:
                    self.report(f"Error mixing background music: {e}", "error")
                    self.report("Falling back to voice-only audio", "warning")
                    
                    # Export voice only
                    export_format = "ipod" if self.is_mac else "mp3"
                    combined.export(output_file, format=export_format)
            else:
                # Just export voice audio directly
                self.report("No background music provided. Using voice-only audio.", "info")
                export_format = "ipod" if self.is_mac else "mp3"
                combined.export(output_file, format=export_format)
            
            # Verify output file exists and has content
            if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                final_duration = await self._get_audio_duration(output_file)
                self.report(f"Final audio file duration: {final_duration:.2f}s", "info")
                return output_file
            else:
                self.report("Error: Output audio file is empty or missing.", "error")
                return ""
                
        except Exception as e:
            self.report(f"Error combining audio segments: {e}", "error")
            return ""
    
    async def execute(self) -> bool:
        """
        Execute the audio processing workflow.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check for required inputs
            if "narration_lines" not in self.workspace:
                self.report("Error: narration_lines not found in workspace", "error")
                return False
            
            # Step 1: Convert text to speech with timing
            timings = await self.text_to_speech(self.workspace["narration_lines"])
            if not timings:
                self.report("Failed to generate speech audio", "error")
                return False
            
            self.workspace["audio_timings"] = timings
            
            # Step 2: Combine audio segments
            bg_music_file = self.config["default_music"]
            # Check if the music file exists in the current directory
            if bg_music_file and not os.path.isabs(bg_music_file):
                current_dir_music = os.path.join(os.getcwd(), bg_music_file)
                if os.path.exists(current_dir_music):
                    bg_music_file = current_dir_music
                    self.report(f"Using background music from current directory: {bg_music_file}", "info")
            
            combined_file = await self.combine_audio(timings, bg_music_file)
            if not combined_file:
                self.report("Failed to combine audio segments", "error")
                return False
            
            self.workspace["combined_audio_file"] = combined_file
            
            # Success
            self.report("Audio processing completed successfully.", "info")
            return True
            
        except Exception as e:
            self.report(f"Error in audio processing: {e}", "error")
            return False
