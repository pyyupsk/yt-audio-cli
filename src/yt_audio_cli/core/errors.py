"""Custom exceptions and error formatting for yt-audio-cli."""

from __future__ import annotations


class DownloadError(Exception):
    """Raised when download fails."""

    def __init__(self, url: str, message: str) -> None:
        """Initialize DownloadError.

        Args:
            url: The URL that failed to download.
            message: Description of the error.
        """
        self.url = url
        self.message = message
        super().__init__(f"Failed to download {url}: {message}")


class ConversionError(Exception):
    """Raised when FFmpeg transcoding fails."""

    def __init__(self, input_path: str, message: str) -> None:
        """Initialize ConversionError.

        Args:
            input_path: Path to the input file that failed to convert.
            message: Description of the error.
        """
        self.input_path = input_path
        self.message = message
        super().__init__(f"Failed to convert {input_path}: {message}")


class FFmpegNotFoundError(Exception):
    """Raised when FFmpeg is not installed."""

    def __init__(self) -> None:
        """Initialize FFmpegNotFoundError."""
        super().__init__(
            "FFmpeg not found. Install FFmpeg: https://ffmpeg.org/download.html"
        )


class BatchError(Exception):
    """Raised when batch processing fails."""

    def __init__(self, message: str, failed_count: int = 0) -> None:
        """Initialize BatchError.

        Args:
            message: Description of the error.
            failed_count: Number of failed jobs in the batch.
        """
        self.message = message
        self.failed_count = failed_count
        super().__init__(message)


class RetryExhaustedError(Exception):
    """Raised when all retry attempts have been exhausted."""

    def __init__(self, url: str, attempts: int, last_error: str) -> None:
        """Initialize RetryExhaustedError.

        Args:
            url: The URL that failed after retries.
            attempts: Number of attempts made.
            last_error: The last error message before giving up.
        """
        self.url = url
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(f"Failed after {attempts} attempts: {url} - {last_error}")


def format_error(error: Exception) -> str:
    """Format error for user display with actionable suggestion.

    Args:
        error: The exception to format.

    Returns:
        Human-readable error message with suggestion.
    """
    if isinstance(error, DownloadError):
        if "private" in error.message.lower():
            return f"Cannot access video: {error.message}. The video may be private or age-restricted."
        if "unavailable" in error.message.lower():
            return f"Video unavailable: {error.message}. Check if the URL is correct."
        if "network" in error.message.lower() or "connection" in error.message.lower():
            return f"Network error: {error.message}. Check your internet connection and retry."
        return f"Download failed: {error.message}"

    if isinstance(error, ConversionError):
        return (
            f"Conversion failed: {error.message}. Ensure FFmpeg is properly installed."
        )

    if isinstance(error, FFmpegNotFoundError):
        return str(error)

    if isinstance(error, FileNotFoundError):
        return f"File not found: {error}. Check that the path exists."

    if isinstance(error, PermissionError):
        return f"Permission denied: {error}. Check file permissions."

    if isinstance(error, OSError):
        if "No space left" in str(error):
            return "Insufficient disk space. Free up space and retry."
        return f"System error: {error}"

    if isinstance(error, BatchError):
        if error.failed_count > 0:
            return f"Batch processing failed: {error.message} ({error.failed_count} failed)"
        return f"Batch processing failed: {error.message}"

    if isinstance(error, RetryExhaustedError):
        return f"Retry exhausted for {error.url}: {error.last_error} (after {error.attempts} attempts)"

    return f"Unexpected error: {error}"
