"""Download feature - handles yt-dlp interaction for audio downloads."""

from yt_audio_cli.download.downloader import (
    DownloadResult,
    download,
    extract_metadata,
    extract_playlist,
    is_playlist,
)

__all__ = [
    "DownloadResult",
    "download",
    "extract_metadata",
    "extract_playlist",
    "is_playlist",
]
