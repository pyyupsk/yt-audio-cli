# yt-audio-cli

[![CI](https://github.com/pyyupsk/yt-audio-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/pyyupsk/yt-audio-cli/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/pyyupsk/yt-audio-cli/graph/badge.svg?token=hvB8RREdML)](https://codecov.io/gh/pyyupsk/yt-audio-cli)
[![PyPI](https://img.shields.io/pypi/v/yt-audio-cli)](https://pypi.org/project/yt-audio-cli/)
[![Python](https://img.shields.io/pypi/pyversions/yt-audio-cli)](https://pypi.org/project/yt-audio-cli/)
[![License](https://img.shields.io/github/license/pyyupsk/yt-audio-cli)](LICENSE)

A simple command-line tool for downloading audio from YouTube and other sites.

## What This Is

yt-audio-cli is an opinionated wrapper around [yt-dlp](https://github.com/yt-dlp/yt-dlp) and [FFmpeg](https://ffmpeg.org/), designed specifically for audio downloads. It provides sensible defaults and a streamlined interface for common audio extraction tasks.

- **yt-dlp** handles all video/audio downloading and site support (1000+ sites)
- **FFmpeg** handles audio conversion and processing
- **yt-audio-cli** ties them together with audio-focused defaults and a simplified CLI

If you need advanced features like video downloads, custom format selection, or fine-grained control, use yt-dlp directly.

## Quick Start

```bash
# Install
pip install yt-audio-cli

# Download audio
yt-audio-cli https://youtube.com/watch?v=VIDEO_ID
```

## Requirements

**FFmpeg** must be installed on your system for audio conversion:

- **Windows**: `winget install FFmpeg` or download from [ffmpeg.org](https://ffmpeg.org/download.html)
- **macOS**: `brew install ffmpeg`
- **Linux**: `sudo apt install ffmpeg` (Debian/Ubuntu) or `sudo dnf install ffmpeg` (Fedora)

yt-dlp is installed automatically as a Python dependency.

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
| `--force`       | `-F`  | Re-download even if file exists    | -           |
| `--version`     | `-v`  | Show version                       | -           |
| `--help`        | `-h`  | Show help                          | -           |

> **Note:** By default, files that already exist in the output directory are skipped. Use `--force` to re-download them.

## Troubleshooting

**"FFmpeg not found"**
Install FFmpeg using the instructions in [Requirements](#requirements).

**"Video unavailable"**
The video may be private, age-restricted, or region-locked. This is a limitation of the source site, not yt-dlp or this tool.

**"Signature solving failed" / JS challenge warnings**
YouTube uses JavaScript challenges to protect some video formats. You may see warnings like:

```bash
yt-dlp: [youtube] Signature solving failed: Some formats may be missing.
```

Downloads usually still work (yt-dlp falls back to alternative formats), but to resolve these warnings:

- **Install Deno** (recommended): `curl -fsSL https://deno.land/install.sh | sh`
- **Or download the solver**: `yt-dlp --remote-components ejs:github`

See [yt-dlp EJS wiki](https://github.com/yt-dlp/yt-dlp/wiki/EJS) for more details.

**Download fails**
Check your internet connection and verify the URL is correct. If the issue persists, ensure yt-dlp is up to date: `pip install -U yt-dlp`

## Metadata

```python
__metadata__ = {
    "name": "yt-audio-cli",
    "version": "0.1.1",
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
