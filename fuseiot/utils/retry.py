import time
import functools
from typing import TypeVar, Callable, Optional, Tuple, Type
from dataclasses import dataclass

F = TypeVar("F", bound=Callable[..., any])


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    
    max_attempts: int = 3
    base_delay: float = 0.1
    max_delay: float = 5.0
    exponential_base: float = 2.0
    retryable_exceptions: Tuple[Type[Exception], ...] = (
        ConnectionError,
        TimeoutError,
        OSError,
    )


def retry(config: Optional[RetryConfig] = None) -> Callable[[F], F]:
    """
    Decorator: retry function with exponential backoff.
    
    Args:
        config: Retry behavior configuration
        
    Example:
        @retry()
        def fetch_data():
            return requests.get(url)
    """
    cfg = config or RetryConfig()
    
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(cfg.max_attempts):
                try:
                    return func(*args, **kwargs)
                except cfg.retryable_exceptions as e:
                    last_exception = e
                    
                    if attempt < cfg.max_attempts - 1:
                        delay = min(
                            cfg.base_delay * (cfg.exponential_base ** attempt),
                            cfg.max_delay
                        )
                        time.sleep(delay)
                    else:
                        raise last_exception
            
            # Should never reach here
            raise last_exception or RuntimeError("Retry failed")
        
        return wrapper  # type: ignore
    
    return decorator