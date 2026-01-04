"""Worker pool executor for parallel downloads."""

from __future__ import annotations

import signal
import sys
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from threading import Event

from yt_audio_cli.batch.job import DownloadJob


@dataclass
class CompletionResult[T]:
    """Result of waiting for futures to complete.

    Attributes:
        results: List of successful results.
        errors: List of (worker_id, exception) tuples for failed futures.
    """

    results: list[T] = field(default_factory=list)
    errors: list[tuple[int | None, Exception]] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        """Check if any futures failed."""
        return len(self.errors) > 0

    @property
    def success_count(self) -> int:
        """Number of successful results."""
        return len(self.results)

    @property
    def error_count(self) -> int:
        """Number of failed futures."""
        return len(self.errors)


# Global shutdown event for signal handling
shutdown_event = Event()

# Track if signal handlers have been installed
_handlers_installed = False


def _signal_handler(_signum: int, _frame: object) -> None:
    """Handle SIGINT/SIGTERM for graceful shutdown."""
    shutdown_event.set()


def install_signal_handlers() -> None:
    """Install signal handlers for graceful shutdown.

    Safe to call multiple times - handlers are only installed once.
    """
    global _handlers_installed
    if _handlers_installed:
        return

    # Only install on main thread
    try:
        if sys.platform != "win32":
            signal.signal(signal.SIGINT, _signal_handler)
            signal.signal(signal.SIGTERM, _signal_handler)
        else:
            # Windows only supports SIGINT
            signal.signal(signal.SIGINT, _signal_handler)
        _handlers_installed = True
    except ValueError:
        # Not on main thread, skip signal handling
        pass


def is_shutdown_requested() -> bool:
    """Check if shutdown has been requested.

    Returns:
        True if SIGINT/SIGTERM was received.
    """
    return shutdown_event.is_set()


def reset_shutdown() -> None:
    """Reset the shutdown event.

    Useful for testing or restarting batch operations.
    """
    shutdown_event.clear()


@dataclass
class WorkerState:
    """Current state of a download worker.

    Attributes:
        worker_id: Unique identifier for this worker.
        job: Current job being processed, or None if idle.
    """

    worker_id: int
    job: DownloadJob | None = None

    @property
    def is_idle(self) -> bool:
        """Check if worker is idle (not processing a job)."""
        return self.job is None

    @property
    def display_line(self) -> str:
        """Get a single-line status display for this worker."""
        if self.is_idle:
            return f"[{self.worker_id}] Idle"

        job = self.job
        assert job is not None  # nosec B101 - guarded by is_idle check above
        title = job.current_title[:40] if job.current_title else "Unknown"
        return f"[{self.worker_id}] {title:40} {job.current_percent:3}%"


@dataclass
class WorkerPool[T]:
    """Thread pool wrapper for parallel job execution.

    Manages a ThreadPoolExecutor and tracks worker states for
    progress display purposes.

    Attributes:
        max_workers: Maximum number of concurrent workers.
        worker_states: Current state of each worker.
    """

    max_workers: int
    worker_states: dict[int, WorkerState] = field(default_factory=dict)
    _executor: ThreadPoolExecutor | None = field(default=None, init=False, repr=False)
    _futures: dict[Future[T], int] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        """Initialize worker states."""
        for i in range(self.max_workers):
            self.worker_states[i] = WorkerState(worker_id=i)

    def __enter__(self) -> WorkerPool[T]:
        """Enter context manager - start the executor."""
        install_signal_handlers()
        self._executor = ThreadPoolExecutor(max_workers=self.max_workers)
        return self

    def __exit__(
        self, exc_type: type | None, exc_val: Exception | None, exc_tb: object
    ) -> None:
        """Exit context manager - shutdown executor gracefully."""
        if self._executor:
            self._executor.shutdown(wait=True, cancel_futures=True)
            self._executor = None

    def submit(
        self,
        fn: Callable[..., T],
        *args: object,
        worker_id: int | None = None,
        **kwargs: object,
    ) -> Future[T] | None:
        """Submit a task for execution.

        Args:
            fn: Function to execute.
            *args: Positional arguments for fn.
            worker_id: Optional worker ID to associate with this task.
            **kwargs: Keyword arguments for fn.

        Returns:
            Future for the submitted task, or None if shutdown requested.
        """
        if is_shutdown_requested():
            return None

        if self._executor is None:
            raise RuntimeError("WorkerPool must be used as context manager")

        future = self._executor.submit(fn, *args, **kwargs)

        if worker_id is not None:
            self._futures[future] = worker_id

        return future

    def submit_job(
        self,
        job: DownloadJob,
        fn: Callable[[DownloadJob, int], T],
        worker_id: int,
    ) -> Future[T] | None:
        """Submit a download job for execution.

        Updates worker state to track the job being processed.

        Args:
            job: The download job to process.
            fn: Function to execute, takes (job, worker_id).
            worker_id: Worker ID to associate with this job.

        Returns:
            Future for the submitted task, or None if shutdown requested.
        """
        if is_shutdown_requested():
            return None

        # Update worker state
        if worker_id in self.worker_states:
            self.worker_states[worker_id].job = job

        return self.submit(fn, job, worker_id, worker_id=worker_id)

    def mark_worker_idle(self, worker_id: int) -> None:
        """Mark a worker as idle after completing a job."""
        if worker_id in self.worker_states:
            self.worker_states[worker_id].job = None

    def get_active_workers(self) -> list[WorkerState]:
        """Get list of workers currently processing jobs."""
        return [ws for ws in self.worker_states.values() if not ws.is_idle]

    def get_idle_workers(self) -> list[int]:
        """Get list of idle worker IDs."""
        return [ws.worker_id for ws in self.worker_states.values() if ws.is_idle]

    def wait_for_completion(
        self,
        futures: list[Future[T]],
        callback: Callable[[Future[T], int | None], None] | None = None,
    ) -> CompletionResult[T]:
        """Wait for futures to complete and collect results.

        Args:
            futures: List of futures to wait for.
            callback: Optional callback called when each future completes.
                Takes (future, worker_id) as arguments.

        Returns:
            CompletionResult containing successful results and any errors.
        """
        completion = CompletionResult[T]()

        for future in as_completed(futures):
            worker_id = self._futures.get(future)

            if callback:
                callback(future, worker_id)

            if worker_id is not None:
                self.mark_worker_idle(worker_id)

            try:
                result = future.result()
                completion.results.append(result)
            except Exception as e:
                completion.errors.append((worker_id, e))

        return completion

    def shutdown(self) -> None:
        """Request graceful shutdown of the worker pool."""
        shutdown_event.set()
        if self._executor:
            self._executor.shutdown(wait=False, cancel_futures=True)
