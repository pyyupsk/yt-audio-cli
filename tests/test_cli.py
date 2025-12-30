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
