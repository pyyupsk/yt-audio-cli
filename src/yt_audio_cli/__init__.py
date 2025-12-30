"""A simple command-line tool for downloading audio from YouTube and other sites."""

from yt_audio_cli.core import ConversionError, DownloadError, FFmpegNotFoundError

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
