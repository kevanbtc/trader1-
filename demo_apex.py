"""
APEX MODE DEMONSTRATION
Shows all 5 advanced modules working together
"""

import asyncio
from web3 import Web3
import os
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Import APEX coordinator
from agents.apex_coordinator import ApexCoordinator

async def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║                  🔥 APEX MODE ACTIVATED 🔥                   ║
║          Professional-Grade Alpha Extraction Engine          ║
╚══════════════════════════════════════════════════════════════╝
""")
    
    # Initialize Web3
    rpc_url = os.getenv('ARBITRUM_RPC', 'https://arb1.arbitrum.io/rpc')
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    
    if not w3.is_connected():
        print("❌ Failed to connect to RPC")
        return
    
    print(f"✅ Connected to Arbitrum (block {w3.eth.block_number:,})")
    
    # Get wallet details
    wallet_address = os.getenv('WALLET_ADDRESS', '0x5fc05DA8cB29f08754ac120Ab6F4F6176774b53E')
    private_key = os.getenv('PRIVATE_KEY', '')  # Would be securely stored
    
    print(f"💼 Wallet: {wallet_address}")
    
    # Initialize price feed (mock for demo)
    class MockPriceFeed:
        pass
    
    price_feed = MockPriceFeed()
    
    # Initialize APEX Coordinator
    apex = ApexCoordinator(w3, price_feed, wallet_address, private_key)
    
    print("\n📋 APEX CAPABILITIES:")
    print("   1️⃣  Expanded Token Universe: 40+ tokens across 8 categories")
    print("   2️⃣  Multi-Hop Routing: A→B→C→A triangular arbitrage")
    print("   3️⃣  Flashloan Execution: 10-100x capital scaling (Aave V3 + Balancer V2)")
    print("   4️⃣  Block Event Hunter: Whale swaps, oracle updates, liquidations")
    print("   5️⃣  Predictive Liquidity: Pre-predict price movements from order book")
    
    print("\n🚀 APEX MODE STATUS:")
    stats = apex.get_apex_stats()
    print(f"   Multi-Hop: {'✅ ENABLED' if stats['multihop_enabled'] else '❌ DISABLED'}")
    print(f"   Flashloan: {'✅ ENABLED' if stats['flashloan_enabled'] else '❌ DISABLED'}")
    print(f"   Event Hunter: {'✅ ENABLED' if stats['event_hunter_enabled'] else '❌ DISABLED'}")
    print(f"   Predictive Model: {'✅ ENABLED' if stats['predictive_enabled'] else '❌ DISABLED'}")
    
    print("\n⚙️  Configuration:")
    print(f"   Min Multi-Hop Profit: ${os.getenv('MIN_MULTIHOP_PROFIT_USD', '0.05')}")
    print(f"   Min Flashloan Profit: ${os.getenv('MIN_FLASHLOAN_PROFIT_USD', '0.10')}")
    print(f"   Max Position: ${os.getenv('MAX_POSITION_USD', '8.50')}")
    print(f"   Scan Interval: {os.getenv('SCAN_INTERVAL_MS', '350')}ms")
    
    print("\n" + "="*62)
    print("🎯 DEMO: Scanning for 30 seconds...")
    print("="*62 + "\n")
    
    # Run APEX scanning for 30 seconds (demo mode)
    try:
        scanning_task = asyncio.create_task(apex.start_apex_scanning())
        await asyncio.wait_for(scanning_task, timeout=30)
    except asyncio.TimeoutError:
        print("\n⏱️  Demo timeout reached")
    except KeyboardInterrupt:
        print("\n⚠️  Demo stopped by user")
    
    # Print summary
    apex.print_apex_summary()
    
    print("""
╔══════════════════════════════════════════════════════════════╗
║                  APEX MODE DEMONSTRATION COMPLETE            ║
║                                                              ║
║  To enable APEX in live trading:                            ║
║  1. Ensure ENABLE_APEX_MODE=true in .env                    ║
║  2. Run: python start_trading.py --apex                     ║
║                                                              ║
║  Note: Flashloan execution requires smart contract          ║
║        deployment for production use.                       ║
╚══════════════════════════════════════════════════════════════╝
""")

if __name__ == "__main__":
    asyncio.run(main())
