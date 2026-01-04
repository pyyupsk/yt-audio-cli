"""Batch download functionality with parallel execution."""

from __future__ import annotations

import contextlib
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from queue import Queue
from typing import TYPE_CHECKING

from yt_audio_cli.batch.executor import WorkerPool, is_shutdown_requested
from yt_audio_cli.batch.job import DownloadJob, JobStatus, ProgressUpdate
from yt_audio_cli.batch.request import BatchRequest, BatchResult
from yt_audio_cli.batch.retry import RetryConfig, is_permanent_error, is_retryable_error
from yt_audio_cli.convert import transcode
from yt_audio_cli.core import resolve_conflict, sanitize
from yt_audio_cli.download.downloader import DownloadResult, download

if TYPE_CHECKING:
    pass


@dataclass
class BatchDownloader:
    """Parallel batch downloader using ThreadPoolExecutor.

    Coordinates parallel download and conversion of multiple URLs
    with progress reporting and graceful shutdown support.

    Attributes:
        request: The batch request to process.
        output_dir: Output directory for converted files.
        audio_format: Target audio format.
        bitrate: Target bitrate in kbps.
        embed_metadata: Whether to embed metadata.
        retry_config: Retry configuration for failed downloads.
        progress_queue: Optional queue for progress updates.
    """

    request: BatchRequest
    output_dir: Path
    audio_format: str = "mp3"
    bitrate: int | None = None
    embed_metadata: bool = True
    retry_config: RetryConfig = field(default_factory=RetryConfig)
    progress_queue: Queue[ProgressUpdate] | None = None
    _rename_lock: threading.Lock = field(
        default_factory=threading.Lock, init=False, repr=False
    )

    def _send_progress(
        self,
        worker_id: int,
        job: DownloadJob,
        event: str,
        percent: int = 0,
        error: str = "",
    ) -> None:
        """Send a progress update to the queue."""
        if self.progress_queue is None:
            return

        update = ProgressUpdate(
            worker_id=worker_id,
            job_url=job.url,
            event=event,  # type: ignore[arg-type]
            percent=percent,
            title=job.current_title,
            error=error,
        )
        self.progress_queue.put(update)

    def _download_single(
        self,
        job: DownloadJob,
        worker_id: int,
    ) -> bool:
        """Download and convert a single job.

        Handles the full download→convert pipeline for one URL.

        Args:
            job: The download job to process.
            worker_id: ID of the worker processing this job.

        Returns:
            True if successful, False otherwise.
        """
        if is_shutdown_requested():
            job.mark_cancelled()
            return False

        job.mark_active()
        self._send_progress(worker_id, job, "started")

        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_dir = Path(temp_dir_str)

            # Download phase
            def progress_callback(downloaded: int, total: int) -> None:
                if total > 0:
                    percent = int((downloaded / total) * 100)
                    job.update_progress(percent)
                    self._send_progress(worker_id, job, "progress", percent)

            try:
                result = download(
                    url=job.url,
                    progress_callback=progress_callback,
                    output_dir=temp_dir,
                )

                if not result.success:
                    job.mark_failed(result.error or "Download failed")
                    self._send_progress(
                        worker_id, job, "failed", error=result.error or "Unknown error"
                    )
                    return False

                if not result.temp_path.exists():
                    job.mark_failed("Temporary file not found")
                    self._send_progress(
                        worker_id, job, "failed", error="Temporary file not found"
                    )
                    return False

                # Update title from result
                if result.title:
                    job.current_title = result.title

                if is_shutdown_requested():
                    job.mark_cancelled()
                    return False

                # Conversion phase
                output_path = self._convert_audio(result, job, worker_id)
                if output_path is None:
                    return False

                job.mark_complete(output_path)
                self._send_progress(worker_id, job, "complete", 100)
                return True

            except Exception as e:
                error_msg = str(e)
                job.mark_failed(error_msg)
                self._send_progress(worker_id, job, "failed", error=error_msg)
                return False

    def _convert_audio(
        self,
        result: DownloadResult,
        job: DownloadJob,
        worker_id: int,
    ) -> Path | None:
        """Convert downloaded audio to target format.

        Args:
            result: Download result with temp file.
            job: The download job.
            worker_id: Worker ID for progress updates.

        Returns:
            Output path if successful, None otherwise.
        """
        import uuid

        sanitized_title = sanitize(result.title)
        final_output_path = self.output_dir / f"{sanitized_title}.{self.audio_format}"
        final_output_path = resolve_conflict(final_output_path)

        # Use UUID to avoid conflicts between parallel jobs
        unique_id = uuid.uuid4().hex[:8]
        temp_output_path = (
            self.output_dir / f".{sanitized_title}_{unique_id}.{self.audio_format}.tmp"
        )

        metadata = {}
        if self.embed_metadata:
            metadata = {"title": result.title, "artist": result.artist}

        try:
            transcode(
                input_path=result.temp_path,
                output_path=temp_output_path,
                audio_format=self.audio_format,
                bitrate=self.bitrate,
                embed_metadata=self.embed_metadata,
                metadata=metadata,
            )

            with self._rename_lock:
                if final_output_path.exists():
                    final_output_path = resolve_conflict(final_output_path)
                temp_output_path.replace(final_output_path)
            return final_output_path

        except Exception as e:
            job.mark_failed(f"Conversion failed: {e}")
            self._send_progress(
                worker_id, job, "failed", error=f"Conversion failed: {e}"
            )
            return None
        finally:
            if temp_output_path.exists():
                with contextlib.suppress(OSError):
                    temp_output_path.unlink()

    def _process_job_with_retry(
        self,
        job: DownloadJob,
        worker_id: int,
    ) -> JobStatus:
        """Process a job with retry logic.

        Args:
            job: The download job to process.
            worker_id: Worker ID.

        Returns:
            JobStatus indicating the final state of the job.
        """
        for attempt in range(self.retry_config.max_attempts):
            if is_shutdown_requested():
                job.mark_cancelled()
                return JobStatus.CANCELLED

            success = self._download_single(job, worker_id)

            if success:
                return JobStatus.COMPLETE

            # Check if we should retry
            error = job.error_message or ""

            # Don't retry permanent errors
            if is_permanent_error(error):
                return JobStatus.FAILED

            # Check if error is retryable
            if not is_retryable_error(error):
                return JobStatus.FAILED

            # Check if we have retries left
            if not self.retry_config.should_retry(attempt):
                return JobStatus.FAILED

            # Wait before retry
            delay = self.retry_config.delay_for_attempt(attempt)
            time.sleep(delay)
            job.increment_retry()

        return JobStatus.FAILED

    def run(self) -> BatchResult:
        """Execute the batch download.

        Runs all jobs in parallel using the configured number of workers.
        Tracks progress and handles failures/retries.

        Returns:
            BatchResult with summary of the operation.
        """
        if not self.request.jobs:
            return BatchResult(
                total=0,
                successful=0,
                failed=0,
                skipped_duplicates=0,
            )

        # Limit workers to number of jobs
        effective_workers = min(self.request.max_workers, len(self.request.jobs))

        with WorkerPool[JobStatus](max_workers=effective_workers) as pool:
            job_index = 0
            pending_futures: dict[object, tuple[DownloadJob, int]] = {}

            # Submit initial batch of jobs
            for worker_id in range(effective_workers):
                if job_index < len(self.request.jobs):
                    job = self.request.jobs[job_index]
                    future = pool.submit_job(
                        job, self._process_job_with_retry, worker_id
                    )
                    if future:
                        pending_futures[future] = (job, worker_id)
                    job_index += 1

            # Process as jobs complete
            while pending_futures:
                if is_shutdown_requested():
                    break

                # Wait for any future to complete
                done_futures = []
                for future in list(pending_futures.keys()):
                    if future.done():  # type: ignore[union-attr]
                        done_futures.append(future)

                if not done_futures:
                    time.sleep(0.01)
                    continue

                for future in done_futures:
                    job, worker_id = pending_futures.pop(future)
                    pool.mark_worker_idle(worker_id)

                    try:
                        status = future.result()  # type: ignore[union-attr]
                        if status == JobStatus.COMPLETE:
                            self.request.increment_completed()
                        elif status == JobStatus.CANCELLED:
                            self.request.increment_cancelled()
                        else:
                            self.request.increment_failed()
                    except Exception:
                        self.request.increment_failed()

                    # Submit next job if available
                    if job_index < len(self.request.jobs):
                        next_job = self.request.jobs[job_index]
                        next_future = pool.submit_job(
                            next_job, self._process_job_with_retry, worker_id
                        )
                        if next_future:
                            pending_futures[next_future] = (next_job, worker_id)
                        job_index += 1

        return BatchResult.from_request(self.request)


