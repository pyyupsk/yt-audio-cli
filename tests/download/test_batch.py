"""Tests for batch download functionality."""

from __future__ import annotations

from pathlib import Path
from queue import Queue
from unittest.mock import MagicMock, patch

import pytest

from yt_audio_cli.batch.executor import reset_shutdown
from yt_audio_cli.batch.job import ProgressUpdate
from yt_audio_cli.batch.request import BatchRequest
from yt_audio_cli.download.batch import BatchDownloader, download_batch
from yt_audio_cli.download.downloader import DownloadResult


@pytest.fixture(autouse=True)
def reset_shutdown_state() -> None:
    """Reset shutdown state before each test."""
    reset_shutdown()


class TestBatchDownloader:
    """Tests for BatchDownloader class."""

    def test_empty_request(self, temp_dir: Path) -> None:
        """Test processing an empty batch request."""
        request = BatchRequest()
        downloader = BatchDownloader(
            request=request,
            output_dir=temp_dir,
        )

        result = downloader.run()
        assert result.total == 0
        assert result.successful == 0
        assert result.failed == 0

    @patch("yt_audio_cli.download.batch.download")
    @patch("yt_audio_cli.download.batch.transcode")
    def test_successful_download(
        self,
        mock_transcode: MagicMock,
        mock_download: MagicMock,
        temp_dir: Path,
    ) -> None:
        """Test successful download and conversion."""
        # Create temp file to simulate download
        temp_audio = temp_dir / "temp_audio.webm"
        temp_audio.write_bytes(b"fake audio data")

        mock_download.return_value = DownloadResult(
            url="https://youtube.com/watch?v=test",
            title="Test Video",
            artist="Test Artist",
            temp_path=temp_audio,
            duration=120.0,
            success=True,
        )
        mock_transcode.return_value = True

        request = BatchRequest(max_workers=1)
        request.add_job("https://youtube.com/watch?v=test", temp_dir)

        downloader = BatchDownloader(
            request=request,
            output_dir=temp_dir,
        )

        # Create output file to simulate conversion
        def create_output(*args, **kwargs):
            output_path = args[1] if len(args) > 1 else kwargs.get("output_path")
            if output_path:
                output_path.write_bytes(b"converted audio")
            return True

        mock_transcode.side_effect = create_output

        result = downloader.run()
        assert result.total == 1
        assert result.successful == 1
        assert result.failed == 0

    @patch("yt_audio_cli.download.batch.download")
    def test_failed_download(
        self,
        mock_download: MagicMock,
        temp_dir: Path,
    ) -> None:
        """Test handling of failed download."""
        mock_download.return_value = DownloadResult(
            url="https://youtube.com/watch?v=test",
            title="",
            artist="",
            temp_path=Path(),
            duration=None,
            success=False,
            error="Video unavailable",
        )

        request = BatchRequest(max_workers=1)
        request.add_job("https://youtube.com/watch?v=test", temp_dir)

        downloader = BatchDownloader(
            request=request,
            output_dir=temp_dir,
        )

        result = downloader.run()
        assert result.total == 1
        assert result.successful == 0
        assert result.failed == 1
        assert len(result.failed_jobs) == 1

    @patch("yt_audio_cli.download.batch.download")
    @patch("yt_audio_cli.download.batch.transcode")
    def test_progress_updates(
        self,
        mock_transcode: MagicMock,
        mock_download: MagicMock,
        temp_dir: Path,
    ) -> None:
        """Test that progress updates are sent to queue."""
        temp_audio = temp_dir / "temp_audio.webm"
        temp_audio.write_bytes(b"fake audio data")

        def download_with_progress(**kwargs):
            url = kwargs.get("url")
            progress_callback = kwargs.get("progress_callback")
            # Simulate progress updates
            if progress_callback:
                progress_callback(50, 100)
                progress_callback(100, 100)
            return DownloadResult(
                url=url,
                title="Test Video",
                artist="Test Artist",
                temp_path=temp_audio,
                duration=120.0,
                success=True,
            )

        mock_download.side_effect = download_with_progress

        def create_output(*args, **kwargs):
            output_path = args[1] if len(args) > 1 else kwargs.get("output_path")
            if output_path:
                output_path.write_bytes(b"converted audio")
            return True

        mock_transcode.side_effect = create_output

        progress_queue: Queue[ProgressUpdate] = Queue()
        request = BatchRequest(max_workers=1)
        request.add_job("https://youtube.com/watch?v=test", temp_dir)

        downloader = BatchDownloader(
            request=request,
            output_dir=temp_dir,
            progress_queue=progress_queue,
        )

        result = downloader.run()
        assert result.successful == 1

        # Check that progress updates were sent
        updates = []
        while not progress_queue.empty():
            updates.append(progress_queue.get())

        # Should have started, progress, and complete events
        events = [u.event for u in updates]
        assert "started" in events
        assert "complete" in events

    @patch("yt_audio_cli.download.batch.download")
    @patch("yt_audio_cli.download.batch.transcode")
    def test_multiple_parallel_downloads(
        self,
        mock_transcode: MagicMock,
        mock_download: MagicMock,
        temp_dir: Path,
    ) -> None:
        """Test parallel download of multiple URLs."""
        call_count = [0]

        def create_download_result(**kwargs):
            url = kwargs.get("url")
            output_dir = kwargs.get("output_dir")
            call_count[0] += 1
            # Create a unique temp file for each call
            temp_audio = output_dir / f"temp_audio_{call_count[0]}.webm"
            temp_audio.write_bytes(b"fake audio data")
            return DownloadResult(
                url=url,
                title=f"Test Video {call_count[0]}",
                artist="Test Artist",
                temp_path=temp_audio,
                duration=120.0,
                success=True,
            )

        mock_download.side_effect = create_download_result

        def create_output(*args, **kwargs):
            output_path = args[1] if len(args) > 1 else kwargs.get("output_path")
            if output_path:
                output_path.write_bytes(b"converted audio")
            return True

        mock_transcode.side_effect = create_output

        request = BatchRequest(max_workers=4)
        for i in range(10):
            request.add_job(f"https://youtube.com/watch?v=test{i}", temp_dir)

        downloader = BatchDownloader(
            request=request,
            output_dir=temp_dir,
        )

        result = downloader.run()
        assert result.total == 10
        assert result.successful == 10
        assert result.failed == 0


