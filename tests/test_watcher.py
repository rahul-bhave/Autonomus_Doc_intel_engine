"""
Pre-Sprint 3 — Directory watcher tests.

Tests for src/watcher.py covering:
- DirectoryWatcher lifecycle (start/stop)
- Callback invocation on file creation
- Extension filtering (only WATCHED_EXTENSIONS)
- Ignoring directories and unsupported file types
- Idempotent start/stop

Run:  PYTHONPATH=. .venv/Scripts/pytest tests/test_watcher.py -v
"""

import os
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.watcher import DirectoryWatcher, WATCHED_EXTENSIONS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _wait_for_call(mock: MagicMock, timeout: float = 3.0, interval: float = 0.1) -> bool:
    """Poll until mock is called or timeout is reached."""
    elapsed = 0.0
    while elapsed < timeout:
        if mock.call_count > 0:
            return True
        time.sleep(interval)
        elapsed += interval
    return False


# ---------------------------------------------------------------------------
# Lifecycle tests
# ---------------------------------------------------------------------------


class TestWatcherLifecycle:
    """Tests for watcher start/stop behaviour."""

    def test_creates_watch_directory(self, tmp_path):
        """Watcher creates the watch directory if it doesn't exist."""
        watch_dir = str(tmp_path / "nonexistent" / "dir")
        watcher = DirectoryWatcher(watch_dir, callback=lambda p: None)
        assert Path(watch_dir).exists()

    def test_start_sets_running(self, tmp_path):
        watcher = DirectoryWatcher(str(tmp_path), callback=lambda p: None)
        assert not watcher.is_running
        watcher.start()
        assert watcher.is_running
        watcher.stop()

    def test_stop_clears_running(self, tmp_path):
        watcher = DirectoryWatcher(str(tmp_path), callback=lambda p: None)
        watcher.start()
        watcher.stop()
        assert not watcher.is_running

    def test_double_start_is_safe(self, tmp_path):
        """Starting twice doesn't create duplicate observers."""
        watcher = DirectoryWatcher(str(tmp_path), callback=lambda p: None)
        watcher.start()
        watcher.start()  # Should not raise
        assert watcher.is_running
        watcher.stop()

    def test_double_stop_is_safe(self, tmp_path):
        """Stopping a non-running watcher is a no-op."""
        watcher = DirectoryWatcher(str(tmp_path), callback=lambda p: None)
        watcher.stop()  # Should not raise

    def test_watch_dir_property(self, tmp_path):
        watcher = DirectoryWatcher(str(tmp_path), callback=lambda p: None)
        assert watcher.watch_dir == str(tmp_path)


# ---------------------------------------------------------------------------
# File detection tests
# ---------------------------------------------------------------------------


class TestFileDetection:
    """Tests for callback invocation on new file creation."""

    def test_pdf_triggers_callback(self, tmp_path):
        callback = MagicMock()
        watcher = DirectoryWatcher(str(tmp_path), callback=callback)
        watcher.start()
        try:
            # Give observer time to start
            time.sleep(0.3)
            test_file = tmp_path / "test.pdf"
            test_file.write_bytes(b"%PDF-1.4 test content")
            assert _wait_for_call(callback), "Callback was not invoked for .pdf"
            callback.assert_called_once()
            called_path = callback.call_args[0][0]
            assert called_path.endswith("test.pdf")
        finally:
            watcher.stop()

    def test_docx_triggers_callback(self, tmp_path):
        callback = MagicMock()
        watcher = DirectoryWatcher(str(tmp_path), callback=callback)
        watcher.start()
        try:
            time.sleep(0.3)
            test_file = tmp_path / "doc.docx"
            test_file.write_bytes(b"PK fake docx")
            assert _wait_for_call(callback), "Callback was not invoked for .docx"
            callback.assert_called_once()
        finally:
            watcher.stop()

    def test_unsupported_extension_ignored(self, tmp_path):
        callback = MagicMock()
        watcher = DirectoryWatcher(str(tmp_path), callback=callback)
        watcher.start()
        try:
            time.sleep(0.3)
            test_file = tmp_path / "readme.txt"
            test_file.write_text("hello")
            time.sleep(1.0)
            callback.assert_not_called()
        finally:
            watcher.stop()

    def test_exe_ignored(self, tmp_path):
        callback = MagicMock()
        watcher = DirectoryWatcher(str(tmp_path), callback=callback)
        watcher.start()
        try:
            time.sleep(0.3)
            test_file = tmp_path / "malware.exe"
            test_file.write_bytes(b"MZ\x90\x00")
            time.sleep(1.0)
            callback.assert_not_called()
        finally:
            watcher.stop()

    def test_multiple_files_trigger_multiple_callbacks(self, tmp_path):
        callback = MagicMock()
        watcher = DirectoryWatcher(str(tmp_path), callback=callback)
        watcher.start()
        try:
            time.sleep(0.3)
            for i in range(3):
                (tmp_path / f"doc_{i}.pdf").write_bytes(b"%PDF test")
                time.sleep(0.3)
            # Wait for all callbacks
            elapsed = 0.0
            while elapsed < 5.0:
                if callback.call_count >= 3:
                    break
                time.sleep(0.2)
                elapsed += 0.2
            assert callback.call_count >= 3
        finally:
            watcher.stop()


# ---------------------------------------------------------------------------
# Extension coverage tests
# ---------------------------------------------------------------------------


class TestWatchedExtensions:
    """Verify all WATCHED_EXTENSIONS are the expected set."""

    def test_expected_extensions(self):
        expected = {".pdf", ".docx", ".pptx", ".png", ".jpg", ".jpeg", ".tiff", ".tif"}
        assert WATCHED_EXTENSIONS == expected

    def test_each_supported_extension_triggers(self, tmp_path):
        """Each extension in WATCHED_EXTENSIONS should trigger the callback."""
        for ext in WATCHED_EXTENSIONS:
            callback = MagicMock()
            watcher = DirectoryWatcher(str(tmp_path), callback=callback)
            watcher.start()
            try:
                time.sleep(0.3)
                test_file = tmp_path / f"test_file{ext}"
                test_file.write_bytes(b"test content bytes")
                triggered = _wait_for_call(callback, timeout=3.0)
                assert triggered, f"Callback not invoked for extension {ext}"
            finally:
                watcher.stop()
            # Clean up for next iteration
            if test_file.exists():
                test_file.unlink()


# ---------------------------------------------------------------------------
# Error handling tests
# ---------------------------------------------------------------------------


class TestCallbackErrorHandling:
    """Verify watcher survives callback exceptions."""

    def test_callback_exception_does_not_crash_watcher(self, tmp_path):
        """If the callback raises, the watcher keeps running."""
        call_count = {"n": 0}

        def failing_callback(path: str) -> None:
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise ValueError("Simulated error")

        watcher = DirectoryWatcher(str(tmp_path), callback=failing_callback)
        watcher.start()
        try:
            time.sleep(0.3)
            # First file triggers exception
            (tmp_path / "file1.pdf").write_bytes(b"%PDF first")
            time.sleep(1.0)
            # Second file should still be picked up
            (tmp_path / "file2.pdf").write_bytes(b"%PDF second")
            time.sleep(1.0)
            assert call_count["n"] >= 2, "Watcher stopped after callback exception"
            assert watcher.is_running
        finally:
            watcher.stop()
