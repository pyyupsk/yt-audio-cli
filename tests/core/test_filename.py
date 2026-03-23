"""Unit tests for filename sanitization and conflict resolution."""

from __future__ import annotations

from pathlib import Path

from yt_audio_cli.core import resolve_conflict, sanitize
from yt_audio_cli.core.filename import MAX_FILENAME_LENGTH


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


class TestSanitizeBoundaryConditions:
    """Boundary condition tests for sanitize() function."""

    def test_none_input_uses_fallback(self) -> None:
        """Test that None input uses fallback (falsy value)."""
        # None is falsy, treated like empty string
        assert sanitize(None) == "audio"  # type: ignore

    def test_empty_string_uses_fallback(self) -> None:
        """Test empty string boundary."""
        assert sanitize("") == "audio"

    def test_whitespace_only_uses_fallback(self) -> None:
        """Test whitespace-only boundary."""
        assert sanitize(" ") == "audio"
        assert sanitize("   ") == "audio"
        assert sanitize("\t") == "audio"
        assert sanitize("\n") == "audio"

    def test_only_invalid_chars_uses_fallback(self) -> None:
        """Test string with only invalid characters."""
        assert sanitize('\\/:*?"<>|') == "audio"
        assert sanitize("***") == "audio"
        assert sanitize("???") == "audio"

    def test_exactly_max_length(self) -> None:
        """Test title exactly at MAX_FILENAME_LENGTH."""
        title = "A" * MAX_FILENAME_LENGTH
        result = sanitize(title)
        assert len(result) == MAX_FILENAME_LENGTH

    def test_one_over_max_length(self) -> None:
        """Test title one character over limit."""
        title = "A" * (MAX_FILENAME_LENGTH + 1)
        result = sanitize(title)
        assert len(result) == MAX_FILENAME_LENGTH

    def test_far_over_max_length(self) -> None:
        """Test title far exceeding limit."""
        title = "A" * 10000
        result = sanitize(title)
        assert len(result) == MAX_FILENAME_LENGTH

    def test_exactly_one_char(self) -> None:
        """Test single character title."""
        assert sanitize("A") == "A"

    def test_exactly_two_chars(self) -> None:
        """Test two character title."""
        assert sanitize("AB") == "AB"

    def test_unicode_at_max_length(self) -> None:
        """Test unicode string at max length."""
        title = "あ" * MAX_FILENAME_LENGTH
        result = sanitize(title)
        assert len(result) <= MAX_FILENAME_LENGTH

    def test_mixed_unicode_and_ascii(self) -> None:
        """Test mixed unicode and ASCII."""
        assert sanitize("Test テスト 测试") == "Test_テスト_测试"

    def test_emoji_characters(self) -> None:
        """Test emoji in title."""
        result = sanitize("Video 🎵 Title")
        assert "🎵" in result or result == "Video_Title"

    def test_zero_width_characters(self) -> None:
        """Test zero-width unicode characters."""
        result = sanitize("Test\u200bTitle")
        assert result is not None

    def test_all_control_chars_0_to_31(self) -> None:
        """Test all control characters 0x00-0x1F."""
        for i in range(32):
            title = f"Test{chr(i)}Title"
            result = sanitize(title)
            assert chr(i) not in result or result == "TestTitle"

    def test_delete_char_0x7f(self) -> None:
        """Test DEL character (0x7F)."""
        result = sanitize("Test\x7fTitle")
        assert "\x7f" not in result

    def test_all_windows_invalid_chars(self) -> None:
        """Test all Windows-invalid characters."""
        invalid = '\\/:*?"<>|'
        for char in invalid:
            result = sanitize(f"Test{char}Title")
            assert char not in result

    def test_consecutive_invalid_chars(self) -> None:
        """Test consecutive invalid characters."""
        result = sanitize("Test\\\\//**Title")
        assert "***" not in result
        assert "___" not in result

    def test_truncation_result_not_empty(self) -> None:
        """Test truncation never returns empty string."""
        for length in [200, 201, 500, 1000]:
            title = "A" * length
            result = sanitize(title)
            assert len(result) > 0

    def test_very_long_string_performance(self) -> None:
        """Test sanitization performance with very long string."""
        import time

        title = "A" * 1000000  # 1 million chars
        start = time.time()
        result = sanitize(title)
        elapsed = time.time() - start

        assert elapsed < 1.0
        assert len(result) == MAX_FILENAME_LENGTH


