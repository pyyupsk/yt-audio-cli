"""A simple command-line tool for downloading audio from YouTube and other sites."""

from importlib.metadata import metadata

from yt_audio_cli.core import ConversionError, DownloadError, FFmpegNotFoundError

_meta = metadata("yt-audio-cli")

__version__ = _meta["Version"]
__metadata__ = {
    "name": _meta["Name"],
    "version": __version__,
    "author": _meta["Author"],
    "license": _meta["License-Expression"],
    "python": _meta["Requires-Python"],
    "repository": "github.com/pyyupsk/yt-audio-cli",
}
__all__ = [
    "ConversionError",
    "DownloadError",
    "FFmpegNotFoundError",
    "__metadata__",
    "__version__",
]
