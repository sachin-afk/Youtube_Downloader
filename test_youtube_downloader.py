"""Comprehensive test suite for YouTube Video Downloader."""

import logging
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import constants
import downloader
import history
import validators

logger = logging.getLogger(__name__)


class ValidateYoutubeUrlTests(unittest.TestCase):
    """Test URL validation."""

    def test_valid_watch_url(self):
        """Test standard watch URL validation."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        self.assertEqual(validators.validate_youtube_url(url), url)

    def test_valid_short_url(self):
        """Test short link (youtu.be) validation."""
        url = "https://youtu.be/dQw4w9WgXcQ"
        self.assertEqual(validators.validate_youtube_url(url), url)

    def test_valid_playlist_url(self):
        """Test playlist URL validation."""
        url = "https://www.youtube.com/playlist?list=PL1234567890abcdef"
        self.assertEqual(validators.validate_youtube_url(url), url)

    def test_valid_shorts_url(self):
        """Test YouTube Shorts URL validation."""
        url = "https://www.youtube.com/shorts/dQw4w9WgXcQ"
        self.assertEqual(validators.validate_youtube_url(url), url)

    def test_valid_live_url(self):
        """Test YouTube Live URL validation."""
        url = "https://www.youtube.com/live/dQw4w9WgXcQ"
        self.assertEqual(validators.validate_youtube_url(url), url)

    def test_valid_embed_url(self):
        """Test embedded URL validation."""
        url = "https://www.youtube.com/embed/dQw4w9WgXcQ"
        self.assertEqual(validators.validate_youtube_url(url), url)

    def test_music_youtube_url(self):
        """Test music.youtube.com URL validation."""
        url = "https://music.youtube.com/watch?v=dQw4w9WgXcQ"
        self.assertEqual(validators.validate_youtube_url(url), url)

    def test_empty_string_is_rejected(self):
        """Test that empty URL is rejected."""
        with self.assertRaises(ValueError) as ctx:
            validators.validate_youtube_url("   ")
        self.assertIn('please enter a youtube url', str(ctx.exception).lower())

    def test_non_youtube_url_is_rejected(self):
        """Test that non-YouTube URLs are rejected."""
        with self.assertRaises(ValueError):
            validators.validate_youtube_url("https://example.com/video")

    def test_watch_url_without_video_id_is_rejected(self):
        """Test that watch URLs without video ID are rejected."""
        with self.assertRaises(ValueError) as ctx:
            validators.validate_youtube_url("https://www.youtube.com/watch")
        self.assertIn('video id', str(ctx.exception).lower())

    def test_invalid_short_video_id_is_rejected(self):
        """Test that short links with invalid video ID are rejected."""
        with self.assertRaises(ValueError):
            validators.validate_youtube_url("https://youtu.be/short")

    def test_playlist_url_without_id_is_rejected(self):
        """Test that playlist URLs without ID are rejected."""
        with self.assertRaises(ValueError) as ctx:
            validators.validate_youtube_url("https://www.youtube.com/playlist")
        self.assertIn('playlist id', str(ctx.exception).lower())

    def test_url_with_whitespace_is_trimmed(self):
        """Test that URLs with whitespace are trimmed."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        result = validators.validate_youtube_url(f"  {url}  ")
        self.assertEqual(result, url)

    def test_http_scheme_is_accepted(self):
        """Test that HTTP scheme is accepted."""
        url = "http://www.youtube.com/watch?v=dQw4w9WgXcQ"
        self.assertEqual(validators.validate_youtube_url(url), url)

    def test_mobile_youtube_url(self):
        """Test m.youtube.com URL."""
        url = "https://m.youtube.com/watch?v=dQw4w9WgXcQ"
        self.assertEqual(validators.validate_youtube_url(url), url)


class PlaylistUrlDetectionTests(unittest.TestCase):
    """Test playlist URL detection."""

    def test_standard_playlist_url_is_detected(self):
        """Test standard playlist URL detection."""
        url = "https://www.youtube.com/playlist?list=PL1234567890abcdef"
        self.assertTrue(validators.is_playlist_url(url))

    def test_watch_url_with_playlist_param_is_detected(self):
        """Test watch URL with playlist parameter is detected."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PL1234567890abcdef"
        self.assertTrue(validators.is_playlist_url(url))

    def test_single_video_watch_url_is_not_detected(self):
        """Test single video watch URL is not detected as playlist."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        self.assertFalse(validators.is_playlist_url(url))


