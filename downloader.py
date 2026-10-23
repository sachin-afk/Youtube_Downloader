"""Download functionality for YouTube Video Downloader."""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable, Optional

from constants import DOWNLOAD_TIMEOUT_SECONDS, MAX_RETRIES, QUALITY_FORMATS, RETRY_DELAY_SECONDS

logger = logging.getLogger(__name__)


class AuthenticationRequiredError(RuntimeError):
    """Raised when YouTube requires authenticated browser cookies."""


class DownloadCancelledError(Exception):
    """Raised when a download operation is cancelled by the user."""



def _is_authentication_error(error: Exception) -> bool:
    """Return whether yt-dlp reported a YouTube authentication challenge."""
    message = str(error).lower()
    return any(
        phrase in message
        for phrase in (
            'sign in to confirm',
            'confirm you’re not a bot',
            "confirm you're not a bot",
            'use --cookies-from-browser',
            'use --cookies',
            'failed to decrypt with dpapi',
            'could not decrypt cookies',
            'error decrypting cookies',
        )
    )


def _authentication_error_message(browser: str) -> str:
    """Build recovery instructions for an authentication or cookie error."""
    if browser.lower() == 'none':
        return (
            'YouTube requires sign-in for this video. Select Chrome, Edge, or Firefox '
            'in the browser dropdown after signing in to YouTube.'
        )
    return (
        f'YouTube could not use {browser} cookies. Sign in to YouTube in {browser}, '
        f'close {browser} completely, then select {browser} in the app and try again. '
        'If DPAPI decryption still fails, use Firefox or export a cookies.txt file.'
    )


try:
    import imageio_ffmpeg
except ImportError:  # pragma: no cover
    imageio_ffmpeg = None

try:
    from yt_dlp import YoutubeDL
except ImportError:  # pragma: no cover
    YoutubeDL = None


def check_ffmpeg_available() -> bool:
    """
    Check if FFmpeg is available.

    Returns:
        True if FFmpeg is available, False otherwise
    """
    if imageio_ffmpeg is None:
        return False
    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        return ffmpeg_exe is not None and Path(ffmpeg_exe).exists()
    except Exception as e:
        logger.warning(f'Failed to locate FFmpeg: {e}')
        return False


def check_yt_dlp_available() -> bool:
    """
    Check if yt-dlp is available.

    Returns:
        True if yt-dlp is available, False otherwise
    """
    return YoutubeDL is not None


def build_download_options(download_folder: Path, browser: str, progress_hook: Callable,
                           quality: str = 'Best available') -> dict:
    """
    Build download options for yt-dlp.

    Args:
        download_folder: Destination folder
        browser: Browser for cookie authentication
        progress_hook: Callback for progress updates
        quality: Quality preset

    Returns:
        Dictionary of yt-dlp options
    """
    format_selector = QUALITY_FORMATS.get(quality, QUALITY_FORMATS['Best available'])
    options = {
        'format': format_selector,
        'outtmpl': str(download_folder / '%(title)s.%(ext)s'),
        'ffmpeg_location': imageio_ffmpeg.get_ffmpeg_exe() if imageio_ffmpeg else None,
        'quiet': True,
        'no_warnings': True,
        'progress_hooks': [progress_hook],
        'socket_timeout': DOWNLOAD_TIMEOUT_SECONDS,
    }

    if quality == 'Audio (MP3)':
        options['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    elif quality in ('Audio (MP4)', 'Audio (M4A)'):
        options['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'm4a',
            'preferredquality': '0',
        }]

    if browser.lower() != 'none':
        options['cookiesfrombrowser'] = (browser.lower(),)

    return options


