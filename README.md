# yt-audio-cli

Download audio from YouTube, SoundCloud, and 1000+ sites with a single command.

## Quick Start

```bash
# Install
pip install yt-audio-cli

# Download audio
yt-audio-cli https://youtube.com/watch?v=VIDEO_ID
```

## Requirements

**FFmpeg** must be installed on your system:

- **Windows**: `winget install FFmpeg` or download from [ffmpeg.org](https://ffmpeg.org/download.html)
- **macOS**: `brew install ffmpeg`
- **Linux**: `sudo apt install ffmpeg` (Debian/Ubuntu) or `sudo dnf install ffmpeg` (Fedora)

## Installation

```bash
pip install yt-audio-cli
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv tool install yt-audio-cli
```

## Usage

### Download Audio

```bash
# Single video (saves as MP3 by default)
yt-audio-cli https://youtube.com/watch?v=VIDEO_ID

# Multiple videos
yt-audio-cli URL1 URL2 URL3

# Entire playlist
yt-audio-cli https://youtube.com/playlist?list=PLAYLIST_ID
```

### Choose Format

```bash
yt-audio-cli -f opus URL   # Opus (smallest size)
yt-audio-cli -f aac URL    # AAC
yt-audio-cli -f mp3 URL    # MP3 (default)
yt-audio-cli -f wav URL    # WAV (lossless)
```

### Choose Quality

```bash
yt-audio-cli -q best URL    # Highest quality (default)
yt-audio-cli -q good URL    # Balanced
yt-audio-cli -q small URL   # Smallest file size

# Or set exact bitrate (32-320 kbps)
yt-audio-cli -b 256 URL
```

### Save Location

```bash
# Save to specific folder
yt-audio-cli -o ~/Music URL

# Default: current directory
```

### Skip Metadata

```bash
# Don't embed title/artist in the file
yt-audio-cli --no-metadata URL
```

## Options

| Option          | Short | Description                        | Default     |
| --------------- | ----- | ---------------------------------- | ----------- |
| `--format`      | `-f`  | Audio format (mp3, aac, opus, wav) | mp3         |
| `--output`      | `-o`  | Output directory                   | Current dir |
| `--quality`     | `-q`  | Quality preset (best, good, small) | best        |
| `--bitrate`     | `-b`  | Exact bitrate in kbps (32-320)     | -           |
| `--no-metadata` |       | Skip embedding metadata            | -           |
| `--version`     | `-v`  | Show version                       | -           |
| `--help`        | `-h`  | Show help                          | -           |

## Troubleshooting

**"FFmpeg not found"**
Install FFmpeg using the instructions in [Requirements](#requirements).

**"Video unavailable"**
The video may be private, age-restricted, or region-locked.

**Download fails**
Check your internet connection and verify the URL is correct.

## Metadata

```python
__metadata__ = {
    "name": "yt-audio-cli",
    "version": "0.1.0",
    "author": "pyyupsk",
    "license": "MIT",
    "python": ">=3.12",
    "repository": "github.com/pyyupsk/yt-audio-cli",
}
```

## Disclaimer

> [!IMPORTANT]
> This tool is intended for downloading content you have the right to access. Respect copyright laws and the terms of service of the platforms you use.

> [!CAUTION]
> The authors are not responsible for any misuse of this software.

## License

This project is licensed under the [MIT License](LICENSE).
