"""
RPC Error Handling and Rate Limiting
Provides backoff logic for 429 errors and other RPC failures
"""

import asyncio
import logging
from typing import Callable, Any, TypeVar, Optional
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')

class RpcRateLimitError(Exception):
    """Raised when RPC returns 429 Too Many Requests"""
    pass

class RpcConnectionError(Exception):
    """Raised when RPC connection fails"""
    pass

def is_rate_limit_error(err: Exception) -> bool:
    """Check if error is a 429 rate limit error"""
    msg = str(err).lower()
    return "429" in msg or "too many requests" in msg

def is_connection_error(err: Exception) -> bool:
    """Check if error is a connection issue"""
    msg = str(err).lower()
    return any(term in msg for term in [
        "connection", "timeout", "unreachable", 
        "502", "503", "504", "network"
    ])

async def safe_rpc_call(fn: Callable[..., T], *args, **kwargs) -> Optional[T]:
    """
    Wrap an RPC call to categorize errors properly
    Returns None on rate limit or connection errors
    """
    try:
        if asyncio.iscoroutinefunction(fn):
            return await fn(*args, **kwargs)
        else:
            return fn(*args, **kwargs)
    except Exception as e:
        if is_rate_limit_error(e):
            raise RpcRateLimitError(f"Rate limited: {e}")
        elif is_connection_error(e):
            raise RpcConnectionError(f"Connection error: {e}")
        raise

def with_rpc_retry(max_retries: int = 3, backoff_base: float = 2.0):
    """
    Decorator for RPC methods that should retry on transient errors
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except RpcRateLimitError as e:
                    # Don't retry rate limits, let backoff handler deal with it
                    raise
                except RpcConnectionError as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        wait_time = backoff_base ** attempt
                        logger.warning(f"RPC connection error, retry {attempt+1}/{max_retries} in {wait_time}s: {e}")
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(f"RPC connection failed after {max_retries} retries")
                        raise
                except Exception as e:
                    # Unknown error, don't retry
                    raise
            raise last_error
        return wrapper
    return decorator

class RpcBackoffManager:
    """
    Manages backoff state for RPC calls
    Tracks consecutive errors and triggers cooldown periods
    """
    def __init__(self, max_consecutive_errors: int = 5, backoff_seconds: float = 15.0):
        self.max_consecutive_errors = max_consecutive_errors
        self.backoff_seconds = backoff_seconds
        self.consecutive_errors = 0
        self.in_backoff = False
        
    def record_success(self):
        """Reset error counter on successful call"""
        self.consecutive_errors = 0
        self.in_backoff = False
        
    def record_error(self) -> bool:
        """
        Record an error and check if we should enter backoff
        Returns True if backoff threshold reached
        """
        self.consecutive_errors += 1
        if self.consecutive_errors >= self.max_consecutive_errors:
            self.in_backoff = True
            return True
        return False
    
    async def maybe_backoff(self) -> bool:
        """
        Check if we're in backoff and wait if needed
        Returns True if we backed off
        """
        if self.in_backoff:
            logger.warning(
                f"🛑 RPC backoff triggered ({self.consecutive_errors} consecutive errors). "
                f"Pausing for {self.backoff_seconds}s..."
            )
            await asyncio.sleep(self.backoff_seconds)
            self.consecutive_errors = 0
            self.in_backoff = False
            logger.info("✅ RPC backoff complete, resuming...")
            return True
        return False
    
    def reset(self):
        """Hard reset of error tracking"""
        self.consecutive_errors = 0
        self.in_backoff = False
