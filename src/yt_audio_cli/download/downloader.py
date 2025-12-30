"""yt-dlp wrapper for video/audio extraction."""

from __future__ import annotations

import contextlib
import json
import logging
import subprocess  # nosec B404
import tempfile
import threading
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import parse_qs, urlparse

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)

# Maximum lines to keep in memory during download progress parsing
MAX_STDOUT_LINES = 1000

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


def extract_playlist_with_metadata(url: str) -> list[PlaylistEntry]:
    """Extract playlist entries with titles (no extra network requests).

    Uses yt-dlp --flat-playlist to get video URLs and titles in one request.
    Much faster than calling extract_metadata() for each video.

    Args:
        url: The playlist URL.

    Returns:
        List of PlaylistEntry with url and title. Empty list if extraction fails.
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

        entries: list[PlaylistEntry] = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            try:
                data = json.loads(line)
                entry_type = data.get("_type", "")

                if entry_type == "video":
                    continue

                # Extract URL
                entry_url = data.get("url") or data.get("webpage_url", "")
                if not entry_url:
                    continue

                # Extract title (available in flat playlist output)
                title = data.get("title", "")

                entries.append(PlaylistEntry(url=entry_url, title=title))
            except json.JSONDecodeError:
                continue

        return entries

    except (subprocess.SubprocessError, FileNotFoundError):
        return []


def extract_metadata(url: str) -> dict | None:
    """Extract video metadata without downloading.

    Args:
        url: The video URL.

    Returns:
        Dictionary with title, uploader/channel, duration, or None if failed.
    """
    cmd = [
        "yt-dlp",
        "--dump-json",
        "--no-download",
        "--no-playlist",
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
            return None

        return json.loads(result.stdout.strip())

    except (subprocess.SubprocessError, FileNotFoundError, json.JSONDecodeError):
        return None


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
            downloaded_raw = data.get("downloaded_bytes", 0) or 0
            total_raw = data.get("total_bytes") or data.get("total_bytes_estimate") or 0

            try:
                downloaded = int(downloaded_raw)
                total = int(total_raw)
            except (ValueError, TypeError, OverflowError):
                return None

            if downloaded < 0 or downloaded > MAX_FILE_SIZE:
                downloaded = 0
            if total < 0 or total > MAX_FILE_SIZE:
                total = 0

            return (downloaded, total)
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
        duration=None,
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
    """Extract clean error message from stderr.

    Standardizes error message extraction to show only the first relevant line.
    """
    if not stderr or not stderr.strip():
        return "Unknown error"

    error_msg = stderr.strip()

    if "ERROR:" in error_msg:
        error_msg = error_msg.split("ERROR:")[-1].strip()

    first_line = error_msg.split("\n")[0].strip()

    if len(first_line) > 200:
        first_line = first_line[:197] + "..."

    return first_line if first_line else "Unknown error"


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
        "--progress",
        "--newline",
        "--progress-template",
        "download:%(progress)j",
        url,
    ]


def _read_stderr(process: subprocess.Popen[str], stderr_lines: list[str]) -> None:
    """Read stderr in a separate thread to prevent deadlock.

    Args:
        process: The subprocess with stderr pipe.
        stderr_lines: List to collect stderr lines (modified in place).
    """
    if not process.stderr:
        return
    for line in process.stderr:
        stderr_lines.append(line)


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


def _log_stderr_warnings(stderr: str) -> None:
    """Log any warnings from stderr output."""
    if not stderr.strip():
        return
    for line in stderr.strip().split("\n"):
        if "WARNING:" in line:
            logger.warning("yt-dlp: %s", line.split("WARNING:")[-1].strip())


def _build_success_result(
    url: str, json_output: dict, output_dir: Path
) -> DownloadResult:
    """Build a successful download result from parsed metadata."""
    return DownloadResult(
        url=url,
        title=json_output.get("title", "Unknown"),
        artist=json_output.get("uploader", json_output.get("channel", "Unknown")),
        temp_path=_extract_file_path(json_output, output_dir),
        duration=_safe_parse_duration(json_output.get("duration")),
        success=True,
        error=None,
    )


def _run_yt_dlp(
    cmd: list[str],
    progress_callback: Callable[[int, int], None],
    output_dir: Path,
) -> DownloadResult:
    """Run yt-dlp subprocess and return download result."""
    with subprocess.Popen(  # nosec B603
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    ) as process:
        stderr_lines: list[str] = []
        stderr_thread = threading.Thread(
            target=_read_stderr, args=(process, stderr_lines), daemon=True
        )
        stderr_thread.start()

        stdout_lines, json_output = _process_stdout(process, progress_callback)

        process.wait()
        stderr_thread.join(timeout=5.0)

        stderr = "".join(stderr_lines)

        if process.returncode != 0:
            return _create_error_result(cmd[-1], _clean_error_message(stderr))

        _log_stderr_warnings(stderr)

        if json_output is None:
            json_output = _find_metadata_in_lines(list(stdout_lines))

        if json_output is None:
            return _create_error_result(cmd[-1], "Failed to parse yt-dlp output")

        return _build_success_result(cmd[-1], json_output, output_dir)


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
        return _run_yt_dlp(cmd, progress_callback, output_dir)
    except FileNotFoundError:
        return _create_error_result(url, "yt-dlp not found. Please install yt-dlp.")
    except subprocess.SubprocessError as e:
        return _create_error_result(url, str(e))


def _process_stdout(
    process: subprocess.Popen[str],
    progress_callback: Callable[[int, int], None],
) -> tuple[deque[str], dict | None]:
    """Process stdout from yt-dlp, calling progress callback and collecting output.

    Uses a bounded deque to prevent unbounded memory growth.

    Returns:
        Tuple of (collected_lines, json_metadata_if_found).
    """
    stdout_lines: deque[str] = deque(maxlen=MAX_STDOUT_LINES)
    json_output: dict | None = None

    if not process.stdout:
        return stdout_lines, json_output

    while True:
        line = process.stdout.readline()
        if not line:
            break

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
