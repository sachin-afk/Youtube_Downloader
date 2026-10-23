"""GUI components for YouTube Video Downloader with queue management and cancellation support."""

import logging
import time
from pathlib import Path
from queue import Empty, Queue
from threading import Event, Thread
from tkinter import (
    Button, Entry, Frame, Label, Listbox, Scrollbar, StringVar, Text, Tk,
    filedialog, messagebox, ttk
)

from constants import (
    BROWSER_OPTIONS, COLOR_ACCENT, COLOR_BG, COLOR_CARD, COLOR_DANGER,
    COLOR_MUTED, COLOR_SHADOW, COLOR_SUCCESS, COLOR_TEXT, DEFAULT_BROWSER,
    DEFAULT_DOWNLOADS_FOLDER, DEFAULT_QUALITY, FONT_LABEL, FONT_NORMAL,
    FONT_SMALL, FONT_SUBTITLE, FONT_TITLE, PROGRESS_BAR_THICKNESS,
    PROGRESS_POLL_INTERVAL_MS, QUALITY_FORMATS, QUEUE_RENDER_THROTTLE_MS,
    UI_MIN_HEIGHT, UI_MIN_WIDTH, UI_PADDING_X, UI_PADDING_Y, UI_WINDOW_HEIGHT,
    UI_WINDOW_WIDTH
)
from downloader import (
    DownloadCancelledError, check_ffmpeg_available, check_yt_dlp_available,
    download_playlist_parallel, download_video
)
from history import DownloadHistory
from queue_manager import DownloadQueue, DownloadStatus
from validators import is_playlist_url, validate_youtube_url

logger = logging.getLogger(__name__)


