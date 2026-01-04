"""Batch request and result entities."""

from __future__ import annotations

import threading
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import ParseResult, parse_qs, urlparse

from yt_audio_cli.batch.job import DownloadJob, JobStatus

if TYPE_CHECKING:
    pass


@dataclass
class BatchRequest:
    """Collection of download jobs to process.

    Thread-safe aggregate counters for tracking batch progress.

    Attributes:
        jobs: List of download jobs to process.
        max_workers: Number of concurrent workers.
        max_retries: Maximum retry attempts per job.
    """

    jobs: list[DownloadJob] = field(default_factory=list)
    max_workers: int = 4
    max_retries: int = 3

    # Private thread-safe counters
    _completed: int = field(default=0, init=False, repr=False)
    _failed: int = field(default=0, init=False, repr=False)
    _cancelled: int = field(default=0, init=False, repr=False)
    _lock: threading.Lock = field(
        default_factory=threading.Lock, init=False, repr=False
    )

    def __post_init__(self) -> None:
        """Validate configuration."""
        if self.max_workers < 1:
            raise ValueError(f"max_workers must be >= 1, got {self.max_workers}")
        if self.max_workers > 16:
            raise ValueError(f"max_workers must be <= 16, got {self.max_workers}")
        if self.max_retries < 0:
            raise ValueError(f"max_retries must be >= 0, got {self.max_retries}")
        if self.max_retries > 10:
            raise ValueError(f"max_retries must be <= 10, got {self.max_retries}")

    @property
    def total(self) -> int:
        """Total number of jobs."""
        return len(self.jobs)

    @property
    def completed(self) -> int:
        """Number of successfully completed jobs (thread-safe)."""
        with self._lock:
            return self._completed

    @property
    def failed(self) -> int:
        """Number of failed jobs (thread-safe)."""
        with self._lock:
            return self._failed

    @property
    def cancelled(self) -> int:
        """Number of cancelled jobs (thread-safe)."""
        with self._lock:
            return self._cancelled

    @property
    def pending(self) -> int:
        """Number of pending jobs."""
        with self._lock:
            return self.total - self._completed - self._failed - self._cancelled

    def increment_completed(self) -> None:
        """Increment completed counter (thread-safe)."""
        with self._lock:
            self._completed += 1

    def increment_failed(self) -> None:
        """Increment failed counter (thread-safe)."""
        with self._lock:
            self._failed += 1

    def increment_cancelled(self) -> None:
        """Increment cancelled counter (thread-safe)."""
        with self._lock:
            self._cancelled += 1

    def pending_jobs(self) -> Iterator[DownloadJob]:
        """Yield jobs that need processing (pending or eligible for retry).

        This is a pure iterator that does not modify job status.
        Jobs are yielded if they are PENDING or FAILED with retries remaining.

        Note: This method is idempotent and can be called multiple times.
        The caller is responsible for updating job status if needed.

        Yields:
            DownloadJob instances that are ready to be processed.
        """
        for job in self.jobs:
            is_pending = job.status == JobStatus.PENDING
            is_retryable = (
                job.status == JobStatus.FAILED and job.retry_count < self.max_retries
            )
            if is_pending or is_retryable:
                yield job

    def add_job(self, url: str, output_dir: Path, audio_format: str = "mp3") -> None:
        """Add a new job to the batch.

        Args:
            url: URL to download.
            output_dir: Output directory.
            audio_format: Target audio format.
        """
        job = DownloadJob(url=url, output_dir=output_dir, format=audio_format)
        self.jobs.append(job)


