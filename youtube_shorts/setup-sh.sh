#!/bin/bash
# Setup script for YouTube Shorts Automation Framework

# Create required directories
mkdir -p youtube_shorts/agents
mkdir -p youtube_shorts/utils

# Copy all the Python files to their respective locations
# Main directory files
cp main.py youtube_shorts/
cp framework.py youtube_shorts/
cp config.py youtube_shorts/
cp coordinator.py youtube_shorts/

# Agent files
cp agents/base_agent.py youtube_shorts/agents/
cp agents/content_agent.py youtube_shorts/agents/
cp agents/audio_agent.py youtube_shorts/agents/
cp agents/visual_agent.py youtube_shorts/agents/
cp agents/video_agent.py youtube_shorts/agents/
cp agents/upload_agent.py youtube_shorts/agents/
cp agents/__init__.py youtube_shorts/agents/

# Utility files
cp utils/visual_helpers.py youtube_shorts/utils/
cp utils/common.py youtube_shorts/utils/
cp utils/__init__.py youtube_shorts/utils/

# Copy README
cp README.md youtube_shorts/

# Create requirements.txt
cat > youtube_shorts/requirements.txt << 'EOL'
ollama
gtts
pydub
pillow
google-auth
google-auth-oauthlib
google-api-python-client
pyyaml
EOL

# Make main.py executable
chmod +x youtube_shorts/main.py

echo "Setup complete! Project structure created in youtube_shorts/"
echo "You can now run: cd youtube_shorts && python main.py"
