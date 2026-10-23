"""Configuration and constants for YouTube Video Downloader."""

import re
from pathlib import Path

# URL Validation Patterns
VIDEO_ID_PATTERN = re.compile(r'^[A-Za-z0-9_-]{11}$')
PLAYLIST_ID_PATTERN = re.compile(r'^[A-Za-z0-9_-]+$')
VALID_HOSTS = {'youtube.com', 'www.youtube.com', 'm.youtube.com', 'music.youtube.com', 'youtu.be'}

# Quality Format Presets
QUALITY_FORMATS = {
    'Best available': 'bestvideo+bestaudio/best',
    '1080p': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]/best',
    '720p': 'bestvideo[height<=720]+bestaudio/best[height<=720]/best',
    '480p': 'bestvideo[height<=480]+bestaudio/best[height<=480]/best',
    '360p': 'bestvideo[height<=360]+bestaudio/best[height<=360]/best',
    'Audio (MP3)': 'bestaudio/best',
    'Audio (M4A)': 'bestaudio[ext=m4a]/bestaudio',
    'Audio (MP4)': 'bestaudio[ext=m4a]/bestaudio',
}

# Browser Options for Cookie Authentication
BROWSER_OPTIONS = ('Chrome', 'Edge', 'Firefox', 'None')

# UI Configuration
UI_WINDOW_WIDTH = 750
UI_WINDOW_HEIGHT = 650
UI_MIN_WIDTH = 550
UI_MIN_HEIGHT = 550
UI_PADDING_X = 20
UI_PADDING_Y = 20

# Color Scheme
COLOR_BG = '#e8edf5'
COLOR_CARD = '#edf2fa'
COLOR_TEXT = '#2d3241'
COLOR_MUTED = '#747d8d'
COLOR_ACCENT = '#6d7ef5'
COLOR_HIGHLIGHT = '#f7f9ff'
COLOR_SHADOW = '#cfd8e7'
COLOR_SUCCESS = '#28a745'
COLOR_DANGER = '#dc3545'

# UI Font Configuration
FONT_TITLE = ('Segoe UI', 18, 'bold')
FONT_SUBTITLE = ('Segoe UI', 11, 'bold')
FONT_NORMAL = ('Segoe UI', 10)
FONT_SMALL = ('Segoe UI', 9, 'bold')
FONT_LABEL = ('Segoe UI', 10, 'bold')

# Download Configuration
DEFAULT_QUALITY = 'Best available'
DEFAULT_BROWSER = 'Chrome'
PROGRESS_BAR_THICKNESS = 18
PROGRESS_POLL_INTERVAL_MS = 100
QUEUE_RENDER_THROTTLE_MS = 200

# Download Timeout & Retry
DOWNLOAD_TIMEOUT_SECONDS = 3600  # 1 hour
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2

# History Configuration
HISTORY_FILE_NAME = 'download_history.json'
MAX_HISTORY_ENTRIES = 50

# Default Paths
DEFAULT_DOWNLOADS_FOLDER = Path(__file__).resolve().parent / 'downloads'

# FFmpeg Configuration
FFMPEG_AUDIO_CODEC = 'm4a'
FFMPEG_AUDIO_QUALITY = '0'
FFMPEG_LOG_LEVEL = 'quiet'

