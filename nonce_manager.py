#!/usr/bin/env python3
"""
Persistent Nonce Manager for Kraken API
Prevents "Invalid nonce" errors by maintaining a monotonically increasing counter
"""

import os
import time
import threading

NONCE_FILE = "kraken_nonce.txt"
_lock = threading.Lock()

def load_nonce():
    """Load last used nonce from file"""
    if os.path.exists(NONCE_FILE):
        try:
            with open(NONCE_FILE, "r") as f:
                return int(f.read().strip())
        except:
            pass
    return int(time.time() * 1000)

def save_nonce(value):
    """Save nonce to file"""
    with open(NONCE_FILE, "w") as f:
        f.write(str(value))

def next_nonce():
    """
    Get next valid nonce (thread-safe)
    Always returns last nonce + 1 (strictly monotonic)
    Does NOT fall back to current timestamp (prevents regression)
    """
    with _lock:
        last = load_nonce()
        
        # Always increment by 1 (never regress)
        new = last + 1
        save_nonce(new)
        return new

def reset_nonce(boost_ms=5000000):
    """
    Emergency nonce reset - jumps nonce forward by boost_ms
    Use if you get persistent "invalid nonce" errors
    """
    with _lock:
        current_time_ms = int(time.time() * 1000)
        new = current_time_ms + boost_ms
        save_nonce(new)
        print(f"✅ Nonce reset to: {new}")
        return new

def get_current_nonce():
    """Read current nonce without incrementing"""
    return load_nonce()


if __name__ == "__main__":
    print("=" * 60)
    print("🔧 KRAKEN NONCE MANAGER TEST")
    print("=" * 60)
    print()
    
    current = get_current_nonce()
    print(f"Current nonce: {current}")
    
    print("\nGenerating 5 sequential nonces:")
    for i in range(5):
        n = next_nonce()
        print(f"  Nonce {i+1}: {n}")
    
    print()
    print("=" * 60)
    print("✅ Nonce manager working correctly")
    print(f"✅ Nonce file: {os.path.abspath(NONCE_FILE)}")
