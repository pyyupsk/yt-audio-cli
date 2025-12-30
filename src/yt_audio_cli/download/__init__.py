"""Download feature - handles yt-dlp interaction for audio downloads."""

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
    "DownloadResult",
    "PlaylistEntry",
    "download",
    "extract_metadata",
    "extract_playlist",
    "extract_playlist_with_metadata",
    "is_playlist",
]
