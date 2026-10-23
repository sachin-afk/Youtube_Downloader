"""URL validation utilities for YouTube Video Downloader."""

from urllib.parse import parse_qs, urlparse

from constants import PLAYLIST_ID_PATTERN, VALID_HOSTS, VIDEO_ID_PATTERN


def validate_youtube_url(url: str) -> str:
    """
    Validate and return a clean YouTube URL.

    Supports: watch URLs, short links (youtu.be), playlists, shorts, live, and embed URLs.

    Args:
        url: The URL to validate

    Returns:
        The validated URL string

    Raises:
        ValueError: If the URL is invalid
    """
    cleaned = (url or '').strip()
    if not cleaned:
        raise ValueError('Please enter a YouTube URL.')

    parsed = urlparse(cleaned)

    if parsed.scheme not in {'http', 'https'}:
        raise ValueError('Enter a valid YouTube video or playlist URL.')

    if parsed.hostname is None:
        raise ValueError('Enter a valid YouTube video or playlist URL.')

    if parsed.hostname.lower() not in VALID_HOSTS:
        raise ValueError('Enter a valid YouTube video or playlist URL.')

    # Handle youtu.be short links
    if parsed.hostname.lower() == 'youtu.be':
        video_id = parsed.path.strip('/').split('/')[0]
        if VIDEO_ID_PATTERN.fullmatch(video_id):
            return cleaned
        raise ValueError('Invalid YouTube short URL format.')

    # Handle standard YouTube URLs
    path = parsed.path.lower().rstrip('/')
    query = parse_qs(parsed.query)

    # Standard watch URL
    if path == '/watch':
        if VIDEO_ID_PATTERN.fullmatch(query.get('v', [''])[0]):
            return cleaned
        raise ValueError('Invalid watch URL: missing or invalid video ID.')

    # Playlist URL
    if path == '/playlist':
        if PLAYLIST_ID_PATTERN.fullmatch(query.get('list', [''])[0]):
            return cleaned
        raise ValueError('Invalid playlist URL: missing or invalid playlist ID.')

    # Shorts, Live, or Embed URLs
    if path.startswith(('/shorts/', '/live/', '/embed/')):
        parts = parsed.path.split('/')
        if len(parts) > 2 and VIDEO_ID_PATTERN.fullmatch(parts[2]):
            return cleaned
        raise ValueError('Invalid YouTube URL format.')

    raise ValueError('Enter a valid YouTube video or playlist URL.')


def is_playlist_url(url: str) -> bool:
    """
    Check if a URL is a playlist URL.

    Args:
        url: The URL to check

    Returns:
        True if the URL is a playlist, False otherwise
    """
    parsed = urlparse(url)
    path = parsed.path.lower().rstrip('/')
    query = parse_qs(parsed.query)
    return path == '/playlist' or bool(query.get('list'))
