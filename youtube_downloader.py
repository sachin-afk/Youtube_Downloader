
"""YouTube Video Downloader - Main entry point."""

import logging
import sys
from tkinter import Tk

from ui import DownloaderApp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('youtube_downloader.log'),
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Launch the YouTube Video Downloader application."""
    logger.info('Starting YouTube Video Downloader')
    root = Tk()
    DownloaderApp(root)
    logger.info('Application window created')
    root.mainloop()
    logger.info('Application closed')


if __name__ == '__main__':
    main()
