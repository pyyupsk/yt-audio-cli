"""Filename sanitization and conflict resolution for yt-audio-cli."""

from __future__ import annotations

import re
import time
from pathlib import Path

# Characters invalid on any OS (Windows is most restrictive)
INVALID_CHARS = r'[\\/:*?"<>|]'

# Maximum filename length (leaving room for extension)
MAX_FILENAME_LENGTH = 200


def sanitize(title: str, fallback: str = "audio") -> str:
    """Sanitize title for cross-platform filesystem compatibility.

    Rules:
    1. Replace invalid characters with underscore
    2. Collapse multiple underscores to single
    3. Strip leading/trailing whitespace and underscores
    4. Truncate to MAX_FILENAME_LENGTH characters
    5. If empty after sanitization, use fallback

    Args:
        title: The video title to sanitize.
        fallback: Fallback name if title becomes empty after sanitization.

    Returns:
        A filesystem-safe filename (without extension).
    """
    if not title:
        return fallback

    # Replace invalid characters with underscore
    sanitized = re.sub(INVALID_CHARS, "_", title)

    # Replace control characters and other problematic chars
    sanitized = re.sub(r"[\x00-\x1f\x7f]", "", sanitized)

    # Collapse multiple underscores/spaces to single underscore
    sanitized = re.sub(r"[_\s]+", "_", sanitized)

    # Strip leading/trailing whitespace and underscores
    sanitized = sanitized.strip(" _")

    # Truncate to max length
    if len(sanitized) > MAX_FILENAME_LENGTH:
        sanitized = sanitized[:MAX_FILENAME_LENGTH]
        sanitized = sanitized.encode("utf-8", errors="ignore").decode(
            "utf-8", errors="ignore"
        )
        sanitized = sanitized.rstrip(" _")

    # Use fallback if empty
    if not sanitized:
        return fallback

    return sanitized


def resolve_conflict(path: Path) -> Path:
    """Append numeric suffix if file exists. Returns unique path.

    If file.mp3 exists, tries file (1).mp3, file (2).mp3, etc.
    Falls back to timestamp-based name if limit exceeded.

    Args:
        path: The desired output path.

    Returns:
        A unique path that doesn't exist yet.
    """
    if not path.exists():
        return path

    stem = path.stem
    suffix = path.suffix
    parent = path.parent

    # Safety limit to prevent excessive iterations
    max_attempts = 9999

    for counter in range(1, max_attempts + 1):
        new_path = parent / f"{stem} ({counter}){suffix}"
        if not new_path.exists():
            return new_path

    timestamp = int(time.time() * 1000)
    return parent / f"{stem}_{timestamp}{suffix}"