class DownloaderApp:
    """Main GUI application for YouTube video downloader with queue management."""

    def __init__(self, root: Tk):
        """Initialize the application."""
        self.root = root
        self.root.title('YouTube Video Downloader')
        self.root.geometry(f'{UI_WINDOW_WIDTH}x{UI_WINDOW_HEIGHT}')
        self.root.minsize(UI_MIN_WIDTH, UI_MIN_HEIGHT)
        self.root.configure(bg=COLOR_BG)

        self.progress_queue: Queue = Queue()
        self.history = DownloadHistory()
        self.download_queue = DownloadQueue(max_concurrent=10)

        # Cancellation Events
        self.single_cancel_event: Event = Event()
        self.queue_cancel_event: Event = Event()
        self.is_single_downloading: bool = False
        self.is_queue_downloading: bool = False
        self._last_queue_render_time: float = 0.0

        # Check dependencies
        self._check_dependencies()

        # Setup UI
        self._setup_ui()

        # Start processing queue
        self.root.after(PROGRESS_POLL_INTERVAL_MS, self.process_queue)

    def _check_dependencies(self) -> None:
        """Check if required dependencies are available."""
        if not check_yt_dlp_available():
            messagebox.showerror(
                'Missing Dependency',
                'yt-dlp is not installed.\nInstall it with: pip install yt-dlp'
            )
            logger.error('yt-dlp not available')

        if not check_ffmpeg_available():
            messagebox.showwarning(
                'Missing Dependency',
                'FFmpeg is not installed.\nInstall it with: pip install imageio-ffmpeg'
            )
            logger.warning('FFmpeg not available')

    def _setup_ui(self) -> None:
        """Setup the user interface."""
        style = ttk.Style()
        style.theme_use('clam')
        style.configure(
            'Downloader.Horizontal.TProgressbar',
            troughcolor='#dfe7f4',
            background=COLOR_ACCENT,
            thickness=PROGRESS_BAR_THICKNESS,
            borderwidth=0
        )

        # Tabbed Container
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=UI_PADDING_X, pady=UI_PADDING_Y)

        # Tab 1: Single Download
        self.single_frame = Frame(notebook, bg=COLOR_CARD)
        notebook.add(self.single_frame, text='Single Download')
        self._setup_single_download_tab()

        # Tab 2: Queue Manager
        self.queue_frame = Frame(notebook, bg=COLOR_CARD)
        notebook.add(self.queue_frame, text='Queue Manager')
        self._setup_queue_management_tab()

    def _setup_single_download_tab(self) -> None:
        """Setup the single download tab."""
        surface = self.single_frame
        surface.grid_columnconfigure(0, weight=1)

        # Title
        Label(
            surface, text='YouTube Video Downloader', bg=COLOR_CARD, fg=COLOR_TEXT,
            font=FONT_TITLE
        ).grid(row=0, column=0, pady=(14, 10), sticky='ew', padx=20)

        # Variables
        self.link = StringVar()
        self.status = StringVar(value='Paste a YouTube link to begin')
        self.progress_value = StringVar(value='0%')
        self.selected_folder = StringVar(value=str(DEFAULT_DOWNLOADS_FOLDER))
        self.cookie_browser = StringVar(value=DEFAULT_BROWSER)
        self.quality = StringVar(value=DEFAULT_QUALITY)
        self.parallel_mode = StringVar(value='off')

        # URL Input
        Label(
            surface, text='YouTube URL:', bg=COLOR_CARD, fg=COLOR_TEXT,
            font=FONT_SUBTITLE
        ).grid(row=1, column=0, sticky='w', padx=20)

        Entry(
            surface, textvariable=self.link, bg=COLOR_BG, fg=COLOR_TEXT, bd=0,
            highlightthickness=1, highlightbackground=COLOR_SHADOW,
            highlightcolor=COLOR_ACCENT, font=FONT_LABEL
        ).grid(row=2, column=0, sticky='ew', padx=20, pady=(6, 12), ipady=8)

        # Progress Bar
        self.progress_bar = ttk.Progressbar(
            surface, style='Downloader.Horizontal.TProgressbar', maximum=100
        )
        self.progress_bar.grid(row=3, column=0, sticky='ew', padx=20)

        Label(
            surface, textvariable=self.progress_value, bg=COLOR_CARD, fg=COLOR_MUTED,
            font=FONT_SMALL
        ).grid(row=4, column=0, sticky='e', padx=20, pady=(4, 8))

        # Status
        Label(
            surface, textvariable=self.status, bg=COLOR_CARD, fg=COLOR_TEXT,
            font=FONT_NORMAL, wraplength=UI_WINDOW_WIDTH - 80
        ).grid(row=5, column=0, sticky='ew', padx=20, pady=(0, 8))

        # Folder Selection
        folder_row = Frame(surface, bg=COLOR_CARD)
        folder_row.grid(row=6, column=0, sticky='ew', padx=20, pady=(0, 6))
        folder_row.grid_columnconfigure(1, weight=1)

        Label(
            folder_row, text='Save Folder:', bg=COLOR_CARD, fg=COLOR_TEXT,
            font=FONT_NORMAL
        ).grid(row=0, column=0, padx=(0, 8))

        Entry(
            folder_row, textvariable=self.selected_folder, bg=COLOR_BG, bd=0,
            font=FONT_NORMAL
        ).grid(row=0, column=1, sticky='ew', ipady=6)

        Button(
            folder_row, text='Browse', command=self.choose_folder, bg=COLOR_BG,
            relief='flat', bd=0, padx=10, pady=4
        ).grid(row=0, column=2, padx=(8, 0))

        # Settings Row (Browser, Quality, Parallel)
        settings_row = Frame(surface, bg=COLOR_CARD)
        settings_row.grid(row=7, column=0, sticky='ew', padx=20, pady=(0, 10))

        Label(
            settings_row, text='Browser Cookies:', bg=COLOR_CARD, fg=COLOR_TEXT,
            font=FONT_NORMAL
        ).pack(side='left', padx=(0, 4))

        ttk.Combobox(
            settings_row, textvariable=self.cookie_browser,
            values=BROWSER_OPTIONS, state='readonly', width=10
        ).pack(side='left', padx=(0, 12))

        Label(
            settings_row, text='Quality:', bg=COLOR_CARD, fg=COLOR_TEXT,
            font=FONT_NORMAL
        ).pack(side='left', padx=(0, 4))

        ttk.Combobox(
            settings_row, textvariable=self.quality,
            values=tuple(QUALITY_FORMATS), state='readonly', width=14
        ).pack(side='left', padx=(0, 12))

        Label(
            settings_row, text='Parallel (Playlist):', bg=COLOR_CARD, fg=COLOR_TEXT,
            font=FONT_NORMAL
        ).pack(side='left', padx=(0, 4))

        ttk.Combobox(
            settings_row, textvariable=self.parallel_mode,
            values=('off', 'on'), state='readonly', width=6
        ).pack(side='left')

        # Action Buttons Row (Download & Cancel)
        action_row = Frame(surface, bg=COLOR_CARD)
        action_row.grid(row=8, column=0, pady=(6, 12))

        self.download_button = Button(
            action_row, text='Download', command=self.start_download,
            bg=COLOR_ACCENT, fg='white', relief='flat', bd=0,
            font=FONT_SUBTITLE, padx=22, pady=8
        )
        self.download_button.pack(side='left', padx=6)

        self.cancel_button = Button(
            action_row, text='Cancel', command=self.cancel_download,
            bg=COLOR_DANGER, fg='white', relief='flat', bd=0,
            font=FONT_SUBTITLE, padx=18, pady=8, state='disabled'
        )
        self.cancel_button.pack(side='left', padx=6)

    def _setup_queue_management_tab(self) -> None:
        """Setup the queue management tab."""
        surface = self.queue_frame
        surface.grid_columnconfigure(0, weight=1)
        surface.grid_rowconfigure(4, weight=1)

        # Title
        Label(
            surface, text='Batch Download Queue', bg=COLOR_CARD, fg=COLOR_TEXT,
            font=FONT_TITLE
        ).grid(row=0, column=0, pady=(12, 6), sticky='ew', padx=20)

        # Queue Settings Row
        queue_settings = Frame(surface, bg=COLOR_CARD)
        queue_settings.grid(row=1, column=0, sticky='ew', padx=20, pady=(0, 6))

        Label(
            queue_settings, text='Quality:', bg=COLOR_CARD, fg=COLOR_TEXT,
            font=FONT_NORMAL
        ).pack(side='left', padx=(0, 4))

        self.queue_quality = StringVar(value=DEFAULT_QUALITY)
        ttk.Combobox(
            queue_settings, textvariable=self.queue_quality,
            values=tuple(QUALITY_FORMATS), state='readonly', width=14
        ).pack(side='left', padx=(0, 12))

        Label(
            queue_settings, text='Browser:', bg=COLOR_CARD, fg=COLOR_TEXT,
            font=FONT_NORMAL
        ).pack(side='left', padx=(0, 4))

        self.queue_browser = StringVar(value=DEFAULT_BROWSER)
        ttk.Combobox(
            queue_settings, textvariable=self.queue_browser,
            values=BROWSER_OPTIONS, state='readonly', width=10
        ).pack(side='left', padx=(0, 12))

        # Multi-URL Input
        Label(
            surface, text='Paste URLs (one per line):', bg=COLOR_CARD, fg=COLOR_TEXT,
            font=FONT_SUBTITLE
        ).grid(row=2, column=0, sticky='w', padx=20, pady=(2, 2))

        self.multi_url_text = Text(
            surface, height=4, bg=COLOR_BG, fg=COLOR_TEXT, bd=0,
            highlightthickness=1, highlightbackground=COLOR_SHADOW,
            highlightcolor=COLOR_ACCENT, font=FONT_NORMAL
        )
        self.multi_url_text.grid(row=3, column=0, sticky='ew', padx=20, pady=(2, 6), ipady=3)

        # Buttons row
        button_row = Frame(surface, bg=COLOR_CARD)
        button_row.grid(row=4, column=0, sticky='ew', padx=20, pady=(0, 6))

        self.add_queue_button = Button(
            button_row, text='Add to Queue', command=self.add_urls_to_queue,
            bg=COLOR_ACCENT, fg='white', relief='flat', bd=0,
            font=FONT_NORMAL, padx=12, pady=6
        )
        self.add_queue_button.pack(side='left', padx=(0, 6))

        self.clear_queue_button = Button(
            button_row, text='Clear Queue', command=self.clear_queue,
            bg=COLOR_MUTED, fg='white', relief='flat', bd=0,
            font=FONT_NORMAL, padx=12, pady=6
        )
        self.clear_queue_button.pack(side='left', padx=6)

        self.start_queue_button = Button(
            button_row, text='Start Download', command=self.start_queue_download,
            bg=COLOR_SUCCESS, fg='white', relief='flat', bd=0,
            font=FONT_NORMAL, padx=14, pady=6
        )
        self.start_queue_button.pack(side='left', padx=6)

        self.stop_queue_button = Button(
            button_row, text='Stop Queue', command=self.stop_queue_download,
            bg=COLOR_DANGER, fg='white', relief='flat', bd=0,
            font=FONT_NORMAL, padx=14, pady=6, state='disabled'
        )
        self.stop_queue_button.pack(side='left', padx=6)

        # Queue Listbox with scrollbar
        queue_container = Frame(surface, bg=COLOR_CARD)
        queue_container.grid(row=5, column=0, sticky='nsew', padx=20, pady=(4, 6))
        queue_container.grid_columnconfigure(0, weight=1)
        queue_container.grid_rowconfigure(0, weight=1)

        scrollbar = Scrollbar(queue_container)
        scrollbar.pack(side='right', fill='y')

        self.queue_listbox = Listbox(
            queue_container, bg=COLOR_BG, fg=COLOR_TEXT, bd=0,
            highlightthickness=0, font=FONT_NORMAL, height=6,
            yscrollcommand=scrollbar.set
        )
        self.queue_listbox.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=self.queue_listbox.yview)

        # Queue Stats
        self.queue_stats = StringVar(value='Queue: 0 items | Pending: 0 | Downloading: 0 | Completed: 0')
        Label(
            surface, textvariable=self.queue_stats, bg=COLOR_CARD, fg=COLOR_MUTED,
            font=FONT_SMALL
        ).grid(row=6, column=0, sticky='ew', padx=20, pady=(2, 8))

    def choose_folder(self) -> None:
        """Open folder selection dialog."""
        folder = filedialog.askdirectory(title='Choose download folder')
        if folder:
            self.selected_folder.set(folder)
            self.status.set(f'Save folder: {folder}')

    def add_urls_to_queue(self) -> None:
        """Add URLs from text box to queue."""
        urls_text = self.multi_url_text.get('1.0', 'end').strip()
        if not urls_text:
            messagebox.showwarning('Empty Input', 'Please paste at least one URL')
            return

        urls = [url.strip() for url in urls_text.split('\n') if url.strip()]
        folder = Path(self.selected_folder.get()).expanduser()
        browser = self.queue_browser.get()
        quality = self.queue_quality.get()

        added_count = 0
        for url in urls:
            try:
                validate_youtube_url(url)
                self.download_queue.add_item(url, quality, browser, folder)
                added_count += 1
            except ValueError as e:
                logger.warning(f'Invalid URL skipped: {url} - {e}')

        if added_count > 0:
            self.multi_url_text.delete('1.0', 'end')
            self.update_queue_display()
            messagebox.showinfo('Added', f'{added_count} URL(s) added to queue')
        else:
            messagebox.showerror('Error', 'No valid URLs found')

    def clear_queue(self) -> None:
        """Clear the download queue."""
        if self.download_queue.items:
            if messagebox.askyesno('Confirm', 'Clear all items from queue?'):
                self.download_queue.clear_queue()
                self.update_queue_display()

    def start_download(self) -> None:
        """Start single download."""
        try:
            url = validate_youtube_url(self.link.get())
        except ValueError as error:
            messagebox.showwarning('Invalid URL', str(error))
            logger.error(f'Invalid URL: {error}')
            return

        folder = Path(self.selected_folder.get()).expanduser()
        browser = self.cookie_browser.get()
        quality = self.quality.get()

        self.single_cancel_event.clear()
        self.is_single_downloading = True
        self.download_button.config(state='disabled')
        self.cancel_button.config(state='normal')
        self.progress_bar['value'] = 0
        self.progress_value.set('0%')
        self.status.set('Downloading...')

        Thread(
            target=self.download_worker,
            args=(url, folder, browser, quality),
            daemon=True
        ).start()

    def cancel_download(self) -> None:
        """Request cancellation of single download."""
        if self.is_single_downloading:
            self.single_cancel_event.set()
            self.status.set('Cancelling download...')
            self.cancel_button.config(state='disabled')
            logger.info('User requested single download cancellation.')

    def download_worker(self, url: str, folder: Path, browser: str, quality: str) -> None:
        """Worker thread for single downloads."""
        try:
            if is_playlist_url(url) and self.parallel_mode.get() == 'on':
                logger.info(f'Downloading playlist in parallel: {url}')
                download_playlist_parallel(
                    url, folder, browser, self.progress_queue.put, quality,
                    max_concurrent=10, cancel_event=self.single_cancel_event
                )
            else:
                download_video(
                    url, folder, browser, self.progress_queue.put, quality,
                    cancel_event=self.single_cancel_event
                )

            title = url.split('/')[-1][:50]
            self.progress_queue.put(('success', folder, title))
        except DownloadCancelledError:
            logger.info(f'Single download cancelled: {url}')
            self.progress_queue.put(('cancelled', None))
        except Exception as error:
            logger.error(f'Download failed: {error}')
            self.progress_queue.put(('error', error))

    def start_queue_download(self) -> None:
        """Start downloading all items in queue."""
        if not self.download_queue.items:
            messagebox.showwarning('Empty Queue', 'Add URLs to queue first')
            return

        has_pending = any(item.status == DownloadStatus.PENDING for item in self.download_queue.items)
        if not has_pending:
            messagebox.showinfo('Queue', 'No pending items in queue.')
            return

        self.queue_cancel_event.clear()
        self.is_queue_downloading = True
        self.start_queue_button.config(state='disabled')
        self.stop_queue_button.config(state='normal')
        self.add_queue_button.config(state='disabled')
        self.clear_queue_button.config(state='disabled')

        Thread(target=self.queue_download_worker, daemon=True).start()

    def stop_queue_download(self) -> None:
        """Stop processing remaining queue downloads."""
        if self.is_queue_downloading:
            self.queue_cancel_event.set()
            self.stop_queue_button.config(state='disabled')
            logger.info('User requested queue download stop.')

    def queue_download_worker(self) -> None:
        """Worker thread for queue downloads."""
        for item in self.download_queue.items:
            if self.queue_cancel_event.is_set():
                if item.status == DownloadStatus.PENDING:
                    self.download_queue.update_item_status(item, DownloadStatus.CANCELLED)
                continue

            if item.status == DownloadStatus.PENDING:
                self.download_queue.update_item_status(item, DownloadStatus.DOWNLOADING)
                self.progress_queue.put(('queue_update', None))

                try:
                    if is_playlist_url(item.url) and self.parallel_mode.get() == 'on':
                        download_playlist_parallel(
                            item.url, item.folder, item.browser,
                            lambda e: self._handle_queue_progress(item, e),
                            item.quality, max_concurrent=10,
                            cancel_event=self.queue_cancel_event
                        )
                    else:
                        download_video(
                            item.url, item.folder, item.browser,
                            lambda e: self._handle_queue_progress(item, e),
                            item.quality, cancel_event=self.queue_cancel_event
                        )

                    self.download_queue.update_item_status(item, DownloadStatus.COMPLETED)
                    self.history.add_record(item.url, 'Video', item.folder, item.quality)
                except DownloadCancelledError:
                    self.download_queue.update_item_status(item, DownloadStatus.CANCELLED)
                    logger.info(f'Queue item cancelled: {item.url}')
                except Exception as e:
                    self.download_queue.update_item_status(item, DownloadStatus.FAILED, str(e))
                    logger.error(f'Queue download failed: {e}')

                self.progress_queue.put(('queue_update', None))

        self.progress_queue.put(('queue_complete', None))

    def _handle_queue_progress(self, item, event: dict) -> None:
        """Handle progress from queue item download with rate throttling."""
        if isinstance(event, dict) and 'downloaded_bytes' in event:
            total = event.get('total_bytes') or event.get('total_bytes_estimate') or 1
            progress = int((event.get('downloaded_bytes', 0) / total) * 100)
            self.download_queue.update_item_progress(item, progress)

            now = time.time()
            if now - self._last_queue_render_time >= QUEUE_RENDER_THROTTLE_MS / 1000.0:
                self._last_queue_render_time = now
                self.progress_queue.put(('queue_progress', None))

    def update_queue_display(self) -> None:
        """Update the queue listbox display efficiently."""
        self.queue_listbox.delete(0, 'end')
        for idx, item in enumerate(self.download_queue.items, 1):
            status_icon = {
                DownloadStatus.PENDING: '⏳',
                DownloadStatus.DOWNLOADING: '⬇️',
                DownloadStatus.COMPLETED: '✅',
                DownloadStatus.FAILED: '❌',
                DownloadStatus.CANCELLED: '⏹️',
            }.get(item.status, '?')

            display_url = item.url[:55] + '...' if len(item.url) > 55 else item.url
            progress_str = f' ({item.progress}%)' if item.status == DownloadStatus.DOWNLOADING else ''
            self.queue_listbox.insert('end', f'{status_icon} {idx}. {display_url}{progress_str}')

        stats = self.download_queue.get_queue_stats()
        self.queue_stats.set(
            f"Queue: {stats['total']} | Pending: {stats['pending']} | "
            f"Downloading: {stats['downloading']} | Completed: {stats['completed']} | "
            f"Failed: {stats['failed']} | Cancelled: {stats['cancelled']}"
        )

    def process_queue(self) -> None:
        """Process background worker messages."""
        try:
            while True:
                item = self.progress_queue.get_nowait()

                if isinstance(item, tuple):
                    msg_type = item[0]

                    if msg_type in ('queue_update', 'queue_progress'):
                        self.update_queue_display()

                    elif msg_type == 'queue_complete':
                        self.is_queue_downloading = False
                        self.start_queue_button.config(state='normal')
                        self.stop_queue_button.config(state='disabled')
                        self.add_queue_button.config(state='normal')
                        self.clear_queue_button.config(state='normal')
                        self.update_queue_display()
                        messagebox.showinfo('Queue Complete', 'Queue processing finished.')
                        logger.info('Queue download completed.')

                    elif msg_type == 'cancelled':
                        self.is_single_downloading = False
                        self.download_button.config(state='normal')
                        self.cancel_button.config(state='disabled')
                        self.status.set('Download was cancelled.')
                        messagebox.showinfo('Cancelled', 'Download cancelled by user.')

                    elif msg_type == 'error':
                        self.is_single_downloading = False
                        self.download_button.config(state='normal')
                        self.cancel_button.config(state='disabled')
                        self.status.set('Download failed')
                        messagebox.showerror('Download failed', str(item[1]))
                        logger.error(f'Download error: {item[1]}')

                    elif msg_type == 'success':
                        self.is_single_downloading = False
                        folder = item[1]
                        title = item[2] if len(item) > 2 else 'Video'
                        self.history.add_record(self.link.get(), title, folder, self.quality.get())
                        self.download_button.config(state='normal')
                        self.cancel_button.config(state='disabled')
                        self.progress_bar['value'] = 100
                        self.progress_value.set('100%')
                        self.status.set(f'Downloaded successfully to {folder}')
                        messagebox.showinfo('Download complete', f'The video was saved in:\n{folder}')
                        logger.info(f'Download completed: {folder}')

                elif isinstance(item, dict):
                    # Progress hook event dictionary from single download
                    total = item.get('total_bytes') or item.get('total_bytes_estimate') or 0
                    if total:
                        percent = max(0, min(100, item.get('downloaded_bytes', 0) / total * 100))
                        self.progress_bar['value'] = percent
                        self.progress_value.set(f'{int(percent)}%')

        except Empty:
            pass

        self.root.after(PROGRESS_POLL_INTERVAL_MS, self.process_queue)
