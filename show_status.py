#!/usr/bin/env python3
"""
Display live trading status without interrupting the main process
"""
import time
import json
from pathlib import Path
from datetime import datetime
from web3 import Web3

# Configuration
from agents.rpc_config import RPCConfig
RPC = RPCConfig.get_rpc('ARBITRUM')
WALLET = "0x5fc05DA8cB29f08754ac120Ab6F4F6176774b53E"
USDC_ADDRESS = "0xaf88d065e77c8cC2239327C5EDb3A432268e5831"

w3 = Web3(Web3.HTTPProvider(RPC))
usdc_abi = [{"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"}]
usdc = w3.eth.contract(address=Web3.to_checksum_address(USDC_ADDRESS), abi=usdc_abi)

print("=" * 80)
print("🐉 LIVE TRADING STATUS")
print("=" * 80)
print()

# Wallet
print("💰 WALLET: 0x5fc05...3b53E")
try:
    eth = w3.eth.get_balance(WALLET) / 1e18
    usdc_bal = usdc.functions.balanceOf(Web3.to_checksum_address(WALLET)).call() / 1e6
    print(f"   ETH:  {eth:.6f} ETH (~${eth*3500:.2f})")
    print(f"   USDC: {usdc_bal:.2f} USDC")
    print(f"   Total: ~${(eth*3500 + usdc_bal):.2f} USD")
except Exception as e:
    print(f"   Error: {e}")
print()

# Network
print("📊 ARBITRUM NETWORK")
try:
    block = w3.eth.block_number
    gas = w3.eth.gas_price / 1e9
    print(f"   Block: {block:,}")
    print(f"   Gas: {gas:.4f} Gwei")
except Exception as e:
    print(f"   Error: {e}")
print()

# Latest session
print("📈 LATEST SESSION")
logs_dir = Path('logs')
if logs_dir.exists():
    log_files = sorted(logs_dir.glob('session_*.json'), key=lambda x: x.stat().st_mtime, reverse=True)
    if log_files:
        try:
            with open(log_files[0], 'r') as f:
                data = json.load(f)
            print(f"   File: {log_files[0].name}")
            print(f"   Duration: {data.get('actual_elapsed_str', 'N/A')}")
            print(f"   Opportunities: {data.get('opportunities_detected', 0)}")
            print(f"   Trades: {data.get('trades_executed', 0)}")
            print(f"   PnL: ${data.get('session_pnl_usd', 0):.2f}")
        except Exception as e:
            print(f"   Error reading log: {e}")
    else:
        print("   No sessions found")
else:
    print("   No logs directory")
print()

print("=" * 80)
print("✅ Trading engine should be running in background")
print("🔍 Scanning every 7 seconds for arbitrage opportunities")
print("🚀 LIVE MODE - Real trades execute automatically")
print("=" * 80)
print()
print("Configuration:")
print("  • Max position: $20 USDC")
print("  • Min profit: $0.30")
print("  • Max daily loss: $7")
print("  • Kill-switch: 3 consecutive losses")
print("  • Session duration: 8 hours")
print()
print("Active strategies:")
print("  1. Uniswap V3 Scalping (WETH/USDC)")
print("  2. Cross-DEX Arbitrage (Multi-token)")
print()
print("⚠️ Run 'python check_wallet.py' to verify balance anytime")
print("=" * 80)
