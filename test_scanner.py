#!/usr/bin/env python3
"""
Bare minimum test - just run the scanner for 10 minutes
"""
import os
import asyncio
from pathlib import Path

# Set env before imports
os.environ['TRADING_MODE'] = 'PAPER'  # PAPER mode for testing
os.environ['MIN_PROFIT_USD'] = '0.30'
os.environ['MAX_POSITION_USD'] = '10.0'

from agents.defi_price_feed import DeFiPriceFeed

async def main():
    print("=" * 60)
    print("SIMPLE 10-MINUTE SCANNER TEST")
    print("=" * 60)
    print()
    
    # Initialize
    from agents.rpc_config import RPCConfig
    rpc = RPCConfig.get_rpc('ARBITRUM')
    feed = DeFiPriceFeed(chain="ARBITRUM", rpc_url=rpc, enable_mcp=False)
    
    # Simple callback
    opp_count = 0
    async def handle_opp(opp):
        nonlocal opp_count
        opp_count += 1
        print(f"#{opp_count}: {opp.buy_dex} → {opp.sell_dex} | ${opp.net_profit_usd:.2f}")
    
    feed.register_opportunity_callback(handle_opp)
    
    # Run for 10 minutes
    print("Starting 10-minute scan...")
    print("Press Ctrl+C to stop")
    print()
    
    try:
        # Create task
        task = asyncio.create_task(feed.monitor_loop(scan_interval_ms=7000, max_position_usd=10.0))
        
        # Wait 10 minutes
        await asyncio.sleep(600)
        
        # Stop
        feed.stop()
        await task
        
    except KeyboardInterrupt:
        print("\nStopped by user")
        feed.stop()
    
    print()
    print("=" * 60)
    print(f"TEST COMPLETE: {opp_count} opportunities detected")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
