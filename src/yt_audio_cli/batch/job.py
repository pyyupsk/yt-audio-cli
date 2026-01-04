"""Download job entity for batch processing."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Literal


class JobStatus(Enum):
    """Status of a download job."""

    PENDING = "pending"
    ACTIVE = "active"
    COMPLETE = "complete"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class DownloadJob:
    """Single download task in a batch.

    Attributes:
        url: The URL to download.
        output_dir: Directory for output files.
        format: Target audio format.
        status: Current job status.
        retry_count: Number of retry attempts made.
        error_message: Error message if job failed.
        output_path: Path to the output file if successful.
        current_percent: Current download progress (0-100).
        current_title: Title of the current download.
    """

    url: str
    output_dir: Path
    format: str = "mp3"

    # Runtime state
    status: JobStatus = field(default=JobStatus.PENDING)
    retry_count: int = 0
    error_message: str | None = None
    output_path: Path | None = None

    # Progress tracking (lightweight, no history)
    current_percent: int = 0
    current_title: str = ""

    def __post_init__(self) -> None:
        """Validate job fields after initialization."""
        if not self.url.startswith(("http://", "https://")):
            raise ValueError(f"Invalid URL: {self.url}")
        if self.retry_count < 0:
            raise ValueError(f"retry_count must be >= 0, got {self.retry_count}")
        if not 0 <= self.current_percent <= 100:
            self.current_percent = max(0, min(100, self.current_percent))

    def mark_active(self, title: str = "") -> None:
        """Mark job as active (started downloading)."""
        self.status = JobStatus.ACTIVE
        self.current_percent = 0
        if title:
            self.current_title = title

    def mark_complete(self, output_path: Path) -> None:
        """Mark job as successfully completed."""
        self.status = JobStatus.COMPLETE
        self.output_path = output_path
        self.current_percent = 100
        self.error_message = None

    def mark_failed(self, error: str) -> None:
        """Mark job as failed."""
        self.status = JobStatus.FAILED
        self.error_message = error

    def mark_cancelled(self) -> None:
        """Mark job as cancelled."""
        self.status = JobStatus.CANCELLED

    def update_progress(self, percent: int, title: str = "") -> None:
        """Update download progress."""
        self.current_percent = max(0, min(100, percent))
        if title:
            self.current_title = title

    def increment_retry(self) -> None:
        """Increment retry count and reset for retry."""
        self.retry_count += 1
        self.status = JobStatus.PENDING
        self.current_percent = 0
        self.error_message = None


@dataclass(frozen=True)
class ProgressUpdate:
    """Progress update message from worker to display.

    Immutable message for thread-safe producer-consumer pattern.

    Attributes:
        worker_id: ID of the worker sending the update.
        job_url: URL of the job being processed.
        event: Type of progress event.
        percent: Download progress percentage (for "progress" events).
        title: Title of the content being downloaded.
        error: Error message (for "failed" events).
    """

    worker_id: int
    job_url: str
    event: Literal["started", "progress", "complete", "failed"]

    # Only for "progress" events
    percent: int = 0
    title: str = ""

    # Only for "failed" events
    error: str = ""
