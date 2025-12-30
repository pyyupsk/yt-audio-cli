"""CLI implementation for yt-audio-cli."""

from __future__ import annotations

import contextlib
import tempfile
from pathlib import Path
from typing import Annotated

import typer

from yt_audio_cli import __version__
from yt_audio_cli.convert import check_ffmpeg, transcode
from yt_audio_cli.core import (
    FFmpegNotFoundError,
    format_error,
    resolve_conflict,
    sanitize,
)
from yt_audio_cli.download import (
    DownloadResult,
    PlaylistEntry,
    download,
    extract_metadata,
    extract_playlist_with_metadata,
    is_playlist,
)
from yt_audio_cli.ui import (
    create_conversion_progress,
    create_download_progress,
    print_error,
    print_info,
    print_success,
    print_warning,
)

# Valid audio formats
VALID_FORMATS = {"mp3", "aac", "opus", "wav"}

# Quality presets mapping format to bitrate
QUALITY_PRESETS = {
    "best": {"mp3": 320, "aac": 256, "opus": 192, "wav": None},
    "good": {"mp3": 192, "aac": 160, "opus": 128, "wav": None},
    "small": {"mp3": 128, "aac": 96, "opus": 64, "wav": None},
}

# Create Typer app
app = typer.Typer(
    name="yt-audio-cli",
    help="A simple command-line tool for downloading audio from YouTube and other sites.",
    add_completion=False,
    no_args_is_help=True,
)


def validate_format(value: str) -> str:
    """Validate and normalize audio format.

    Args:
        value: The format string to validate.

    Returns:
        Normalized format string (lowercase).

    Raises:
        typer.BadParameter: If format is not valid.
    """
    normalized = value.lower()
    if normalized not in VALID_FORMATS:
        raise typer.BadParameter(
            f"Invalid format '{value}'. Valid formats: {', '.join(sorted(VALID_FORMATS))}"
        )
    return normalized


def resolve_quality(
    quality: str | None,
    bitrate: int | None,
    audio_format: str,
) -> int | None:
    """Resolve quality settings to bitrate.

    Bitrate takes precedence over quality preset.

    Args:
        quality: Quality preset (best, good, small).
        bitrate: Explicit bitrate in kbps.
        audio_format: Target audio format.

    Returns:
        Resolved bitrate in kbps, or None for lossless.
    """
    # Bitrate takes precedence
    if bitrate is not None:
        return bitrate

    # Use quality preset
    if quality and quality in QUALITY_PRESETS:
        return QUALITY_PRESETS[quality].get(audio_format)

    # Default to best quality
    return QUALITY_PRESETS["best"].get(audio_format)


def _check_exists(
    url: str, audio_format: str, output_dir: Path, title: str = ""
) -> bool:
    """Check if output file for URL already exists.

    Args:
        url: Video URL.
        audio_format: Target audio format.
        output_dir: Output directory.
        title: Pre-fetched title (if empty, will fetch from URL).

    Returns:
        True if file exists and should be skipped, False otherwise.
    """
    # Use pre-fetched title if available, otherwise fetch it
    if not title:
        metadata = extract_metadata(url)
        if not metadata:
            return False
        title = metadata.get("title", "")

    filename = sanitize(title)
    if not filename:
        return False
    output_path = output_dir / f"{filename}.{audio_format}"
    return output_path.exists()


def _filter_existing_entries(
    entries: list[PlaylistEntry],
    audio_format: str,
    output_dir: Path,
) -> tuple[list[str], int]:
    """Filter out entries whose output files already exist.

    Uses pre-fetched titles when available, avoiding network requests.

    Args:
        entries: List of PlaylistEntry to check.
        audio_format: Target audio format.
        output_dir: Output directory.

    Returns:
        Tuple of (urls_to_download, skipped_count).
    """
    urls_to_download: list[str] = []
    skipped = 0

    for entry in entries:
        if _check_exists(entry.url, audio_format, output_dir, entry.title):
            skipped += 1
        else:
            urls_to_download.append(entry.url)

    return urls_to_download, skipped


