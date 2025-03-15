# YouTube Shorts Automation Framework

A modular, agent-based framework for automating the creation and upload of YouTube Shorts.
Each agent specializes in a specific part of the workflow, with a coordinator orchestrating
the entire process.

## Features

- Content generation using Ollama with Deepseek
- Text-to-speech conversion and background music mixing
- Automatic frame generation with smooth animations
- GPU-accelerated video encoding (on macOS)
- YouTube upload with OAuth authentication
- Multi-processing optimization for faster frame generation
- Automatic dependency installation

## Prerequisites

- Python 3.8+
- FFmpeg (for audio and video processing)
- Ollama server running locally (for content generation)

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/youtube-shorts-automation.git
   cd youtube-shorts-automation
   ```

2. Create a virtual environment (optional but recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. If you want to use Ollama with Deepseek, make sure to pull the model:
   ```bash
   ollama pull deepseek-r1:latest
   ```

## Usage

### Basic Usage

```bash
python main.py
```

This will:
1. Generate a health tip and script
2. Convert text to speech
3. Create animated frames
4. Combine frames and audio into a video
5. Save the final video to your current directory

### Options

```
  -h, --help            Show this help message and exit
  -c CONFIG, --config CONFIG
                        Path to configuration file (JSON or YAML)
  -b BACKGROUND, --background BACKGROUND
                        Path to background image
  -m MUSIC, --music MUSIC
                        Path to background music
  -u, --upload          Enable auto-upload to YouTube
  -v, --verbose         Enable verbose logging
  --setup               Run first-time setup for YouTube API
  --model MODEL         Specify LLM model to use (e.g. deepseek-r1:latest)
  --debug-llm           Print raw LLM output for debugging
```

### Examples

With custom background and music:
```bash
python main.py -b my_background.jpg -m my_music.mp3
```

Upload to YouTube:
```bash
python main.py -u
```

First-time YouTube setup:
```bash
python main.py --setup
```

Use a different Ollama model:
```bash
python main.py --model llama3:8b
```

## Configuration

You can create a YAML or JSON configuration file with the following options:

```yaml
# config.yaml
llm_model: "deepseek-r1:latest"
max_duration: 45
video_width: 1080
video_height: 1920
fps: 30
parallel_processes: 6
default_background: "custom_background.jpg"
default_music: "custom_music.mp3"
auto_upload: false
use_gpu: true
quality: "medium"
logging_level: "INFO"
debug_llm_output: false
```

Then use it with:
```bash
python main.py -c config.yaml
```

## Project Structure

```
youtube_shorts/
├── main.py                  # Entry point
├── framework.py             # Main framework class
├── config.py                # Configuration and constants
├── coordinator.py           # Coordinator agent
├── agents/
│   ├── __init__.py
│   ├── base_agent.py        # Base Agent class
│   ├── content_agent.py     # Content generation
│   ├── audio_agent.py       # Audio processing
│   ├── visual_agent.py      # Visual processing
│   ├── video_agent.py       # Video encoding
│   └── upload_agent.py      # YouTube upload
└── utils/
    ├── __init__.py
    ├── visual_helpers.py    # Visual processing helper functions
    └── common.py            # Shared utilities
```

## License

MIT
