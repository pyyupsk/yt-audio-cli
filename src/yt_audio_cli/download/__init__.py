"""Download feature - handles yt-dlp interaction for audio downloads."""

from yt_audio_cli.download.batch import BatchDownloader, download_batch
from yt_audio_cli.download.downloader import (
    DownloadResult,
    PlaylistEntry,
    download,
    extract_metadata,
    extract_playlist,
    extract_playlist_with_metadata,
    is_playlist,
)

__all__ = [
    "BatchDownloader",
    "DownloadResult",
    "PlaylistEntry",
    "download",
    "download_batch",
    "extract_metadata",
    "extract_playlist",
    "extract_playlist_with_metadata",
    "is_playlist",
]
