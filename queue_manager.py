"""Download queue management for YouTube Video Downloader."""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class DownloadStatus(Enum):
    """Status of a download in the queue."""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class QueueItem:
    """A single item in the download queue."""
    url: str
    quality: str = "Best available"
    browser: str = "Chrome"
    folder: Path = field(default_factory=lambda: Path.cwd() / "downloads")
    status: DownloadStatus = field(default=DownloadStatus.PENDING)
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    progress: int = 0  # 0-100

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'url': self.url,
            'quality': self.quality,
            'browser': self.browser,
            'folder': str(self.folder),
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'error_message': self.error_message,
            'progress': self.progress,
        }


class DownloadQueue:
    """Manages a queue of downloads."""

    def __init__(self, max_queue_size: int = 100, max_concurrent: int = 10):
        """
        Initialize the download queue.

        Args:
            max_queue_size: Maximum number of items in queue
            max_concurrent: Maximum concurrent downloads (for playlists)
        """
        self.items: list[QueueItem] = []
        self.max_queue_size = max_queue_size
        self.max_concurrent = max_concurrent
        self.current_download: Optional[QueueItem] = None

    def add_item(self, url: str, quality: str = "Best available", 
                 browser: str = "Chrome", folder: Optional[Path] = None) -> QueueItem:
        """
        Add an item to the queue.

        Args:
            url: YouTube URL to download
            quality: Quality preset
            browser: Browser for authentication
            folder: Download destination

        Returns:
            The added QueueItem

        Raises:
            ValueError: If queue is full
        """
        if len(self.items) >= self.max_queue_size:
            raise ValueError(f'Queue is full (max {self.max_queue_size} items)')

        if folder is None:
            folder = Path.cwd() / "downloads"

        item = QueueItem(
            url=url,
            quality=quality,
            browser=browser,
            folder=folder
        )
        self.items.append(item)
        logger.info(f'Added to queue: {url} (Queue size: {len(self.items)})')
        return item

    def get_next_pending(self) -> Optional[QueueItem]:
        """Get the next pending item in the queue."""
        for item in self.items:
            if item.status == DownloadStatus.PENDING:
                return item
        return None

    def get_all_pending(self, limit: Optional[int] = None) -> list[QueueItem]:
        """Get all pending items up to limit (for parallel downloads)."""
        pending = [item for item in self.items if item.status == DownloadStatus.PENDING]
        if limit:
            return pending[:limit]
        return pending

    def update_item_status(self, item: QueueItem, status: DownloadStatus,
                          error: Optional[str] = None) -> None:
        """Update the status of a queue item."""
        item.status = status
        if status == DownloadStatus.DOWNLOADING and item.started_at is None:
            item.started_at = datetime.now()
        elif status == DownloadStatus.COMPLETED:
            item.completed_at = datetime.now()
        elif status == DownloadStatus.FAILED:
            item.error_message = error
            item.completed_at = datetime.now()

        logger.info(f'Queue item status updated: {item.url} -> {status.value}')

    def update_item_progress(self, item: QueueItem, progress: int) -> None:
        """Update download progress for a queue item (0-100)."""
        item.progress = max(0, min(100, progress))

    def remove_item(self, item: QueueItem) -> None:
        """Remove an item from the queue."""
        if item in self.items:
            self.items.remove(item)
            logger.info(f'Removed from queue: {item.url}')

    def clear_completed(self) -> int:
        """Clear all completed and failed items. Returns count removed."""
        completed_items = [
            item for item in self.items
            if item.status in (DownloadStatus.COMPLETED, DownloadStatus.FAILED)
        ]
        for item in completed_items:
            self.remove_item(item)
        return len(completed_items)

    def clear_queue(self) -> None:
        """Clear all items from queue."""
        self.items.clear()
        logger.info('Queue cleared')

    def get_queue_stats(self) -> dict[str, int]:
        """Get statistics about the queue."""
        return {
            'total': len(self.items),
            'pending': sum(1 for item in self.items if item.status == DownloadStatus.PENDING),
            'downloading': sum(1 for item in self.items if item.status == DownloadStatus.DOWNLOADING),
            'completed': sum(1 for item in self.items if item.status == DownloadStatus.COMPLETED),
            'failed': sum(1 for item in self.items if item.status == DownloadStatus.FAILED),
            'cancelled': sum(1 for item in self.items if item.status == DownloadStatus.CANCELLED),
        }

    def get_queue_progress(self) -> float:
        """Get overall queue progress as percentage."""
        if not self.items:
            return 0.0
        total_progress = sum(item.progress for item in self.items)
        return total_progress / len(self.items)

    def to_list(self) -> list[dict[str, Any]]:
        """Convert queue to list of dictionaries."""
        return [item.to_dict() for item in self.items]
