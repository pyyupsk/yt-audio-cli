"""Unit tests for filename sanitization and conflict resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

from yt_audio_cli.filename import resolve_conflict, sanitize


class TestSanitize:
    """Tests for sanitize() function."""

    def test_simple_title(self) -> None:
        """Test sanitization of a simple valid title."""
        assert sanitize("My Video Title") == "My_Video_Title"

    def test_invalid_characters(self) -> None:
        """Test that invalid characters are replaced."""
        assert sanitize('Video: "Test" <file>') == "Video_Test_file"
        assert sanitize("path/to\\file") == "path_to_file"
        assert sanitize("file*name?test") == "file_name_test"

    def test_multiple_spaces_and_underscores(self) -> None:
        """Test collapsing multiple spaces/underscores."""
        assert sanitize("Video   Title") == "Video_Title"
        assert sanitize("Video___Title") == "Video_Title"
        assert sanitize("Video _ _ Title") == "Video_Title"

    def test_leading_trailing_cleanup(self) -> None:
        """Test stripping leading/trailing whitespace and underscores."""
        assert sanitize("  Video Title  ") == "Video_Title"
        assert sanitize("__Video Title__") == "Video_Title"
        assert sanitize(" _ Video _ ") == "Video"

    def test_empty_title(self) -> None:
        """Test fallback for empty title."""
        assert sanitize("") == "audio"
        assert sanitize("   ") == "audio"
        assert sanitize("___") == "audio"

    def test_custom_fallback(self) -> None:
        """Test custom fallback value."""
        assert sanitize("", fallback="untitled") == "untitled"
        assert sanitize("???", fallback="video") == "video"

    def test_control_characters(self) -> None:
        """Test removal of control characters."""
        # Control chars are removed (not replaced with underscore)
        assert sanitize("Video\x00Title") == "VideoTitle"
        assert sanitize("Video\nTitle") == "VideoTitle"
        assert sanitize("Video\tTitle") == "VideoTitle"

    def test_truncation(self) -> None:
        """Test truncation of long titles."""
        long_title = "A" * 300
        result = sanitize(long_title)
        assert len(result) <= 200

    def test_unicode_preserved(self) -> None:
        """Test that unicode characters are preserved."""
        assert sanitize("日本語タイトル") == "日本語タイトル"
        assert sanitize("Müsik Vïdëö") == "Müsik_Vïdëö"

    def test_pipe_character(self) -> None:
        """Test pipe character removal."""
        assert sanitize("Video | Title") == "Video_Title"

    def test_all_invalid_chars(self) -> None:
        """Test title with only invalid characters."""
        assert sanitize('\\/:*?"<>|') == "audio"


class TestResolveConflict:
    """Tests for resolve_conflict() function."""

    def test_no_conflict(self, temp_dir: Path) -> None:
        """Test when file doesn't exist."""
        path = temp_dir / "test.mp3"
        assert resolve_conflict(path) == path

    def test_single_conflict(self, temp_dir: Path) -> None:
        """Test resolving a single conflict."""
        path = temp_dir / "test.mp3"
        path.touch()

        result = resolve_conflict(path)
        assert result == temp_dir / "test (1).mp3"

    def test_multiple_conflicts(self, temp_dir: Path) -> None:
        """Test resolving multiple conflicts."""
        base_path = temp_dir / "test.mp3"
        base_path.touch()
        (temp_dir / "test (1).mp3").touch()
        (temp_dir / "test (2).mp3").touch()

        result = resolve_conflict(base_path)
        assert result == temp_dir / "test (3).mp3"

    def test_preserves_extension(self, temp_dir: Path) -> None:
        """Test that extension is preserved."""
        path = temp_dir / "song.opus"
        path.touch()

        result = resolve_conflict(path)
        assert result.suffix == ".opus"

    def test_different_extensions_no_conflict(self, temp_dir: Path) -> None:
        """Test that different extensions don't conflict."""
        (temp_dir / "test.mp3").touch()
        path = temp_dir / "test.wav"

        assert resolve_conflict(path) == path