class DownloadOptionsTests(unittest.TestCase):
    """Test download options builder."""

    @patch.object(downloader, 'imageio_ffmpeg')
    def test_quality_selection_sets_format(self, ffmpeg):
        """Test quality setting affects format selection."""
        ffmpeg.get_ffmpeg_exe.return_value = 'ffmpeg'
        options = downloader.build_download_options(
            Path('downloads'), 'none', lambda _: None, '720p'
        )
        self.assertEqual(options['format'], constants.QUALITY_FORMATS['720p'])

    @patch.object(downloader, 'imageio_ffmpeg')
    def test_mp3_audio_selection_sets_audio_format_and_postprocessor(self, ffmpeg):
        """Test MP3 audio format selection includes MP3 postprocessor."""
        ffmpeg.get_ffmpeg_exe.return_value = 'ffmpeg'
        options = downloader.build_download_options(
            Path('downloads'), 'none', lambda _: None, 'Audio (MP3)'
        )
        self.assertEqual(options['format'], 'bestaudio/best')
        self.assertEqual(options['postprocessors'], [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }])

    @patch.object(downloader, 'imageio_ffmpeg')
    def test_mp4_audio_selection_sets_audio_format_and_postprocessor(self, ffmpeg):
        """Test audio format selection includes postprocessor."""
        ffmpeg.get_ffmpeg_exe.return_value = 'ffmpeg'
        options = downloader.build_download_options(
            Path('downloads'), 'none', lambda _: None, 'Audio (MP4)'
        )
        self.assertEqual(options['format'], 'bestaudio[ext=m4a]/bestaudio')
        self.assertEqual(options['postprocessors'], [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'm4a',
            'preferredquality': '0',
        }])

    @patch.object(downloader, 'imageio_ffmpeg')
    def test_browser_cookies_are_configured(self, ffmpeg):
        """Test browser authentication is configured."""
        ffmpeg.get_ffmpeg_exe.return_value = 'ffmpeg'
        options = downloader.build_download_options(
            Path('downloads'), 'edge', lambda _: None
        )
        self.assertEqual(options['cookiesfrombrowser'], ('edge',))
        self.assertEqual(options['ffmpeg_location'], 'ffmpeg')

    @patch.object(downloader, 'imageio_ffmpeg')
    def test_none_browser_does_not_configure_cookies(self, ffmpeg):
        """Test 'none' browser doesn't configure cookies."""
        ffmpeg.get_ffmpeg_exe.return_value = 'ffmpeg'
        options = downloader.build_download_options(
            Path('downloads'), 'none', lambda _: None
        )
        self.assertNotIn('cookiesfrombrowser', options)

    @patch.object(downloader, 'check_ffmpeg_available', return_value=True)
    @patch.object(downloader, 'YoutubeDL')
    def test_download_cancelled_event_raises_error(self, ytdl, ffmpeg):
        """Test setting cancel_event raises DownloadCancelledError without downloading."""
        from threading import Event
        cancel_event = Event()
        cancel_event.set()

        with self.assertRaises(downloader.DownloadCancelledError):
            downloader.download_video(
                'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                Path('downloads'),
                cancel_event=cancel_event
            )
        self.assertEqual(ytdl.call_count, 0)


    @patch.object(downloader, 'check_ffmpeg_available', return_value=True)
    @patch.object(downloader, 'YoutubeDL')
    def test_authentication_failure_is_not_retried(self, ytdl, ffmpeg):
        """Test YouTube authentication challenges fail without retrying."""
        ytdl.return_value.__enter__.return_value.download.side_effect = RuntimeError(
            "Sign in to confirm you're not a bot. Use --cookies-from-browser"
        )

        with self.assertRaises(downloader.AuthenticationRequiredError):
            downloader.download_video(
                'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                Path('downloads'),
                browser='Chrome',
                max_retries=3,
            )

        self.assertEqual(ytdl.return_value.__enter__.return_value.download.call_count, 1)

    @patch.object(downloader, 'check_ffmpeg_available', return_value=True)
    @patch.object(downloader, 'YoutubeDL')
    def test_dpapi_cookie_failure_is_not_retried(self, ytdl, ffmpeg):
        """Test browser cookie decryption failures fail without retrying."""
        ytdl.return_value.__enter__.return_value.download.side_effect = RuntimeError(
            'ERROR: Failed to decrypt with DPAPI'
        )

        with self.assertRaises(downloader.AuthenticationRequiredError) as context:
            downloader.download_video(
                'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                Path('downloads'),
                browser='Chrome',
                max_retries=3,
            )

        self.assertIn('could not use Chrome cookies', str(context.exception))
        self.assertEqual(ytdl.return_value.__enter__.return_value.download.call_count, 1)

    @patch.object(downloader, 'check_ffmpeg_available', return_value=True)
    @patch.object(downloader, 'download_video')
    @patch.object(downloader, 'YoutubeDL')
    def test_playlist_extraction_uses_browser_cookies(self, ytdl, download, ffmpeg):
        """Test authenticated playlist extraction receives browser cookies."""
        ytdl.return_value.__enter__.return_value.extract_info.return_value = {
            'entries': [{'id': 'dQw4w9WgXcQ'}]
        }

        downloader.download_playlist_parallel(
            'https://www.youtube.com/playlist?list=PLtest',
            Path('downloads'),
            browser='Edge',
        )

        options = ytdl.call_args.args[0]
        self.assertEqual(options['cookiesfrombrowser'], ('edge',))

    @patch.object(downloader, 'imageio_ffmpeg')
    def test_all_quality_formats_generate_valid_options(self, ffmpeg):
        """Test all quality presets generate valid options."""
        ffmpeg.get_ffmpeg_exe.return_value = 'ffmpeg'
        for quality in constants.QUALITY_FORMATS.keys():
            options = downloader.build_download_options(
                Path('downloads'), 'none', lambda _: None, quality
            )
            self.assertIn(options['format'], constants.QUALITY_FORMATS.values())


            self.assertIn('Chrome', constants.BROWSER_OPTIONS)