class TestResolveConflictBoundaryConditions:
    """Boundary condition tests for resolve_conflict() function."""

    def test_path_doesnt_exist_returns_same(self, temp_dir: Path) -> None:
        """Test non-existent path returns unchanged."""
        path = temp_dir / "nonexistent.mp3"
        result = resolve_conflict(path)
        assert result == path

    def test_many_files_exist_returns_next_available(self, temp_dir: Path) -> None:
        """Test many existing files returns next available."""
        base = temp_dir / "test.mp3"
        base.touch()
        for i in range(1, 100):
            (temp_dir / f"test ({i}).mp3").touch()

        result = resolve_conflict(base)
        assert result == temp_dir / "test (100).mp3"

    def test_counter_starts_at_one(self, temp_dir: Path) -> None:
        """Test counter starts at 1, not 0."""
        path = temp_dir / "test.mp3"
        path.touch()
        result = resolve_conflict(path)
        assert "(0)" not in str(result)
        assert "(1)" in str(result)

    def test_multiple_dots_in_filename(self, temp_dir: Path) -> None:
        """Test filename with multiple dots."""
        path = temp_dir / "test.file.name.mp3"
        path.touch()
        result = resolve_conflict(path)
        assert result == temp_dir / "test.file.name (1).mp3"
        assert result.suffix == ".mp3"

    def test_no_extension(self, temp_dir: Path) -> None:
        """Test file without extension."""
        path = temp_dir / "testfile"
        path.touch()
        result = resolve_conflict(path)
        assert result == temp_dir / "testfile (1)"

    def test_hidden_file(self, temp_dir: Path) -> None:
        """Test hidden file (starts with dot)."""
        path = temp_dir / ".hidden"
        path.touch()
        result = resolve_conflict(path)
        assert result == temp_dir / ".hidden (1)"

    def test_nested_directory(self, temp_dir: Path) -> None:
        """Test nested directory path."""
        nested = temp_dir / "a" / "b" / "c"
        nested.mkdir(parents=True)
        path = nested / "test.mp3"
        path.touch()
        result = resolve_conflict(path)
        assert result == nested / "test (1).mp3"

    def test_parent_directory_doesnt_conflict(self, temp_dir: Path) -> None:
        """Test same name in different dirs don't conflict."""
        dir1 = temp_dir / "dir1"
        dir2 = temp_dir / "dir2"
        dir1.mkdir()
        dir2.mkdir()

        path1 = dir1 / "test.mp3"
        path2 = dir2 / "test.mp3"

        path1.touch()
        result = resolve_conflict(path2)
        assert result == path2

    def test_gaps_in_numbering(self, temp_dir: Path) -> None:
        """Test gaps in numbering are filled."""
        base = temp_dir / "test.mp3"
        base.touch()
        (temp_dir / "test (1).mp3").touch()
        (temp_dir / "test (3).mp3").touch()

        result = resolve_conflict(base)
        assert result == temp_dir / "test (2).mp3"

    def test_hundred_conflicts(self, temp_dir: Path) -> None:
        """Test resolving 100+ conflicts."""
        base = temp_dir / "test.mp3"
        base.touch()
        for i in range(1, 101):
            (temp_dir / f"test ({i}).mp3").touch()

        result = resolve_conflict(base)
        assert result == temp_dir / "test (101).mp3"

    def test_unicode_in_filename(self, temp_dir: Path) -> None:
        """Test unicode characters in filename."""
        path = temp_dir / "テスト.mp3"
        path.touch()
        result = resolve_conflict(path)
        assert result == temp_dir / "テスト (1).mp3"

    def test_very_long_path(self, temp_dir: Path) -> None:
        """Test very long path."""
        deep_path = temp_dir
        for i in range(50):
            deep_path = deep_path / f"dir{i}"
        deep_path.mkdir(parents=True, exist_ok=True)

        path = deep_path / "test.mp3"
        path.touch()
        result = resolve_conflict(path)
        assert result == deep_path / "test (1).mp3"
