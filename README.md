# YouTube Video Downloader

A modern, responsive desktop application built in Python (Tkinter) for downloading YouTube videos, playlists, and audio using `yt-dlp` and `imageio-ffmpeg`.

## ✨ Key Features

- **Single & Batch Queue Downloads**: Download single videos or paste multiple URLs into a batch queue.
- **Download Cancellation**: Instant, safe cancellation for both single downloads and queue processing.
- **Parallel Playlist Downloads**: Concurrently download up to 10 playlist items using multi-threading.
- **Format Flexibility**:
  - Video: `Best available`, `1080p`, `720p`, `480p`, `360p`
  - Audio extraction: `Audio (MP3)` (192 kbps) and `Audio (M4A)` (original quality)
- **Cookie Authentication**: Extract session cookies from Chrome, Edge, or Firefox to bypass anti-bot and sign-in requirements.
- **Throttled GUI Updates**: Smooth, flicker-free listbox rendering and progress tracking.
- **Persistent History**: Rolling JSON-based history (`download_history.json`) for tracking past downloads.
- **Automatic Retry & Error Recovery**: 3-attempt exponential backoff for network resilience.
- **Non-Blocking Architecture**: Background daemon threads communicating with the Tkinter event loop via thread-safe queues.

---

## 🚀 Quick Start

### 1. Requirements
- Python 3.10+
- Windows, macOS, or Linux

### 2. Installation

```powershell
# Navigate to the project directory
cd .\path\to\project

# Activate your virtual environment
.\.venv\Scripts\Activate.ps1

# Install requirements
pip install -r Requirements.txt
```

### 3. Launch Application

```powershell
python youtube_downloader.py
```

---

## 📖 Usage Guide

### Single Download Tab
1. Paste any valid YouTube URL (video, playlist, shorts, live, or embed).
2. Choose a destination folder and select video quality or audio extraction (`Audio (MP3)` / `Audio (M4A)`).
3. If downloading a playlist, toggle **Parallel (Playlist)** to `on` for concurrent downloads.
4. Click **Download**. Click **Cancel** at any time to halt the operation cleanly.

### Queue Manager Tab
1. Switch to the **Queue Manager** tab.
2. Select your desired default quality and browser authentication.
3. Paste multiple URLs (one per line) in the input box and click **Add to Queue**.
4. Click **Start Download** to process queue items sequentially.
5. Use **Stop Queue** to cancel active downloads and halt processing of remaining items.

---

## 🧪 Testing & Verification

Run the full automated test suite (46 unit tests):
```powershell
python -m unittest test_youtube_downloader.py
```

Run the runtime feature verification script:
```powershell
python verify_features.py
```

---

## 📁 Project Architecture

```
youtube_downloader/
├── youtube_downloader.py         # Main entry point & logger setup
├── ui.py                         # Unified modern Tkinter tabbed GUI
├── downloader.py                 # Download engine (yt-dlp, FFmpeg, retries, cancellation)
├── queue_manager.py              # Queue state machine & item tracking
├── validators.py                 # URL regex parsers & validators
├── history.py                    # Persistent JSON history tracker
├── constants.py                  # Colors, fonts, presets, timeouts
├── test_youtube_downloader.py    # 46 automated unit tests
├── verify_features.py            # Runtime verification script
├── Requirements.txt              # yt-dlp & imageio-ffmpeg
└── downloads/                    # Default download folder
    └── download_history.json     # Saved download records
```

---

## ⚙️ Configuration & Customization

Modify [constants.py](constants.py) to configure:
- Window dimensions (`UI_WINDOW_WIDTH`, `UI_WINDOW_HEIGHT`)
- UI Color Palette (`COLOR_BG`, `COLOR_CARD`, `COLOR_ACCENT`, `COLOR_DANGER`, `COLOR_SUCCESS`)
- Rate throttling (`QUEUE_RENDER_THROTTLE_MS`)
- Maximum history entries (`MAX_HISTORY_ENTRIES = 50`)
- Timeout and retry policies (`DOWNLOAD_TIMEOUT_SECONDS = 3600`, `MAX_RETRIES = 3`)
