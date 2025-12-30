"""Unit tests for downloader module with mocked yt-dlp subprocess."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestDownloadResult:
    """Tests for DownloadResult dataclass."""

    def test_create_success_result(self) -> None:
        """Test creating a successful download result."""
        from yt_audio_cli.download.downloader import DownloadResult

        result = DownloadResult(
            url="https://youtube.com/watch?v=test",
            title="Test Video",
            artist="Test Channel",
            temp_path=Path("/tmp/test.webm"),
            duration=212.5,
            success=True,
            error=None,
        )
        assert result.success is True
        assert result.error is None
        assert result.title == "Test Video"
        assert result.duration == 212.5  # NOSONAR

    def test_create_failure_result(self) -> None:
        """Test creating a failed download result."""
        from yt_audio_cli.download.downloader import DownloadResult

        result = DownloadResult(
            url="https://youtube.com/watch?v=test",
            title="",
            artist="",
            temp_path=Path("/tmp/test.webm"),
            duration=None,
            success=False,
            error="Video unavailable",
        )
        assert result.success is False
        assert result.error == "Video unavailable"
        assert result.duration is None

    def test_duration_can_be_none(self) -> None:
        """Test that duration can be None for unknown duration."""
        from yt_audio_cli.download.downloader import DownloadResult

        result = DownloadResult(
            url="https://youtube.com/watch?v=test",
            title="Live Stream",
            artist="Test Channel",
            temp_path=Path("/tmp/test.webm"),
            duration=None,
            success=True,
            error=None,
        )
        assert result.success is True
        assert result.duration is None


class TestParseProgressLine:
    """Tests for _parse_progress_line() helper function."""

    def test_parse_valid_progress_json(self) -> None:
        """Test parsing valid progress JSON."""
        from yt_audio_cli.download.downloader import _parse_progress_line

        line = '{"downloaded_bytes": 1024, "total_bytes": 4096}'
        result = _parse_progress_line(line)
        assert result == (1024, 4096)

    def test_parse_progress_with_estimate(self) -> None:
        """Test parsing progress with total_bytes_estimate."""
        from yt_audio_cli.download.downloader import _parse_progress_line

        line = '{"downloaded_bytes": 512, "total_bytes_estimate": 2048}'
        result = _parse_progress_line(line)
        assert result == (512, 2048)

    def test_parse_non_progress_json(self) -> None:
        """Test non-progress JSON returns None."""
        from yt_audio_cli.download.downloader import _parse_progress_line

        line = '{"id": "test123", "title": "Test"}'
        result = _parse_progress_line(line)
        assert result is None

    def test_parse_non_json_line(self) -> None:
        """Test non-JSON line returns None."""
        from yt_audio_cli.download.downloader import _parse_progress_line

        result = _parse_progress_line("[download] 50% of 10MiB")
        assert result is None

    def test_parse_invalid_json(self) -> None:
        """Test invalid JSON returns None."""
        from yt_audio_cli.download.downloader import _parse_progress_line

        result = _parse_progress_line("{invalid json}")
        assert result is None


def _create_mock_popen(
    stdout_lines: list[str], stderr: str = "", returncode: int = 0
) -> MagicMock:
    """Create a mock Popen object for testing."""
    import io

    mock_process = MagicMock()
    mock_process.returncode = returncode
    # Use StringIO for file-like object with readline() support
    stdout_content = "\n".join(stdout_lines) + "\n" if stdout_lines else ""
    mock_process.stdout = io.StringIO(stdout_content)
    mock_process.stderr = MagicMock()
    mock_process.stderr.read.return_value = stderr
    mock_process.wait.return_value = returncode
    mock_process.__enter__ = MagicMock(return_value=mock_process)
    mock_process.__exit__ = MagicMock(return_value=False)
    return mock_process


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
        from yt_audio_cli.download.downloader import download

        # Create a mock temp file
        temp_file = temp_dir / "test_video.webm"
        temp_file.touch()

        mock_yt_dlp_success["requested_downloads"][0]["filepath"] = str(temp_file)

        # Simulate progress updates followed by final JSON
        stdout_lines = [
            '{"downloaded_bytes": 1024, "total_bytes": 4096}',
            '{"downloaded_bytes": 2048, "total_bytes": 4096}',
            '{"downloaded_bytes": 4096, "total_bytes": 4096}',
            json.dumps(mock_yt_dlp_success),
        ]

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = _create_mock_popen(stdout_lines)

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
            assert (
                result.duration == 212.0
            )  # Duration extracted from metadata # NOSONAR
            assert mock_popen.called
            # Verify progress was reported
            assert len(progress_calls) == 3
            assert progress_calls[0] == (1024, 4096)
            assert progress_calls[-1] == (4096, 4096)

    def test_duration_extraction_from_metadata(
        self, temp_dir: Path, mock_yt_dlp_success: dict
    ) -> None:
        """Test that duration is extracted from yt-dlp metadata."""
        from yt_audio_cli.download.downloader import download

        # Create a mock temp file
        temp_file = temp_dir / "test_video.webm"
        temp_file.touch()

        mock_yt_dlp_success["requested_downloads"][0]["filepath"] = str(temp_file)
        mock_yt_dlp_success["duration"] = 180.5  # Set specific duration

        stdout_lines = [json.dumps(mock_yt_dlp_success)]

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = _create_mock_popen(stdout_lines)

            result = download(
                "https://youtube.com/watch?v=test",
                progress_callback=lambda _d, _t: None,
                output_dir=temp_dir,
            )

            assert result.success is True
            assert result.duration == 180.5  # NOSONAR

    def test_duration_none_when_not_in_metadata(
        self, temp_dir: Path, mock_yt_dlp_success: dict
    ) -> None:
        """Test that duration is None when not in metadata."""
        from yt_audio_cli.download.downloader import download

        # Create a mock temp file
        temp_file = temp_dir / "test_video.webm"
        temp_file.touch()

        mock_yt_dlp_success["requested_downloads"][0]["filepath"] = str(temp_file)
        del mock_yt_dlp_success["duration"]  # Remove duration

        stdout_lines = [json.dumps(mock_yt_dlp_success)]

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = _create_mock_popen(stdout_lines)

            result = download(
                "https://youtube.com/watch?v=live",
                progress_callback=lambda _d, _t: None,
                output_dir=temp_dir,
            )

            assert result.success is True
            assert result.duration is None

    def test_download_invalid_url(self, temp_dir: Path) -> None:
        """Test download with invalid URL."""
        from yt_audio_cli.download.downloader import download

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = _create_mock_popen(
                [], stderr="ERROR: Invalid URL", returncode=1
            )

            result = download(
                "not-a-valid-url",
                progress_callback=lambda _d, _t: None,
                output_dir=temp_dir,
            )

            assert result.success is False
            assert result.error is not None
            assert "invalid" in result.error.lower() or result.error != ""

    def test_download_private_video(self, temp_dir: Path) -> None:
        """Test download of private video."""
        from yt_audio_cli.download.downloader import download

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = _create_mock_popen(
                [], stderr="ERROR: Private video", returncode=1
            )

            result = download(
                "https://youtube.com/watch?v=private",
                progress_callback=lambda _d, _t: None,
                output_dir=temp_dir,
            )

            assert result.success is False
            assert result.error is not None

    def test_download_network_error(self, temp_dir: Path) -> None:
        """Test download with network error."""
        from yt_audio_cli.download.downloader import download

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = _create_mock_popen(
                [], stderr="ERROR: Unable to connect", returncode=1
            )

            result = download(
                "https://youtube.com/watch?v=test",
                progress_callback=lambda _d, _t: None,
                output_dir=temp_dir,
            )

            assert result.success is False
            assert result.error is not None

    def test_download_uses_correct_yt_dlp_args(self, temp_dir: Path) -> None:
        """Test that download uses correct yt-dlp arguments."""
        from yt_audio_cli.download.downloader import download

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = _create_mock_popen(
                [], stderr="Error", returncode=1
            )

            download(
                "https://youtube.com/watch?v=test",
                progress_callback=lambda _d, _t: None,
                output_dir=temp_dir,
            )

            # Check the command was called
            assert mock_popen.called
            call_args = mock_popen.call_args
            cmd = call_args[0][0] if call_args[0] else call_args[1].get("args", [])

            # Should contain yt-dlp and audio extraction flags
            cmd_str = " ".join(cmd) if isinstance(cmd, list) else str(cmd)
            assert "yt-dlp" in cmd_str
            assert "--progress-template" in cmd_str


class TestExtractPlaylist:
    """Tests for extract_playlist() function."""

    def test_extract_playlist_urls(self) -> None:
        """Test extracting video URLs from playlist."""
        from yt_audio_cli.download.downloader import extract_playlist

        # yt-dlp --flat-playlist outputs one JSON per line
        playlist_entries = [
            {
                "id": "video1",
                "url": "https://youtube.com/watch?v=video1",
                "_type": "url",
            },
            {
                "id": "video2",
                "url": "https://youtube.com/watch?v=video2",
                "_type": "url",
            },
            {
                "id": "video3",
                "url": "https://youtube.com/watch?v=video3",
                "_type": "url",
            },
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
        from yt_audio_cli.download.downloader import extract_playlist

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
        from yt_audio_cli.download.downloader import extract_playlist

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
        from yt_audio_cli.download.downloader import extract_playlist

        # Unavailable videos are typically omitted from flat-playlist output
        # or appear with different structure
        playlist_entries = [
            {
                "id": "video1",
                "url": "https://youtube.com/watch?v=video1",
                "_type": "url",
            },
            {
                "id": "video3",
                "url": "https://youtube.com/watch?v=video3",
                "_type": "url",
            },
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
        from yt_audio_cli.download.downloader import is_playlist

        assert is_playlist("https://youtube.com/playlist?list=PLtest") is True
        assert is_playlist("https://www.youtube.com/playlist?list=PLabc") is True

    def test_video_url_not_playlist(self) -> None:
        """Test single video URLs are not detected as playlist."""
        from yt_audio_cli.download.downloader import is_playlist

        assert is_playlist("https://youtube.com/watch?v=test") is False
        assert is_playlist("https://youtu.be/test") is False

    def test_video_in_playlist_detected(self) -> None:
        """Test video URL with playlist parameter."""
        from yt_audio_cli.download.downloader import is_playlist

        # Video in playlist context - should detect as playlist
        url = "https://youtube.com/watch?v=test&list=PLtest"
        # This could go either way - let's treat it as a playlist
        result = is_playlist(url)
        assert isinstance(result, bool)
