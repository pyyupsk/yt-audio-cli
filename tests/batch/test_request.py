"""Unit tests for BatchRequest and BatchResult entities."""

from __future__ import annotations

from pathlib import Path

import pytest

from yt_audio_cli.batch.job import DownloadJob, JobStatus
from yt_audio_cli.batch.request import (
    BatchRequest,
    BatchResult,
    deduplicate_urls,
    normalize_url,
    parse_batch_file,
)


class TestBatchRequest:
    """Tests for BatchRequest dataclass."""

    def test_create_empty_request(self) -> None:
        """Test creating an empty batch request."""
        request = BatchRequest()
        assert request.total == 0
        assert request.completed == 0
        assert request.failed == 0
        assert request.pending == 0
        assert request.max_workers == 4
        assert request.max_retries == 3

    def test_create_request_with_jobs(self, temp_dir: Path) -> None:
        """Test creating a request with jobs."""
        jobs = [
            DownloadJob(url="https://youtube.com/watch?v=test1", output_dir=temp_dir),
            DownloadJob(url="https://youtube.com/watch?v=test2", output_dir=temp_dir),
        ]
        request = BatchRequest(jobs=jobs, max_workers=8)
        assert request.total == 2
        assert request.pending == 2
        assert request.max_workers == 8

    def test_invalid_max_workers_low(self) -> None:
        """Test that max_workers < 1 raises ValueError."""
        with pytest.raises(ValueError, match="max_workers must be >= 1"):
            BatchRequest(max_workers=0)

    def test_invalid_max_workers_high(self) -> None:
        """Test that max_workers > 16 raises ValueError."""
        with pytest.raises(ValueError, match="max_workers must be <= 16"):
            BatchRequest(max_workers=17)

    def test_invalid_max_retries_low(self) -> None:
        """Test that max_retries < 0 raises ValueError."""
        with pytest.raises(ValueError, match="max_retries must be >= 0"):
            BatchRequest(max_retries=-1)

    def test_invalid_max_retries_high(self) -> None:
        """Test that max_retries > 10 raises ValueError."""
        with pytest.raises(ValueError, match="max_retries must be <= 10"):
            BatchRequest(max_retries=11)

    def test_thread_safe_counters(self, temp_dir: Path) -> None:
        """Test that counters are thread-safe."""
        request = BatchRequest()
        request.add_job("https://youtube.com/watch?v=test", temp_dir)

        request.increment_completed()
        assert request.completed == 1

        request.increment_failed()
        assert request.failed == 1

    def test_add_job(self, temp_dir: Path) -> None:
        """Test adding a job to the request."""
        request = BatchRequest()
        request.add_job("https://youtube.com/watch?v=test", temp_dir, "opus")

        assert request.total == 1
        assert request.jobs[0].url == "https://youtube.com/watch?v=test"
        assert request.jobs[0].format == "opus"

    def test_pending_jobs_iterator(self, temp_dir: Path) -> None:
        """Test iterating over pending jobs."""
        jobs = [
            DownloadJob(url="https://youtube.com/watch?v=test1", output_dir=temp_dir),
            DownloadJob(url="https://youtube.com/watch?v=test2", output_dir=temp_dir),
        ]
        jobs[0].status = JobStatus.COMPLETE
        request = BatchRequest(jobs=jobs)

        pending = list(request.pending_jobs())
        assert len(pending) == 1
        assert pending[0].url == "https://youtube.com/watch?v=test2"

    def test_pending_jobs_includes_retryable_failed(self, temp_dir: Path) -> None:
        """Test that failed jobs with retries remaining are included."""
        job = DownloadJob(url="https://youtube.com/watch?v=test", output_dir=temp_dir)
        job.mark_failed("Timeout")
        request = BatchRequest(jobs=[job], max_retries=3)

        pending = list(request.pending_jobs())
        assert len(pending) == 1
        assert pending[0].status == JobStatus.PENDING

    def test_pending_jobs_excludes_exhausted_retries(self, temp_dir: Path) -> None:
        """Test that failed jobs with exhausted retries are excluded."""
        job = DownloadJob(url="https://youtube.com/watch?v=test", output_dir=temp_dir)
        job.mark_failed("Timeout")
        job.retry_count = 3
        request = BatchRequest(jobs=[job], max_retries=3)

        pending = list(request.pending_jobs())
        assert len(pending) == 0


