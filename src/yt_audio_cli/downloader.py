"""yt-dlp wrapper for video/audio extraction."""

from __future__ import annotations

import contextlib
import json
import subprocess  # nosec B404
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
        result = subprocess.run(  # nosec B603
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


def _parse_progress_line(line: str) -> tuple[int, int] | None:
    """Parse a yt-dlp progress line.

    Args:
        line: A line of output from yt-dlp.

    Returns:
        Tuple of (downloaded_bytes, total_bytes) or None if not a progress line.
    """
    if not line.startswith("{"):
        return None
    try:
        data = json.loads(line)
        if "downloaded_bytes" in data:
            downloaded = data.get("downloaded_bytes", 0) or 0
            total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
            return (int(downloaded), int(total))
    except (ValueError, TypeError):
        pass
    return None


def _create_error_result(url: str, error: str) -> DownloadResult:
    """Create a failed download result."""
    return DownloadResult(
        url=url,
        title="",
        artist="",
        temp_path=Path(),
        success=False,
        error=error,
    )


def _parse_metadata_line(line: str) -> dict | None:
    """Parse a line as JSON metadata if it contains video info."""
    if line.startswith("{") and '"id"' in line:
        with contextlib.suppress(json.JSONDecodeError):
            return json.loads(line)
    return None


def _find_metadata_in_lines(lines: list[str]) -> dict | None:
    """Search collected lines for JSON metadata."""
    for line in lines:
        metadata = _parse_metadata_line(line)
        if metadata:
            return metadata
    return None


def _extract_file_path(metadata: dict, output_dir: Path) -> Path:
    """Extract file path from yt-dlp metadata."""
    if metadata.get("requested_downloads"):
        return Path(metadata["requested_downloads"][0]["filepath"])
    # Fallback: construct path from template
    video_id = metadata.get("id", "unknown")
    ext = metadata.get("ext", "webm")
    return output_dir / f"{video_id}.{ext}"


def _clean_error_message(stderr: str) -> str:
    """Extract clean error message from stderr."""
    error_msg = stderr.strip() if stderr else "Unknown error"
    if "ERROR:" in error_msg:
        error_msg = error_msg.split("ERROR:")[-1].strip()
    return error_msg


def _build_yt_dlp_command(url: str, output_template: str) -> list[str]:
    """Build yt-dlp command for audio download."""
    return [
        "yt-dlp",
        "-f",
        "bestaudio/best",  # Download best audio stream, fallback to best
        "--output",
        output_template,
        "--print-json",
        "--no-playlist",
        "--newline",
        "--progress-template",
        "%(progress)j",
        url,
    ]


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

    output_template = str(output_dir / "%(id)s.%(ext)s")
    cmd = _build_yt_dlp_command(url, output_template)

    try:
        with subprocess.Popen(  # nosec B603
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        ) as process:
            stdout_lines, json_output = _process_stdout(process, progress_callback)

            process.wait()
            stderr = process.stderr.read() if process.stderr else ""

            if process.returncode != 0:
                return _create_error_result(url, _clean_error_message(stderr))

            if json_output is None:
                json_output = _find_metadata_in_lines(stdout_lines)

            if json_output is None:
                return _create_error_result(url, "Failed to parse yt-dlp output")

            return DownloadResult(
                url=url,
                title=json_output.get("title", "Unknown"),
                artist=json_output.get(
                    "uploader", json_output.get("channel", "Unknown")
                ),
                temp_path=_extract_file_path(json_output, output_dir),
                success=True,
                error=None,
            )

    except FileNotFoundError:
        return _create_error_result(url, "yt-dlp not found. Please install yt-dlp.")
    except subprocess.SubprocessError as e:
        return _create_error_result(url, str(e))


def _process_stdout(
    process: subprocess.Popen[str],
    progress_callback: Callable[[int, int], None],
) -> tuple[list[str], dict | None]:
    """Process stdout from yt-dlp, calling progress callback and collecting output.

    Returns:
        Tuple of (collected_lines, json_metadata_if_found).
    """
    stdout_lines: list[str] = []
    json_output: dict | None = None

    if not process.stdout:
        return stdout_lines, json_output

    for line in process.stdout:
        line = line.strip()
        if not line:
            continue

        stdout_lines.append(line)

        progress = _parse_progress_line(line)
        if progress:
            progress_callback(progress[0], progress[1])
        elif json_output is None:
            json_output = _parse_metadata_line(line)

    return stdout_lines, json_output
