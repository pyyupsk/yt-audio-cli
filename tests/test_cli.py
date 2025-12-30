"""Unit tests for CLI argument parsing and integration."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

if TYPE_CHECKING:
    pass

# Import will work after CLI is implemented
# For now, we set up the structure


class TestCLIArgumentParsing:
    """Tests for CLI argument parsing."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def cli_app(self) -> MagicMock:
        """Get the CLI app for testing."""
        from yt_audio_cli.cli import app

        return app

    def test_help_flag(self, runner: CliRunner, cli_app: MagicMock) -> None:
        """Test --help flag shows help text."""
        result = runner.invoke(cli_app, ["--help"])
        assert result.exit_code == 0
        assert "URLS" in result.output or "urls" in result.output.lower()
        assert "--format" in result.output or "-f" in result.output
        assert "--output" in result.output or "-o" in result.output

    def test_version_flag(self, runner: CliRunner, cli_app: MagicMock) -> None:
        """Test --version flag shows version."""
        result = runner.invoke(cli_app, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_no_urls_shows_error(self, runner: CliRunner, cli_app: MagicMock) -> None:
        """Test that missing URLs shows error."""
        result = runner.invoke(cli_app, [])
        assert result.exit_code != 0

    def test_single_url_accepted(self, runner: CliRunner, cli_app: MagicMock) -> None:
        """Test single URL is accepted as argument."""
        with patch("yt_audio_cli.cli.process_urls") as mock_process:
            mock_process.return_value = 0
            result = runner.invoke(cli_app, ["https://youtube.com/watch?v=test"])
            # Should call process_urls with the URL
            assert mock_process.called or result.exit_code == 0

    def test_format_flag_default(self, runner: CliRunner, cli_app: MagicMock) -> None:
        """Test default format is mp3."""
        result = runner.invoke(cli_app, ["--help"])
        assert "mp3" in result.output.lower()

    def test_format_flag_short(self, runner: CliRunner, cli_app: MagicMock) -> None:
        """Test -f short flag for format."""
        with patch("yt_audio_cli.cli.process_urls") as mock_process:
            mock_process.return_value = 0
            result = runner.invoke(
                cli_app, ["-f", "opus", "https://youtube.com/watch?v=test"]
            )
            # Format should be accepted
            assert result.exit_code == 0 or mock_process.called

    def test_format_flag_long(self, runner: CliRunner, cli_app: MagicMock) -> None:
        """Test --format long flag."""
        with patch("yt_audio_cli.cli.process_urls") as mock_process:
            mock_process.return_value = 0
            result = runner.invoke(
                cli_app, ["--format", "aac", "https://youtube.com/watch?v=test"]
            )
            assert result.exit_code == 0 or mock_process.called

    def test_invalid_format_rejected(
        self, runner: CliRunner, cli_app: MagicMock
    ) -> None:
        """Test invalid format is rejected."""
        result = runner.invoke(
            cli_app, ["--format", "invalid", "https://youtube.com/watch?v=test"]
        )
        assert result.exit_code == 2 or "invalid" in result.output.lower()

    def test_output_flag_short(self, runner: CliRunner, cli_app: MagicMock) -> None:
        """Test -o short flag for output directory."""
        with patch("yt_audio_cli.cli.process_urls") as mock_process:
            mock_process.return_value = 0
            result = runner.invoke(
                cli_app, ["-o", "/tmp", "https://youtube.com/watch?v=test"]
            )
            assert result.exit_code == 0 or mock_process.called

    def test_output_flag_long(self, runner: CliRunner, cli_app: MagicMock) -> None:
        """Test --output long flag."""
        with patch("yt_audio_cli.cli.process_urls") as mock_process:
            mock_process.return_value = 0
            result = runner.invoke(
                cli_app, ["--output", "/tmp", "https://youtube.com/watch?v=test"]
            )
            assert result.exit_code == 0 or mock_process.called

    def test_output_nonexistent_directory_error(
        self, runner: CliRunner, cli_app: MagicMock
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
    def cli_app(self) -> MagicMock:
        """Get the CLI app for testing."""
        from yt_audio_cli.cli import app

        return app

    def test_success_exit_code_zero(
        self, runner: CliRunner, cli_app: MagicMock
    ) -> None:
        """Test successful download returns exit code 0."""
        with patch("yt_audio_cli.cli.process_urls") as mock_process:
            mock_process.return_value = 0
            result = runner.invoke(cli_app, ["https://youtube.com/watch?v=test"])
            assert result.exit_code == 0

    def test_download_failure_exit_code_one(
        self, runner: CliRunner, cli_app: MagicMock
    ) -> None:
        """Test download failure returns exit code 1."""
        with patch("yt_audio_cli.cli.process_urls") as mock_process:
            mock_process.return_value = 1
            result = runner.invoke(cli_app, ["https://youtube.com/watch?v=test"])
            assert result.exit_code == 1

    def test_config_error_exit_code_two(
        self, runner: CliRunner, cli_app: MagicMock
    ) -> None:
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
    def cli_app(self) -> MagicMock:
        """Get the CLI app for testing."""
        from yt_audio_cli.cli import app

        return app

    def test_multiple_urls_accepted(
        self, runner: CliRunner, cli_app: MagicMock
    ) -> None:
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
        self, runner: CliRunner, cli_app: MagicMock
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

    def test_batch_all_success_exit_zero(
        self, runner: CliRunner, cli_app: MagicMock
    ) -> None:
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
    def cli_app(self) -> MagicMock:
        """Get the CLI app for testing."""
        from yt_audio_cli.cli import app

        return app

    def test_no_metadata_flag_parsing(
        self, runner: CliRunner, cli_app: MagicMock
    ) -> None:
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
        self, runner: CliRunner, cli_app: MagicMock
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
