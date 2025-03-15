"""
Upload agent for YouTube integration in YouTube Shorts Automation Framework.
"""

import os
import sys
import pickle
import subprocess
from typing import List, Dict, Any, Optional

from agents.base_agent import Agent


class UploadAgent(Agent):
    """Agent responsible for YouTube upload and authentication."""
    
    def setup(self):
        """Set up YouTube API client."""
        # Set to disable OAuthlib's HTTPS verification when running locally
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
        
        # Path to token storage
        self.token_path = self.config.get("youtube_token_path", os.path.join(os.path.expanduser("~"), ".youtube_tokens", "token.pickle"))
        
        # Create token directory if it doesn't exist
        token_dir = os.path.dirname(self.token_path)
        if not os.path.exists(token_dir):
            os.makedirs(token_dir, exist_ok=True)
            
        # Check if required packages are installed
        try:
            import google.oauth2.credentials
            import google_auth_oauthlib.flow
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaFileUpload
            self.google_api_available = True
        except ImportError:
            self.google_api_available = False
            self.report("Google API client packages not installed. Running pip install...", "warning")
            try:
                packages = [
                    "google-auth",
                    "google-auth-oauthlib",
                    "google-api-python-client"
                ]
                subprocess.check_call([sys.executable, "-m", "pip", "install"] + packages)
                
                import google.oauth2.credentials
                import google_auth_oauthlib.flow
                from google.auth.transport.requests import Request
                from googleapiclient.discovery import build
                from googleapiclient.http import MediaFileUpload
                self.google_api_available = True
            except Exception as e:
                self.report(f"Failed to install Google API packages: {e}", "error")
    
    def _get_saved_credentials(self) -> Optional[object]:
        """
        Get saved credentials if they exist.
        
        Returns:
            google.oauth2.credentials.Credentials or None
        """
        if not self.google_api_available:
            return None
            
        if os.path.exists(self.token_path):
            with open(self.token_path, 'rb') as token:
                try:
                    credentials = pickle.load(token)
                    self.report(f"Loaded saved credentials from {self.token_path}", "debug")
                    return credentials
                except Exception as e:
                    self.report(f"Error loading saved credentials: {e}", "error")
        return None
    
    def _save_credentials(self, credentials) -> bool:
        """
        Save credentials for future use.
        
        Args:
            credentials: Google OAuth credentials
            
        Returns:
            bool: True if saved successfully, False otherwise
        """
        if not self.google_api_available:
            return False
            
        try:
            # Ensure the directory exists
            token_dir = os.path.dirname(self.token_path)
            if not os.path.exists(token_dir):
                os.makedirs(token_dir)
            
            with open(self.token_path, 'wb') as token:
                pickle.dump(credentials, token)
            
            try:
                os.chmod(self.token_path, 0o600)  # Secure permissions
            except:
                pass  # May fail on Windows, that's OK
                
            self.report(f"Credentials saved to {self.token_path}", "debug")
            return True
        except Exception as e:
            self.report(f"Error saving credentials: {e}", "error")
            return False
    
    async def setup_youtube_oauth(self, save_creds: bool = True) -> Optional[object]:
        """
        Set up OAuth 2.0 credentials for YouTube API.
        
        Args:
            save_creds: Whether to save credentials for future use
            
        Returns:
            google.oauth2.credentials.Credentials or None
        """
        if not self.google_api_available:
            self.report("Google API client not available, cannot authenticate", "error")
            return None
            
        from google.auth.transport.requests import Request
        import google_auth_oauthlib.flow
        
        # First, check for saved credentials
        credentials = self._get_saved_credentials()
        
        # If we have credentials that are valid, use them
        if credentials and credentials.valid:
            self.report("Using existing valid credentials", "info")
            return credentials
        
        # If we have credentials with a refresh token, try to refresh them
        if credentials and credentials.refresh_token:
            try:
                self.report("Refreshing expired credentials", "info")
                credentials.refresh(Request())
                if save_creds:
                    self._save_credentials(credentials)
                return credentials
            except Exception as e:
                self.report(f"Error refreshing credentials: {e}", "error")
                # If refresh fails, continue with authorization flow
        
        # If we get here, we need to get new credentials
        self.report("No valid credentials found. Starting authorization flow.", "info")
        
        # This OAuth 2.0 access scope allows for full read/write access to the
        # authenticated user's account on YouTube.
        scopes = ["https://www.googleapis.com/auth/youtube.upload"]
        
        try:
            # Get client secrets
            client_secrets_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "client_secrets.json")
            if not os.path.exists(client_secrets_file):
                self.report(f"Client secrets file not found: {client_secrets_file}", "error")
                self.report("Please download client_secrets.json from Google Developer Console", "error")
                self.report("and place it in the root directory of this project.", "error")
                return None
                
            # Create the flow using the client secrets file
            flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                client_secrets_file, scopes
            )
            
            # Run the OAuth flow to get credentials
            credentials = flow.run_local_server(port=0)
            
            # Save the credentials for future use
            if save_creds:
                self._save_credentials(credentials)
                
            self.report("Successfully obtained new credentials", "info")
            return credentials
                
        except Exception as e:
            self.report(f"Error in authorization flow: {e}", "error")
            return None
    
    async def upload_video(self, video_path: str, title: str, description: str, tags: List[str] = None) -> Optional[str]:
        """
        Upload a video to YouTube using existing credentials.
        
        Args:
            video_path: Path to the video file
            title: Video title
            description: Video description
            tags: List of video tags
            
        Returns:
            str: YouTube video ID if successful, None otherwise
        """
        if not self.google_api_available:
            self.report("Google API client not available, cannot upload", "error")
            return None
            
        # Check if video file exists
        if not os.path.exists(video_path):
            self.report(f"Video file not found: {video_path}", "error")
            return None
        
        # Get credentials
        credentials = await self.setup_youtube_oauth()
        if not credentials:
            self.report("No valid credentials available for automatic upload", "error")
            return None
        
        try:
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaFileUpload
            
            # Create the YouTube API client
            youtube = build("youtube", "v3", credentials=credentials)
            
            # Construct video metadata
            body = {
                "snippet": {
                    "title": title,
                    "description": description,
                    "tags": tags or ["health", "tips", "wellness", "shorts"],
                    "categoryId": "22"  # People & Blogs category
                },
                "status": {
                    "privacyStatus": "public",
                    "selfDeclaredMadeForKids": False
                }
            }
            
            # Create the media upload object
            media = MediaFileUpload(
                video_path, 
                mimetype="video/mp4", 
                resumable=True,
                chunksize=1024*1024
            )
            
            # Execute the upload request
            self.report(f"Starting upload to YouTube...", "info")
            request = youtube.videos().insert(
                part=",".join(body.keys()),
                body=body,
                media_body=media
            )
            
            # Upload the video with progress reporting
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    self.report(f"Uploaded {int(status.progress() * 100)}%", "info")
            
            video_id = response['id']
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            
            self.report(f"Video upload complete! Video ID: {video_id}", "info")
            self.report(f"Video URL: {video_url}", "info")
            
            return video_id
            
        except Exception as e:
            self.report(f"Error during upload: {e}", "error")
            return None
    
    async def execute(self) -> bool:
        """
        Execute the upload workflow if auto_upload is enabled.
        
        Returns:
            bool: True if successful or skipped, False on failure
        """
        # Check if auto_upload is enabled
        if not self.config.get("auto_upload", False):
            self.report("Auto-upload disabled. Skipping upload.", "info")
            return True
        
        # Check if we have necessary data
        if "output_video" not in self.workspace or "health_tip" not in self.workspace:
            self.report("Missing required workspace data for upload", "error")
            return False
        
        try:
            # Set up title and description
            title = f"Health Tip: {self.workspace['health_tip']}"
            description = (
                f"A quick health tip about {self.workspace['health_tip']}.\n\n"
                "Generated using AI for educational purposes."
            )
            tags = ["health", "tips", "wellness", "shorts", "health tips", "healthy living"]
            
            # Upload the video
            video_id = await self.upload_video(
                self.workspace["output_video"],
                title,
                description,
                tags
            )
            
            if video_id:
                self.workspace["youtube_video_id"] = video_id
                self.workspace["youtube_video_url"] = f"https://www.youtube.com/watch?v={video_id}"
                self.report("Upload completed successfully.", "info")
                return True
            else:
                self.report("Upload failed.", "error")
                return False
                
        except Exception as e:
            self.report(f"Error in upload process: {e}", "error")
            return False
