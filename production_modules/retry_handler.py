import time
import logging
from typing import Callable, Any, Optional, Type, Tuple
from functools import wraps
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    after_log
)
from dataclasses import dataclass


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """Configuration for retry behavior"""
    max_attempts: int = 3
    initial_wait: float = 1.0  # seconds
    max_wait: float = 10.0  # seconds
    exponential_base: int = 2
    retry_on_timeout: bool = True
    retry_on_rate_limit: bool = True
    retry_on_server_error: bool = True


class APIError(Exception):
    """Base exception for API errors"""
    pass


class RateLimitError(APIError):
    """Raised when API rate limit is exceeded"""
    pass


class TimeoutError(APIError):
    """Raised when API request times out"""
    pass


class ServerError(APIError):
    """Raised when API server returns 5xx error"""
    pass


class RetryExhaustedError(Exception):
    """Raised when all retry attempts have been exhausted"""
    pass


class RetryHandler:
    """
    Handles automatic retries with exponential backoff for API calls.
    Implements resilient error handling for transient failures.
    """
    
    def __init__(self, config: Optional[RetryConfig] = None):
        """
        Initialize retry handler.
        
        Args:
            config: RetryConfig object (uses defaults if None)
        """
        self.config = config or RetryConfig()
        self.retry_stats = {
            "total_attempts": 0,
            "successful_attempts": 0,
            "failed_attempts": 0,
            "total_retries": 0,
            "retry_reasons": {}
        }
    
    def classify_error(self, error: Exception) -> Tuple[bool, str]:
        """
        Determines if an error is retryable and returns error type.
        
        Args:
            error: Exception to classify
            
        Returns:
            Tuple of (is_retryable, error_type)
        """
        error_str = str(error).lower()
        
        # Rate limit errors (429)
        if "rate limit" in error_str or "429" in error_str:
            return self.config.retry_on_rate_limit, "rate_limit"
        
        # Timeout errors
        if "timeout" in error_str or "timed out" in error_str:
            return self.config.retry_on_timeout, "timeout"
        
        # Server errors (5xx)
        if any(code in error_str for code in ["500", "502", "503", "504"]):
            return self.config.retry_on_server_error, "server_error"
        
        # Connection errors
        if "connection" in error_str or "network" in error_str:
            return True, "connection_error"
        
        # Not retryable (4xx client errors except 429)
        return False, "client_error"
    
    def should_retry(self, error: Exception, attempt: int) -> bool:
        """
        Determines if another retry should be attempted.
        
        Args:
            error: The exception that occurred
            attempt: Current attempt number (1-indexed)
            
        Returns:
            True if should retry, False otherwise
        """
        if attempt >= self.config.max_attempts:
            logger.warning(f"Max retry attempts ({self.config.max_attempts}) reached")
            return False
        
        is_retryable, error_type = self.classify_error(error)
        
        if not is_retryable:
            logger.info(f"Error type '{error_type}' is not retryable")
            return False
        
        return True
    
    def calculate_wait_time(self, attempt: int) -> float:
        """
        Calculates wait time using exponential backoff with jitter.
        
        Args:
            attempt: Current attempt number (1-indexed)
            
        Returns:
            Wait time in seconds
        """
        # Exponential backoff: initial_wait * (base ^ (attempt - 1))
        wait_time = self.config.initial_wait * (
            self.config.exponential_base ** (attempt - 1)
        )
        
        # Cap at max_wait
        wait_time = min(wait_time, self.config.max_wait)
        
        # Add jitter (randomness) to prevent thundering herd
        import random
        jitter = random.uniform(0, 0.1 * wait_time)
        
        return wait_time + jitter
    
    def execute_with_retry(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Executes a function with automatic retry logic.
        
        Args:
            func: Function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Result from the function
            
        Raises:
            RetryExhaustedError: If all retries are exhausted
        """
        last_error = None
        
        for attempt in range(1, self.config.max_attempts + 1):
            self.retry_stats["total_attempts"] += 1
            
            try:
                logger.info(f"Attempt {attempt}/{self.config.max_attempts}")
                result = func(*args, **kwargs)
                
                # Success!
                self.retry_stats["successful_attempts"] += 1
                if attempt > 1:
                    logger.info(f"✓ Succeeded on attempt {attempt}")
                
                return result
                
            except Exception as error:
                last_error = error
                is_retryable, error_type = self.classify_error(error)
                
                # Track retry reasons
                if error_type not in self.retry_stats["retry_reasons"]:
                    self.retry_stats["retry_reasons"][error_type] = 0
                self.retry_stats["retry_reasons"][error_type] += 1
                
                logger.warning(
                    f"✗ Attempt {attempt} failed: {error_type} - {str(error)[:100]}"
                )
                
                # Check if we should retry
                if not self.should_retry(error, attempt):
                    self.retry_stats["failed_attempts"] += 1
                    raise error
                
                # Calculate wait time and sleep
                if attempt < self.config.max_attempts:
                    wait_time = self.calculate_wait_time(attempt)
                    logger.info(f"Waiting {wait_time:.2f}s before retry...")
                    time.sleep(wait_time)
                    self.retry_stats["total_retries"] += 1
        
        # All retries exhausted
        self.retry_stats["failed_attempts"] += 1
        raise RetryExhaustedError(
            f"Failed after {self.config.max_attempts} attempts. "
            f"Last error: {last_error}"
        )
    
    def get_statistics(self) -> dict:
        """Get retry statistics"""
        success_rate = (
            self.retry_stats["successful_attempts"] / 
            max(self.retry_stats["total_attempts"], 1) * 100
        )
        
        return {
            **self.retry_stats,
            "success_rate_percent": round(success_rate, 2),
            "average_retries_per_request": round(
                self.retry_stats["total_retries"] / 
                max(self.retry_stats["total_attempts"], 1),
                2
            )
        }
    
    def reset_statistics(self):
        """Reset retry statistics"""
        self.retry_stats = {
            "total_attempts": 0,
            "successful_attempts": 0,
            "failed_attempts": 0,
            "total_retries": 0,
            "retry_reasons": {}
        }


def with_retry(config: Optional[RetryConfig] = None):
    """
    Decorator for automatic retry with exponential backoff.
    
    Usage:
        @with_retry(RetryConfig(max_attempts=5))
        def my_api_call():
            # ... API call logic
            pass
    """
    def decorator(func: Callable) -> Callable:
        handler = RetryHandler(config)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            return handler.execute_with_retry(func, *args, **kwargs)
        
        # Attach handler for accessing statistics
        wrapper.retry_handler = handler
        
        return wrapper
    
    return decorator


# Tenacity-based retry decorator (alternative approach)
def with_tenacity_retry(
    max_attempts: int = 3,
    initial_wait: float = 1.0,
    max_wait: float = 10.0
):
    """
    Alternative retry decorator using the tenacity library.
    Provides more sophisticated retry logic out-of-the-box.
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(
            multiplier=initial_wait,
            max=max_wait
        ),
        retry=retry_if_exception_type((
            RateLimitError,
            TimeoutError,
            ServerError,
            ConnectionError
        )),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        after=after_log(logger, logging.INFO)
    )


