"""Rich progress display for yt-audio-cli."""

from __future__ import annotations

from rich.console import Console
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    ProgressColumn,
    SpinnerColumn,
    Task,
    TaskID,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from rich.text import Text

# Global console instance for consistent output
console = Console()

# Common progress format strings
_TASK_DESCRIPTION_FORMAT = "[bold blue]{task.description}"


class TimeProgressColumn(ProgressColumn):
    """Display time progress as elapsed / total (e.g., '0:45 / 3:20').

    For conversion progress, displays processed time vs total duration.
    When total is None or 0, shows only elapsed time.
    """

    def render(self, task: Task) -> Text:
        """Render the time progress column.

        Args:
            task: The Rich Task to render progress for.

        Returns:
            Text object with formatted time progress.
        """
        elapsed = task.completed or 0

        if task.total is None or task.total == 0:
            return Text(self._format_time(elapsed), style="progress.elapsed")

        return Text(
            f"{self._format_time(elapsed)} / {self._format_time(task.total)}",
            style="progress.elapsed",
        )

    def _format_time(self, seconds: float) -> str:
        """Format seconds as M:SS or H:MM:SS.

        Args:
            seconds: Time in seconds to format.

        Returns:
            Formatted time string.
        """
        total_secs = int(seconds)
        minutes, secs = divmod(total_secs, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"


def create_progress() -> Progress:
    """Create Rich progress display with download and conversion tasks.

    Returns:
        Configured Progress instance.

    Note:
        Deprecated. Use create_download_progress() or create_conversion_progress().
    """
    return Progress(
        SpinnerColumn(),
        TextColumn(_TASK_DESCRIPTION_FORMAT),
        BarColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        console=console,
        transient=True,
    )


def create_download_progress() -> Progress:
    """Create Rich progress display for download phase (byte-based).

    Displays: spinner, description, progress bar, downloaded/total bytes,
    transfer speed, and estimated time remaining.

    Returns:
        Configured Progress instance for download operations.
    """
    return Progress(
        SpinnerColumn(),
        TextColumn(_TASK_DESCRIPTION_FORMAT),
        BarColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        console=console,
        transient=True,
    )


def create_conversion_progress() -> Progress:
    """Create Rich progress display for conversion phase (time-based).

    Displays: spinner, description, progress bar, processed/total time,
    and percentage complete.

    Returns:
        Configured Progress instance for conversion operations.
    """
    return Progress(
        SpinnerColumn(),
        TextColumn(_TASK_DESCRIPTION_FORMAT),
        BarColumn(),
        TimeProgressColumn(),
        TaskProgressColumn(),
        console=console,
        transient=True,
    )


def create_batch_progress() -> Progress:
    """Create Rich progress display for batch operations.

    Returns:
        Configured Progress instance for batch mode.
    """
    return Progress(
        SpinnerColumn(),
        TextColumn(_TASK_DESCRIPTION_FORMAT),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("({task.completed}/{task.total})"),
        console=console,
        transient=False,
    )


def update_download(
    progress: Progress,
    task_id: TaskID,
    downloaded: int,
    total: int,
) -> None:
    """Update download progress bar.

    Args:
        progress: The Progress instance.
        task_id: The task ID to update.
        downloaded: Bytes downloaded so far.
        total: Total bytes to download.
    """
    progress.update(task_id, completed=downloaded, total=total)


def print_success(message: str) -> None:
    """Print a success message.

    Args:
        message: The message to print.
    """
    console.print(f"[green]✓[/green] {message}")


def print_error(message: str) -> None:
    """Print an error message.

    Args:
        message: The message to print.
    """
    console.print(f"[red]✗[/red] {message}", style="red")


def print_warning(message: str) -> None:
    """Print a warning message.

    Args:
        message: The message to print.
    """
    console.print(f"[yellow]![/yellow] {message}", style="yellow")


def print_info(message: str) -> None:
    """Print an info message.

    Args:
        message: The message to print.
    """
    console.print(f"[blue]→[/blue] {message}")
