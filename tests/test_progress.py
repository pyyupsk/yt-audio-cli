"""Unit tests for progress module."""

from __future__ import annotations

from unittest.mock import MagicMock

from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)


class TestCreateDownloadProgress:
    """Tests for create_download_progress() factory function."""

    def test_returns_progress_instance(self) -> None:
        """Test that factory returns a Progress instance."""
        from yt_audio_cli.progress import create_download_progress

        progress = create_download_progress()
        assert isinstance(progress, Progress)

    def test_has_required_columns(self) -> None:
        """Test that download progress has all required columns."""
        from yt_audio_cli.progress import create_download_progress

        progress = create_download_progress()
        column_types = [type(col) for col in progress.columns]

        # Must have spinner, text, bar, download column, speed, and time remaining
        assert SpinnerColumn in column_types
        assert TextColumn in column_types
        assert BarColumn in column_types
        assert DownloadColumn in column_types
        assert TransferSpeedColumn in column_types
        assert TimeRemainingColumn in column_types

    def test_uses_console(self) -> None:
        """Test that progress uses the shared console instance."""
        from yt_audio_cli.progress import console, create_download_progress

        progress = create_download_progress()
        assert progress.console is console

    def test_can_add_task(self) -> None:
        """Test that a task can be added to the progress."""
        from yt_audio_cli.progress import create_download_progress

        with create_download_progress() as progress:
            task_id = progress.add_task("Downloading...", total=1000)
            assert task_id is not None

    def test_can_update_task(self) -> None:
        """Test that a task can be updated with progress."""
        from yt_audio_cli.progress import create_download_progress

        with create_download_progress() as progress:
            task_id = progress.add_task("Downloading...", total=1000)
            progress.update(task_id, completed=500)

            task = progress.tasks[0]
            assert task.completed == 500
            assert task.total == 1000


class TestCreateProgress:
    """Tests for deprecated create_progress() factory function."""

    def test_returns_progress_instance(self) -> None:
        """Test that factory returns a Progress instance."""
        from yt_audio_cli.progress import create_progress

        progress = create_progress()
        assert isinstance(progress, Progress)

    def test_has_download_columns(self) -> None:
        """Test that progress has download-style columns."""
        from yt_audio_cli.progress import create_progress

        progress = create_progress()
        column_types = [type(col) for col in progress.columns]

        assert DownloadColumn in column_types
        assert TransferSpeedColumn in column_types


class TestTimeProgressColumn:
    """Tests for TimeProgressColumn custom column."""

    def test_format_time_under_one_hour(self) -> None:
        """Test time formatting for durations under one hour."""
        from yt_audio_cli.progress import TimeProgressColumn

        column = TimeProgressColumn()

        # Test various times under an hour
        assert column._format_time(0) == "0:00"
        assert column._format_time(45) == "0:45"
        assert column._format_time(60) == "1:00"
        assert column._format_time(90) == "1:30"
        assert column._format_time(599) == "9:59"
        assert column._format_time(3599) == "59:59"

    def test_format_time_over_one_hour(self) -> None:
        """Test time formatting for durations over one hour."""
        from yt_audio_cli.progress import TimeProgressColumn

        column = TimeProgressColumn()

        assert column._format_time(3600) == "1:00:00"
        assert column._format_time(3661) == "1:01:01"
        assert column._format_time(7200) == "2:00:00"
        assert column._format_time(36000) == "10:00:00"

    def test_render_with_total(self) -> None:
        """Test rendering when total duration is known."""
        from yt_audio_cli.progress import TimeProgressColumn

        column = TimeProgressColumn()

        # Create mock task with known total
        mock_task = MagicMock()
        mock_task.completed = 45.0
        mock_task.total = 180.0

        result = column.render(mock_task)
        assert "0:45" in str(result)
        assert "3:00" in str(result)

    def test_render_without_total(self) -> None:
        """Test rendering when total duration is unknown."""
        from yt_audio_cli.progress import TimeProgressColumn

        column = TimeProgressColumn()

        # Create mock task without total
        mock_task = MagicMock()
        mock_task.completed = 45.0
        mock_task.total = None

        result = column.render(mock_task)
        text_str = str(result)
        assert "0:45" in text_str
        # Should not have "/" when total is None
        assert "/" not in text_str

    def test_render_with_zero_total(self) -> None:
        """Test rendering when total is zero (indeterminate)."""
        from yt_audio_cli.progress import TimeProgressColumn

        column = TimeProgressColumn()

        mock_task = MagicMock()
        mock_task.completed = 30.0
        mock_task.total = 0

        result = column.render(mock_task)
        text_str = str(result)
        assert "0:30" in text_str
        assert "/" not in text_str


class TestCreateConversionProgress:
    """Tests for create_conversion_progress() factory function."""

    def test_returns_progress_instance(self) -> None:
        """Test that factory returns a Progress instance."""
        from yt_audio_cli.progress import create_conversion_progress

        progress = create_conversion_progress()
        assert isinstance(progress, Progress)

    def test_has_required_columns(self) -> None:
        """Test that conversion progress has time-based columns."""
        from yt_audio_cli.progress import TimeProgressColumn, create_conversion_progress

        progress = create_conversion_progress()
        column_types = [type(col) for col in progress.columns]

        assert SpinnerColumn in column_types
        assert TextColumn in column_types
        assert BarColumn in column_types
        assert TimeProgressColumn in column_types
        assert TaskProgressColumn in column_types

    def test_does_not_have_download_columns(self) -> None:
        """Test that conversion progress does NOT have byte-based columns."""
        from yt_audio_cli.progress import create_conversion_progress

        progress = create_conversion_progress()
        column_types = [type(col) for col in progress.columns]

        # Should NOT have download-specific columns
        assert DownloadColumn not in column_types
        assert TransferSpeedColumn not in column_types

    def test_uses_console(self) -> None:
        """Test that progress uses the shared console instance."""
        from yt_audio_cli.progress import console, create_conversion_progress

        progress = create_conversion_progress()
        assert progress.console is console