# Example usage and testing
if __name__ == "__main__":
    # Test the retry handler
    handler = RetryHandler(RetryConfig(max_attempts=3, initial_wait=0.5))
    
    # Simulate API call that fails twice then succeeds
    class APICallCounter:
        def __init__(self):
            self.call_count = 0
    
    counter = APICallCounter()
    
    def flaky_api_call():
        counter.call_count += 1
        print(f"API call attempt {counter.call_count}")
        
        if counter.call_count < 3:
            raise TimeoutError("Connection timeout")
        
        return {"status": "success", "data": "classified"}
    
    try:
        result = handler.execute_with_retry(flaky_api_call)
        print(f"\n✓ Success: {result}")
    except Exception as e:
        print(f"\n✗ Failed: {e}")
    
    print("\nRetry Statistics:")
    print("="*50)
    stats = handler.get_statistics()
    for key, value in stats.items():
        print(f"{key}: {value}")
    
    # Test with decorator
    print("\n" + "="*50)
    print("Testing decorator approach:")
    print("="*50)
    
    @with_retry(RetryConfig(max_attempts=2))
    def test_api():
        import random
        if random.random() < 0.5:
            raise ServerError("500 Internal Server Error")
        return "Success!"
    
    try:
        result = test_api()
        print(f"Result: {result}")
    except Exception as e:
        print(f"Failed: {e}")
