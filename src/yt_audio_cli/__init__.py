"""YouTube Audio CLI - Download audio from video URLs."""

from yt_audio_cli.errors import ConversionError, DownloadError, FFmpegNotFoundError

__version__ = "0.1.0"

__metadata__ = {
    "name": "yt-audio-cli",
    "version": __version__,
    "author": "pyyupsk",
    "license": "MIT",
    "python": ">=3.12",
    "repository": "github.com/pyyupsk/yt-audio-cli",
}
__all__ = [
    "ConversionError",
    "DownloadError",
    "FFmpegNotFoundError",
    "__metadata__",
    "__version__",
]
