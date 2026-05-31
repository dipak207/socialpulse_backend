"""Retry decorators and helpers using tenacity for robust scraping."""
import asyncio
import functools
from typing import Any, Callable, Coroutine, Optional, Type
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    after_log,
)
import logging

logger = logging.getLogger(__name__)

# Default retry exceptions
_DEFAULT_RETRY_EXCEPTIONS = (
    Exception,  # broad — subclasses can narrow this
)


def async_retry(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 10.0,
    multiplier: float = 2.0,
    retry_exceptions: tuple = _DEFAULT_RETRY_EXCEPTIONS,
    reraise: bool = True,
):
    """
    Decorator that retries an async function with exponential backoff.

    Args:
        max_attempts: Total number of attempts (including the first).
        min_wait: Minimum seconds to wait between attempts.
        max_wait: Maximum seconds to wait between attempts.
        multiplier: Backoff multiplier.
        retry_exceptions: Tuple of exception types to retry on.
        reraise: Whether to re-raise the last exception after exhausting retries.
    """
    def decorator(func: Callable) -> Callable:
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=multiplier, min=min_wait, max=max_wait),
            retry=retry_if_exception_type(retry_exceptions),
            reraise=reraise,
        )
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await func(*args, **kwargs)

        return wrapper

    return decorator


async def retry_with_backoff(
    coro: Coroutine,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    exceptions: tuple = (Exception,),
) -> Any:
    """
    Execute a coroutine with exponential backoff retry logic.

    Args:
        coro: The coroutine to execute.
        max_attempts: Maximum number of attempts.
        base_delay: Initial delay in seconds before doubling.
        exceptions: Exception types that should trigger a retry.

    Returns:
        The result of the coroutine.

    Raises:
        The last exception if all attempts fail.
    """
    last_exc: Optional[Exception] = None
    for attempt in range(max_attempts):
        try:
            return await coro
        except exceptions as exc:  # type: ignore[misc]
            last_exc = exc
            if attempt < max_attempts - 1:
                delay = base_delay * (2 ** attempt)
                logger.warning(
                    "Attempt %d/%d failed: %s. Retrying in %.1fs…",
                    attempt + 1,
                    max_attempts,
                    exc,
                    delay,
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    "All %d attempts failed. Last error: %s", max_attempts, exc
                )
    raise last_exc  # type: ignore[misc]


__all__ = ["async_retry", "retry_with_backoff"]
