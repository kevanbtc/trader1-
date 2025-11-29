"""
Centralized RPC Configuration
Eliminates all hardcoded Alchemy dependencies and provides robust RPC handling
"""
import os
import time
import random
import logging
from typing import Optional, Dict, List
from functools import wraps

logger = logging.getLogger(__name__)

# ============================================
# CENTRALIZED RPC ENDPOINTS
# ============================================

class RPCConfig:
    """Single source of truth for all RPC endpoints"""
    
    # Primary public RPCs (no rate limits, no API keys)
    PUBLIC_RPCS = {
        "ARBITRUM": [
            "https://arb1.arbitrum.io/rpc",
            "https://arbitrum.llamarpc.com",
            "https://rpc.ankr.com/arbitrum",
        ],
        "ETHEREUM": [
            "https://eth.llamarpc.com",
            "https://rpc.ankr.com/eth",
        ],
        "POLYGON": [
            "https://polygon.llamarpc.com",
            "https://rpc.ankr.com/polygon",
        ],
        "OPTIMISM": [
            "https://mainnet.optimism.io",
            "https://rpc.ankr.com/optimism",
        ],
        "BASE": [
            "https://mainnet.base.org",
            "https://base.llamarpc.com",
        ],
    }
    
    @classmethod
    def get_rpc(cls, chain: str = "ARBITRUM", prefer_env: bool = True) -> str:
        """
        Get RPC URL for a specific chain
        
        Args:
            chain: Chain name (ARBITRUM, ETHEREUM, etc.)
            prefer_env: Try environment variable first
            
        Returns:
            RPC URL string
        """
        chain = chain.upper()
        
        # Try environment variable first
        if prefer_env:
            env_key = f"ARB_RPC_1" if chain == "ARBITRUM" else f"{chain}_RPC"
            env_rpc = os.getenv(env_key)
            if env_rpc and not "alchemy" in env_rpc.lower():
                return env_rpc
        
        # Fall back to public RPC
        public_rpcs = cls.PUBLIC_RPCS.get(chain, [])
        if public_rpcs:
            return public_rpcs[0]
        
        # Final fallback
        if chain == "ARBITRUM":
            return "https://arb1.arbitrum.io/rpc"
        
        raise ValueError(f"No RPC configured for chain: {chain}")
    
    @classmethod
    def get_all_rpcs(cls, chain: str = "ARBITRUM") -> List[str]:
        """Get all available RPCs for a chain (for fallback)"""
        chain = chain.upper()
        return cls.PUBLIC_RPCS.get(chain, [])


# ============================================
# RETRY LOGIC WITH EXPONENTIAL BACKOFF
# ============================================

class RetryConfig:
    """Retry configuration for RPC calls"""
    MAX_RETRIES = 5
    BASE_DELAY = 0.1  # 100ms
    MAX_DELAY = 5.0   # 5 seconds
    JITTER_RANGE = (0.05, 0.2)  # 50-200ms random jitter


def exponential_backoff_with_jitter(attempt: int) -> float:
    """Calculate delay with exponential backoff and random jitter"""
    delay = min(
        RetryConfig.BASE_DELAY * (2 ** attempt),
        RetryConfig.MAX_DELAY
    )
    jitter = random.uniform(*RetryConfig.JITTER_RANGE)
    return delay + jitter


def robust_rpc_call(max_retries: int = RetryConfig.MAX_RETRIES):
    """
    Decorator for robust RPC calls with retry logic
    
    Usage:
        @robust_rpc_call(max_retries=5)
        def get_quote(...):
            return w3.eth.call(...)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                    
                except Exception as e:
                    last_error = e
                    error_msg = str(e).lower()
                    
                    # Don't retry on certain errors
                    if any(x in error_msg for x in ["invalid", "revert", "execution"]):
                        logger.debug(f"{func.__name__} - Non-retryable error: {e}")
                        raise
                    
                    # Rate limit or connection error - retry
                    if attempt < max_retries - 1:
                        delay = exponential_backoff_with_jitter(attempt)
                        logger.debug(
                            f"{func.__name__} - Attempt {attempt + 1}/{max_retries} failed, "
                            f"retrying in {delay:.2f}s: {e}"
                        )
                        time.sleep(delay)
                    else:
                        logger.warning(f"{func.__name__} - All {max_retries} attempts failed")
            
            # All retries exhausted
            raise last_error
        
        return wrapper
    return decorator


# ============================================
# CIRCUIT BREAKER
# ============================================

class CircuitBreaker:
    """
    Circuit breaker to prevent cascading failures
    Opens circuit after consecutive failures, preventing further attempts
    """
    
    def __init__(self, failure_threshold: int = 3, timeout: float = 30.0):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = {}  # key -> failure_count
        self.last_failure_time = {}  # key -> timestamp
        self.open_circuits = set()  # keys with open circuits
    
    def is_open(self, key: str) -> bool:
        """Check if circuit is open for a given key"""
        if key not in self.open_circuits:
            return False
        
        # Check if timeout has passed
        if time.time() - self.last_failure_time.get(key, 0) > self.timeout:
            self._reset(key)
            return False
        
        return True
    
    def record_success(self, key: str):
        """Record successful call"""
        self._reset(key)
    
    def record_failure(self, key: str):
        """Record failed call"""
        self.failures[key] = self.failures.get(key, 0) + 1
        self.last_failure_time[key] = time.time()
        
        if self.failures[key] >= self.failure_threshold:
            self.open_circuits.add(key)
            logger.warning(
                f"Circuit breaker OPEN for {key} after {self.failures[key]} failures. "
                f"Will retry in {self.timeout}s"
            )
    
    def _reset(self, key: str):
        """Reset circuit breaker for key"""
        self.failures.pop(key, None)
        self.last_failure_time.pop(key, None)
        self.open_circuits.discard(key)


# Global circuit breaker instance
circuit_breaker = CircuitBreaker(failure_threshold=3, timeout=30.0)


# ============================================
# USAGE EXAMPLES
# ============================================

if __name__ == "__main__":
    # Example 1: Get RPC for Arbitrum
    arb_rpc = RPCConfig.get_rpc("ARBITRUM")
    print(f"Arbitrum RPC: {arb_rpc}")
    
    # Example 2: Get all fallback RPCs
    all_rpcs = RPCConfig.get_all_rpcs("ARBITRUM")
    print(f"All Arbitrum RPCs: {all_rpcs}")
    
    # Example 3: Use retry decorator
    @robust_rpc_call(max_retries=3)
    def sample_rpc_call():
        # This will retry up to 3 times with backoff
        return "result"
    
    # Example 4: Use circuit breaker
    key = "uniswap_v3"
    if not circuit_breaker.is_open(key):
        try:
            # Make RPC call
            result = sample_rpc_call()
            circuit_breaker.record_success(key)
        except Exception as e:
            circuit_breaker.record_failure(key)