@dataclass
class BatchResult:
    """Summary of batch processing outcome.

    Attributes:
        total: Total number of jobs processed.
        successful: Number of successfully completed jobs.
        failed: Number of failed jobs.
        skipped_duplicates: Number of duplicate URLs skipped.
        successful_files: List of paths to successfully downloaded files.
        failed_jobs: List of jobs that failed for error reporting.
    """

    total: int
    successful: int
    failed: int
    skipped_duplicates: int

    successful_files: list[Path] = field(default_factory=list)
    failed_jobs: list[DownloadJob] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        """Calculate success rate as a decimal (0.0 to 1.0)."""
        if self.total == 0:
            return 1.0
        return self.successful / self.total

    @property
    def has_failures(self) -> bool:
        """Check if any jobs failed."""
        return self.failed > 0

    @classmethod
    def from_request(cls, request: BatchRequest, skipped: int = 0) -> BatchResult:
        """Create result from a completed batch request.

        Args:
            request: The completed batch request.
            skipped: Number of duplicates skipped.

        Returns:
            BatchResult summarizing the batch processing.
        """
        successful_files: list[Path] = []
        failed_jobs: list[DownloadJob] = []

        for job in request.jobs:
            if job.status == JobStatus.COMPLETE and job.output_path:
                successful_files.append(job.output_path)
            elif job.status == JobStatus.FAILED:
                failed_jobs.append(job)

        return cls(
            total=request.total,
            successful=len(successful_files),
            failed=len(failed_jobs),
            skipped_duplicates=skipped,
            successful_files=successful_files,
            failed_jobs=failed_jobs,
        )


def parse_batch_file(path: Path) -> list[str]:
    """Parse a batch file containing URLs.

    Reads a text file with one URL per line, ignoring blank lines
    and lines starting with #.

    Args:
        path: Path to the batch file.

    Returns:
        List of URLs from the file.

    Raises:
        FileNotFoundError: If the file doesn't exist.
        ValueError: If the file is empty or contains no valid URLs.
    """
    if not path.exists():
        raise FileNotFoundError(f"Batch file not found: {path}")

    urls: list[str] = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            urls.append(line)

    if not urls:
        raise ValueError(f"Batch file is empty: {path}")

    return urls


def normalize_url(url: str) -> str:
    """Normalize a URL for duplicate detection.

    Handles YouTube-specific URL variations (youtu.be, youtube.com, etc.)
    to detect duplicates regardless of URL format.

    Args:
        url: The URL to normalize.

    Returns:
        Normalized URL string for comparison.
    """
    url = url.strip().rstrip("/")

    try:
        parsed = urlparse(url)
    except Exception:
        return url

    # YouTube-specific normalization
    host = parsed.netloc.lower()
    if "youtube.com" in host or "youtu.be" in host:
        video_id = _extract_youtube_video_id(parsed)
        if video_id:
            return f"youtube:{video_id}"

    return url


def _extract_youtube_video_id(parsed: ParseResult) -> str | None:
    """Extract YouTube video ID from various URL formats.

    Args:
        parsed: Parsed URL object.

    Returns:
        Video ID if found, None otherwise.
    """
    # youtube.com/watch?v=VIDEO_ID
    query_params = parse_qs(parsed.query)
    if "v" in query_params:
        return query_params["v"][0]

    # youtu.be/VIDEO_ID
    if "youtu.be" in parsed.netloc:
        path = parsed.path.strip("/")
        if path and "/" not in path:
            return path

    # youtube.com/embed/VIDEO_ID or youtube.com/v/VIDEO_ID
    path_parts = parsed.path.strip("/").split("/")
    if len(path_parts) >= 2 and path_parts[0] in ("embed", "v"):
        return path_parts[1]

    return None


def deduplicate_urls(urls: list[str]) -> tuple[list[str], list[str]]:
    """Deduplicate a list of URLs.

    Uses URL normalization to detect duplicates even when URLs
    use different formats for the same content.

    Args:
        urls: List of URLs to deduplicate.

    Returns:
        Tuple of (unique_urls, duplicate_urls).
    """
    seen: set[str] = set()
    unique: list[str] = []
    duplicates: list[str] = []

    for url in urls:
        normalized = normalize_url(url)
        if normalized in seen:
            duplicates.append(url)
        else:
            seen.add(normalized)
            unique.append(url)

    return unique, duplicates
