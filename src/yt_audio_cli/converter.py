"""FFmpeg wrapper for audio transcoding."""

from __future__ import annotations

import shutil
import subprocess  # nosec B404
from pathlib import Path
from typing import TYPE_CHECKING

from yt_audio_cli.errors import ConversionError, FFmpegNotFoundError

if TYPE_CHECKING:
    from collections.abc import Callable


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
                if microseconds >= 0:
                    seconds = microseconds / 1_000_000
                    callback(seconds)
            except (ValueError, IndexError):
                pass


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

    cmd = ["ffmpeg", "-y"]

    if progress_callback:
        cmd.extend(["-progress", "pipe:1", "-nostats"])

    cmd.extend(["-i", str(input_path)])

    # Add codec based on format
    codec_map = {
        "mp3": "libmp3lame",
        "aac": "aac",
        "opus": "libopus",
        "wav": "pcm_s16le",
    }

    codec = codec_map.get(audio_format)
    if codec:
        cmd.extend(["-c:a", codec])

    # Add bitrate if specified (not applicable to WAV)
    if bitrate and audio_format != "wav":
        cmd.extend(["-b:a", f"{bitrate}k"])

    # Add metadata if embedding is enabled
    if embed_metadata and metadata:
        for key, value in metadata.items():
            if value:
                cmd.extend(["-metadata", f"{key}={value}"])

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd.append(str(output_path))

    try:
        if progress_callback:
            with subprocess.Popen(  # nosec B603
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            ) as process:
                _process_ffmpeg_progress(process, progress_callback)
                process.wait()
                stderr = process.stderr.read() if process.stderr else ""
                if process.returncode != 0:
                    raise ConversionError(str(input_path), stderr or "Unknown error")
        else:
            result = subprocess.run(  # nosec B603
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                raise ConversionError(str(input_path), result.stderr or "Unknown error")

        return True

    except FileNotFoundError as e:
        raise FFmpegNotFoundError from e
    except subprocess.SubprocessError as e:
        raise ConversionError(str(input_path), str(e)) from e
