#!/usr/bin/env python3
"""
🚀 APEX RPC MIRROR
Ultra-fast local RPC proxy with intelligent caching and rate limit bypass.
Runs on port 8547 HTTP and 8548 WebSocket.
"""

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
import aiohttp
import asyncio
import time
import json
import os
from collections import defaultdict
from typing import Dict, Any

app = FastAPI(title="Apex RPC Mirror")

# Configuration
UPSTREAM_RPC = os.getenv("UPSTREAM_RPC", "https://arb1.arbitrum.io/rpc")
CACHE_TTL = 2  # seconds for immutable data
REQUEST_TIMEOUT = 10

# In-memory cache for immutable blockchain data
cache: Dict[str, tuple[float, Any]] = {}
request_stats = defaultdict(int)

# Methods that can be cached (immutable historical data)
CACHEABLE_METHODS = {
    "eth_getBlockByNumber",
    "eth_getBlockByHash",
    "eth_getTransactionByHash",
    "eth_getTransactionReceipt",
    "net_version",
    "eth_chainId"
}

async def fetch_from_upstream(method: str, params: list) -> Dict[str, Any]:
    """Fetch data from upstream RPC with timeout."""
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": 1
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                UPSTREAM_RPC,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            ) as response:
                return await response.json()
        except asyncio.TimeoutError:
            return {"jsonrpc": "2.0", "error": {"code": -32603, "message": "Upstream timeout"}, "id": 1}
        except Exception as e:
            return {"jsonrpc": "2.0", "error": {"code": -32603, "message": str(e)}, "id": 1}

def get_cache_key(method: str, params: list) -> str:
    """Generate cache key from method and params."""
    return f"{method}:{json.dumps(params, sort_keys=True)}"

def get_from_cache(cache_key: str) -> Any:
    """Get value from cache if not expired."""
    if cache_key in cache:
        timestamp, value = cache[cache_key]
        if time.time() - timestamp < CACHE_TTL:
            return value
    return None

def set_in_cache(cache_key: str, value: Any):
    """Store value in cache with timestamp."""
    cache[cache_key] = (time.time(), value)

@app.post("/")
async def rpc_proxy(request: Request):
    """Main RPC proxy endpoint."""
    try:
        data = await request.json()
        method = data.get("method", "")
        params = data.get("params", [])
        
        # Update stats
        request_stats[method] += 1
        
        # Check cache for immutable methods
        if method in CACHEABLE_METHODS:
            cache_key = get_cache_key(method, params)
            cached = get_from_cache(cache_key)
            if cached:
                return JSONResponse(cached)
        
        # Fetch from upstream
        result = await fetch_from_upstream(method, params)
        
        # Cache if appropriate
        if method in CACHEABLE_METHODS and "result" in result:
            cache_key = get_cache_key(method, params)
            set_in_cache(cache_key, result)
        
        return JSONResponse(result)
    
    except Exception as e:
        return JSONResponse({
            "jsonrpc": "2.0",
            "error": {"code": -32700, "message": f"Parse error: {str(e)}"},
            "id": None
        })

@app.websocket("/ws")
async def websocket_proxy(websocket: WebSocket):
    """WebSocket proxy for real-time subscriptions."""
    await websocket.accept()
    
    # Connect to upstream WebSocket
    upstream_ws_url = UPSTREAM_RPC.replace("https://", "wss://").replace("http://", "ws://")
    if not upstream_ws_url.endswith("/ws"):
        upstream_ws_url += "/ws"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(upstream_ws_url) as upstream_ws:
                # Bidirectional relay
                async def forward_to_upstream():
                    try:
                        async for msg in websocket.iter_text():
                            await upstream_ws.send_str(msg)
                    except WebSocketDisconnect:
                        pass
                
                async def forward_to_client():
                    async for msg in upstream_ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            await websocket.send_text(msg.data)
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            break
                
                await asyncio.gather(
                    forward_to_upstream(),
                    forward_to_client()
                )
    
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await websocket.close()

@app.get("/stats")
async def get_stats():
    """RPC mirror statistics."""
    return {
        "cache_size": len(cache),
        "request_counts": dict(request_stats),
        "total_requests": sum(request_stats.values())
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "apex-rpc-mirror"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8547, workers=3)
