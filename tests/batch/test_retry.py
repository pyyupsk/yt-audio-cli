"""Unit tests for RetryConfig and retry logic."""

from __future__ import annotations

import pytest

from yt_audio_cli.batch.retry import (
    RetryConfig,
    is_permanent_error,
    is_retryable_error,
)


class TestRetryConfig:
    """Tests for RetryConfig dataclass."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = RetryConfig()
        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 30.0
        assert config.jitter is True

    def test_custom_values(self) -> None:
        """Test custom configuration values."""
        config = RetryConfig(
            max_attempts=5,
            base_delay=2.0,
            max_delay=60.0,
            jitter=False,
        )
        assert config.max_attempts == 5
        assert config.base_delay == 2.0
        assert config.max_delay == 60.0
        assert config.jitter is False

    def test_invalid_max_attempts_low(self) -> None:
        """Test that max_attempts < 1 raises ValueError."""
        with pytest.raises(ValueError, match="max_attempts must be >= 1"):
            RetryConfig(max_attempts=0)

    def test_invalid_max_attempts_high(self) -> None:
        """Test that max_attempts > 10 raises ValueError."""
        with pytest.raises(ValueError, match="max_attempts must be <= 10"):
            RetryConfig(max_attempts=11)

    def test_invalid_base_delay(self) -> None:
        """Test that negative base_delay raises ValueError."""
        with pytest.raises(ValueError, match="base_delay must be >= 0"):
            RetryConfig(base_delay=-1.0)

    def test_invalid_max_delay(self) -> None:
        """Test that max_delay < base_delay raises ValueError."""
        with pytest.raises(ValueError, match=r"max_delay .* must be >= base_delay"):
            RetryConfig(base_delay=10.0, max_delay=5.0)

    def test_delay_for_attempt_exponential(self) -> None:
        """Test exponential backoff calculation."""
        config = RetryConfig(base_delay=1.0, max_delay=30.0, jitter=False)

        assert config.delay_for_attempt(0) == 1.0  # 1 * 2^0 = 1
        assert config.delay_for_attempt(1) == 2.0  # 1 * 2^1 = 2
        assert config.delay_for_attempt(2) == 4.0  # 1 * 2^2 = 4
        assert config.delay_for_attempt(3) == 8.0  # 1 * 2^3 = 8
        assert config.delay_for_attempt(4) == 16.0  # 1 * 2^4 = 16
        assert config.delay_for_attempt(5) == 30.0  # capped at max_delay

    def test_delay_for_attempt_with_jitter(self) -> None:
        """Test that jitter adds randomness to delay."""
        config = RetryConfig(base_delay=1.0, max_delay=30.0, jitter=True)

        delay = config.delay_for_attempt(0)
        # Base delay is 1.0, jitter adds 0-1, so delay should be 1.0-2.0
        assert 1.0 <= delay <= 2.0

    def test_delay_for_negative_attempt(self) -> None:
        """Test that negative attempt number is treated as 0."""
        config = RetryConfig(base_delay=1.0, jitter=False)
        assert config.delay_for_attempt(-1) == 1.0

    def test_should_retry(self) -> None:
        """Test should_retry logic."""
        config = RetryConfig(max_attempts=3)

        assert config.should_retry(0) is True  # Can retry after attempt 0
        assert config.should_retry(1) is True  # Can retry after attempt 1
        assert config.should_retry(2) is False  # No retry after attempt 2 (3rd attempt)
        assert config.should_retry(3) is False  # Definitely no more retries


class TestRetryableErrors:
    """Tests for error classification functions."""

    @pytest.mark.parametrize(
        "error",
        [
            "Connection timeout",
            "connection reset by peer",
            "temporary failure in name resolution",
            "HTTP Error 429: Too Many Requests",
            "503 Service Unavailable",
            "Network is unreachable",
            "Read timed out",
            "SSL Error: Connection reset",
        ],
    )
    def test_retryable_errors(self, error: str) -> None:
        """Test that transient errors are classified as retryable."""
        assert is_retryable_error(error) is True

    @pytest.mark.parametrize(
        "error",
        [
            "Video unavailable",
            "This video is private",
            "HTTP Error 404: Not Found",
            "This video has been removed",
            "Sign in to confirm your age",
            "This video is age-restricted",
            "Video is blocked in your country",
            "This video is only available to members",
            "Copyright claim",
        ],
    )
    def test_permanent_errors(self, error: str) -> None:
        """Test that permanent errors are not retryable."""
        assert is_retryable_error(error) is False
        assert is_permanent_error(error) is True

    def test_empty_error_not_retryable(self) -> None:
        """Test that empty error is not retryable."""
        assert is_retryable_error("") is False
        assert is_permanent_error("") is False

    def test_unknown_error_not_retryable(self) -> None:
        """Test that unknown errors are not retryable by default."""
        assert is_retryable_error("Some random error message") is False

    def test_permanent_error_takes_precedence(self) -> None:
        """Test that permanent error patterns take precedence."""
        # This contains both "timeout" (retryable) and "video unavailable" (permanent)
        error = "timeout while checking video unavailable status"
        assert is_retryable_error(error) is False
        assert is_permanent_error(error) is True
