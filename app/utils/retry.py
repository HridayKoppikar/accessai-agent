"""
Retry utilities for AccessAI

Provides exponential backoff retry logic for handling transient API errors
like 503 UNAVAILABLE, high demand, etc.
"""

import asyncio
from typing import Callable, Any, Optional


async def with_retry(
    func: Callable,
    max_retries: int = 3,
    base_delay: float = 2.0,
    backoff_multiplier: float = 2.0,
    retryable_errors: Optional[list] = None
) -> Any:
    """Execute function with exponential backoff for transient errors.

    Args:
        func: Async function to execute
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        backoff_multiplier: Multiplier for delay between retries
        retryable_errors: List of error strings that trigger retry (default: common transient errors)

    Returns:
        Result of the function

    Raises:
        The last exception encountered if all retries exhausted
    """
    if retryable_errors is None:
        retryable_errors = [
            'unavailable', '503', 'high demand', 'temporarily',
            'service unavailable', 'rate limit', 'too many requests'
        ]

    last_error = None

    for attempt in range(max_retries):
        try:
            if asyncio.iscoroutinefunction(func):
                return await func()
            return func()

        except Exception as e:
            last_error = e
            error_msg = str(e).lower()

            # Check if this is a retryable error
            is_retryable = any(err in error_msg for err in retryable_errors)

            if is_retryable and attempt < max_retries - 1:
                # Calculate delay with exponential backoff
                delay = base_delay * (backoff_multiplier ** attempt)

                print(f"  [Retry] Transient error detected. Attempt {attempt + 1}/{max_retries}")
                print(f"  [Retry] Waiting {delay:.1f}s before retry...")

                await asyncio.sleep(delay)
                continue

            # Non-retryable error or max retries reached
            if not is_retryable:
                print(f"  [Retry] Non-retryable error: {type(e).__name__}")
            else:
                print(f"  [Retry] Max retries ({max_retries}) exhausted")

            raise last_error

    return None


def retry_on_unavailable(max_retries: int = 3, base_delay: float = 2.0):
    """Decorator for automatic retry on unavailable errors.

    Usage:
        @retry_on_unavailable(max_retries=3)
        async def my_function():
            ...
    """
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            return await with_retry(
                lambda: func(*args, **kwargs),
                max_retries=max_retries,
                base_delay=base_delay
            )
        return wrapper
    return decorator


class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 2.0,
        max_delay: float = 60.0,
        backoff_multiplier: float = 2.0
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_multiplier = backoff_multiplier

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for a given attempt number."""
        delay = self.base_delay * (self.backoff_multiplier ** attempt)
        return min(delay, self.max_delay)


async def retry_with_config(
    func: Callable,
    config: RetryConfig,
    retryable_errors: Optional[list] = None
) -> Any:
    """Execute function with custom retry configuration."""
    last_error = None

    for attempt in range(config.max_retries):
        try:
            if asyncio.iscoroutinefunction(func):
                return await func()
            return func()

        except Exception as e:
            last_error = e
            error_msg = str(e).lower()

            if retryable_errors and not any(err in error_msg for err in retryable_errors):
                raise e

            if attempt < config.max_retries - 1:
                delay = config.get_delay(attempt)
                await asyncio.sleep(delay)

    raise last_error