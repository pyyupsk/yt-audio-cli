"""Shared pytest fixtures for yt-audio-cli tests."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test outputs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_yt_dlp_success() -> dict:
    """Mock yt-dlp JSON output for a successful download."""
    return {
        "id": "dQw4w9WgXcQ",
        "title": "Test Video Title",
        "uploader": "Test Channel",
        "duration": 212,
        "ext": "webm",
        "requested_downloads": [
            {
                "filepath": "/tmp/test_video.webm",
            }
        ],
    }


@pytest.fixture
def mock_yt_dlp_playlist() -> dict:
    """Mock yt-dlp JSON output for a playlist."""
    return {
        "_type": "playlist",
        "id": "PLtest123",
        "title": "Test Playlist",
        "entries": [
            {"id": "video1", "title": "Video 1", "url": "https://youtube.com/watch?v=video1"},
            {"id": "video2", "title": "Video 2", "url": "https://youtube.com/watch?v=video2"},
            {"id": "video3", "title": "Video 3", "url": "https://youtube.com/watch?v=video3"},
        ],
    }


@pytest.fixture
def mock_subprocess_success() -> MagicMock:
    """Mock subprocess.run for successful command execution."""
    mock = MagicMock()
    mock.returncode = 0
    mock.stdout = ""
    mock.stderr = ""
    return mock


@pytest.fixture
def mock_subprocess_failure() -> MagicMock:
    """Mock subprocess.run for failed command execution."""
    mock = MagicMock()
    mock.returncode = 1
    mock.stdout = ""
    mock.stderr = "Error: Command failed"
    return mock
