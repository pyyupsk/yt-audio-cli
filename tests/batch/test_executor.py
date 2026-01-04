"""Unit tests for WorkerPool executor."""

from __future__ import annotations

import time
from concurrent.futures import Future
from pathlib import Path

from yt_audio_cli.batch.executor import (
    WorkerPool,
    WorkerState,
    is_shutdown_requested,
    reset_shutdown,
)
from yt_audio_cli.batch.job import DownloadJob


class TestWorkerState:
    """Tests for WorkerState dataclass."""

    def test_idle_worker(self) -> None:
        """Test idle worker state."""
        state = WorkerState(worker_id=0)
        assert state.is_idle is True
        assert "Idle" in state.display_line

    def test_active_worker(self, temp_dir: Path) -> None:
        """Test active worker with a job."""
        job = DownloadJob(
            url="https://youtube.com/watch?v=test",
            output_dir=temp_dir,
        )
        job.current_title = "Test Video Title"
        job.current_percent = 50

        state = WorkerState(worker_id=1, job=job)
        assert state.is_idle is False
        assert "50%" in state.display_line
        assert "Test Video" in state.display_line

    def test_display_line_truncates_title(self, temp_dir: Path) -> None:
        """Test that long titles are truncated in display line."""
        job = DownloadJob(
            url="https://youtube.com/watch?v=test",
            output_dir=temp_dir,
        )
        job.current_title = "A" * 100  # Very long title
        job.current_percent = 25

        state = WorkerState(worker_id=0, job=job)
        display = state.display_line
        # Title should be truncated to 40 chars
        assert len(display) < 100


class TestWorkerPool:
    """Tests for WorkerPool executor."""

    def setup_method(self) -> None:
        """Reset shutdown state before each test."""
        reset_shutdown()

    def test_context_manager(self) -> None:
        """Test using WorkerPool as context manager."""
        with WorkerPool[int](max_workers=2) as pool:
            assert pool._executor is not None
            assert len(pool.worker_states) == 2

        assert pool._executor is None

    def test_submit_task(self) -> None:
        """Test submitting a task to the pool."""
        results: list[int] = []

        def task(x: int) -> int:
            results.append(x)
            return x * 2

        with WorkerPool[int](max_workers=2) as pool:
            future = pool.submit(task, 5)
            assert future is not None
            result = future.result()
            assert result == 10
            assert 5 in results

    def test_submit_job(self, temp_dir: Path) -> None:
        """Test submitting a download job."""
        job = DownloadJob(
            url="https://youtube.com/watch?v=test",
            output_dir=temp_dir,
        )

        def process_job(j: DownloadJob, worker_id: int) -> str:
            return f"Processed {j.url} by worker {worker_id}"

        with WorkerPool[str](max_workers=2) as pool:
            future = pool.submit_job(job, process_job, worker_id=0)
            assert future is not None
            result = future.result()
            assert "Processed" in result
            assert "worker 0" in result

    def test_worker_state_tracking(self, temp_dir: Path) -> None:
        """Test that worker state is tracked correctly."""
        job = DownloadJob(
            url="https://youtube.com/watch?v=test",
            output_dir=temp_dir,
        )

        def slow_task(_j: DownloadJob, _worker_id: int) -> str:
            time.sleep(0.1)
            return "done"

        with WorkerPool[str](max_workers=2) as pool:
            # Initially all workers are idle
            assert len(pool.get_idle_workers()) == 2

            # Submit a job
            future = pool.submit_job(job, slow_task, worker_id=0)

            # Worker 0 should now have the job
            assert pool.worker_states[0].job == job

            # Wait for completion
            if future:
                future.result()

            # Mark worker as idle
            pool.mark_worker_idle(0)
            assert pool.worker_states[0].is_idle

    def test_parallel_execution(self) -> None:
        """Test that tasks run in parallel."""
        start_times: dict[int, float] = {}
        end_times: dict[int, float] = {}

        def timed_task(task_id: int) -> int:
            start_times[task_id] = time.time()
            time.sleep(0.1)
            end_times[task_id] = time.time()
            return task_id

        with WorkerPool[int](max_workers=4) as pool:
            futures = [pool.submit(timed_task, i) for i in range(4)]
            for future in futures:
                if future:
                    future.result()

        # With 4 workers, tasks should overlap significantly
        # If sequential, total time would be ~0.4s
        # If parallel, total time should be ~0.1s
        overall_start = min(start_times.values())
        overall_end = max(end_times.values())
        total_time = overall_end - overall_start

        # Allow some margin, but should be much less than sequential time
        assert total_time < 0.3

    def test_wait_for_completion(self) -> None:
        """Test waiting for futures to complete."""

        def task(x: int) -> int:
            time.sleep(0.01)
            return x * 2

        completed: list[int] = []

        def on_complete(future: Future[int], _worker_id: int | None) -> None:
            completed.append(future.result())

        with WorkerPool[int](max_workers=2) as pool:
            futures = [pool.submit(task, i) for i in range(4)]
            valid_futures = [f for f in futures if f is not None]
            completion = pool.wait_for_completion(valid_futures, callback=on_complete)

        assert len(completed) == 4
        assert sorted(completion.results) == [0, 2, 4, 6]
        assert completion.has_errors is False
        assert completion.success_count == 4
        assert completion.error_count == 0

    def test_wait_for_completion_with_errors(self) -> None:
        """Test that errors are captured in CompletionResult."""

        def task(x: int) -> int:
            if x == 2:
                raise ValueError("Error on 2")
            return x * 2

        with WorkerPool[int](max_workers=2) as pool:
            futures = [pool.submit(task, i) for i in range(4)]
            valid_futures = [f for f in futures if f is not None]
            completion = pool.wait_for_completion(valid_futures)

        assert completion.success_count == 3
        assert completion.error_count == 1
        assert completion.has_errors is True
        assert sorted(completion.results) == [0, 2, 6]
        # Check the error was captured
        assert len(completion.errors) == 1
        _worker_id, error = completion.errors[0]
        assert isinstance(error, ValueError)
        assert "Error on 2" in str(error)

    def test_shutdown_prevents_new_tasks(self) -> None:
        """Test that shutdown prevents new task submission."""
        with WorkerPool[int](max_workers=2) as pool:
            # Trigger shutdown
            pool.shutdown()
            assert is_shutdown_requested()

            # New submission should return None
            future = pool.submit(lambda x: x, 1)
            assert future is None

    def test_get_active_and_idle_workers(self, temp_dir: Path) -> None:
        """Test getting lists of active and idle workers."""
        with WorkerPool[str](max_workers=4) as pool:
            # Initially all idle
            assert len(pool.get_idle_workers()) == 4
            assert len(pool.get_active_workers()) == 0

            # Simulate job assignment
            job = DownloadJob(
                url="https://youtube.com/watch?v=test",
                output_dir=temp_dir,
            )
            pool.worker_states[0].job = job
            pool.worker_states[1].job = job

            assert len(pool.get_idle_workers()) == 2
            assert len(pool.get_active_workers()) == 2
