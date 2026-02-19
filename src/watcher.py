"""
Directory Watcher — Watchdog Integration
Pre-Sprint 3 — Client Requirement

Monitors a directory (default: data/input/) for new document files.
When a file is created (or moved in), it fires a callback with the file path.

Usage:
    from src.watcher import DirectoryWatcher

    def on_new_document(path: str) -> None:
        print(f"New document: {path}")

    watcher = DirectoryWatcher("data/input", callback=on_new_document)
    watcher.start()   # non-blocking (runs in background thread)
    # ... later ...
    watcher.stop()

The watcher is sync-only (Sprint 5 will add async if needed with FastAPI).
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Callable, Optional

from watchdog.events import FileCreatedEvent, FileMovedEvent, FileSystemEventHandler
from watchdog.observers import Observer

logger = logging.getLogger(__name__)

# Supported extensions that the watcher will pick up
WATCHED_EXTENSIONS: frozenset[str] = frozenset({
    ".pdf", ".docx", ".pptx", ".png", ".jpg", ".jpeg", ".tiff", ".tif",
})


class _DocumentHandler(FileSystemEventHandler):
    """Watchdog event handler that filters for supported document types."""

    def __init__(self, callback: Callable[[str], None]) -> None:
        super().__init__()
        self._callback = callback

    def on_created(self, event: FileCreatedEvent) -> None:  # type: ignore[override]
        if event.is_directory:
            return
        self._handle(event.src_path)

    def on_moved(self, event: FileMovedEvent) -> None:  # type: ignore[override]
        if event.is_directory:
            return
        self._handle(event.dest_path)

    def _handle(self, path: str) -> None:
        ext = Path(path).suffix.lower()
        if ext not in WATCHED_EXTENSIONS:
            logger.debug("Ignoring file with unsupported extension: %s", path)
            return
        logger.info("New document detected: %s", path)
        try:
            self._callback(path)
        except Exception:
            logger.exception("Callback failed for %s", path)


class DirectoryWatcher:
    """
    Watches a directory for new document files and invokes a callback.

    Args:
        watch_dir: Directory path to monitor. Created if it doesn't exist.
        callback: Function called with the absolute path of each new file.
        recursive: Whether to watch subdirectories (default False).
    """

    def __init__(
        self,
        watch_dir: str,
        callback: Callable[[str], None],
        recursive: bool = False,
    ) -> None:
        self._watch_dir = os.path.abspath(watch_dir)
        self._callback = callback
        self._recursive = recursive
        self._observer: Optional[Observer] = None

        # Ensure the watch directory exists
        Path(self._watch_dir).mkdir(parents=True, exist_ok=True)

    @property
    def watch_dir(self) -> str:
        """Absolute path of the watched directory."""
        return self._watch_dir

    @property
    def is_running(self) -> bool:
        """True if the observer thread is alive."""
        return self._observer is not None and self._observer.is_alive()

    def start(self) -> None:
        """Start watching in a background thread. Idempotent — safe to call twice."""
        if self.is_running:
            logger.warning("Watcher already running for %s", self._watch_dir)
            return

        handler = _DocumentHandler(self._callback)
        self._observer = Observer()
        self._observer.schedule(handler, self._watch_dir, recursive=self._recursive)
        self._observer.daemon = True
        self._observer.start()
        logger.info(
            "Started watching '%s' (recursive=%s)", self._watch_dir, self._recursive,
        )

    def stop(self, timeout: float = 5.0) -> None:
        """Stop the watcher and wait for the observer thread to finish."""
        if self._observer is None:
            return
        self._observer.stop()
        self._observer.join(timeout=timeout)
        logger.info("Stopped watching '%s'", self._watch_dir)
        self._observer = None
