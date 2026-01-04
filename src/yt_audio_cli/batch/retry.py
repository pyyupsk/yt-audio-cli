"""Retry configuration and exponential backoff logic."""

from __future__ import annotations

import random
from dataclasses import dataclass

# Error patterns that indicate transient/retryable failures
RETRYABLE_PATTERNS = frozenset(
    {
        "timeout",
        "connection reset",
        "temporary failure",
        "429",
        "too many requests",
        "503",
        "service unavailable",
        "network",
        "timed out",
        "connection refused",
        "connection error",
        "ssl error",
        "read timeout",
        "write timeout",
    }
)

# Error patterns that indicate permanent failures (no retry)
PERMANENT_PATTERNS = frozenset(
    {
        "404",
        "not found",
        "video unavailable",
        "private video",
        "is private",
        "age restricted",
        "age-restricted",
        "copyright",
        "removed",
        "deleted",
        "blocked",
        "geo restricted",
        "members only",
        "available to members",
        "sign in",
        "login required",
        "invalid url",
        "unsupported url",
    }
)


@dataclass
class RetryConfig:
    """Retry behavior configuration.

    Attributes:
        max_attempts: Maximum number of retry attempts (1 = no retries).
        base_delay: Base delay in seconds for exponential backoff.
        max_delay: Maximum delay cap in seconds.
        jitter: Whether to add random jitter to delays.
    """

    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    jitter: bool = True

    def __post_init__(self) -> None:
        """Validate configuration."""
        if self.max_attempts < 1:
            raise ValueError(f"max_attempts must be >= 1, got {self.max_attempts}")
        if self.max_attempts > 10:
            raise ValueError(f"max_attempts must be <= 10, got {self.max_attempts}")
        if self.base_delay < 0:
            raise ValueError(f"base_delay must be >= 0, got {self.base_delay}")
        if self.max_delay < self.base_delay:
            raise ValueError(
                f"max_delay ({self.max_delay}) must be >= base_delay ({self.base_delay})"
            )

    def delay_for_attempt(self, attempt: int) -> float:
        """Calculate delay for given attempt number.

        Uses exponential backoff: delay = min(base * 2^attempt, max_delay)
        With optional jitter: delay += random(0, 1)

        Args:
            attempt: The attempt number (0-indexed).

        Returns:
            Delay in seconds before the next retry.
        """
        if attempt < 0:
            attempt = 0

        delay = min(self.base_delay * (2**attempt), self.max_delay)

        if self.jitter:
            delay += random.uniform(0, 1)  # nosec B311 - jitter, not security

        return delay

    def should_retry(self, attempt: int) -> bool:
        """Check if another retry attempt should be made.

        Args:
            attempt: The current attempt number (0-indexed).

        Returns:
            True if more retries are allowed.
        """
        return attempt < self.max_attempts - 1


def is_retryable_error(error: str) -> bool:
    """Check if an error is retryable (transient).

    Args:
        error: The error message to check.

    Returns:
        True if the error appears to be transient and worth retrying.
    """
    if not error:
        return False

    error_lower = error.lower()

    # First check if it's a permanent error
    if is_permanent_error(error):
        return False

    # Check for retryable patterns
    return any(pattern in error_lower for pattern in RETRYABLE_PATTERNS)


def is_permanent_error(error: str) -> bool:
    """Check if an error is permanent (should not retry).

    Args:
        error: The error message to check.

    Returns:
        True if the error appears to be permanent.
    """
    if not error:
        return False

    error_lower = error.lower()
    return any(pattern in error_lower for pattern in PERMANENT_PATTERNS)