def download_video(url: str, download_folder: Path, browser: str = 'none',
                   progress_callback: Optional[Callable] = None, quality: str = 'Best available',
                   max_retries: int = MAX_RETRIES,
                   cancel_event: Optional[Any] = None) -> None:
    """
    Download a YouTube video or playlist with retry logic and cancellation support.

    Args:
        url: YouTube URL
        download_folder: Destination folder
        browser: Browser for authentication
        progress_callback: Callback for progress updates
        quality: Quality preset
        max_retries: Maximum retry attempts
        cancel_event: Optional threading.Event to cancel download

    Raises:
        DownloadCancelledError: If download was cancelled by user
        RuntimeError: If required dependencies are missing or download fails
        Exception: If download fails after all retries
    """
    if YoutubeDL is None:
        raise RuntimeError('yt_dlp is not installed. Install it with: pip install yt-dlp')

    if not check_ffmpeg_available():
        raise RuntimeError(
            'FFmpeg is not installed. Install it with: pip install imageio-ffmpeg'
        )

    if cancel_event is not None and cancel_event.is_set():
        raise DownloadCancelledError('Download cancelled by user.')

    download_folder.mkdir(parents=True, exist_ok=True)

    def progress_hook(event: dict) -> None:
        """Internal progress hook wrapper."""
        if cancel_event is not None and cancel_event.is_set():
            raise DownloadCancelledError('Download cancelled by user.')
        if progress_callback and event.get('status') in {'downloading', 'finished'}:
            progress_callback(event)

    from validators import is_playlist_url
    options = build_download_options(download_folder, browser, progress_hook, quality)
    options['noplaylist'] = not is_playlist_url(url)

    last_error = None
    for attempt in range(1, max_retries + 1):
        if cancel_event is not None and cancel_event.is_set():
            raise DownloadCancelledError('Download cancelled by user.')
        try:
            logger.info(f'Download attempt {attempt}/{max_retries}: {url}')
            with YoutubeDL(options) as downloader:
                downloader.download([url])
            logger.info(f'Successfully downloaded: {url}')
            return
        except DownloadCancelledError:
            logger.info(f'Download cancelled by user: {url}')
            raise
        except Exception as e:
            last_error = e
            logger.warning(f'Download attempt {attempt} failed: {e}')
            if _is_authentication_error(e):
                raise AuthenticationRequiredError(_authentication_error_message(browser)) from e
            if cancel_event is not None and cancel_event.is_set():
                raise DownloadCancelledError('Download cancelled by user.')
            if attempt < max_retries:
                wait_time = RETRY_DELAY_SECONDS * attempt
                logger.info(f'Retrying in {wait_time} seconds...')
                time.sleep(wait_time)

    raise RuntimeError(f'Download failed after {max_retries} attempts: {last_error}')


