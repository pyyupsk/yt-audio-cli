"""yt-dlp wrapper for video/audio extraction."""

from __future__ import annotations

import logging
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast
from urllib.parse import parse_qs, urlparse

from yt_dlp import YoutubeDL

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)

# Maximum reasonable file size (10TB) for validation
MAX_FILE_SIZE = 10 * 1024 * 1024 * 1024 * 1024


@dataclass
class DownloadResult:
    """Result of a download operation.

    Attributes:
        url: The original URL that was downloaded.
        title: The video title.
        artist: The video artist/channel name.
        temp_path: Path to the downloaded temporary file.
        duration: Media duration in seconds (None if unavailable).
        success: Whether the download succeeded.
        error: Error message if download failed.
    """

    url: str
    title: str
    artist: str
    temp_path: Path
    duration: float | None
    success: bool
    error: str | None = None


@dataclass
class PlaylistEntry:
    """Entry from a playlist extraction.

    Attributes:
        url: The video URL.
        title: The video title (may be empty if unavailable).
    """

    url: str
    title: str


def is_playlist(url: str) -> bool:
    """Check if URL is a playlist.

    Args:
        url: The URL to check.

    Returns:
        True if URL appears to be a playlist, False otherwise.
    """
    if not url or not isinstance(url, str):
        return False

    try:
        parsed = urlparse(url)
    except (ValueError, AttributeError):
        return False

    if not parsed.scheme or not parsed.netloc:
        return False

    if parsed.scheme.lower() not in ("http", "https"):
        return False

    query_params = parse_qs(parsed.query)

    # Check for playlist parameter
    if "list" in query_params:
        # If it's just a list parameter without a video, it's a playlist
        if "v" not in query_params:
            return True
        # If both v and list are present, treat as playlist
        return True

    # Check for /playlist path
    return "/playlist" in parsed.path


def _create_progress_hook(
    callback: Callable[[int, int], None],
) -> Callable[[dict[str, Any]], None]:
    """Create a yt-dlp progress hook that wraps our callback.

    Args:
        callback: Function taking (downloaded_bytes, total_bytes).

    Returns:
        A yt-dlp compatible progress hook function.
    """

    def hook(d: dict[str, Any]) -> None:
        if d.get("status") == "downloading":
            downloaded = d.get("downloaded_bytes", 0) or 0
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0

            # Validate ranges
            if downloaded < 0 or downloaded > MAX_FILE_SIZE:
                downloaded = 0
            if total < 0 or total > MAX_FILE_SIZE:
                total = 0

            callback(int(downloaded), int(total))

    return hook


def _create_error_result(url: str, error: str) -> DownloadResult:
    """Create a failed download result."""
    return DownloadResult(
        url=url,
        title="",
        artist="",
        temp_path=Path(),
        duration=None,
        success=False,
        error=error,
    )


def _safe_parse_duration(duration_value: float | int | str | None) -> float | None:
    """Safely parse duration value to float.

    Args:
        duration_value: The duration value from yt-dlp output.

    Returns:
        Duration as float, or None if parsing fails.
    """
    if duration_value is None:
        return None
    try:
        result = float(duration_value)
        if result < 0 or result > 86400:
            return None
        return result
    except (ValueError, TypeError, OverflowError):
        return None


def _clean_error_message(error: str | Exception) -> str:
    """Extract clean error message.

    Standardizes error message extraction to show only the first relevant line.
    """
    error_str = str(error)
    if not error_str or not error_str.strip():
        return "Unknown error"

    error_msg = error_str.strip()

    if "ERROR:" in error_msg:
        error_msg = error_msg.split("ERROR:")[-1].strip()

    first_line = error_msg.split("\n")[0].strip()

    if len(first_line) > 200:
        first_line = first_line[:197] + "..."

    return first_line if first_line else "Unknown error"


def _get_base_ydl_opts() -> dict[str, Any]:
    """Get base YoutubeDL options."""
    return {
        "quiet": True,
        "no_warnings": True,
        "no_color": True,
    }


