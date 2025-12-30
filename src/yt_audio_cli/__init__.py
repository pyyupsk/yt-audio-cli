"""YouTube Audio CLI - Download audio from video URLs."""

from yt_audio_cli.errors import ConversionError, DownloadError, FFmpegNotFoundError

__version__ = "0.1.0"
__all__ = [
    "__version__",
    "ConversionError",
    "DownloadError",
    "FFmpegNotFoundError",
]
