"""Core utilities - errors and filename handling."""

from yt_audio_cli.core.errors import (
    ConversionError,
    DownloadError,
    FFmpegNotFoundError,
    format_error,
)
from yt_audio_cli.core.filename import resolve_conflict, sanitize

__all__ = [
    "ConversionError",
    "DownloadError",
    "FFmpegNotFoundError",
    "format_error",
    "resolve_conflict",
    "sanitize",
]