class FFmpegAvailabilityTests(unittest.TestCase):
    """Test FFmpeg availability checking."""

    def test_ffmpeg_not_available_when_module_missing(self):
        """Test FFmpeg detection when module is not available."""
        with patch.object(downloader, 'imageio_ffmpeg', None):
            self.assertFalse(downloader.check_ffmpeg_available())

    @patch.object(downloader, 'imageio_ffmpeg')
    def test_ffmpeg_available_when_exe_found(self, ffmpeg_mock):
        """Test FFmpeg detection when executable exists."""
        ffmpeg_mock.get_ffmpeg_exe.return_value = 'ffmpeg_path'
        with patch('pathlib.Path.exists', return_value=True):
            self.assertTrue(downloader.check_ffmpeg_available())

    @patch.object(downloader, 'imageio_ffmpeg')
    def test_ffmpeg_not_available_when_exe_not_found(self, ffmpeg_mock):
        """Test FFmpeg detection when executable doesn't exist."""
        ffmpeg_mock.get_ffmpeg_exe.return_value = None
        self.assertFalse(downloader.check_ffmpeg_available())


class YtDlpAvailabilityTests(unittest.TestCase):
    """Test yt-dlp availability checking."""

    def test_yt_dlp_available_when_module_imported(self):
        """Test yt-dlp availability detection."""
        with patch.object(downloader, 'YoutubeDL', True):
            self.assertTrue(downloader.check_yt_dlp_available())

    def test_yt_dlp_not_available_when_module_missing(self):
        """Test yt-dlp detection when not available."""
        with patch.object(downloader, 'YoutubeDL', None):
            self.assertFalse(downloader.check_yt_dlp_available())


