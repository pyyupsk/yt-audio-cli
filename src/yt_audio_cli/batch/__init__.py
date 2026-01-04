"""Batch processing module for parallel downloads."""

from __future__ import annotations

from yt_audio_cli.batch.executor import (
    CompletionResult,
    WorkerPool,
    WorkerState,
    install_signal_handlers,
    is_shutdown_requested,
    reset_shutdown,
)
from yt_audio_cli.batch.job import DownloadJob, JobStatus, ProgressUpdate
from yt_audio_cli.batch.request import (
    BatchRequest,
    BatchResult,
    deduplicate_urls,
    normalize_url,
    parse_batch_file,
)
from yt_audio_cli.batch.retry import (
    RetryConfig,
    is_permanent_error,
    is_retryable_error,
)

__all__ = [
    "BatchRequest",
    "BatchResult",
    "CompletionResult",
    "DownloadJob",
    "JobStatus",
    "ProgressUpdate",
    "RetryConfig",
    "WorkerPool",
    "WorkerState",
    "deduplicate_urls",
    "install_signal_handlers",
    "is_permanent_error",
    "is_retryable_error",
    "is_shutdown_requested",
    "normalize_url",
    "parse_batch_file",
    "reset_shutdown",
]