def _download_audio(url: str, temp_dir: Path) -> DownloadResult:
    """Download audio and return result."""
    with create_download_progress() as progress:
        task_id = progress.add_task("Downloading...", total=None)

        def callback(downloaded: int, total: int) -> None:
            if total > 0:
                progress.update(task_id, completed=downloaded, total=total)
            else:
                progress.update(task_id, completed=downloaded)

        return download(url=url, progress_callback=callback, output_dir=temp_dir)


def _convert_audio(
    result: DownloadResult,
    output_dir: Path,
    audio_format: str,
    bitrate: int | None,
    embed_metadata: bool,
) -> Path | None:
    """Convert downloaded audio and return output path, or None on failure."""
    with create_conversion_progress() as progress:
        task_id = progress.add_task("Converting...", total=result.duration)

        def callback(processed_seconds: float) -> None:
            progress.update(task_id, completed=processed_seconds)

        final_output_path = output_dir / f"{sanitize(result.title)}.{audio_format}"
        final_output_path = resolve_conflict(final_output_path)

        temp_output_path = output_dir / f".{sanitize(result.title)}.{audio_format}.tmp"

        metadata = (
            {"title": result.title, "artist": result.artist} if embed_metadata else {}
        )

        try:
            transcode(
                input_path=result.temp_path,
                output_path=temp_output_path,
                audio_format=audio_format,
                bitrate=bitrate,
                embed_metadata=embed_metadata,
                metadata=metadata,
                progress_callback=callback,
            )
            if final_output_path.exists():
                final_output_path = resolve_conflict(final_output_path)
            temp_output_path.replace(final_output_path)
            return final_output_path
        except FFmpegNotFoundError:
            print_error(format_error(FFmpegNotFoundError()))
        except Exception as e:
            print_error(format_error(e))
        finally:
            if temp_output_path.exists():
                with contextlib.suppress(OSError):
                    temp_output_path.unlink()
        return None


def process_single_url(
    url: str,
    audio_format: str,
    output_dir: Path,
    bitrate: int | None,
    embed_metadata: bool,
) -> bool:
    """Process a single URL download.

    Args:
        url: Video URL to download.
        audio_format: Target audio format.
        output_dir: Output directory.
        bitrate: Target bitrate in kbps.
        embed_metadata: Whether to embed metadata.

    Returns:
        True if download and conversion succeeded.
    """
    with tempfile.TemporaryDirectory() as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        result = _download_audio(url, temp_dir)

        if not result.success:
            print_error(f"Download failed: {result.error}")
            return False

        if not result.temp_path.exists():
            print_error(
                f"Download failed: Temporary file not found at {result.temp_path}"
            )
            return False

        output_path = _convert_audio(
            result, output_dir, audio_format, bitrate, embed_metadata
        )
        if output_path is None:
            return False

        print_success(f"Saved: {output_path}")
        return True


def expand_playlist_urls(urls: list[str]) -> list[PlaylistEntry]:
    """Expand playlist URLs to individual video entries with titles.

    Args:
        urls: List of URLs that may include playlists.

    Returns:
        Expanded list of PlaylistEntry with URLs and pre-fetched titles (deduplicated).
    """
    expanded: list[PlaylistEntry] = []

    for url in urls:
        if is_playlist(url):
            print_info(f"Extracting playlist: {url}")
            entries = extract_playlist_with_metadata(url)
            if entries:
                print_info(f"Found {len(entries)} videos in playlist")
                expanded.extend(entries)
            else:
                # Could not extract, treat as single video
                print_info("Could not extract playlist, treating as single video")
                expanded.append(PlaylistEntry(url=url, title=""))
        else:
            # Single URL - title will be fetched later if needed
            expanded.append(PlaylistEntry(url=url, title=""))

    # Deduplicate by URL, keeping first occurrence
    seen: dict[str, PlaylistEntry] = {}
    for entry in expanded:
        if entry.url not in seen:
            seen[entry.url] = entry
    deduplicated = list(seen.values())

    if len(deduplicated) < len(expanded):
        print_info(f"Removed {len(expanded) - len(deduplicated)} duplicate(s)")

    return deduplicated