class TestDownloadBatch:
    """Tests for download_batch convenience function."""

    @patch("yt_audio_cli.download.batch.download")
    @patch("yt_audio_cli.download.batch.transcode")
    def test_download_batch_function(
        self,
        mock_transcode: MagicMock,
        mock_download: MagicMock,
        temp_dir: Path,
    ) -> None:
        """Test the download_batch convenience function."""
        call_count = [0]

        def create_download_result(**kwargs):
            url = kwargs.get("url")
            output_dir = kwargs.get("output_dir")
            call_count[0] += 1
            temp_audio = output_dir / f"temp_audio_{call_count[0]}.webm"
            temp_audio.write_bytes(b"fake audio data")
            return DownloadResult(
                url=url,
                title=f"Test Video {call_count[0]}",
                artist="Test Artist",
                temp_path=temp_audio,
                duration=120.0,
                success=True,
            )

        mock_download.side_effect = create_download_result

        def create_output(*args, **kwargs):
            output_path = args[1] if len(args) > 1 else kwargs.get("output_path")
            if output_path:
                output_path.write_bytes(b"converted audio")
            return True

        mock_transcode.side_effect = create_output

        urls = [
            "https://youtube.com/watch?v=test1",
            "https://youtube.com/watch?v=test2",
        ]

        result = download_batch(
            urls=urls,
            output_dir=temp_dir,
            audio_format="mp3",
            max_workers=2,
        )

        assert result.total == 2
        assert result.successful == 2

    @patch("yt_audio_cli.download.batch.download")
    def test_download_batch_with_failures(
        self,
        mock_download: MagicMock,
        temp_dir: Path,
    ) -> None:
        """Test download_batch with some failures."""
        mock_download.return_value = DownloadResult(
            url="https://youtube.com/watch?v=test",
            title="",
            artist="",
            temp_path=Path(),
            duration=None,
            success=False,
            error="Video unavailable",
        )

        urls = ["https://youtube.com/watch?v=test1"]

        result = download_batch(
            urls=urls,
            output_dir=temp_dir,
            max_workers=1,
        )

        assert result.total == 1
        assert result.failed == 1
        assert result.has_failures is True
