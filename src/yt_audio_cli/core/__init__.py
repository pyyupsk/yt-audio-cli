"""Core utilities - errors and filename handling."""

from yt_audio_cli.core.errors import (
    BatchError,
    ConversionError,
    DownloadError,
    FFmpegNotFoundError,
    RetryExhaustedError,
    format_error,
)
from yt_audio_cli.core.filename import resolve_conflict, sanitize

__all__ = [
    "BatchError",
    "ConversionError",
    "DownloadError",
    "FFmpegNotFoundError",
    "RetryExhaustedError",
    "format_error",
    "resolve_conflict",
    "sanitize",
]