def extract_playlist(url: str) -> list[str]:
    """Extract individual video URLs from a playlist.

    Uses yt-dlp flat playlist extraction to get video URLs without downloading.

    Args:
        url: The playlist URL.

    Returns:
        List of video URLs in the playlist. Empty list if not a playlist
        or if extraction fails.
    """
    ydl_opts = {
        **_get_base_ydl_opts(),
        "extract_flat": "in_playlist",
        "skip_download": True,
    }

    try:
        with YoutubeDL(cast(Any, ydl_opts)) as ydl:
            info = ydl.extract_info(url, download=False)

            if info is None:
                return []

            # Check if it's a playlist with entries
            entries = info.get("entries")
            if entries is None:
                return []

            urls: list[str] = []
            for entry in entries:
                if entry is None:
                    continue

                # Skip single video results
                if entry.get("_type") == "video":
                    continue

                # Extract URL from entry
                entry_url = entry.get("url") or entry.get("webpage_url", "")
                if entry_url:
                    urls.append(entry_url)

            return urls

    except Exception:
        return []


def extract_playlist_with_metadata(url: str) -> list[PlaylistEntry]:
    """Extract playlist entries with titles (no extra network requests).

    Uses yt-dlp flat playlist extraction to get video URLs and titles in one request.
    Much faster than calling extract_metadata() for each video.

    Args:
        url: The playlist URL.

    Returns:
        List of PlaylistEntry with url and title. Empty list if extraction fails.
    """
    ydl_opts = {
        **_get_base_ydl_opts(),
        "extract_flat": "in_playlist",
        "skip_download": True,
    }

    try:
        with YoutubeDL(cast(Any, ydl_opts)) as ydl:
            info = ydl.extract_info(url, download=False)

            if info is None:
                return []

            entries = info.get("entries")
            if entries is None:
                return []

            result: list[PlaylistEntry] = []
            for entry in entries:
                if entry is None:
                    continue

                if entry.get("_type") == "video":
                    continue

                entry_url = entry.get("url") or entry.get("webpage_url", "")
                if not entry_url:
                    continue

                title = entry.get("title", "")
                result.append(PlaylistEntry(url=entry_url, title=title))

            return result

    except Exception:
        return []


def extract_metadata(url: str) -> dict[str, Any] | None:
    """Extract video metadata without downloading.

    Args:
        url: The video URL.

    Returns:
        Dictionary with title, uploader/channel, duration, or None if failed.
    """
    ydl_opts = {
        **_get_base_ydl_opts(),
        "skip_download": True,
        "noplaylist": True,
    }

    try:
        with YoutubeDL(cast(Any, ydl_opts)) as ydl:
            info = ydl.extract_info(url, download=False)

            if info is None:
                return None

            return cast(dict[str, Any], ydl.sanitize_info(info))

    except Exception:
        return None


def download(
    url: str,
    progress_callback: Callable[[int, int], None],
    output_dir: Path | None = None,
) -> DownloadResult:
    """Download audio from URL using yt-dlp.

    Downloads the best audio stream and returns metadata.

    Args:
        url: The video URL to download.
        progress_callback: Callback function for progress updates.
            Takes (downloaded_bytes, total_bytes) as arguments.
        output_dir: Directory for temporary output. Uses system temp if None.

    Returns:
        DownloadResult with download status and metadata.
    """
    if output_dir is None:
        output_dir = Path(tempfile.gettempdir())

    ydl_opts = {
        **_get_base_ydl_opts(),
        "format": "bestaudio/best",
        "outtmpl": str(output_dir / "%(id)s.%(ext)s"),
        "noplaylist": True,
        "progress_hooks": [_create_progress_hook(progress_callback)],
    }

    try:
        with YoutubeDL(cast(Any, ydl_opts)) as ydl:
            raw_info = ydl.extract_info(url, download=True)

            if raw_info is None:
                return _create_error_result(url, "Failed to extract video info")

            info = cast(dict[str, Any], ydl.sanitize_info(raw_info))

            # Get the downloaded file path with defensive checks
            temp_path: Path | None = None
            requested_downloads = info.get("requested_downloads")

            if isinstance(requested_downloads, list) and len(requested_downloads) > 0:
                first_download = requested_downloads[0]
                if isinstance(first_download, dict):
                    filepath = first_download.get("filepath")
                    if filepath and isinstance(filepath, str):
                        temp_path = Path(filepath)

            # Fallback: construct path from template
            if temp_path is None:
                video_id = str(info.get("id", "unknown"))
                ext = str(info.get("ext", "webm"))
                temp_path = output_dir / f"{video_id}.{ext}"

            return DownloadResult(
                url=url,
                title=str(info.get("title", "Unknown")),
                artist=str(info.get("uploader") or info.get("channel") or "Unknown"),
                temp_path=temp_path,
                duration=_safe_parse_duration(info.get("duration")),
                success=True,
                error=None,
            )

    except Exception as e:
        return _create_error_result(url, _clean_error_message(e))
