"""FFmpeg wrapper for audio transcoding."""

from __future__ import annotations

import logging
import shutil
import subprocess  # nosec B404
from pathlib import Path
from typing import TYPE_CHECKING

from yt_audio_cli.core import ConversionError, FFmpegNotFoundError

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)

# Maximum reasonable duration for progress tracking (24 hours in seconds)
MAX_DURATION_SECONDS = 86400

# Codec mapping for audio formats
_CODEC_MAP = {
    "mp3": "libmp3lame",
    "aac": "aac",
    "opus": "libopus",
    "wav": "pcm_s16le",
}

# FFmpeg format mapping (used with -f flag)
_FORMAT_MAP = {
    "mp3": "mp3",
    "aac": "adts",
    "opus": "opus",
    "wav": "wav",
}


def check_ffmpeg() -> bool:
    """Check if FFmpeg is available on PATH.

    Returns:
        True if FFmpeg is available, False otherwise.
    """
    return shutil.which("ffmpeg") is not None


def _process_ffmpeg_progress(
    process: subprocess.Popen[str],
    callback: Callable[[float], None],
) -> None:
    """Parse FFmpeg progress output and invoke callback.

    FFmpeg outputs progress in key=value format when using -progress pipe:1.
    The out_time_ms field contains the processed time in microseconds.

    Args:
        process: The FFmpeg subprocess with stdout pipe.
        callback: Callback function that receives processed time in seconds.
    """
    if not process.stdout:
        return

    for line in process.stdout:
        line = line.strip()
        if line.startswith("out_time_ms="):
            try:
                microseconds = int(line.split("=")[1])
                if microseconds < 0:
                    continue
                seconds = microseconds / 1_000_000
                if seconds > MAX_DURATION_SECONDS:
                    continue
                callback(seconds)
            except (ValueError, IndexError, OverflowError):
                pass


def _build_ffmpeg_command(
    input_path: Path,
    output_path: Path,
    audio_format: str,
    bitrate: int | None,
    metadata: dict[str, str] | None,
    with_progress: bool,
) -> list[str]:
    """Build FFmpeg command for transcoding."""
    cmd = ["ffmpeg", "-y"]

    if with_progress:
        cmd.extend(["-progress", "pipe:1", "-nostats"])

    cmd.extend(["-i", str(input_path)])

    codec = _CODEC_MAP.get(audio_format)
    if codec:
        cmd.extend(["-c:a", codec])

    if bitrate and audio_format != "wav":
        cmd.extend(["-b:a", f"{bitrate}k"])

    output_format = _FORMAT_MAP.get(audio_format)
    if output_format:
        cmd.extend(["-f", output_format])

    if metadata:
        for key, value in metadata.items():
            if value:
                cmd.extend(["-metadata", f"{key}={value}"])
            else:
                logger.debug("Skipping empty metadata field: %s", key)

    cmd.append(str(output_path))
    return cmd


def _run_with_progress(
    cmd: list[str],
    input_path: Path,
    callback: Callable[[float], None],
) -> None:
    """Run FFmpeg with progress callback."""
    with subprocess.Popen(  # nosec B603
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ) as process:
        _process_ffmpeg_progress(process, callback)
        process.wait()
        stderr = process.stderr.read() if process.stderr else ""
        if process.returncode != 0:
            raise ConversionError(str(input_path), stderr or "Unknown error")


def _run_without_progress(cmd: list[str], input_path: Path) -> None:
    """Run FFmpeg without progress callback."""
    result = subprocess.run(  # nosec B603
        cmd,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise ConversionError(str(input_path), result.stderr or "Unknown error")


def transcode(
    input_path: Path,
    output_path: Path,
    audio_format: str,
    bitrate: int | None = None,
    embed_metadata: bool = True,
    metadata: dict[str, str] | None = None,
    progress_callback: Callable[[float], None] | None = None,
) -> bool:
    """Transcode audio file via FFmpeg.

    Args:
        input_path: Path to the input audio file.
        output_path: Path for the output audio file.
        audio_format: Target audio format (mp3, aac, opus, wav).
        bitrate: Target bitrate in kbps. None for default/lossless.
        embed_metadata: Whether to embed metadata in the output file.
        metadata: Dictionary of metadata tags (title, artist, etc.).
        progress_callback: Optional callback for progress updates.
            Takes processed_seconds (float) as argument.

    Returns:
        True if transcoding succeeded.

    Raises:
        FFmpegNotFoundError: If FFmpeg is not installed.
        ConversionError: If transcoding fails.
    """
    if not check_ffmpeg():
        raise FFmpegNotFoundError

    effective_metadata = metadata if embed_metadata else None
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = _build_ffmpeg_command(
        input_path=input_path,
        output_path=output_path,
        audio_format=audio_format,
        bitrate=bitrate,
        metadata=effective_metadata,
        with_progress=progress_callback is not None,
    )

    try:
        if progress_callback:
            _run_with_progress(cmd, input_path, progress_callback)
        else:
            _run_without_progress(cmd, input_path)
        return True

    except FileNotFoundError as e:
        raise FFmpegNotFoundError from e
    except subprocess.SubprocessError as e:
        raise ConversionError(str(input_path), str(e)) from e
