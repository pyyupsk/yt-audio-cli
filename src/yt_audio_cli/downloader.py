"""yt-dlp wrapper for video/audio extraction."""

from __future__ import annotations

import json
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import parse_qs, urlparse

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass
class DownloadResult:
    """Result of a download operation.

    Attributes:
        url: The original URL that was downloaded.
        title: The video title.
        artist: The video artist/channel name.
        temp_path: Path to the downloaded temporary file.
        success: Whether the download succeeded.
        error: Error message if download failed.
    """

    url: str
    title: str
    artist: str
    temp_path: Path
    success: bool
    error: str | None = None


def is_playlist(url: str) -> bool:
    """Check if URL is a playlist.

    Args:
        url: The URL to check.

    Returns:
        True if URL appears to be a playlist, False otherwise.
    """
    parsed = urlparse(url)
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


def extract_playlist(url: str) -> list[str]:
    """Extract individual video URLs from a playlist.

    Uses yt-dlp --flat-playlist to get video URLs without downloading.

    Args:
        url: The playlist URL.

    Returns:
        List of video URLs in the playlist. Empty list if not a playlist
        or if extraction fails.
    """
    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--dump-json",
        url,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            return []

        # Each line is a JSON object for a video in the playlist
        urls: list[str] = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            try:
                data = json.loads(line)
                # Check if this is a playlist entry (has _type=url or url field)
                # Single videos have _type=video and no url field for extraction
                entry_type = data.get("_type", "")

                # Skip if this is a single video (not a playlist entry)
                if entry_type == "video":
                    continue

                # Extract URL from playlist entry
                if "url" in data:
                    urls.append(data["url"])
                elif "webpage_url" in data:
                    urls.append(data["webpage_url"])
            except json.JSONDecodeError:
                continue

        return urls

    except (subprocess.SubprocessError, FileNotFoundError):
        return []


def download(
    url: str,
    progress_callback: Callable[[int, int], None],  # noqa: ARG001
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
    # Use temp directory if not specified
    if output_dir is None:
        output_dir = Path(tempfile.gettempdir())

    # Output template for yt-dlp
    output_template = str(output_dir / "%(id)s.%(ext)s")

    cmd = [
        "yt-dlp",
        "--extract-audio",
        "--audio-format",
        "best",
        "--audio-quality",
        "0",
        "--output",
        output_template,
        "--print-json",
        "--no-playlist",  # Download single video even if in playlist context
        "--progress",
        "--newline",  # Progress on separate lines for parsing
        url,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            error_msg = result.stderr.strip() if result.stderr else "Unknown error"
            # Clean up error message
            if "ERROR:" in error_msg:
                error_msg = error_msg.split("ERROR:")[-1].strip()
            return DownloadResult(
                url=url,
                title="",
                artist="",
                temp_path=Path(),
                success=False,
                error=error_msg,
            )

        # Parse JSON output from yt-dlp
        json_output = None
        for line in result.stdout.strip().split("\n"):
            if line.startswith("{"):
                try:
                    json_output = json.loads(line)
                    break
                except json.JSONDecodeError:
                    continue

        if json_output is None:
            return DownloadResult(
                url=url,
                title="",
                artist="",
                temp_path=Path(),
                success=False,
                error="Failed to parse yt-dlp output",
            )

        # Extract metadata
        title = json_output.get("title", "Unknown")
        artist = json_output.get("uploader", json_output.get("channel", "Unknown"))

        # Get the downloaded file path
        if json_output.get("requested_downloads"):
            temp_path = Path(json_output["requested_downloads"][0]["filepath"])
        else:
            # Fallback: construct path from template
            video_id = json_output.get("id", "unknown")
            ext = json_output.get("ext", "webm")
            temp_path = output_dir / f"{video_id}.{ext}"

        return DownloadResult(
            url=url,
            title=title,
            artist=artist,
            temp_path=temp_path,
            success=True,
            error=None,
        )

    except FileNotFoundError:
        return DownloadResult(
            url=url,
            title="",
            artist="",
            temp_path=Path(),
            success=False,
            error="yt-dlp not found. Please install yt-dlp.",
        )
    except subprocess.SubprocessError as e:
        return DownloadResult(
            url=url,
            title="",
            artist="",
            temp_path=Path(),
            success=False,
            error=str(e),
        )
