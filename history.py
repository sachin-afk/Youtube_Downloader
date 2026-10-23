"""Download history tracking for YouTube Video Downloader."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


class DownloadHistory:
    """Manages download history records."""

    def __init__(self, history_file: Optional[Path] = None):
        """
        Initialize download history manager.

        Args:
            history_file: Path to history JSON file. Defaults to downloads/download_history.json
        """
        if history_file is None:
            history_file = Path(__file__).resolve().parent / 'downloads' / 'download_history.json'

        self.history_file = history_file
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        self.records = self._load_history()

    def _load_history(self) -> list[dict[str, Any]]:
        """Load history from file."""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return []
        return []

    def _save_history(self) -> None:
        """Save history to file."""
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(self.records, f, indent=2, ensure_ascii=False)

    def add_record(self, url: str, title: str, folder: Path, quality: str, status: str = 'success') -> None:
        """
        Add a download record to history.

        Args:
            url: YouTube URL
            title: Video/playlist title
            folder: Download destination folder
            quality: Quality setting used
            status: Download status (success, failed, cancelled)
        """
        record = {
            'timestamp': datetime.now().isoformat(),
            'url': url,
            'title': title,
            'folder': str(folder),
            'quality': quality,
            'status': status,
        }
        self.records.insert(0, record)  # Newest first

        # Keep only last N records
        from constants import MAX_HISTORY_ENTRIES
        self.records = self.records[:MAX_HISTORY_ENTRIES]
        self._save_history()

    def get_recent(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent download records."""
        return self.records[:limit]

    def clear_history(self) -> None:
        """Clear all history records."""
        self.records = []
        self._save_history()

    def get_failed_downloads(self) -> list[dict[str, Any]]:
        """Get all failed download records."""
        return [r for r in self.records if r.get('status') == 'failed']
