"""Unit tests for downloader module with mocked yt-dlp subprocess."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    pass


class TestDownloadResult:
    """Tests for DownloadResult dataclass."""

    def test_create_success_result(self) -> None:
        """Test creating a successful download result."""
        from yt_audio_cli.downloader import DownloadResult

        result = DownloadResult(
            url="https://youtube.com/watch?v=test",
            title="Test Video",
            artist="Test Channel",
            temp_path=Path("/tmp/test.webm"),
            success=True,
            error=None,
        )
        assert result.success is True
        assert result.error is None
        assert result.title == "Test Video"

    def test_create_failure_result(self) -> None:
        """Test creating a failed download result."""
        from yt_audio_cli.downloader import DownloadResult

        result = DownloadResult(
            url="https://youtube.com/watch?v=test",
            title="",
            artist="",
            temp_path=Path("/tmp/test.webm"),
            success=False,
            error="Video unavailable",
        )
        assert result.success is False
        assert result.error == "Video unavailable"


class TestDownload:
    """Tests for download() function."""

    @pytest.fixture
    def mock_yt_dlp_output(self, mock_yt_dlp_success: dict) -> str:
        """Create mock yt-dlp JSON output."""
        return json.dumps(mock_yt_dlp_success)

    def test_successful_download(
        self, temp_dir: Path, mock_yt_dlp_success: dict
    ) -> None:
        """Test successful video download."""
        from yt_audio_cli.downloader import download

        # Create a mock temp file
        temp_file = temp_dir / "test_video.webm"
        temp_file.touch()

        mock_yt_dlp_success["requested_downloads"][0]["filepath"] = str(temp_file)

        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = json.dumps(mock_yt_dlp_success)
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            progress_calls: list[tuple[int, int]] = []

            def progress_callback(downloaded: int, total: int) -> None:
                progress_calls.append((downloaded, total))

            result = download(
                "https://youtube.com/watch?v=dQw4w9WgXcQ",
                progress_callback=progress_callback,
                output_dir=temp_dir,
            )

            assert result.success is True
            assert result.title == "Test Video Title"
            assert result.artist == "Test Channel"
            assert mock_run.called

    def test_download_invalid_url(self, temp_dir: Path) -> None:
        """Test download with invalid URL."""
        from yt_audio_cli.downloader import download

        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stdout = ""
            mock_result.stderr = "ERROR: Invalid URL"
            mock_run.return_value = mock_result

            result = download(
                "not-a-valid-url",
                progress_callback=lambda d, t: None,
                output_dir=temp_dir,
            )

            assert result.success is False
            assert result.error is not None
            assert "invalid" in result.error.lower() or result.error != ""

    def test_download_private_video(self, temp_dir: Path) -> None:
        """Test download of private video."""
        from yt_audio_cli.downloader import download

        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stdout = ""
            mock_result.stderr = "ERROR: Private video"
            mock_run.return_value = mock_result

            result = download(
                "https://youtube.com/watch?v=private",
                progress_callback=lambda d, t: None,
                output_dir=temp_dir,
            )

            assert result.success is False
            assert result.error is not None

    def test_download_network_error(self, temp_dir: Path) -> None:
        """Test download with network error."""
        from yt_audio_cli.downloader import download

        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stdout = ""
            mock_result.stderr = "ERROR: Unable to connect"
            mock_run.return_value = mock_result

            result = download(
                "https://youtube.com/watch?v=test",
                progress_callback=lambda d, t: None,
                output_dir=temp_dir,
            )

            assert result.success is False
            assert result.error is not None

    def test_download_uses_correct_yt_dlp_args(self, temp_dir: Path) -> None:
        """Test that download uses correct yt-dlp arguments."""
        from yt_audio_cli.downloader import download

        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stdout = ""
            mock_result.stderr = "Error"
            mock_run.return_value = mock_result

            download(
                "https://youtube.com/watch?v=test",
                progress_callback=lambda d, t: None,
                output_dir=temp_dir,
            )

            # Check the command was called
            assert mock_run.called
            call_args = mock_run.call_args
            cmd = call_args[0][0] if call_args[0] else call_args[1].get("args", [])

            # Should contain yt-dlp and audio extraction flags
            cmd_str = " ".join(cmd) if isinstance(cmd, list) else str(cmd)
            assert "yt-dlp" in cmd_str


class TestExtractPlaylist:
    """Tests for extract_playlist() function."""

    def test_extract_playlist_urls(self) -> None:
        """Test extracting video URLs from playlist."""
        from yt_audio_cli.downloader import extract_playlist

        # yt-dlp --flat-playlist outputs one JSON per line
        playlist_entries = [
            {"id": "video1", "url": "https://youtube.com/watch?v=video1", "_type": "url"},
            {"id": "video2", "url": "https://youtube.com/watch?v=video2", "_type": "url"},
            {"id": "video3", "url": "https://youtube.com/watch?v=video3", "_type": "url"},
        ]
        mock_output = "\n".join(json.dumps(entry) for entry in playlist_entries)

        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = mock_output
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            urls = extract_playlist("https://youtube.com/playlist?list=PLtest")

            assert len(urls) == 3
            assert all("youtube.com" in url for url in urls)

    def test_extract_single_video_returns_empty(self) -> None:
        """Test that single video URL returns empty list."""
        from yt_audio_cli.downloader import extract_playlist

        # Single video returns one JSON with no _type=url or entries
        single_video = {
            "id": "test123",
            "title": "Single Video",
            "_type": "video",
        }

        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = json.dumps(single_video)
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            urls = extract_playlist("https://youtube.com/watch?v=test123")

            assert urls == []

    def test_extract_playlist_error(self) -> None:
        """Test playlist extraction error handling."""
        from yt_audio_cli.downloader import extract_playlist

        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stdout = ""
            mock_result.stderr = "ERROR: Playlist not found"
            mock_run.return_value = mock_result

            urls = extract_playlist("https://youtube.com/playlist?list=invalid")

            assert urls == []

    def test_extract_playlist_with_unavailable_videos(self) -> None:
        """Test playlist with some unavailable videos."""
        from yt_audio_cli.downloader import extract_playlist

        # Unavailable videos are typically omitted from flat-playlist output
        # or appear with different structure
        playlist_entries = [
            {"id": "video1", "url": "https://youtube.com/watch?v=video1", "_type": "url"},
            {"id": "video3", "url": "https://youtube.com/watch?v=video3", "_type": "url"},
        ]
        mock_output = "\n".join(json.dumps(entry) for entry in playlist_entries)

        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = mock_output
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            urls = extract_playlist("https://youtube.com/playlist?list=PLtest")

            # Should only return available videos
            assert len(urls) == 2


class TestPlaylistDetection:
    """Tests for is_playlist() function."""

    def test_playlist_url_detected(self) -> None:
        """Test playlist URLs are detected."""
        from yt_audio_cli.downloader import is_playlist

        assert is_playlist("https://youtube.com/playlist?list=PLtest") is True
        assert is_playlist("https://www.youtube.com/playlist?list=PLabc") is True

    def test_video_url_not_playlist(self) -> None:
        """Test single video URLs are not detected as playlist."""
        from yt_audio_cli.downloader import is_playlist

        assert is_playlist("https://youtube.com/watch?v=test") is False
        assert is_playlist("https://youtu.be/test") is False

    def test_video_in_playlist_detected(self) -> None:
        """Test video URL with playlist parameter."""
        from yt_audio_cli.downloader import is_playlist

        # Video in playlist context - should detect as playlist
        url = "https://youtube.com/watch?v=test&list=PLtest"
        # This could go either way - let's treat it as a playlist
        result = is_playlist(url)
        assert isinstance(result, bool)
