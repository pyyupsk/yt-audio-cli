"""Convert feature - handles FFmpeg interaction for audio transcoding."""

from yt_audio_cli.convert.transcoder import check_ffmpeg, transcode

__all__ = [
    "check_ffmpeg",
    "transcode",
]
