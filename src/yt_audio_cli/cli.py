"""CLI implementation for yt-audio-cli."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Annotated

import typer

from yt_audio_cli import __version__
from yt_audio_cli.converter import check_ffmpeg, transcode
from yt_audio_cli.downloader import download, extract_playlist, is_playlist
from yt_audio_cli.errors import FFmpegNotFoundError, format_error
from yt_audio_cli.filename import resolve_conflict, sanitize
from yt_audio_cli.progress import (
    create_progress,
    print_error,
    print_info,
    print_success,
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
    help="Download audio from video URLs and save locally in common audio formats.",
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
    with create_progress() as progress:
        # Add download task
        task_id = progress.add_task("Downloading...", total=None)

        def progress_callback(downloaded: int, total: int) -> None:
            progress.update(task_id, completed=downloaded, total=total)

        # Download audio
        with tempfile.TemporaryDirectory() as temp_dir:
            result = download(
                url=url,
                progress_callback=progress_callback,
                output_dir=Path(temp_dir),
            )

            if not result.success:
                progress.stop()
                print_error(f"Download failed: {result.error}")
                return False

            progress.update(task_id, description="Converting...")

            # Prepare output path
            filename = sanitize(result.title)
            output_path = output_dir / f"{filename}.{audio_format}"
            output_path = resolve_conflict(output_path)

            # Prepare metadata
            metadata = {}
            if embed_metadata:
                metadata = {
                    "title": result.title,
                    "artist": result.artist,
                }

            # Transcode
            try:
                transcode(
                    input_path=result.temp_path,
                    output_path=output_path,
                    audio_format=audio_format,
                    bitrate=bitrate,
                    embed_metadata=embed_metadata,
                    metadata=metadata,
                )
            except FFmpegNotFoundError:
                progress.stop()
                print_error(format_error(FFmpegNotFoundError()))
                return False
            except Exception as e:
                progress.stop()
                print_error(format_error(e))
                return False

    print_success(f"Saved: {output_path}")
    return True


def expand_playlist_urls(urls: list[str]) -> list[str]:
    """Expand playlist URLs to individual video URLs.

    Args:
        urls: List of URLs that may include playlists.

    Returns:
        Expanded list with all video URLs.
    """
    expanded: list[str] = []

    for url in urls:
        if is_playlist(url):
            print_info(f"Extracting playlist: {url}")
            playlist_urls = extract_playlist(url)
            if playlist_urls:
                print_info(f"Found {len(playlist_urls)} videos in playlist")
                expanded.extend(playlist_urls)
            else:
                # Could not extract, treat as single video
                print_info("Could not extract playlist, treating as single video")
                expanded.append(url)
        else:
            expanded.append(url)

    return expanded


def process_urls(
    urls: list[str],
    audio_format: str,
    output_dir: Path,
    bitrate: int | None,
    embed_metadata: bool,
) -> int:
    """Process multiple URLs.

    Args:
        urls: List of video URLs.
        audio_format: Target audio format.
        output_dir: Output directory.
        bitrate: Target bitrate in kbps.
        embed_metadata: Whether to embed metadata.

    Returns:
        Exit code (0 = all success, 1 = some failures).
    """
    # Expand any playlist URLs
    expanded_urls = expand_playlist_urls(urls)

    if len(expanded_urls) == 1:
        # Single URL mode
        success = process_single_url(
            url=expanded_urls[0],
            audio_format=audio_format,
            output_dir=output_dir,
            bitrate=bitrate,
            embed_metadata=embed_metadata,
        )
        return 0 if success else 1

    # Batch mode
    succeeded = 0
    failed = 0

    for i, url in enumerate(expanded_urls, 1):
        print_info(f"Processing {i}/{len(expanded_urls)}: {url}")

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

    # Print summary
    print_info(f"\nCompleted: {succeeded} succeeded, {failed} failed")

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

    # Process URLs
    exit_code = process_urls(
        urls=urls,
        audio_format=audio_format,
        output_dir=output,
        bitrate=resolved_bitrate,
        embed_metadata=not no_metadata,
    )

    raise typer.Exit(code=exit_code)


if __name__ == "__main__":
    app()
