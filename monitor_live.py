#!/usr/bin/env python3
"""
Live Trading Monitor - Shows real-time trading activity
"""
import time
import json
from pathlib import Path
from datetime import datetime
from web3 import Web3
import os

# Configuration
from agents.rpc_config import RPCConfig
RPC = RPCConfig.get_rpc('ARBITRUM')
WALLET = "0x5fc05DA8cB29f08754ac120Ab6F4F6176774b53E"
USDC_ADDRESS = "0xaf88d065e77c8cC2239327C5EDb3A432268e5831"

# Initialize
w3 = Web3(Web3.HTTPProvider(RPC))
usdc_abi = [{"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"}]
usdc = w3.eth.contract(address=Web3.to_checksum_address(USDC_ADDRESS), abi=usdc_abi)

def get_balances():
    eth = w3.eth.get_balance(WALLET) / 1e18
    usdc_bal = usdc.functions.balanceOf(Web3.to_checksum_address(WALLET)).call() / 1e6
    return eth, usdc_bal

def get_latest_log():
    logs_dir = Path('logs')
    if not logs_dir.exists():
        return None
    log_files = sorted(logs_dir.glob('session_*.json'), key=lambda x: x.stat().st_mtime, reverse=True)
    if log_files:
        try:
            with open(log_files[0], 'r') as f:
                return json.load(f)
        except:
            pass
    return None

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

print("🔴 LIVE TRADING MONITOR STARTING...")
print("Press Ctrl+C to stop")
print()

initial_eth, initial_usdc = get_balances()
start_time = datetime.now()

while True:
    try:
        clear_screen()
        
        # Current time and uptime
        now = datetime.now()
        uptime = now - start_time
        
        print("=" * 80)
        print("🐉 LIVE TRADING MONITOR")
        print("=" * 80)
        print(f"Time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Uptime: {str(uptime).split('.')[0]}")
        print()
        
        # Blockchain info
        try:
            block = w3.eth.block_number
            gas_price = w3.eth.gas_price / 1e9
            print(f"📊 Arbitrum Block: {block:,}")
            print(f"⛽ Gas Price: {gas_price:.4f} Gwei")
        except Exception as e:
            print(f"⚠️ RPC Error: {e}")
        
        print()
        
        # Wallet balances
        try:
            eth, usdc_bal = get_balances()
            eth_change = eth - initial_eth
            usdc_change = usdc_bal - initial_usdc
            
            print("💰 WALLET BALANCE")
            print(f"   ETH:  {eth:.6f} ({eth_change:+.6f})")
            print(f"   USDC: {usdc_bal:.2f} ({usdc_change:+.2f})")
            print(f"   Total: ${(eth*3500 + usdc_bal):.2f} USD")
        except Exception as e:
            print(f"⚠️ Balance Error: {e}")
        
        print()
        
        # Session info
        log_data = get_latest_log()
        if log_data:
            print("📈 SESSION STATS")
            print(f"   Opportunities: {log_data.get('opportunities_detected', 0)}")
            print(f"   Trades: {log_data.get('trades_executed', 0)}")
            print(f"   PnL: ${log_data.get('session_pnl_usd', 0):.2f}")
            print(f"   Duration: {log_data.get('actual_elapsed_str', 'N/A')}")
        else:
            print("📈 SESSION STATS")
            print("   Waiting for trading activity...")
        
        print()
        print("=" * 80)
        print("🔍 Scanning for opportunities every 7 seconds...")
        print("🚀 LIVE MODE - Real trades on Arbitrum")
        print("⚠️ Max position: $20 | Min profit: $0.30")
        print("=" * 80)
        
        # Wait before refresh
        time.sleep(5)
        
    except KeyboardInterrupt:
        print("\n\n✅ Monitor stopped by user")
        break
    except Exception as e:
        print(f"\n⚠️ Error: {e}")
        time.sleep(5)
