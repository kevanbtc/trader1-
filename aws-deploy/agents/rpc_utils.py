"""
RPC utilities for resilient Web3 access on Arbitrum.

Features:
- Loads multiple RPC endpoints from environment variables
- Uses MultiProviderRPC to health-check and select best provider
- Runs provider monitoring in a background thread
- Exposes a Web3 proxy that always routes to the current best provider

Environment variables supported (first non-empty are used):
- ARB_RPC_1 .. ARB_RPC_5
- ALCHEMY_ARB_HTTPS (full https URL)
- INFURA_ARB_HTTPS (full https URL)
- ARBITRUM_RPC (legacy single URL)

Fallbacks (if nothing set):
- https://arb1.arbitrum.io/rpc
- https://arbitrum-one.publicnode.com
"""

from __future__ import annotations

import os
import threading
import time
from typing import Dict, List, Optional

from dotenv import load_dotenv

try:
    # Local import within repo
    from .multi_provider_rpc import MultiProviderRPC
except Exception:
    # Fallback absolute import if called from other working dirs
    from agents.multi_provider_rpc import MultiProviderRPC


_manager_singleton = None
_manager_lock = threading.Lock()


def _collect_arbitrum_providers() -> Dict[str, str]:
    """
    Collect Arbitrum RPC endpoints from environment variables.
    Returns a dict mapping provider names to endpoint URLs.
    """
    load_dotenv()

    # Ordered list of possible keys to read from env
    env_keys: List[str] = [
        "ALCHEMY_ARB_HTTPS",
        "INFURA_ARB_HTTPS",
        "ARB_RPC_1",
        "ARB_RPC_2",
        "ARB_RPC_3",
        "ARB_RPC_4",
        "ARB_RPC_5",
        # Legacy single URL
        "ARBITRUM_RPC",
    ]

    providers: Dict[str, str] = {}

    # Friendly names for common vendors
    vendor_alias = {
        "ALCHEMY_ARB_HTTPS": "Alchemy",
        "INFURA_ARB_HTTPS": "Infura",
        "ARBITRUM_RPC": "Primary",
    }

    for key in env_keys:
        url = os.getenv(key, "").strip()
        if url:
            name = vendor_alias.get(key, key)
            providers[name] = url

    # Add safe fallbacks if nothing configured
    if not providers:
        providers = {
            "Arbitrum": "https://arb1.arbitrum.io/rpc",
            "PublicNode": "https://arbitrum-one.publicnode.com",
        }

    return providers


class _ProviderMonitorThread(threading.Thread):
    """Runs MultiProviderRPC monitoring in a background thread."""

    daemon = True

    def __init__(self, manager: MultiProviderRPC):
        super().__init__(name="rpc-monitor")
        self._manager = manager
        self._stop = threading.Event()

    def run(self) -> None:
        import asyncio

        async def _runner():
            await self._manager.start_monitoring()
            # Keep the task alive; monitoring has its own loop
            while not self._stop.is_set():
                await asyncio.sleep(0.5)

        try:
            asyncio.run(_runner())
        except Exception:
            # Avoid crashing the process if monitor dies; best-effort
            pass

    def stop(self):
        self._stop.set()


class Web3Proxy:
    """
    Lightweight proxy that forwards attribute access to the current best Web3
    from the MultiProviderRPC manager. This keeps existing code changes minimal:

        w3 = get_arbitrum_w3()
        w3.eth.gas_price

    Each attribute access fetches the current best provider.
    """

    def __init__(self, manager: MultiProviderRPC):
        self._manager = manager

    def _get_w3(self):
        w3 = self._manager.get_web3()
        if w3 is None:
            # As a last resort, try rebuilding from providers list
            time.sleep(0.1)
            w3 = self._manager.get_web3()
        return w3

    def __getattr__(self, item):
        w3 = self._get_w3()
        if w3 is None:
            raise RuntimeError("No RPC providers available (Web3Proxy)")
        return getattr(w3, item)


def get_arbitrum_w3() -> Web3Proxy:
    """
    Return a Web3 proxy backed by MultiProviderRPC with provider monitoring.
    Ensures a single shared manager per process for efficiency.
    """
    global _manager_singleton
    with _manager_lock:
        if _manager_singleton is None:
            providers = _collect_arbitrum_providers()
            _manager_singleton = MultiProviderRPC(providers)

            # Start monitoring in a background thread
            monitor = _ProviderMonitorThread(_manager_singleton)
            monitor.start()

    return Web3Proxy(_manager_singleton)
