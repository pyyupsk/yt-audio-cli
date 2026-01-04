"""Unit tests for DownloadJob entity."""

from __future__ import annotations

from pathlib import Path

import pytest

from yt_audio_cli.batch.job import DownloadJob, JobStatus, ProgressUpdate


class TestDownloadJob:
    """Tests for DownloadJob dataclass."""

    def test_create_valid_job(self, temp_dir: Path) -> None:
        """Test creating a valid download job."""
        job = DownloadJob(
            url="https://youtube.com/watch?v=test123",
            output_dir=temp_dir,
            format="mp3",
        )
        assert job.url == "https://youtube.com/watch?v=test123"
        assert job.output_dir == temp_dir
        assert job.format == "mp3"
        assert job.status == JobStatus.PENDING
        assert job.retry_count == 0
        assert job.error_message is None
        assert job.output_path is None
        assert job.current_percent == 0
        assert job.current_title == ""

    def test_invalid_url_raises(self, temp_dir: Path) -> None:
        """Test that invalid URL raises ValueError."""
        with pytest.raises(ValueError, match="Invalid URL"):
            DownloadJob(
                url="not-a-valid-url",
                output_dir=temp_dir,
            )

    def test_negative_retry_count_raises(self, temp_dir: Path) -> None:
        """Test that negative retry count raises ValueError."""
        with pytest.raises(ValueError, match="retry_count must be >= 0"):
            DownloadJob(
                url="https://youtube.com/watch?v=test",
                output_dir=temp_dir,
                retry_count=-1,
            )

    def test_percent_clamped_to_valid_range(self, temp_dir: Path) -> None:
        """Test that percent is clamped to 0-100 range."""
        job = DownloadJob(
            url="https://youtube.com/watch?v=test",
            output_dir=temp_dir,
            current_percent=150,
        )
        assert job.current_percent == 100

        job2 = DownloadJob(
            url="https://youtube.com/watch?v=test",
            output_dir=temp_dir,
            current_percent=-10,
        )
        assert job2.current_percent == 0

    def test_mark_active(self, temp_dir: Path) -> None:
        """Test marking job as active."""
        job = DownloadJob(
            url="https://youtube.com/watch?v=test",
            output_dir=temp_dir,
        )
        job.mark_active(title="Test Video")
        assert job.status == JobStatus.ACTIVE
        assert job.current_percent == 0
        assert job.current_title == "Test Video"

    def test_mark_complete(self, temp_dir: Path) -> None:
        """Test marking job as complete."""
        job = DownloadJob(
            url="https://youtube.com/watch?v=test",
            output_dir=temp_dir,
        )
        output_path = temp_dir / "test.mp3"
        job.mark_complete(output_path)
        assert job.status == JobStatus.COMPLETE
        assert job.output_path == output_path
        assert job.current_percent == 100
        assert job.error_message is None

    def test_mark_failed(self, temp_dir: Path) -> None:
        """Test marking job as failed."""
        job = DownloadJob(
            url="https://youtube.com/watch?v=test",
            output_dir=temp_dir,
        )
        job.mark_failed("Connection timeout")
        assert job.status == JobStatus.FAILED
        assert job.error_message == "Connection timeout"

    def test_mark_cancelled(self, temp_dir: Path) -> None:
        """Test marking job as cancelled."""
        job = DownloadJob(
            url="https://youtube.com/watch?v=test",
            output_dir=temp_dir,
        )
        job.mark_cancelled()
        assert job.status == JobStatus.CANCELLED

    def test_update_progress(self, temp_dir: Path) -> None:
        """Test updating progress."""
        job = DownloadJob(
            url="https://youtube.com/watch?v=test",
            output_dir=temp_dir,
        )
        job.update_progress(50, "Downloading...")
        assert job.current_percent == 50
        assert job.current_title == "Downloading..."

        # Test clamping
        job.update_progress(150)
        assert job.current_percent == 100

        job.update_progress(-10)
        assert job.current_percent == 0

    def test_increment_retry(self, temp_dir: Path) -> None:
        """Test incrementing retry count."""
        job = DownloadJob(
            url="https://youtube.com/watch?v=test",
            output_dir=temp_dir,
        )
        job.mark_failed("Error")
        job.increment_retry()

        assert job.retry_count == 1
        assert job.status == JobStatus.PENDING
        assert job.current_percent == 0
        assert job.error_message is None


class TestProgressUpdate:
    """Tests for ProgressUpdate dataclass."""

    def test_create_started_event(self) -> None:
        """Test creating a started progress update."""
        update = ProgressUpdate(
            worker_id=0,
            job_url="https://youtube.com/watch?v=test",
            event="started",
        )
        assert update.worker_id == 0
        assert update.job_url == "https://youtube.com/watch?v=test"
        assert update.event == "started"
        assert update.percent == 0
        assert update.title == ""
        assert update.error == ""

    def test_create_progress_event(self) -> None:
        """Test creating a progress update."""
        update = ProgressUpdate(
            worker_id=1,
            job_url="https://youtube.com/watch?v=test",
            event="progress",
            percent=50,
            title="Test Video",
        )
        assert update.event == "progress"
        assert update.percent == 50
        assert update.title == "Test Video"

    def test_create_failed_event(self) -> None:
        """Test creating a failed progress update."""
        update = ProgressUpdate(
            worker_id=2,
            job_url="https://youtube.com/watch?v=test",
            event="failed",
            error="Connection timeout",
        )
        assert update.event == "failed"
        assert update.error == "Connection timeout"

    def test_progress_update_is_immutable(self) -> None:
        """Test that ProgressUpdate is frozen (immutable)."""
        update = ProgressUpdate(
            worker_id=0,
            job_url="https://youtube.com/watch?v=test",
            event="started",
        )
        with pytest.raises(AttributeError):
            update.worker_id = 1  # type: ignore[misc]