class DownloadHistoryTests(unittest.TestCase):
    """Test download history tracking."""

    def test_add_record_creates_history_file(self):
        """Test that adding a record creates the history file."""
        with TemporaryDirectory() as tmpdir:
            history_file = Path(tmpdir) / 'history.json'
            hist = history.DownloadHistory(history_file)
            hist.add_record(
                'https://youtube.com/watch?v=test',
                'Test Video',
                Path(tmpdir),
                'Best available'
            )
            self.assertTrue(history_file.exists())

    def test_history_persists_to_disk(self):
        """Test that history persists across instances."""
        with TemporaryDirectory() as tmpdir:
            history_file = Path(tmpdir) / 'history.json'
            hist1 = history.DownloadHistory(history_file)
            hist1.add_record('https://youtube.com/watch?v=test1', 'Video 1', Path(tmpdir), 'Best available')

            hist2 = history.DownloadHistory(history_file)
            self.assertEqual(len(hist2.records), 1)
            self.assertEqual(hist2.records[0]['url'], 'https://youtube.com/watch?v=test1')

    def test_get_recent_returns_limited_records(self):
        """Test get_recent returns limited number of records."""
        with TemporaryDirectory() as tmpdir:
            history_file = Path(tmpdir) / 'history.json'
            hist = history.DownloadHistory(history_file)
            for i in range(20):
                hist.add_record(f'https://youtube.com/watch?v=test{i}', f'Video {i}', Path(tmpdir), 'Best available')

            recent = hist.get_recent(limit=5)
            self.assertEqual(len(recent), 5)

    def test_clear_history_removes_all_records(self):
        """Test clearing history removes all records."""
        with TemporaryDirectory() as tmpdir:
            history_file = Path(tmpdir) / 'history.json'
            hist = history.DownloadHistory(history_file)
            hist.add_record('https://youtube.com/watch?v=test', 'Test Video', Path(tmpdir), 'Best available')
            hist.clear_history()
            self.assertEqual(len(hist.records), 0)

    def test_max_history_entries_enforced(self):
        """Test maximum history entries limit is enforced."""
        with TemporaryDirectory() as tmpdir:
            history_file = Path(tmpdir) / 'history.json'
            hist = history.DownloadHistory(history_file)
            for i in range(100):
                hist.add_record(f'https://youtube.com/watch?v=test{i}', f'Video {i}', Path(tmpdir), 'Best available')

            self.assertLessEqual(len(hist.records), constants.MAX_HISTORY_ENTRIES)

    def test_failed_download_status_tracked(self):
        """Test failed download status is tracked."""
        with TemporaryDirectory() as tmpdir:
            history_file = Path(tmpdir) / 'history.json'
            hist = history.DownloadHistory(history_file)
            hist.add_record('https://youtube.com/watch?v=test', 'Test Video', Path(tmpdir), 'Best available', 'failed')
            failed = hist.get_failed_downloads()
            self.assertEqual(len(failed), 1)
            self.assertEqual(failed[0]['status'], 'failed')


class ConstantsTests(unittest.TestCase):
    """Test constants configuration."""

    def test_video_id_pattern_matches_valid_ids(self):
        """Test video ID pattern validation."""
        valid_ids = [
            'dQw4w9WgXcQ',
            'jNQXAC9IVRw',
            'AQOLSNAP33U',
        ]
        for vid_id in valid_ids:
            self.assertTrue(constants.VIDEO_ID_PATTERN.fullmatch(vid_id))

    def test_video_id_pattern_rejects_invalid_ids(self):
        """Test video ID pattern rejects invalid IDs."""
        invalid_ids = [
            'short',
            'toolongvideoididthatismorethan11chars',
            'invalid@chars',
        ]
        for vid_id in invalid_ids:
            self.assertFalse(constants.VIDEO_ID_PATTERN.fullmatch(vid_id))

    def test_quality_formats_not_empty(self):
        """Test quality formats are defined."""
        self.assertGreater(len(constants.QUALITY_FORMATS), 0)

    def test_browser_options_defined(self):
        """Test browser options are defined."""
        self.assertGreater(len(constants.BROWSER_OPTIONS), 0)
        self.assertIn('Chrome', constants.BROWSER_OPTIONS)


class QueueManagerTests(unittest.TestCase):
    """Test Queue management module."""

    def test_queue_add_and_stats(self):
        """Test adding items to download queue and stats calculation."""
        from queue_manager import DownloadQueue, DownloadStatus
        queue = DownloadQueue(max_queue_size=10)
        item = queue.add_item('https://www.youtube.com/watch?v=dQw4w9WgXcQ', 'Best available')
        self.assertEqual(item.status, DownloadStatus.PENDING)
        self.assertEqual(len(queue.items), 1)

        stats = queue.get_queue_stats()
        self.assertEqual(stats['total'], 1)
        self.assertEqual(stats['pending'], 1)

    def test_queue_status_updates(self):
        """Test updating queue item status and progress."""
        from queue_manager import DownloadQueue, DownloadStatus
        queue = DownloadQueue(max_queue_size=10)
        item = queue.add_item('https://www.youtube.com/watch?v=dQw4w9WgXcQ', 'Best available')
        queue.update_item_status(item, DownloadStatus.DOWNLOADING)
        self.assertEqual(item.status, DownloadStatus.DOWNLOADING)

        queue.update_item_progress(item, 75)
        self.assertEqual(item.progress, 75)


class UiImportTests(unittest.TestCase):
    """Test UI imports and class instantiation."""

    def test_ui_import_downloader_app(self):
        """Test DownloaderApp imports cleanly from ui."""
        from ui import DownloaderApp
        self.assertTrue(callable(DownloaderApp))


if __name__ == '__main__':
    unittest.main()