class TestBatchResult:
    """Tests for BatchResult dataclass."""

    def test_create_result(self, temp_dir: Path) -> None:
        """Test creating a batch result."""
        result = BatchResult(
            total=10,
            successful=8,
            failed=2,
            skipped_duplicates=1,
            successful_files=[temp_dir / "test.mp3"],
        )
        assert result.total == 10
        assert result.successful == 8
        assert result.failed == 2
        assert result.skipped_duplicates == 1

    def test_success_rate(self) -> None:
        """Test success rate calculation."""
        result = BatchResult(total=10, successful=8, failed=2, skipped_duplicates=0)
        assert result.success_rate == 0.8

    def test_success_rate_empty(self) -> None:
        """Test success rate with no jobs."""
        result = BatchResult(total=0, successful=0, failed=0, skipped_duplicates=0)
        assert result.success_rate == 1.0

    def test_has_failures(self) -> None:
        """Test has_failures property."""
        result_with_failures = BatchResult(
            total=10, successful=8, failed=2, skipped_duplicates=0
        )
        assert result_with_failures.has_failures is True

        result_without_failures = BatchResult(
            total=10, successful=10, failed=0, skipped_duplicates=0
        )
        assert result_without_failures.has_failures is False

    def test_from_request(self, temp_dir: Path) -> None:
        """Test creating result from a completed request."""
        jobs = [
            DownloadJob(url="https://youtube.com/watch?v=test1", output_dir=temp_dir),
            DownloadJob(url="https://youtube.com/watch?v=test2", output_dir=temp_dir),
        ]
        jobs[0].mark_complete(temp_dir / "test1.mp3")
        jobs[1].mark_failed("Error")

        request = BatchRequest(jobs=jobs)
        result = BatchResult.from_request(request, skipped=1)

        assert result.total == 2
        assert result.successful == 1
        assert result.failed == 1
        assert result.skipped_duplicates == 1
        assert len(result.successful_files) == 1
        assert len(result.failed_jobs) == 1


class TestParseBatchFile:
    """Tests for parse_batch_file function."""

    def test_parse_valid_file(self, temp_dir: Path) -> None:
        """Test parsing a valid batch file."""
        batch_file = temp_dir / "urls.txt"
        batch_file.write_text(
            """# This is a comment
https://youtube.com/watch?v=test1

# Another comment
https://youtube.com/watch?v=test2
https://youtube.com/watch?v=test3
"""
        )

        urls = parse_batch_file(batch_file)
        assert len(urls) == 3
        assert urls[0] == "https://youtube.com/watch?v=test1"
        assert urls[1] == "https://youtube.com/watch?v=test2"
        assert urls[2] == "https://youtube.com/watch?v=test3"

    def test_parse_file_not_found(self, temp_dir: Path) -> None:
        """Test that missing file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="Batch file not found"):
            parse_batch_file(temp_dir / "nonexistent.txt")

    def test_parse_empty_file(self, temp_dir: Path) -> None:
        """Test that empty file raises ValueError."""
        batch_file = temp_dir / "empty.txt"
        batch_file.write_text("")

        with pytest.raises(ValueError, match="Batch file is empty"):
            parse_batch_file(batch_file)

    def test_parse_comments_only_file(self, temp_dir: Path) -> None:
        """Test that file with only comments raises ValueError."""
        batch_file = temp_dir / "comments.txt"
        batch_file.write_text("# Just a comment\n# Another comment\n")

        with pytest.raises(ValueError, match="Batch file is empty"):
            parse_batch_file(batch_file)


class TestNormalizeUrl:
    """Tests for normalize_url function."""

    def test_normalize_standard_youtube(self) -> None:
        """Test normalizing standard YouTube URLs."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert normalize_url(url) == "youtube:dQw4w9WgXcQ"

    def test_normalize_youtu_be(self) -> None:
        """Test normalizing youtu.be short URLs."""
        url = "https://youtu.be/dQw4w9WgXcQ"
        assert normalize_url(url) == "youtube:dQw4w9WgXcQ"

    def test_normalize_youtube_embed(self) -> None:
        """Test normalizing YouTube embed URLs."""
        url = "https://www.youtube.com/embed/dQw4w9WgXcQ"
        assert normalize_url(url) == "youtube:dQw4w9WgXcQ"

    def test_normalize_with_trailing_slash(self) -> None:
        """Test that trailing slashes are removed."""
        url = "https://example.com/video/"
        assert normalize_url(url) == "https://example.com/video"

    def test_normalize_non_youtube(self) -> None:
        """Test normalizing non-YouTube URLs."""
        url = "https://vimeo.com/12345"
        assert normalize_url(url) == "https://vimeo.com/12345"


class TestDeduplicateUrls:
    """Tests for deduplicate_urls function."""

    def test_no_duplicates(self) -> None:
        """Test with no duplicates."""
        urls = [
            "https://youtube.com/watch?v=abc",
            "https://youtube.com/watch?v=def",
        ]
        unique, dupes = deduplicate_urls(urls)
        assert len(unique) == 2
        assert len(dupes) == 0

    def test_exact_duplicates(self) -> None:
        """Test with exact duplicate URLs."""
        urls = [
            "https://youtube.com/watch?v=abc",
            "https://youtube.com/watch?v=abc",
        ]
        unique, dupes = deduplicate_urls(urls)
        assert len(unique) == 1
        assert len(dupes) == 1

    def test_normalized_duplicates(self) -> None:
        """Test detecting duplicates across URL formats."""
        urls = [
            "https://youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
            "https://www.youtube.com/embed/dQw4w9WgXcQ",
        ]
        unique, dupes = deduplicate_urls(urls)
        assert len(unique) == 1
        assert len(dupes) == 2
