"""Unit tests for downloader module with mocked yt-dlp."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from yt_audio_cli.download import DownloadResult, PlaylistEntry


def _create_mock_ydl(
    info: dict[str, Any] | None = None,
    raise_error: Exception | None = None,
) -> MagicMock:
    """Create a mock YoutubeDL instance."""
    mock_ydl = MagicMock()
    mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
    mock_ydl.__exit__ = MagicMock(return_value=False)

    if raise_error:
        mock_ydl.extract_info.side_effect = raise_error
    else:
        mock_ydl.extract_info.return_value = info
        mock_ydl.sanitize_info.return_value = info

    return mock_ydl


class TestDownloadResult:
    """Tests for DownloadResult dataclass."""

    def test_download_result_success(self) -> None:
        """Test creating a successful download result."""
        result = DownloadResult(
            url="https://test.com/video",
            title="Test Video",
            artist="Test Artist",
            temp_path=Path("/tmp/test.mp3"),
            duration=120.0,
            success=True,
            error=None,
        )

        assert result.url == "https://test.com/video"
        assert result.title == "Test Video"
        assert result.artist == "Test Artist"
        assert result.temp_path == Path("/tmp/test.mp3")
        assert result.duration == 120.0
        assert result.success is True
        assert result.error is None

    def test_download_result_failure(self) -> None:
        """Test creating a failed download result."""
        result = DownloadResult(
            url="https://test.com/video",
            title="",
            artist="",
            temp_path=Path(),
            duration=None,
            success=False,
            error="Download failed",
        )

        assert result.success is False
        assert result.error == "Download failed"
        assert result.title == ""


class TestPlaylistEntry:
    """Tests for PlaylistEntry dataclass."""

    def test_playlist_entry(self) -> None:
        """Test creating a playlist entry."""
        entry = PlaylistEntry(url="https://test.com/video", title="Test Video")

        assert entry.url == "https://test.com/video"
        assert entry.title == "Test Video"


class TestDownload:
    """Tests for download() function."""

    def test_download_success(self, temp_dir: Path) -> None:
        """Test successful download."""
        from yt_audio_cli.download.downloader import download

        temp_file = temp_dir / "test123.webm"
        temp_file.touch()

        mock_info = {
            "id": "test123",
            "title": "Test Video",
            "uploader": "Test Channel",
            "duration": 180,
            "ext": "webm",
            "requested_downloads": [{"filepath": str(temp_file)}],
        }

        mock_ydl = _create_mock_ydl(mock_info)

        with patch("yt_audio_cli.download.downloader.YoutubeDL", return_value=mock_ydl):
            result = download(
                "https://youtube.com/watch?v=test123",
                progress_callback=lambda _d, _t: None,
                output_dir=temp_dir,
            )

            assert result.success is True
            assert result.title == "Test Video"
            assert result.artist == "Test Channel"
            assert result.duration == 180
            assert result.temp_path == temp_file

    def test_download_with_channel_fallback(self, temp_dir: Path) -> None:
        """Test download uses channel when uploader is missing."""
        from yt_audio_cli.download.downloader import download

        temp_file = temp_dir / "test123.webm"
        temp_file.touch()

        mock_info = {
            "id": "test123",
            "title": "Test Video",
            "channel": "Test Channel",
            "duration": 180,
            "ext": "webm",
            "requested_downloads": [{"filepath": str(temp_file)}],
        }

        mock_ydl = _create_mock_ydl(mock_info)

        with patch("yt_audio_cli.download.downloader.YoutubeDL", return_value=mock_ydl):
            result = download(
                "https://youtube.com/watch?v=test123",
                progress_callback=lambda _d, _t: None,
                output_dir=temp_dir,
            )

            assert result.artist == "Test Channel"

    def test_download_fallback_path(self, temp_dir: Path) -> None:
        """Test download constructs path when requested_downloads missing."""
        from yt_audio_cli.download.downloader import download

        mock_info = {
            "id": "test123",
            "title": "Test Video",
            "uploader": "Test Channel",
            "duration": 180,
            "ext": "webm",
        }

        mock_ydl = _create_mock_ydl(mock_info)

        with patch("yt_audio_cli.download.downloader.YoutubeDL", return_value=mock_ydl):
            result = download(
                "https://youtube.com/watch?v=test123",
                progress_callback=lambda _d, _t: None,
                output_dir=temp_dir,
            )

            assert result.success is True
            assert result.temp_path == temp_dir / "test123.webm"

    def test_download_failure(self, temp_dir: Path) -> None:
        """Test download failure returns error result."""
        from yt_audio_cli.download.downloader import download

        mock_ydl = _create_mock_ydl(raise_error=Exception("Video unavailable"))

        with patch("yt_audio_cli.download.downloader.YoutubeDL", return_value=mock_ydl):
            result = download(
                "https://youtube.com/watch?v=invalid",
                progress_callback=lambda _d, _t: None,
                output_dir=temp_dir,
            )

            assert result.success is False
            assert result.error is not None
            assert "Video unavailable" in result.error

    def test_download_none_info(self, temp_dir: Path) -> None:
        """Test download handles None info result."""
        from yt_audio_cli.download.downloader import download

        mock_ydl = _create_mock_ydl(info=None)

        with patch("yt_audio_cli.download.downloader.YoutubeDL", return_value=mock_ydl):
            result = download(
                "https://youtube.com/watch?v=test",
                progress_callback=lambda _d, _t: None,
                output_dir=temp_dir,
            )

            assert result.success is False
            assert result.error is not None
            assert "Failed to extract" in result.error

    def test_download_uses_temp_dir_when_none(self) -> None:
        """Test download uses temp directory when output_dir is None."""
        from yt_audio_cli.download.downloader import download

        mock_info = {
            "id": "test123",
            "title": "Test",
            "uploader": "Test",
            "ext": "webm",
        }

        mock_ydl = _create_mock_ydl(mock_info)

        with patch("yt_audio_cli.download.downloader.YoutubeDL", return_value=mock_ydl):
            result = download(
                "https://youtube.com/watch?v=test123",
                progress_callback=lambda _d, _t: None,
                output_dir=None,
            )

            assert result.success is True


class TestExtractPlaylist:
    """Tests for extract_playlist() function."""

    def test_extract_playlist_success(self) -> None:
        """Test successful playlist extraction."""
        from yt_audio_cli.download.downloader import extract_playlist

        mock_info = {
            "entries": [
                {"url": "https://youtube.com/watch?v=video1", "_type": "url"},
                {"url": "https://youtube.com/watch?v=video2", "_type": "url"},
                {"url": "https://youtube.com/watch?v=video3", "_type": "url"},
            ]
        }

        mock_ydl = _create_mock_ydl(mock_info)

        with patch("yt_audio_cli.download.downloader.YoutubeDL", return_value=mock_ydl):
            urls = extract_playlist("https://youtube.com/playlist?list=test")

            assert len(urls) == 3
            assert "video1" in urls[0]
            assert "video2" in urls[1]

    def test_extract_playlist_uses_webpage_url_fallback(self) -> None:
        """Test playlist extraction falls back to webpage_url."""
        from yt_audio_cli.download.downloader import extract_playlist

        mock_info = {
            "entries": [
                {"webpage_url": "https://youtube.com/watch?v=video1"},
            ]
        }

        mock_ydl = _create_mock_ydl(mock_info)

        with patch("yt_audio_cli.download.downloader.YoutubeDL", return_value=mock_ydl):
            urls = extract_playlist("https://youtube.com/playlist?list=test")

            assert len(urls) == 1
            assert "video1" in urls[0]

    def test_extract_playlist_skips_video_type(self) -> None:
        """Test playlist extraction skips video type entries."""
        from yt_audio_cli.download.downloader import extract_playlist

        mock_info = {
            "entries": [
                {"url": "https://youtube.com/watch?v=video1", "_type": "video"},
                {"url": "https://youtube.com/watch?v=video2", "_type": "url"},
            ]
        }

        mock_ydl = _create_mock_ydl(mock_info)

        with patch("yt_audio_cli.download.downloader.YoutubeDL", return_value=mock_ydl):
            urls = extract_playlist("https://youtube.com/playlist?list=test")

            assert len(urls) == 1
            assert "video2" in urls[0]

    def test_extract_playlist_handles_none_entries(self) -> None:
        """Test playlist extraction handles None entries."""
        from yt_audio_cli.download.downloader import extract_playlist

        mock_info = {
            "entries": [
                None,
                {"url": "https://youtube.com/watch?v=video1"},
                None,
            ]
        }

        mock_ydl = _create_mock_ydl(mock_info)

        with patch("yt_audio_cli.download.downloader.YoutubeDL", return_value=mock_ydl):
            urls = extract_playlist("https://youtube.com/playlist?list=test")

            assert len(urls) == 1

    def test_extract_playlist_returns_empty_on_no_entries(self) -> None:
        """Test playlist extraction returns empty when no entries."""
        from yt_audio_cli.download.downloader import extract_playlist

        mock_info = {"title": "Not a playlist"}

        mock_ydl = _create_mock_ydl(mock_info)

        with patch("yt_audio_cli.download.downloader.YoutubeDL", return_value=mock_ydl):
            urls = extract_playlist("https://youtube.com/watch?v=single")

            assert urls == []

    def test_extract_playlist_returns_empty_on_error(self) -> None:
        """Test playlist extraction returns empty on error."""
        from yt_audio_cli.download.downloader import extract_playlist

        mock_ydl = _create_mock_ydl(raise_error=Exception("Network error"))

        with patch("yt_audio_cli.download.downloader.YoutubeDL", return_value=mock_ydl):
            urls = extract_playlist("https://youtube.com/playlist?list=test")

            assert urls == []

    def test_extract_playlist_returns_empty_on_none_info(self) -> None:
        """Test playlist extraction returns empty when info is None."""
        from yt_audio_cli.download.downloader import extract_playlist

        mock_ydl = _create_mock_ydl(info=None)

        with patch("yt_audio_cli.download.downloader.YoutubeDL", return_value=mock_ydl):
            urls = extract_playlist("https://youtube.com/playlist?list=test")

            assert urls == []


class TestExtractPlaylistWithMetadata:
    """Tests for extract_playlist_with_metadata() function."""

    def test_successful_extraction(self) -> None:
        """Test successful extraction with titles."""
        from yt_audio_cli.download.downloader import extract_playlist_with_metadata

        mock_info = {
            "entries": [
                {
                    "url": "https://youtube.com/watch?v=video1",
                    "title": "Video 1 Title",
                    "_type": "url",
                },
                {
                    "url": "https://youtube.com/watch?v=video2",
                    "title": "Video 2 Title",
                    "_type": "url",
                },
            ]
        }

        mock_ydl = _create_mock_ydl(mock_info)

        with patch("yt_audio_cli.download.downloader.YoutubeDL", return_value=mock_ydl):
            result = extract_playlist_with_metadata(
                "https://youtube.com/playlist?list=test"
            )

            assert len(result) == 2
            assert result[0].url == "https://youtube.com/watch?v=video1"
            assert result[0].title == "Video 1 Title"
            assert result[1].title == "Video 2 Title"

    def test_skips_video_type_entries(self) -> None:
        """Test that video type entries are skipped."""
        from yt_audio_cli.download.downloader import extract_playlist_with_metadata

        mock_info = {
            "entries": [
                {
                    "url": "https://youtube.com/watch?v=video1",
                    "title": "Video 1",
                    "_type": "video",
                },
            ]
        }

        mock_ydl = _create_mock_ydl(mock_info)

        with patch("yt_audio_cli.download.downloader.YoutubeDL", return_value=mock_ydl):
            result = extract_playlist_with_metadata(
                "https://youtube.com/playlist?list=test"
            )

            assert len(result) == 0

    def test_uses_webpage_url_fallback(self) -> None:
        """Test fallback to webpage_url when url is missing."""
        from yt_audio_cli.download.downloader import extract_playlist_with_metadata

        mock_info = {
            "entries": [
                {
                    "webpage_url": "https://youtube.com/watch?v=video1",
                    "title": "Video 1",
                    "_type": "url",
                },
            ]
        }

        mock_ydl = _create_mock_ydl(mock_info)

        with patch("yt_audio_cli.download.downloader.YoutubeDL", return_value=mock_ydl):
            result = extract_playlist_with_metadata(
                "https://youtube.com/playlist?list=test"
            )

            assert len(result) == 1
            assert "video1" in result[0].url

    def test_skips_entries_without_url(self) -> None:
        """Test that entries without URL are skipped."""
        from yt_audio_cli.download.downloader import extract_playlist_with_metadata

        mock_info = {
            "entries": [
                {"title": "Video 1", "_type": "url"},
            ]
        }

        mock_ydl = _create_mock_ydl(mock_info)

        with patch("yt_audio_cli.download.downloader.YoutubeDL", return_value=mock_ydl):
            result = extract_playlist_with_metadata(
                "https://youtube.com/playlist?list=test"
            )

            assert len(result) == 0

    def test_handles_error(self) -> None:
        """Test handling of errors."""
        from yt_audio_cli.download.downloader import extract_playlist_with_metadata

        mock_ydl = _create_mock_ydl(raise_error=Exception("Failed"))

        with patch("yt_audio_cli.download.downloader.YoutubeDL", return_value=mock_ydl):
            result = extract_playlist_with_metadata(
                "https://youtube.com/playlist?list=test"
            )

            assert result == []

    def test_handles_none_info(self) -> None:
        """Test handling when info is None."""
        from yt_audio_cli.download.downloader import extract_playlist_with_metadata

        mock_ydl = _create_mock_ydl(info=None)

        with patch("yt_audio_cli.download.downloader.YoutubeDL", return_value=mock_ydl):
            result = extract_playlist_with_metadata(
                "https://youtube.com/playlist?list=test"
            )

            assert result == []

    def test_handles_no_entries(self) -> None:
        """Test handling when no entries in info."""
        from yt_audio_cli.download.downloader import extract_playlist_with_metadata

        mock_info = {"title": "Playlist"}

        mock_ydl = _create_mock_ydl(mock_info)

        with patch("yt_audio_cli.download.downloader.YoutubeDL", return_value=mock_ydl):
            result = extract_playlist_with_metadata(
                "https://youtube.com/playlist?list=test"
            )

            assert result == []

    def test_handles_none_entries(self) -> None:
        """Test that None entries are skipped."""
        from yt_audio_cli.download.downloader import extract_playlist_with_metadata

        mock_info = {
            "entries": [
                None,
                {
                    "url": "https://youtube.com/watch?v=video1",
                    "title": "Video 1",
                    "_type": "url",
                },
                None,
            ]
        }

        mock_ydl = _create_mock_ydl(mock_info)

        with patch("yt_audio_cli.download.downloader.YoutubeDL", return_value=mock_ydl):
            result = extract_playlist_with_metadata(
                "https://youtube.com/playlist?list=test"
            )

            assert len(result) == 1
            assert result[0].title == "Video 1"


class TestExtractMetadata:
    """Tests for extract_metadata() function."""

    def test_extract_metadata_success(self) -> None:
        """Test successful metadata extraction."""
        from yt_audio_cli.download.downloader import extract_metadata

        mock_info = {
            "id": "test123",
            "title": "Test Video",
            "uploader": "Test Channel",
            "duration": 180,
        }

        mock_ydl = _create_mock_ydl(mock_info)

        with patch("yt_audio_cli.download.downloader.YoutubeDL", return_value=mock_ydl):
            result = extract_metadata("https://youtube.com/watch?v=test123")

            assert result is not None
            assert result["title"] == "Test Video"
            assert result["uploader"] == "Test Channel"
            assert result["duration"] == 180

    def test_extract_metadata_failure(self) -> None:
        """Test metadata extraction failure."""
        from yt_audio_cli.download.downloader import extract_metadata

        mock_ydl = _create_mock_ydl(raise_error=Exception("Network error"))

        with patch("yt_audio_cli.download.downloader.YoutubeDL", return_value=mock_ydl):
            result = extract_metadata("https://youtube.com/watch?v=invalid")

            assert result is None

    def test_extract_metadata_none_info(self) -> None:
        """Test metadata extraction when info is None."""
        from yt_audio_cli.download.downloader import extract_metadata

        mock_ydl = _create_mock_ydl(info=None)

        with patch("yt_audio_cli.download.downloader.YoutubeDL", return_value=mock_ydl):
            result = extract_metadata("https://youtube.com/watch?v=test")

            assert result is None


class TestPlaylistDetection:
    """Tests for is_playlist() function."""

    def test_playlist_url_detected(self) -> None:
        """Test playlist URLs are detected correctly."""
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
        result = is_playlist(url)
        assert result is True

    def test_empty_url_returns_false(self) -> None:
        """Test empty URL returns False."""
        from yt_audio_cli.download.downloader import is_playlist

        assert is_playlist("") is False
        assert is_playlist(None) is False  # type: ignore[arg-type]

    def test_non_string_url_returns_false(self) -> None:
        """Test non-string URL returns False."""
        from yt_audio_cli.download.downloader import is_playlist

        assert is_playlist(123) is False  # type: ignore[arg-type]

    def test_url_without_scheme_returns_false(self) -> None:
        """Test URL without scheme returns False."""
        from yt_audio_cli.download.downloader import is_playlist

        assert is_playlist("youtube.com/playlist?list=test") is False

    def test_non_http_scheme_returns_false(self) -> None:
        """Test non-HTTP scheme returns False."""
        from yt_audio_cli.download.downloader import is_playlist

        assert is_playlist("ftp://youtube.com/playlist?list=test") is False

    def test_urlparse_exception_returns_false(self) -> None:
        """Test URL that causes urlparse exception returns False."""
        from yt_audio_cli.download.downloader import is_playlist

        with patch(
            "yt_audio_cli.download.downloader.urlparse",
            side_effect=ValueError("parse error"),
        ):
            assert is_playlist("https://youtube.com/playlist?list=test") is False


class TestProgressHook:
    """Tests for _create_progress_hook() function."""

    def test_progress_hook_calls_callback(self) -> None:
        """Test progress hook calls the callback with correct values."""
        from yt_audio_cli.download.downloader import _create_progress_hook

        progress_values: list[tuple[int, int]] = []

        def callback(downloaded: int, total: int) -> None:
            progress_values.append((downloaded, total))

        hook = _create_progress_hook(callback)

        # Simulate downloading status
        hook({"status": "downloading", "downloaded_bytes": 1024, "total_bytes": 4096})

        assert len(progress_values) == 1
        assert progress_values[0] == (1024, 4096)

    def test_progress_hook_uses_total_bytes_estimate(self) -> None:
        """Test progress hook falls back to total_bytes_estimate."""
        from yt_audio_cli.download.downloader import _create_progress_hook

        progress_values: list[tuple[int, int]] = []

        hook = _create_progress_hook(lambda d, t: progress_values.append((d, t)))

        hook(
            {
                "status": "downloading",
                "downloaded_bytes": 1024,
                "total_bytes_estimate": 4096,
            }
        )

        assert progress_values[0] == (1024, 4096)

    def test_progress_hook_ignores_non_downloading(self) -> None:
        """Test progress hook ignores non-downloading status."""
        from yt_audio_cli.download.downloader import _create_progress_hook

        progress_values: list[tuple[int, int]] = []

        hook = _create_progress_hook(lambda d, t: progress_values.append((d, t)))

        hook({"status": "finished", "downloaded_bytes": 4096, "total_bytes": 4096})

        assert len(progress_values) == 0

    def test_progress_hook_handles_invalid_values(self) -> None:
        """Test progress hook handles invalid byte values."""
        from yt_audio_cli.download.downloader import _create_progress_hook

        progress_values: list[tuple[int, int]] = []

        hook = _create_progress_hook(lambda d, t: progress_values.append((d, t)))

        # Negative values should be replaced with 0
        hook({"status": "downloading", "downloaded_bytes": -100, "total_bytes": -50})

        assert progress_values[0] == (0, 0)


class TestCleanErrorMessage:
    """Tests for _clean_error_message() helper function."""

    def test_extracts_error_after_prefix(self) -> None:
        """Test extracting error after ERROR: prefix."""
        from yt_audio_cli.download.downloader import _clean_error_message

        error = "WARNING: Something\nERROR: Video unavailable"

        result = _clean_error_message(error)

        assert result == "Video unavailable"

    def test_returns_first_line(self) -> None:
        """Test returns first line of multi-line error."""
        from yt_audio_cli.download.downloader import _clean_error_message

        error = "First line\nSecond line\nThird line"

        result = _clean_error_message(error)

        assert result == "First line"

    def test_truncates_long_messages(self) -> None:
        """Test truncates messages over 200 characters."""
        from yt_audio_cli.download.downloader import _clean_error_message

        long_message = "A" * 250

        result = _clean_error_message(long_message)

        assert len(result) == 200
        assert result.endswith("...")

    def test_returns_unknown_for_empty(self) -> None:
        """Test returns 'Unknown error' for empty input."""
        from yt_audio_cli.download.downloader import _clean_error_message

        assert _clean_error_message("") == "Unknown error"
        assert _clean_error_message("   ") == "Unknown error"

    def test_handles_exception_input(self) -> None:
        """Test handling Exception input."""
        from yt_audio_cli.download.downloader import _clean_error_message

        result = _clean_error_message(Exception("Something went wrong"))

        assert result == "Something went wrong"


class TestSafeParseDuration:
    """Tests for _safe_parse_duration() helper function."""

    def test_parses_valid_duration(self) -> None:
        """Test parsing valid duration values."""
        from yt_audio_cli.download.downloader import _safe_parse_duration

        assert _safe_parse_duration(180) == 180.0
        assert _safe_parse_duration(180.5) == 180.5
        assert _safe_parse_duration("180") == 180.0

    def test_returns_none_for_invalid(self) -> None:
        """Test returns None for invalid values."""
        from yt_audio_cli.download.downloader import _safe_parse_duration

        assert _safe_parse_duration(None) is None
        assert _safe_parse_duration("invalid") is None
        assert _safe_parse_duration(-10) is None
        assert _safe_parse_duration(100000) is None  # > 86400
