"""Rich progress display for yt-audio-cli."""

from __future__ import annotations

from rich.console import Console
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

# Global console instance for consistent output
console = Console()


def create_progress() -> Progress:
    """Create Rich progress display with download and conversion tasks.

    Returns:
        Configured Progress instance.
    """
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
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
        TextColumn("[bold blue]{task.description}"),
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
