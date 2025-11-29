#!/usr/bin/env python3
"""
🔭 APEX MEMPOOL SNIFFER
Real-time pending transaction analyzer for front-running and sandwich opportunities.
"""

import asyncio
import websockets
import json
import os
from web3 import Web3
from datetime import datetime
from collections import deque
from typing import Dict, Any

# Configuration
WS_URL = os.getenv("ARBITRUM_WS", "ws://127.0.0.1:8548")
OUTPUT_FILE = os.getenv("MEMPOOL_LOG", "logs/mempool_feed.log")
MIN_VALUE_ETH = float(os.getenv("MIN_MEMPOOL_VALUE", "0.1"))

# DEX router addresses on Arbitrum
DEX_ROUTERS = {
    "0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506": "SushiSwap",
    "0xE592427A0AEce92De3Edee1F18E0157C05861564": "Uniswap V3",
    "0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45": "Uniswap Router2",
    "0xc873fEcbd354f5A56E00E710B90EF4201db2448d": "Camelot",
}

# Track recent transactions
recent_txs = deque(maxlen=1000)
opportunity_count = 0

def parse_pending_tx(tx_data: Dict[str, Any]) -> Dict[str, Any]:
    """Parse pending transaction data."""
    try:
        tx = tx_data.get("params", {}).get("result", {})
        
        return {
            "hash": tx.get("hash", ""),
            "from": tx.get("from", ""),
            "to": tx.get("to", ""),
            "value": int(tx.get("value", "0x0"), 16),
            "gas_price": int(tx.get("gasPrice", "0x0"), 16),
            "input": tx.get("input", "")[:10],  # First 10 chars (function selector)
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return None

def is_dex_interaction(tx: Dict[str, Any]) -> bool:
    """Check if transaction interacts with known DEX."""
    to_address = tx.get("to", "").lower()
    return to_address in [addr.lower() for addr in DEX_ROUTERS.keys()]

def analyze_opportunity(tx: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze if transaction presents arbitrage opportunity."""
    if not is_dex_interaction(tx):
        return None
    
    value_eth = tx["value"] / 1e18
    if value_eth < MIN_VALUE_ETH:
        return None
    
    # Check function selector for swap methods
    function_selector = tx["input"]
    swap_selectors = ["0x38ed1739", "0x8803dbee", "0x7ff36ab5", "0x5c11d795"]  # Common swap methods
    
    if function_selector in swap_selectors:
        return {
            "type": "large_swap",
            "tx_hash": tx["hash"],
            "dex": DEX_ROUTERS.get(tx["to"], "Unknown"),
            "value_eth": value_eth,
            "gas_price_gwei": tx["gas_price"] / 1e9,
            "timestamp": tx["timestamp"]
        }
    
    return None

async def log_opportunity(opp: Dict[str, Any]):
    """Log opportunity to file."""
    global opportunity_count
    opportunity_count += 1
    
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "a") as f:
        f.write(json.dumps(opp) + "\n")
    
    print(f"🎯 OPPORTUNITY #{opportunity_count}: {opp['type']} on {opp['dex']} - {opp['value_eth']:.4f} ETH")

async def subscribe_to_mempool():
    """Subscribe to pending transactions via WebSocket."""
    print(f"🔭 Starting Apex Mempool Sniffer...")
    print(f"   Connecting to: {WS_URL}")
    print(f"   Min value: {MIN_VALUE_ETH} ETH")
    print(f"   Output: {OUTPUT_FILE}")
    print()
    
    while True:
        try:
            async with websockets.connect(WS_URL) as ws:
                # Subscribe to pending transactions
                subscribe_msg = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "eth_subscribe",
                    "params": ["newPendingTransactions"]
                }
                await ws.send(json.dumps(subscribe_msg))
                
                print("✅ Subscribed to mempool feed\n")
                
                tx_count = 0
                while True:
                    msg = await ws.recv()
                    data = json.loads(msg)
                    
                    tx_count += 1
                    if tx_count % 100 == 0:
                        print(f"📊 Processed {tx_count} pending txs | Opportunities: {opportunity_count}")
                    
                    # Parse transaction
                    tx = parse_pending_tx(data)
                    if not tx:
                        continue
                    
                    recent_txs.append(tx)
                    
                    # Check for opportunity
                    opp = analyze_opportunity(tx)
                    if opp:
                        await log_opportunity(opp)
        
        except websockets.exceptions.ConnectionClosed:
            print("⚠️ WebSocket connection closed. Reconnecting in 5s...")
            await asyncio.sleep(5)
        except Exception as e:
            print(f"❌ Error: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(subscribe_to_mempool())
