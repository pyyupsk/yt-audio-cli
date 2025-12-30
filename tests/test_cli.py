"""Unit tests for CLI argument parsing and integration."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

# Import will work after CLI is implemented
# For now, we set up the structure


class TestCLIArgumentParsing:
    """Tests for CLI argument parsing."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def cli_app(self) -> Any:
        """Get the CLI app for testing."""
        from yt_audio_cli.cli import app

        return app

    def test_help_flag(self, runner: CliRunner, cli_app: Any) -> None:
        """Test --help flag shows help text."""
        result = runner.invoke(cli_app, ["--help"])
        assert result.exit_code == 0
        assert "URLS" in result.output or "urls" in result.output.lower()
        assert "--format" in result.output or "-f" in result.output
        assert "--output" in result.output or "-o" in result.output

    def test_version_flag(self, runner: CliRunner, cli_app: Any) -> None:
        """Test --version flag shows version."""
        result = runner.invoke(cli_app, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_no_urls_shows_error(self, runner: CliRunner, cli_app: Any) -> None:
        """Test that missing URLs shows error."""
        result = runner.invoke(cli_app, [])
        assert result.exit_code != 0

    def test_single_url_accepted(self, runner: CliRunner, cli_app: Any) -> None:
        """Test single URL is accepted as argument."""
        with patch("yt_audio_cli.cli.process_urls") as mock_process:
            mock_process.return_value = 0
            result = runner.invoke(cli_app, ["https://youtube.com/watch?v=test"])
            # Should call process_urls with the URL
            assert mock_process.called or result.exit_code == 0

    def test_format_flag_default(self, runner: CliRunner, cli_app: Any) -> None:
        """Test default format is mp3."""
        result = runner.invoke(cli_app, ["--help"])
        assert "mp3" in result.output.lower()

    def test_format_flag_short(self, runner: CliRunner, cli_app: Any) -> None:
        """Test -f short flag for format."""
        with patch("yt_audio_cli.cli.process_urls") as mock_process:
            mock_process.return_value = 0
            result = runner.invoke(
                cli_app, ["-f", "opus", "https://youtube.com/watch?v=test"]
            )
            # Format should be accepted
            assert result.exit_code == 0 or mock_process.called

    def test_format_flag_long(self, runner: CliRunner, cli_app: Any) -> None:
        """Test --format long flag."""
        with patch("yt_audio_cli.cli.process_urls") as mock_process:
            mock_process.return_value = 0
            result = runner.invoke(
                cli_app, ["--format", "aac", "https://youtube.com/watch?v=test"]
            )
            assert result.exit_code == 0 or mock_process.called

    def test_invalid_format_rejected(self, runner: CliRunner, cli_app: Any) -> None:
        """Test invalid format is rejected."""
        result = runner.invoke(
            cli_app, ["--format", "invalid", "https://youtube.com/watch?v=test"]
        )
        assert result.exit_code == 2 or "invalid" in result.output.lower()

    def test_output_flag_short(self, runner: CliRunner, cli_app: Any) -> None:
        """Test -o short flag for output directory."""
        with patch("yt_audio_cli.cli.process_urls") as mock_process:
            mock_process.return_value = 0
            result = runner.invoke(
                cli_app, ["-o", "/tmp", "https://youtube.com/watch?v=test"]
            )
            assert result.exit_code == 0 or mock_process.called

    def test_output_flag_long(self, runner: CliRunner, cli_app: Any) -> None:
        """Test --output long flag."""
        with patch("yt_audio_cli.cli.process_urls") as mock_process:
            mock_process.return_value = 0
            result = runner.invoke(
                cli_app, ["--output", "/tmp", "https://youtube.com/watch?v=test"]
            )
            assert result.exit_code == 0 or mock_process.called

    def test_output_nonexistent_directory_error(
        self, runner: CliRunner, cli_app: Any
    ) -> None:
        """Test error when output directory doesn't exist."""
        result = runner.invoke(
            cli_app,
            ["--output", "/nonexistent/path", "https://youtube.com/watch?v=test"],
        )
        # Should fail with exit code 2 (config error)
        assert result.exit_code == 2 or "not exist" in result.output.lower()


class TestFormatValidation:
    """Tests for format validation callback."""

    def test_valid_formats(self) -> None:
        """Test all valid formats are accepted."""
        from yt_audio_cli.cli import validate_format

        for fmt in ["mp3", "aac", "opus", "wav"]:
            assert validate_format(fmt) == fmt

    def test_case_insensitive(self) -> None:
        """Test format validation is case insensitive."""
        from yt_audio_cli.cli import validate_format

        assert validate_format("MP3") == "mp3"
        assert validate_format("Opus") == "opus"

    def test_invalid_format_raises(self) -> None:
        """Test invalid format raises BadParameter."""
        import typer

        from yt_audio_cli.cli import validate_format

        with pytest.raises(typer.BadParameter):
            validate_format("flac")


class TestExitCodes:
    """Tests for CLI exit codes."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def cli_app(self) -> Any:
        """Get the CLI app for testing."""
        from yt_audio_cli.cli import app

        return app

    def test_success_exit_code_zero(self, runner: CliRunner, cli_app: Any) -> None:
        """Test successful download returns exit code 0."""
        with patch("yt_audio_cli.cli.process_urls") as mock_process:
            mock_process.return_value = 0
            result = runner.invoke(cli_app, ["https://youtube.com/watch?v=test"])
            assert result.exit_code == 0

    def test_download_failure_exit_code_one(
        self, runner: CliRunner, cli_app: Any
    ) -> None:
        """Test download failure returns exit code 1."""
        with patch("yt_audio_cli.cli.process_urls") as mock_process:
            mock_process.return_value = 1
            result = runner.invoke(cli_app, ["https://youtube.com/watch?v=test"])
            assert result.exit_code == 1

    def test_config_error_exit_code_two(self, runner: CliRunner, cli_app: Any) -> None:
        """Test config error returns exit code 2."""
        result = runner.invoke(cli_app, ["--format", "invalid", "https://test.com"])
        assert result.exit_code == 2


class TestBatchDownload:
    """Tests for batch download functionality (US2)."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def cli_app(self) -> Any:
        """Get the CLI app for testing."""
        from yt_audio_cli.cli import app

        return app

    def test_multiple_urls_accepted(self, runner: CliRunner, cli_app: Any) -> None:
        """Test multiple URLs are accepted as arguments."""
        with patch("yt_audio_cli.cli.process_urls") as mock_process:
            mock_process.return_value = 0
            result = runner.invoke(
                cli_app,
                [
                    "https://youtube.com/watch?v=test1",
                    "https://youtube.com/watch?v=test2",
                    "https://youtube.com/watch?v=test3",
                ],
            )
            assert result.exit_code == 0
            # Verify all URLs were passed
            call_args = mock_process.call_args
            assert len(call_args[1]["urls"]) == 3

    def test_batch_partial_failure_continues(
        self, runner: CliRunner, cli_app: Any
    ) -> None:
        """Test batch continues on partial failure."""
        # process_urls returns 1 when some downloads fail
        with patch("yt_audio_cli.cli.process_urls") as mock_process:
            mock_process.return_value = 1
            result = runner.invoke(
                cli_app,
                [
                    "https://youtube.com/watch?v=test1",
                    "https://youtube.com/watch?v=test2",
                ],
            )
            # Should return 1 for partial failure
            assert result.exit_code == 1

    def test_batch_all_success_exit_zero(self, runner: CliRunner, cli_app: Any) -> None:
        """Test all successful downloads return exit code 0."""
        with patch("yt_audio_cli.cli.process_urls") as mock_process:
            mock_process.return_value = 0
            result = runner.invoke(
                cli_app,
                [
                    "https://youtube.com/watch?v=test1",
                    "https://youtube.com/watch?v=test2",
                ],
            )
            assert result.exit_code == 0


class TestBatchFailureHandling:
    """Tests for batch failure handling (US2)."""

    def test_process_urls_partial_success(self) -> None:
        """Test process_urls handles partial success correctly."""
        from yt_audio_cli.cli import process_urls

        with (
            patch("yt_audio_cli.cli.process_single_url") as mock_process,
            patch("yt_audio_cli.cli.print_info"),
        ):
            # Simulate first succeeds, second fails
            mock_process.side_effect = [True, False]

            from pathlib import Path

            exit_code = process_urls(
                urls=["https://test1.com", "https://test2.com"],
                audio_format="mp3",
                output_dir=Path("/tmp"),
                bitrate=320,
                embed_metadata=True,
            )

            # Should return 1 for partial failure
            assert exit_code == 1

    def test_process_urls_all_fail(self) -> None:
        """Test process_urls when all downloads fail."""
        from yt_audio_cli.cli import process_urls

        with (
            patch("yt_audio_cli.cli.process_single_url") as mock_process,
            patch("yt_audio_cli.cli.print_info"),
        ):
            mock_process.return_value = False

            from pathlib import Path

            exit_code = process_urls(
                urls=["https://test1.com", "https://test2.com"],
                audio_format="mp3",
                output_dir=Path("/tmp"),
                bitrate=320,
                embed_metadata=True,
            )

            # Should return 1 for all failures
            assert exit_code == 1

    def test_process_urls_all_success(self) -> None:
        """Test process_urls when all downloads succeed."""
        from yt_audio_cli.cli import process_urls

        with (
            patch("yt_audio_cli.cli.process_single_url") as mock_process,
            patch("yt_audio_cli.cli.print_info"),
        ):
            mock_process.return_value = True

            from pathlib import Path

            exit_code = process_urls(
                urls=["https://test1.com", "https://test2.com"],
                audio_format="mp3",
                output_dir=Path("/tmp"),
                bitrate=320,
                embed_metadata=True,
            )

            # Should return 0 for all success
            assert exit_code == 0


class TestPlaylistDownload:
    """Tests for playlist download functionality (US3)."""

    def test_playlist_url_expansion(self) -> None:
        """Test playlist URLs are expanded to video URLs."""
        from yt_audio_cli.cli import expand_playlist_urls

        with (
            patch("yt_audio_cli.cli.is_playlist") as mock_is_playlist,
            patch("yt_audio_cli.cli.extract_playlist") as mock_extract,
            patch("yt_audio_cli.cli.print_info"),
        ):
            mock_is_playlist.side_effect = [True, False]
            mock_extract.return_value = [
                "https://youtube.com/watch?v=video1",
                "https://youtube.com/watch?v=video2",
            ]

            result = expand_playlist_urls(
                [
                    "https://youtube.com/playlist?list=PLtest",
                    "https://youtube.com/watch?v=single",
                ]
            )

            # Should have 3 URLs: 2 from playlist + 1 single
            assert len(result) == 3
            assert "https://youtube.com/watch?v=video1" in result
            assert "https://youtube.com/watch?v=video2" in result
            assert "https://youtube.com/watch?v=single" in result

    def test_playlist_extraction_failure_fallback(self) -> None:
        """Test fallback to single URL when playlist extraction fails."""
        from yt_audio_cli.cli import expand_playlist_urls

        with (
            patch("yt_audio_cli.cli.is_playlist") as mock_is_playlist,
            patch("yt_audio_cli.cli.extract_playlist") as mock_extract,
            patch("yt_audio_cli.cli.print_info"),
        ):
            mock_is_playlist.return_value = True
            mock_extract.return_value = []  # Extraction failed

            result = expand_playlist_urls(["https://youtube.com/playlist?list=PLtest"])

            # Should fall back to original URL
            assert len(result) == 1
            assert result[0] == "https://youtube.com/playlist?list=PLtest"

    def test_non_playlist_url_passthrough(self) -> None:
        """Test non-playlist URLs are passed through unchanged."""
        from yt_audio_cli.cli import expand_playlist_urls

        with patch("yt_audio_cli.cli.is_playlist") as mock_is_playlist:
            mock_is_playlist.return_value = False

            result = expand_playlist_urls(
                [
                    "https://youtube.com/watch?v=test1",
                    "https://youtube.com/watch?v=test2",
                ]
            )

            assert len(result) == 2
            assert result[0] == "https://youtube.com/watch?v=test1"
            assert result[1] == "https://youtube.com/watch?v=test2"


class TestQualitySelection:
    """Tests for quality selection functionality (US4)."""

    def test_quality_presets(self) -> None:
        """Test quality presets resolve to correct bitrates."""
        from yt_audio_cli.cli import resolve_quality

        # Test best quality
        assert resolve_quality("best", None, "mp3") == 320
        assert resolve_quality("best", None, "aac") == 256
        assert resolve_quality("best", None, "opus") == 192
        assert resolve_quality("best", None, "wav") is None

        # Test good quality
        assert resolve_quality("good", None, "mp3") == 192
        assert resolve_quality("good", None, "aac") == 160

        # Test small quality
        assert resolve_quality("small", None, "mp3") == 128
        assert resolve_quality("small", None, "opus") == 64

    def test_bitrate_overrides_quality(self) -> None:
        """Test explicit bitrate overrides quality preset."""
        from yt_audio_cli.cli import resolve_quality

        # Explicit bitrate should take precedence
        assert resolve_quality("best", 128, "mp3") == 128
        assert resolve_quality("small", 320, "mp3") == 320

    def test_default_quality_is_best(self) -> None:
        """Test default quality is 'best'."""
        from yt_audio_cli.cli import resolve_quality

        # None for quality should default to best
        assert resolve_quality(None, None, "mp3") == 320


class TestMetadataEmbedding:
    """Tests for metadata embedding functionality (US5)."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def cli_app(self) -> Any:
        """Get the CLI app for testing."""
        from yt_audio_cli.cli import app

        return app

    def test_no_metadata_flag_parsing(self, runner: CliRunner, cli_app: Any) -> None:
        """Test --no-metadata flag is parsed."""
        with patch("yt_audio_cli.cli.process_urls") as mock_process:
            mock_process.return_value = 0
            result = runner.invoke(
                cli_app,
                ["--no-metadata", "https://youtube.com/watch?v=test"],
            )
            assert result.exit_code == 0
            # Verify embed_metadata is False
            call_args = mock_process.call_args
            assert call_args[1]["embed_metadata"] is False

    def test_metadata_embedded_by_default(
        self, runner: CliRunner, cli_app: Any
    ) -> None:
        """Test metadata is embedded by default."""
        with patch("yt_audio_cli.cli.process_urls") as mock_process:
            mock_process.return_value = 0
            result = runner.invoke(
                cli_app,
                ["https://youtube.com/watch?v=test"],
            )
            assert result.exit_code == 0
            # Verify embed_metadata is True by default
            call_args = mock_process.call_args
            assert call_args[1]["embed_metadata"] is True


class TestCheckExists:
    """Tests for _check_exists() helper function."""

    def test_returns_true_when_file_exists(self, temp_dir: Any) -> None:
        """Test returns True when output file already exists."""
        from pathlib import Path

        from yt_audio_cli.cli import _check_exists

        # Create existing file
        (temp_dir / "Test_Video.mp3").touch()

        with patch("yt_audio_cli.cli.extract_metadata") as mock_extract:
            mock_extract.return_value = {"title": "Test Video"}
            result = _check_exists("https://test.com", "mp3", Path(temp_dir))
            assert result is True

    def test_returns_false_when_file_missing(self, temp_dir: Any) -> None:
        """Test returns False when output file doesn't exist."""
        from pathlib import Path

        from yt_audio_cli.cli import _check_exists

        with patch("yt_audio_cli.cli.extract_metadata") as mock_extract:
            mock_extract.return_value = {"title": "Test Video"}
            result = _check_exists("https://test.com", "mp3", Path(temp_dir))
            assert result is False

    def test_returns_false_when_metadata_extraction_fails(self, temp_dir: Any) -> None:
        """Test returns False when metadata extraction fails."""
        from pathlib import Path

        from yt_audio_cli.cli import _check_exists

        with patch("yt_audio_cli.cli.extract_metadata") as mock_extract:
            mock_extract.return_value = None
            result = _check_exists("https://test.com", "mp3", Path(temp_dir))
            assert result is False

    def test_returns_false_when_title_empty(self, temp_dir: Any) -> None:
        """Test returns False when title is empty."""
        from pathlib import Path

        from yt_audio_cli.cli import _check_exists

        with patch("yt_audio_cli.cli.extract_metadata") as mock_extract:
            mock_extract.return_value = {"title": ""}
            result = _check_exists("https://test.com", "mp3", Path(temp_dir))
            assert result is False

    def test_returns_false_when_sanitized_filename_empty(self, temp_dir: Any) -> None:
        """Test returns False when sanitized filename is empty (special chars only)."""
        from pathlib import Path

        from yt_audio_cli.cli import _check_exists

        with (
            patch("yt_audio_cli.cli.extract_metadata") as mock_extract,
            patch("yt_audio_cli.cli.sanitize") as mock_sanitize,
        ):
            mock_extract.return_value = {"title": "***"}
            mock_sanitize.return_value = ""  # sanitize returns empty for special chars
            result = _check_exists("https://test.com", "mp3", Path(temp_dir))
            assert result is False


class TestFilterExistingUrls:
    """Tests for _filter_existing_urls() helper function."""

    def test_filters_out_existing_files(self, temp_dir: Any) -> None:
        """Test filters out URLs with existing files."""
        from pathlib import Path

        from yt_audio_cli.cli import _filter_existing_urls

        # Create existing file for first URL
        (temp_dir / "Video_1.mp3").touch()

        with patch("yt_audio_cli.cli.extract_metadata") as mock_extract:
            mock_extract.side_effect = [
                {"title": "Video 1"},  # exists
                {"title": "Video 2"},  # doesn't exist
                {"title": "Video 3"},  # doesn't exist
            ]
            urls = ["https://test.com/1", "https://test.com/2", "https://test.com/3"]
            result, skipped = _filter_existing_urls(urls, "mp3", Path(temp_dir))

            assert len(result) == 2
            assert skipped == 1
            assert "https://test.com/2" in result
            assert "https://test.com/3" in result

    def test_returns_all_urls_when_none_exist(self, temp_dir: Any) -> None:
        """Test returns all URLs when no files exist."""
        from pathlib import Path

        from yt_audio_cli.cli import _filter_existing_urls

        with patch("yt_audio_cli.cli.extract_metadata") as mock_extract:
            mock_extract.return_value = {"title": "New Video"}
            urls = ["https://test.com/1", "https://test.com/2"]
            result, skipped = _filter_existing_urls(urls, "mp3", Path(temp_dir))

            assert len(result) == 2
            assert skipped == 0

    def test_returns_empty_when_all_exist(self, temp_dir: Any) -> None:
        """Test returns empty list when all files exist."""
        from pathlib import Path

        from yt_audio_cli.cli import _filter_existing_urls

        # Create existing files
        (temp_dir / "Video_1.mp3").touch()
        (temp_dir / "Video_2.mp3").touch()

        with patch("yt_audio_cli.cli.extract_metadata") as mock_extract:
            mock_extract.side_effect = [{"title": "Video 1"}, {"title": "Video 2"}]
            urls = ["https://test.com/1", "https://test.com/2"]
            result, skipped = _filter_existing_urls(urls, "mp3", Path(temp_dir))

            assert len(result) == 0
            assert skipped == 2


class TestDownloadAudio:
    """Tests for _download_audio() helper function."""

    def test_successful_download(self, temp_dir: Any) -> None:
        """Test successful download returns result."""
        from pathlib import Path

        from yt_audio_cli.cli import _download_audio
        from yt_audio_cli.download import DownloadResult

        mock_result = DownloadResult(
            url="https://test.com",
            success=True,
            title="Test",
            artist="Artist",
            duration=120.0,
            temp_path=Path(temp_dir) / "test.webm",
            error=None,
        )

        with (
            patch("yt_audio_cli.cli.download") as mock_download,
            patch("yt_audio_cli.cli.create_download_progress"),
        ):
            mock_download.return_value = mock_result
            result = _download_audio("https://test.com", Path(temp_dir))
            assert result.success is True
            assert result.title == "Test"

    def test_download_with_progress_callback(self, temp_dir: Any) -> None:
        """Test download updates progress via callback."""
        from pathlib import Path
        from unittest.mock import MagicMock

        from yt_audio_cli.cli import _download_audio
        from yt_audio_cli.download import DownloadResult

        mock_result = DownloadResult(
            url="https://test.com",
            success=True,
            title="Test",
            artist="Artist",
            duration=120.0,
            temp_path=Path(temp_dir) / "test.webm",
            error=None,
        )

        mock_progress = MagicMock()
        mock_progress.__enter__ = MagicMock(return_value=mock_progress)
        mock_progress.__exit__ = MagicMock(return_value=False)
        mock_progress.add_task = MagicMock(return_value=1)

        with (
            patch("yt_audio_cli.cli.download") as mock_download,
            patch(
                "yt_audio_cli.cli.create_download_progress",
                return_value=mock_progress,
            ),
        ):
            mock_download.return_value = mock_result
            _download_audio("https://test.com", Path(temp_dir))

            # Verify progress.add_task was called
            mock_progress.add_task.assert_called_once()


class TestConvertAudio:
    """Tests for _convert_audio() helper function."""

    def test_successful_conversion(self, temp_dir: Any) -> None:
        """Test successful conversion returns output path."""
        from pathlib import Path
        from unittest.mock import MagicMock

        from yt_audio_cli.cli import _convert_audio
        from yt_audio_cli.download import DownloadResult

        # Create temp input file
        temp_file = Path(temp_dir) / "input.webm"
        temp_file.touch()

        result = DownloadResult(
            url="https://test.com",
            success=True,
            title="Test Song",
            artist="Test Artist",
            duration=120.0,
            temp_path=temp_file,
            error=None,
        )

        mock_progress = MagicMock()
        mock_progress.__enter__ = MagicMock(return_value=mock_progress)
        mock_progress.__exit__ = MagicMock(return_value=False)
        mock_progress.add_task = MagicMock(return_value=1)

        with (
            patch("yt_audio_cli.cli.transcode") as mock_transcode,
            patch(
                "yt_audio_cli.cli.create_conversion_progress",
                return_value=mock_progress,
            ),
        ):
            output_path = _convert_audio(result, Path(temp_dir), "mp3", 320, True)
            assert output_path is not None
            assert output_path.suffix == ".mp3"
            mock_transcode.assert_called_once()

    def test_conversion_with_ffmpeg_not_found(self, temp_dir: Any) -> None:
        """Test conversion handles FFmpegNotFoundError."""
        from pathlib import Path
        from unittest.mock import MagicMock

        from yt_audio_cli.cli import _convert_audio
        from yt_audio_cli.core import FFmpegNotFoundError
        from yt_audio_cli.download import DownloadResult

        temp_file = Path(temp_dir) / "input.webm"
        temp_file.touch()

        result = DownloadResult(
            url="https://test.com",
            success=True,
            title="Test",
            artist="Artist",
            duration=120.0,
            temp_path=temp_file,
            error=None,
        )

        mock_progress = MagicMock()
        mock_progress.__enter__ = MagicMock(return_value=mock_progress)
        mock_progress.__exit__ = MagicMock(return_value=False)
        mock_progress.add_task = MagicMock(return_value=1)

        with (
            patch("yt_audio_cli.cli.transcode") as mock_transcode,
            patch(
                "yt_audio_cli.cli.create_conversion_progress",
                return_value=mock_progress,
            ),
            patch("yt_audio_cli.cli.print_error"),
        ):
            mock_transcode.side_effect = FFmpegNotFoundError()
            output_path = _convert_audio(result, Path(temp_dir), "mp3", 320, True)
            assert output_path is None

    def test_conversion_with_generic_error(self, temp_dir: Any) -> None:
        """Test conversion handles generic errors."""
        from pathlib import Path
        from unittest.mock import MagicMock

        from yt_audio_cli.cli import _convert_audio
        from yt_audio_cli.download import DownloadResult

        temp_file = Path(temp_dir) / "input.webm"
        temp_file.touch()

        result = DownloadResult(
            url="https://test.com",
            success=True,
            title="Test",
            artist="Artist",
            duration=120.0,
            temp_path=temp_file,
            error=None,
        )

        mock_progress = MagicMock()
        mock_progress.__enter__ = MagicMock(return_value=mock_progress)
        mock_progress.__exit__ = MagicMock(return_value=False)
        mock_progress.add_task = MagicMock(return_value=1)

        with (
            patch("yt_audio_cli.cli.transcode") as mock_transcode,
            patch(
                "yt_audio_cli.cli.create_conversion_progress",
                return_value=mock_progress,
            ),
            patch("yt_audio_cli.cli.print_error"),
        ):
            mock_transcode.side_effect = RuntimeError("Unknown error")
            output_path = _convert_audio(result, Path(temp_dir), "mp3", 320, True)
            assert output_path is None

    def test_conversion_without_metadata(self, temp_dir: Any) -> None:
        """Test conversion without embedding metadata."""
        from pathlib import Path
        from unittest.mock import MagicMock

        from yt_audio_cli.cli import _convert_audio
        from yt_audio_cli.download import DownloadResult

        temp_file = Path(temp_dir) / "input.webm"
        temp_file.touch()

        result = DownloadResult(
            url="https://test.com",
            success=True,
            title="Test",
            artist="Artist",
            duration=120.0,
            temp_path=temp_file,
            error=None,
        )

        mock_progress = MagicMock()
        mock_progress.__enter__ = MagicMock(return_value=mock_progress)
        mock_progress.__exit__ = MagicMock(return_value=False)
        mock_progress.add_task = MagicMock(return_value=1)

        with (
            patch("yt_audio_cli.cli.transcode") as mock_transcode,
            patch(
                "yt_audio_cli.cli.create_conversion_progress",
                return_value=mock_progress,
            ),
        ):
            _convert_audio(result, Path(temp_dir), "mp3", 320, False)
            # Verify metadata is empty when embed_metadata=False
            call_kwargs = mock_transcode.call_args[1]
            assert call_kwargs["metadata"] == {}


class TestProcessSingleUrl:
    """Tests for process_single_url() function."""

    def test_successful_download_and_conversion(self, temp_dir: Any) -> None:
        """Test successful download and conversion flow."""
        from pathlib import Path

        from yt_audio_cli.cli import process_single_url
        from yt_audio_cli.download import DownloadResult

        mock_result = DownloadResult(
            url="https://test.com",
            success=True,
            title="Test",
            artist="Artist",
            duration=120.0,
            temp_path=Path(temp_dir) / "test.webm",
            error=None,
        )

        with (
            patch("yt_audio_cli.cli._download_audio") as mock_download,
            patch("yt_audio_cli.cli._convert_audio") as mock_convert,
            patch("yt_audio_cli.cli.print_success"),
            patch("tempfile.TemporaryDirectory") as mock_tempdir,
        ):
            mock_tempdir.return_value.__enter__ = lambda s: str(temp_dir)
            mock_tempdir.return_value.__exit__ = lambda s, *args: None
            mock_download.return_value = mock_result
            mock_result.temp_path.touch()
            mock_convert.return_value = Path(temp_dir) / "test.mp3"

            success = process_single_url(
                "https://test.com",
                "mp3",
                Path(temp_dir),
                320,
                True,
            )
            assert success is True

    def test_download_failure(self, temp_dir: Any) -> None:
        """Test handles download failure."""
        from pathlib import Path

        from yt_audio_cli.cli import process_single_url
        from yt_audio_cli.download import DownloadResult

        mock_result = DownloadResult(
            url="https://test.com",
            success=False,
            title="",
            artist="",
            duration=0.0,
            temp_path=Path(temp_dir) / "test.webm",
            error="Connection failed",
        )

        with (
            patch("yt_audio_cli.cli._download_audio") as mock_download,
            patch("yt_audio_cli.cli.print_error"),
            patch("tempfile.TemporaryDirectory") as mock_tempdir,
        ):
            mock_tempdir.return_value.__enter__ = lambda s: str(temp_dir)
            mock_tempdir.return_value.__exit__ = lambda s, *args: None
            mock_download.return_value = mock_result

            success = process_single_url(
                "https://test.com",
                "mp3",
                Path(temp_dir),
                320,
                True,
            )
            assert success is False

    def test_temp_file_not_found(self, temp_dir: Any) -> None:
        """Test handles missing temp file after download."""
        from pathlib import Path

        from yt_audio_cli.cli import process_single_url
        from yt_audio_cli.download import DownloadResult

        mock_result = DownloadResult(
            url="https://test.com",
            success=True,
            title="Test",
            artist="Artist",
            duration=120.0,
            temp_path=Path(temp_dir) / "nonexistent.webm",
            error=None,
        )

        with (
            patch("yt_audio_cli.cli._download_audio") as mock_download,
            patch("yt_audio_cli.cli.print_error"),
            patch("tempfile.TemporaryDirectory") as mock_tempdir,
        ):
            mock_tempdir.return_value.__enter__ = lambda s: str(temp_dir)
            mock_tempdir.return_value.__exit__ = lambda s, *args: None
            mock_download.return_value = mock_result
            # Don't create the temp file

            success = process_single_url(
                "https://test.com",
                "mp3",
                Path(temp_dir),
                320,
                True,
            )
            assert success is False

    def test_conversion_failure(self, temp_dir: Any) -> None:
        """Test handles conversion failure."""
        from pathlib import Path

        from yt_audio_cli.cli import process_single_url
        from yt_audio_cli.download import DownloadResult

        mock_result = DownloadResult(
            url="https://test.com",
            success=True,
            title="Test",
            artist="Artist",
            duration=120.0,
            temp_path=Path(temp_dir) / "test.webm",
            error=None,
        )

        with (
            patch("yt_audio_cli.cli._download_audio") as mock_download,
            patch("yt_audio_cli.cli._convert_audio") as mock_convert,
            patch("tempfile.TemporaryDirectory") as mock_tempdir,
        ):
            mock_tempdir.return_value.__enter__ = lambda s: str(temp_dir)
            mock_tempdir.return_value.__exit__ = lambda s, *args: None
            mock_download.return_value = mock_result
            mock_result.temp_path.touch()
            mock_convert.return_value = None  # Conversion failed

            success = process_single_url(
                "https://test.com",
                "mp3",
                Path(temp_dir),
                320,
                True,
            )
            assert success is False


class TestProcessUrlsSkipScenarios:
    """Tests for process_urls() skip and filter scenarios."""

    def test_skipped_files_shows_warning(self, temp_dir: Any) -> None:
        """Test shows warning when files are skipped."""
        from pathlib import Path

        from yt_audio_cli.cli import process_urls

        with (
            patch("yt_audio_cli.cli.expand_playlist_urls") as mock_expand,
            patch("yt_audio_cli.cli._filter_existing_urls") as mock_filter,
            patch("yt_audio_cli.cli.process_single_url") as mock_process,
            patch("yt_audio_cli.cli.print_info"),
            patch("yt_audio_cli.cli.print_warning") as mock_warning,
        ):
            mock_expand.return_value = ["https://test.com/1", "https://test.com/2"]
            mock_filter.return_value = (["https://test.com/2"], 1)  # 1 skipped
            mock_process.return_value = True

            process_urls(
                urls=["https://test.com/1", "https://test.com/2"],
                audio_format="mp3",
                output_dir=Path(temp_dir),
                bitrate=320,
                embed_metadata=True,
                force=False,
            )

            mock_warning.assert_called_once_with("Skipped 1 already downloaded")

    def test_nothing_to_download_when_all_skipped(self, temp_dir: Any) -> None:
        """Test returns 0 when all files already exist."""
        from pathlib import Path

        from yt_audio_cli.cli import process_urls

        with (
            patch("yt_audio_cli.cli.expand_playlist_urls") as mock_expand,
            patch("yt_audio_cli.cli._filter_existing_urls") as mock_filter,
            patch("yt_audio_cli.cli.print_info") as mock_info,
        ):
            mock_expand.return_value = ["https://test.com/1", "https://test.com/2"]
            mock_filter.return_value = ([], 2)  # All skipped

            exit_code = process_urls(
                urls=["https://test.com/1", "https://test.com/2"],
                audio_format="mp3",
                output_dir=Path(temp_dir),
                bitrate=320,
                embed_metadata=True,
                force=False,
            )

            assert exit_code == 0
            mock_info.assert_any_call("Nothing to download")

    def test_single_url_after_filtering(self, temp_dir: Any) -> None:
        """Test single URL path after filtering out existing files."""
        from pathlib import Path

        from yt_audio_cli.cli import process_urls

        with (
            patch("yt_audio_cli.cli.expand_playlist_urls") as mock_expand,
            patch("yt_audio_cli.cli._filter_existing_urls") as mock_filter,
            patch("yt_audio_cli.cli.process_single_url") as mock_process,
            patch("yt_audio_cli.cli.print_info"),
            patch("yt_audio_cli.cli.print_warning"),
        ):
            mock_expand.return_value = ["https://test.com/1", "https://test.com/2"]
            mock_filter.return_value = (["https://test.com/2"], 1)  # Only 1 remains
            mock_process.return_value = True

            exit_code = process_urls(
                urls=["https://test.com/1", "https://test.com/2"],
                audio_format="mp3",
                output_dir=Path(temp_dir),
                bitrate=320,
                embed_metadata=True,
                force=False,
            )

            assert exit_code == 0
            mock_process.assert_called_once()

    def test_force_skips_filtering(self, temp_dir: Any) -> None:
        """Test force=True skips the filtering step."""
        from pathlib import Path

        from yt_audio_cli.cli import process_urls

        with (
            patch("yt_audio_cli.cli.expand_playlist_urls") as mock_expand,
            patch("yt_audio_cli.cli._filter_existing_urls") as mock_filter,
            patch("yt_audio_cli.cli.process_single_url") as mock_process,
            patch("yt_audio_cli.cli.print_info"),
        ):
            mock_expand.return_value = ["https://test.com/1", "https://test.com/2"]
            mock_process.return_value = True

            process_urls(
                urls=["https://test.com/1", "https://test.com/2"],
                audio_format="mp3",
                output_dir=Path(temp_dir),
                bitrate=320,
                embed_metadata=True,
                force=True,
            )

            # Filter should not be called when force=True
            mock_filter.assert_not_called()

    def test_summary_includes_skip_count(self, temp_dir: Any) -> None:
        """Test summary includes skip count when files were skipped."""
        from pathlib import Path

        from yt_audio_cli.cli import process_urls

        with (
            patch("yt_audio_cli.cli.expand_playlist_urls") as mock_expand,
            patch("yt_audio_cli.cli._filter_existing_urls") as mock_filter,
            patch("yt_audio_cli.cli.process_single_url") as mock_process,
            patch("yt_audio_cli.cli.print_info") as mock_info,
            patch("yt_audio_cli.cli.print_warning"),
        ):
            mock_expand.return_value = [
                "https://test.com/1",
                "https://test.com/2",
                "https://test.com/3",
            ]
            # 1 skipped, 2 to process
            mock_filter.return_value = (
                ["https://test.com/2", "https://test.com/3"],
                1,
            )
            mock_process.return_value = True

            process_urls(
                urls=["https://test.com/1", "https://test.com/2", "https://test.com/3"],
                audio_format="mp3",
                output_dir=Path(temp_dir),
                bitrate=320,
                embed_metadata=True,
                force=False,
            )

            # Check summary includes skip count
            summary_calls = [
                call for call in mock_info.call_args_list if "skipped" in str(call)
            ]
            assert len(summary_calls) == 1


class TestProgressCallbacks:
    """Tests for progress callback execution in download/convert."""

    def test_download_callback_with_total(self, temp_dir: Any) -> None:
        """Test download progress callback when total is known."""
        from pathlib import Path
        from unittest.mock import MagicMock

        from yt_audio_cli.cli import _download_audio
        from yt_audio_cli.download import DownloadResult

        mock_result = DownloadResult(
            url="https://test.com",
            success=True,
            title="Test",
            artist="Artist",
            duration=120.0,
            temp_path=Path(temp_dir) / "test.webm",
            error=None,
        )

        mock_progress = MagicMock()
        mock_progress.__enter__ = MagicMock(return_value=mock_progress)
        mock_progress.__exit__ = MagicMock(return_value=False)
        mock_progress.add_task = MagicMock(return_value=1)

        captured_callback = None

        def capture_callback(**kwargs: Any) -> DownloadResult:
            nonlocal captured_callback
            captured_callback = kwargs.get("progress_callback")
            return mock_result

        with (
            patch("yt_audio_cli.cli.download", side_effect=capture_callback),
            patch(
                "yt_audio_cli.cli.create_download_progress",
                return_value=mock_progress,
            ),
        ):
            _download_audio("https://test.com", Path(temp_dir))

            # Call the callback with total > 0
            assert captured_callback is not None  # NOSONAR - modified by closure
            captured_callback(1000, 5000)
            mock_progress.update.assert_called_with(1, completed=1000, total=5000)

    def test_download_callback_without_total(self, temp_dir: Any) -> None:
        """Test download progress callback when total is unknown."""
        from pathlib import Path
        from unittest.mock import MagicMock

        from yt_audio_cli.cli import _download_audio
        from yt_audio_cli.download import DownloadResult

        mock_result = DownloadResult(
            url="https://test.com",
            success=True,
            title="Test",
            artist="Artist",
            duration=120.0,
            temp_path=Path(temp_dir) / "test.webm",
            error=None,
        )

        mock_progress = MagicMock()
        mock_progress.__enter__ = MagicMock(return_value=mock_progress)
        mock_progress.__exit__ = MagicMock(return_value=False)
        mock_progress.add_task = MagicMock(return_value=1)

        captured_callback = None

        def capture_callback(**kwargs: Any) -> DownloadResult:
            nonlocal captured_callback
            captured_callback = kwargs.get("progress_callback")
            return mock_result

        with (
            patch("yt_audio_cli.cli.download", side_effect=capture_callback),
            patch(
                "yt_audio_cli.cli.create_download_progress",
                return_value=mock_progress,
            ),
        ):
            _download_audio("https://test.com", Path(temp_dir))

            # Call the callback with total = 0
            assert captured_callback is not None  # NOSONAR - modified by closure
            captured_callback(1000, 0)
            mock_progress.update.assert_called_with(1, completed=1000)

    def test_convert_callback_updates_progress(self, temp_dir: Any) -> None:
        """Test conversion progress callback updates task."""
        from pathlib import Path
        from unittest.mock import MagicMock

        from yt_audio_cli.cli import _convert_audio
        from yt_audio_cli.download import DownloadResult

        temp_file = Path(temp_dir) / "input.webm"
        temp_file.touch()

        result = DownloadResult(
            url="https://test.com",
            success=True,
            title="Test",
            artist="Artist",
            duration=120.0,
            temp_path=temp_file,
            error=None,
        )

        mock_progress = MagicMock()
        mock_progress.__enter__ = MagicMock(return_value=mock_progress)
        mock_progress.__exit__ = MagicMock(return_value=False)
        mock_progress.add_task = MagicMock(return_value=1)

        captured_callback = None

        def capture_callback(**kwargs: Any) -> None:
            nonlocal captured_callback
            captured_callback = kwargs.get("progress_callback")

        with (
            patch("yt_audio_cli.cli.transcode", side_effect=capture_callback),
            patch(
                "yt_audio_cli.cli.create_conversion_progress",
                return_value=mock_progress,
            ),
        ):
            _convert_audio(result, Path(temp_dir), "mp3", 320, True)

            # Call the callback
            assert captured_callback is not None  # NOSONAR - modified by closure
            captured_callback(60.0)
            mock_progress.update.assert_called_with(1, completed=60.0)
