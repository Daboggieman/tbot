import time
import logging
import random
from functools import wraps

logger = logging.getLogger(__name__)

def retry_with_backoff(retries=5, initial_delay=1, backoff_factor=2, jitter=True, allowed_exceptions=(Exception,)):
    """
    A decorator to retry a function with an exponential backoff strategy.

    Args:
        retries (int): The maximum number of retries.
        initial_delay (int): The initial delay in seconds.
        backoff_factor (int): The factor by which the delay increases.
        jitter (bool): Whether to add a random jitter to the delay.
        allowed_exceptions (tuple): A tuple of exception types to catch and retry on.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            for i in range(retries):
                try:
                    return func(*args, **kwargs)
                except allowed_exceptions as e:
                    if i == retries - 1:
                        logger.error(f"Function {func.__name__} failed after {retries} retries.")
                        raise
                    
                    sleep_duration = delay
                    if jitter:
                        sleep_duration += random.uniform(0, delay * 0.5)

                    logger.warning(f"Function {func.__name__} failed with {e.__class__.__name__}. Retrying in {sleep_duration:.2f} seconds...")
                    time.sleep(sleep_duration)
                    delay *= backoff_factor
        return wrapper
    return decorator
