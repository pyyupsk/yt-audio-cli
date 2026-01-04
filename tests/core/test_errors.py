"""Unit tests for error formatting."""

from __future__ import annotations

from yt_audio_cli.core import (
    ConversionError,
    DownloadError,
    FFmpegNotFoundError,
    format_error,
)
from yt_audio_cli.core.errors import BatchError, RetryExhaustedError


class TestDownloadError:
    """Tests for DownloadError exception."""

    def test_message_format(self) -> None:
        """Test error message contains URL and message."""
        error = DownloadError("https://example.com/video", "Connection refused")
        assert "https://example.com/video" in str(error)
        assert "Connection refused" in str(error)

    def test_attributes(self) -> None:
        """Test error attributes are set correctly."""
        error = DownloadError("https://test.com", "Test message")
        assert error.url == "https://test.com"
        assert error.message == "Test message"


class TestConversionError:
    """Tests for ConversionError exception."""

    def test_message_format(self) -> None:
        """Test error message contains input path and message."""
        error = ConversionError("/tmp/video.webm", "Invalid codec")
        assert "/tmp/video.webm" in str(error)
        assert "Invalid codec" in str(error)

    def test_attributes(self) -> None:
        """Test error attributes are set correctly."""
        error = ConversionError("/path/to/file", "Error details")
        assert error.input_path == "/path/to/file"
        assert error.message == "Error details"


class TestFFmpegNotFoundError:
    """Tests for FFmpegNotFoundError exception."""

    def test_message_contains_install_url(self) -> None:
        """Test error message contains installation URL."""
        error = FFmpegNotFoundError()
        assert "ffmpeg.org" in str(error).lower()


class TestFormatError:
    """Tests for format_error() function."""

    def test_download_error_private(self) -> None:
        """Test formatting of private video error."""
        error = DownloadError("url", "Video is private")
        result = format_error(error)
        assert "private" in result.lower()

    def test_download_error_unavailable(self) -> None:
        """Test formatting of unavailable video error."""
        error = DownloadError("url", "Video unavailable")
        result = format_error(error)
        assert "unavailable" in result.lower()

    def test_download_error_network(self) -> None:
        """Test formatting of network error."""
        error = DownloadError("url", "Network connection failed")
        result = format_error(error)
        assert "network" in result.lower() or "connection" in result.lower()

    def test_download_error_generic(self) -> None:
        """Test formatting of generic download error."""
        error = DownloadError("url", "Unknown error")
        result = format_error(error)
        assert "download failed" in result.lower()

    def test_conversion_error(self) -> None:
        """Test formatting of conversion error."""
        error = ConversionError("/path", "Codec error")
        result = format_error(error)
        assert "conversion" in result.lower()
        assert "ffmpeg" in result.lower()

    def test_ffmpeg_not_found(self) -> None:
        """Test formatting of FFmpeg not found error."""
        error = FFmpegNotFoundError()
        result = format_error(error)
        assert "ffmpeg" in result.lower()

    def test_file_not_found(self) -> None:
        """Test formatting of file not found error."""
        error = FileNotFoundError("test.mp3")
        result = format_error(error)
        assert "not found" in result.lower()

    def test_permission_error(self) -> None:
        """Test formatting of permission error."""
        error = PermissionError("Access denied")
        result = format_error(error)
        assert "permission" in result.lower()

    def test_disk_full_error(self) -> None:
        """Test formatting of disk full error."""
        error = OSError("No space left on device")
        result = format_error(error)
        assert "disk space" in result.lower()

    def test_generic_os_error(self) -> None:
        """Test formatting of generic OS error."""
        error = OSError("Some OS error")
        result = format_error(error)
        assert "system error" in result.lower()

    def test_unknown_error(self) -> None:
        """Test formatting of unknown error type."""
        error = ValueError("Some value error")
        result = format_error(error)
        assert "unexpected" in result.lower()

    def test_batch_error_with_failed_count(self) -> None:
        """Test formatting of batch error with failed count."""
        error = BatchError("Batch failed", failed_count=5)
        result = format_error(error)
        assert "batch" in result.lower()
        assert "5" in result

    def test_batch_error_without_failed_count(self) -> None:
        """Test formatting of batch error without failed count."""
        error = BatchError("Batch failed", failed_count=0)
        result = format_error(error)
        assert "batch" in result.lower()

    def test_retry_exhausted_error(self) -> None:
        """Test formatting of retry exhausted error."""
        error = RetryExhaustedError(
            url="https://example.com",
            attempts=3,
            last_error="Connection timeout",
        )
        result = format_error(error)
        assert "retry" in result.lower() or "exhausted" in result.lower()
        assert "3" in result


class TestBatchError:
    """Tests for BatchError exception."""

    def test_message_format(self) -> None:
        """Test error message is set correctly."""
        error = BatchError("Test batch error", failed_count=3)
        assert "Test batch error" in str(error)

    def test_attributes(self) -> None:
        """Test error attributes are set correctly."""
        error = BatchError("Batch failed", failed_count=5)
        assert error.message == "Batch failed"
        assert error.failed_count == 5

    def test_default_failed_count(self) -> None:
        """Test default failed count is zero."""
        error = BatchError("Error")
        assert error.failed_count == 0


class TestRetryExhaustedError:
    """Tests for RetryExhaustedError exception."""

    def test_message_format(self) -> None:
        """Test error message contains all details."""
        error = RetryExhaustedError(
            url="https://example.com/video",
            attempts=5,
            last_error="Network timeout",
        )
        assert "https://example.com/video" in str(error)
        assert "5" in str(error)
        assert "Network timeout" in str(error)

    def test_attributes(self) -> None:
        """Test error attributes are set correctly."""
        error = RetryExhaustedError(
            url="https://test.com",
            attempts=3,
            last_error="Connection refused",
        )
        assert error.url == "https://test.com"
        assert error.attempts == 3
        assert error.last_error == "Connection refused"