def download_playlist_parallel(url: str, download_folder: Path, browser: str = 'none',
                               progress_callback: Optional[Callable] = None,
                               quality: str = 'Best available', max_concurrent: int = 10,
                               cancel_event: Optional[Any] = None) -> None:
    """
    Download a playlist with parallel/concurrent downloads and cancellation support.

    Downloads up to max_concurrent videos at the same time.

    Args:
        url: YouTube playlist URL
        download_folder: Destination folder
        browser: Browser for authentication
        progress_callback: Callback for progress updates
        quality: Quality preset
        max_concurrent: Maximum concurrent downloads (default 10)
        cancel_event: Optional threading.Event to cancel download

    Raises:
        DownloadCancelledError: If download was cancelled by user
        RuntimeError: If required dependencies are missing or download fails
    """
    if YoutubeDL is None:
        raise RuntimeError('yt_dlp is not installed. Install it with: pip install yt-dlp')

    if not check_ffmpeg_available():
        raise RuntimeError(
            'FFmpeg is not installed. Install it with: pip install imageio-ffmpeg'
        )

    if cancel_event is not None and cancel_event.is_set():
        raise DownloadCancelledError('Download cancelled by user.')

    from validators import is_playlist_url

    if not is_playlist_url(url):
        raise ValueError('URL is not a playlist. Use download_video() instead.')

    download_folder.mkdir(parents=True, exist_ok=True)

    # First, extract all video URLs from the playlist
    logger.info(f'Extracting playlist videos from: {url}')
    options = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': 'in_playlist',
        'socket_timeout': DOWNLOAD_TIMEOUT_SECONDS,
    }
    if browser.lower() != 'none':
        options['cookiesfrombrowser'] = (browser.lower(),)

    video_urls = []
    try:
        with YoutubeDL(options) as downloader:
            info = downloader.extract_info(url, download=False)
            if 'entries' in info:
                video_urls = [f"https://www.youtube.com/watch?v={entry['id']}"
                             for entry in info['entries'] if entry and 'id' in entry]
    except Exception as e:
        logger.error(f'Failed to extract playlist: {e}')
        raise RuntimeError(f'Failed to extract playlist videos: {e}')

    if not video_urls:
        logger.warning('Playlist has no videos')
        return

    logger.info(f'Found {len(video_urls)} videos in playlist. Starting parallel downloads '
               f'(max {max_concurrent} concurrent)...')

    def download_single_video(video_url: str) -> dict:
        """Download a single video. Returns result dict."""
        if cancel_event is not None and cancel_event.is_set():
            return {'url': video_url, 'status': 'cancelled'}
        try:
            def progress_hook(event: dict) -> None:
                if cancel_event is not None and cancel_event.is_set():
                    raise DownloadCancelledError('Download cancelled by user.')
                if progress_callback and event.get('status') in {'downloading', 'finished'}:
                    progress_callback({'url': video_url, **event})

            download_video(video_url, download_folder, browser, progress_hook, quality,
                           cancel_event=cancel_event)
            return {'url': video_url, 'status': 'success'}
        except DownloadCancelledError:
            return {'url': video_url, 'status': 'cancelled'}
        except Exception as e:
            logger.error(f'Failed to download {video_url}: {e}')
            return {'url': video_url, 'status': 'failed', 'error': str(e)}

    # Download videos in parallel
    results = []
    with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
        futures = {executor.submit(download_single_video, u): u for u in video_urls}
        completed = 0
        for future in as_completed(futures):
            completed += 1
            result = future.result()
            results.append(result)
            status = result.get('status', 'unknown')
            logger.info(f'Playlist download progress: {completed}/{len(video_urls)} - {status}')
            if cancel_event is not None and cancel_event.is_set():
                logger.info('Playlist download cancellation requested.')
                break

    if cancel_event is not None and cancel_event.is_set():
        raise DownloadCancelledError('Playlist download cancelled by user.')

    # Summary
    successful = sum(1 for r in results if r['status'] == 'success')
    failed = sum(1 for r in results if r['status'] == 'failed')
    logger.info(f'Playlist download complete: {successful} successful, {failed} failed')

    if failed > 0:
        raise RuntimeError(f'Playlist download completed with {failed} failures')


def download_multiple_urls(urls: list[str], download_folder: Path, browser: str = 'none',
                          progress_callback: Optional[Callable] = None,
                          quality: str = 'Best available',
                          cancel_event: Optional[Any] = None) -> dict[str, str]:
    """
    Download multiple URLs sequentially from a queue with cancellation support.

    Args:
        urls: List of YouTube URLs
        download_folder: Destination folder
        browser: Browser for authentication
        progress_callback: Callback for progress updates
        quality: Quality preset
        cancel_event: Optional threading.Event to cancel download

    Returns:
        Dictionary with results: {'url': 'status'}
    """
    if not urls:
        return {}

    logger.info(f'Starting downloads for {len(urls)} URLs')
    results = {}

    for idx, url in enumerate(urls, 1):
        if cancel_event is not None and cancel_event.is_set():
            logger.info(f'Cancelled remaining downloads at #{idx}')
            results[url] = 'cancelled'
            break

        try:
            logger.info(f'Downloading {idx}/{len(urls)}: {url}')
            if progress_callback:
                progress_callback({
                    'status': 'info',
                    'message': f'Downloading {idx}/{len(urls)}',
                    'url': url
                })

            download_video(url, download_folder, browser, progress_callback, quality,
                           cancel_event=cancel_event)
            results[url] = 'success'
        except DownloadCancelledError:
            results[url] = 'cancelled'
            break
        except Exception as e:
            logger.error(f'Failed to download {url}: {e}')
            results[url] = f'failed: {str(e)}'

    return results