def process_urls(
    urls: list[str],
    audio_format: str,
    output_dir: Path,
    bitrate: int | None,
    embed_metadata: bool,
    force: bool = False,
) -> int:
    """Process multiple URLs.

    Args:
        urls: List of video URLs.
        audio_format: Target audio format.
        output_dir: Output directory.
        bitrate: Target bitrate in kbps.
        embed_metadata: Whether to embed metadata.
        force: If False, skip files that already exist.

    Returns:
        Exit code (0 = all success, 1 = some failures).
    """
    expanded_entries = expand_playlist_urls(urls)

    # Filter out existing files unless force is set
    skipped = 0
    if not force and len(expanded_entries) > 0:
        print_info("Checking for existing files...")
        urls_to_process, skipped = _filter_existing_entries(
            expanded_entries, audio_format, output_dir
        )
        if skipped > 0:
            print_warning(f"Skipped {skipped} already downloaded")
    else:
        urls_to_process = [entry.url for entry in expanded_entries]

    if len(urls_to_process) == 0:
        print_info("Nothing to download")
        return 0

    if len(urls_to_process) == 1:
        success = process_single_url(
            url=urls_to_process[0],
            audio_format=audio_format,
            output_dir=output_dir,
            bitrate=bitrate,
            embed_metadata=embed_metadata,
        )
        return 0 if success else 1

    succeeded = 0
    failed = 0

    for i, url in enumerate(urls_to_process, 1):
        print_info(f"Processing {i}/{len(urls_to_process)}: {url}")

        success = process_single_url(
            url=url,
            audio_format=audio_format,
            output_dir=output_dir,
            bitrate=bitrate,
            embed_metadata=embed_metadata,
        )

        if success:
            succeeded += 1
        else:
            failed += 1

    # Print summary with skip info
    summary = f"\nCompleted: {succeeded} succeeded, {failed} failed"
    if skipped > 0:
        summary += f", {skipped} skipped"
    print_info(summary)

    return 0 if failed == 0 else 1


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        print(f"yt-audio-cli version {__version__}")
        raise typer.Exit()


@app.command()
def main(
    urls: Annotated[
        list[str],
        typer.Argument(
            help="One or more video or playlist URLs to download.",
            show_default=False,
        ),
    ],
    audio_format: Annotated[
        str,
        typer.Option(
            "--format",
            "-f",
            help="Output audio format: mp3, aac, opus, wav",
            callback=lambda v: validate_format(v),
        ),
    ] = "mp3",
    output: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="Output directory for downloaded files.",
            exists=True,
            file_okay=False,
            dir_okay=True,
            resolve_path=True,
        ),
    ] = Path(),
    quality: Annotated[
        str,
        typer.Option(
            "--quality",
            "-q",
            help="Audio quality preset: best, good, small",
        ),
    ] = "best",
    bitrate: Annotated[
        int | None,
        typer.Option(
            "--bitrate",
            "-b",
            help="Target bitrate in kbps (overrides --quality).",
            min=32,
            max=320,
        ),
    ] = None,
    no_metadata: Annotated[
        bool,
        typer.Option(
            "--no-metadata",
            help="Skip embedding title/artist metadata.",
        ),
    ] = False,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            "-F",
            help="Download even if file already exists.",
        ),
    ] = False,
    version: Annotated[  # noqa: ARG001
        bool,
        typer.Option(
            "--version",
            "-v",
            help="Show version and exit.",
            callback=version_callback,
            is_eager=True,
        ),
    ] = False,
) -> None:
    """Download audio from video URLs and save locally."""
    # Check FFmpeg availability
    if not check_ffmpeg():
        print_error(format_error(FFmpegNotFoundError()))
        raise typer.Exit(code=2)

    # Validate quality preset
    if quality not in QUALITY_PRESETS:
        print_error(
            f"Invalid quality '{quality}'. Valid options: {', '.join(QUALITY_PRESETS.keys())}"
        )
        raise typer.Exit(code=2)

    # Resolve bitrate
    resolved_bitrate = resolve_quality(quality, bitrate, audio_format)

    exit_code = process_urls(
        urls=urls,
        audio_format=audio_format,
        output_dir=output,
        bitrate=resolved_bitrate,
        embed_metadata=not no_metadata,
        force=force,
    )

    raise typer.Exit(code=exit_code)


if __name__ == "__main__":
    app()