def download_batch(
    urls: list[str],
    output_dir: Path,
    audio_format: str = "mp3",
    max_workers: int = 4,
    max_retries: int = 3,
    bitrate: int | None = None,
    embed_metadata: bool = True,
    progress_queue: Queue[ProgressUpdate] | None = None,
) -> BatchResult:
    """Download multiple URLs in parallel.

    Convenience function that creates a BatchRequest and BatchDownloader.

    Args:
        urls: List of URLs to download.
        output_dir: Output directory for converted files.
        audio_format: Target audio format.
        max_workers: Number of concurrent workers.
        max_retries: Maximum retry attempts per job.
        bitrate: Target bitrate in kbps.
        embed_metadata: Whether to embed metadata.
        progress_queue: Optional queue for progress updates.

    Returns:
        BatchResult with summary of the operation.
    """
    request = BatchRequest(max_workers=max_workers, max_retries=max_retries)
    for url in urls:
        request.add_job(url, output_dir, audio_format)

    retry_config = RetryConfig(max_attempts=max_retries + 1)

    downloader = BatchDownloader(
        request=request,
        output_dir=output_dir,
        audio_format=audio_format,
        bitrate=bitrate,
        embed_metadata=embed_metadata,
        retry_config=retry_config,
        progress_queue=progress_queue,
    )

    return downloader.run()
