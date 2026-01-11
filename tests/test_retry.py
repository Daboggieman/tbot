import pytest
import time
from bot.retry_utils import retry_with_backoff

def test_retry_success():
    call_count = 0
    
    @retry_with_backoff(retries=3, initial_delay=0.1)
    def succeed_on_second_try():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise ValueError("Fail first time")
        return "Success"
    
    result = succeed_on_second_try()
    assert result == "Success"
    assert call_count == 2

def test_retry_failure_after_max_retries():
    call_count = 0
    
    @retry_with_backoff(retries=3, initial_delay=0.1)
    def always_fail():
        nonlocal call_count
        call_count += 1
        raise ValueError("Always fail")
    
    with pytest.raises(ValueError, match="Always fail"):
        always_fail()
    assert call_count == 3
