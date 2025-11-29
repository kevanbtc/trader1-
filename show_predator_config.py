"""
🔥 PREDATOR MODE CONFIGURATION SUMMARY
"""

import os
from pathlib import Path

def read_env():
    env_file = Path(__file__).parent / '.env'
    config = {}
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()
    return config

config = read_env()

print("="*60)
print("🐉 TRADING DRAGON - PREDATOR MODE CONFIGURATION")
print("="*60)
print()

print("💰 CAPITAL & RISK")
print(f"   Max Position: ${config.get('MAX_POSITION_USD', 'N/A')}")
print(f"   Min Profit: ${config.get('MIN_PROFIT_USD', 'N/A')}")
print(f"   Max Gas: {config.get('MAX_GAS_GWEI', 'N/A')} Gwei")
print(f"   Max Slippage: {config.get('MAX_SLIPPAGE_BPS', 'N/A')} bps")
print()

print("⚡ PERFORMANCE")
print(f"   Scan Interval: {config.get('SCAN_INTERVAL_MS', 'N/A')}ms")
print(f"   Mode: {config.get('TRADING_MODE', 'N/A')}")
print(f"   Paper Mode: {config.get('ENABLE_PAPER_MODE', 'N/A')}")
print()

print("🧠 INTELLIGENCE")
print(f"   MCP: {'✅ ENABLED' if config.get('ENABLE_MCP') == 'true' else '❌ DISABLED'}")
print(f"   Swarm: {'✅ ENABLED' if config.get('ENABLE_SWARM') == 'true' else '❌ DISABLED'}")
print(f"   Intel Ingestor: {'✅ ENABLED' if config.get('ENABLE_INTEL_INGESTOR') == 'true' else '❌ DISABLED'}")
print(f"   MCP Confidence: {config.get('MCP_CONFIDENCE_THRESHOLD', 'N/A')}")
print(f"   Swarm Agreement: {config.get('SWARM_REQUIRED_AGREEMENT', 'N/A')} agents")
print()

print("🌐 DEX VENUES")
venues = []
if config.get('ENABLE_CAMELOT') == 'true': venues.append('Camelot')
if config.get('ENABLE_BALANCER') == 'true': venues.append('Balancer')
if config.get('ENABLE_TRADERJOE') == 'true': venues.append('TraderJoe')
if config.get('ENABLE_RAMSES') == 'true': venues.append('Ramses')
if config.get('ENABLE_KYBERSWAP') == 'true': venues.append('KyberSwap')

print(f"   Core: Uniswap V3, Sushiswap, Curve")
print(f"   Extended: {', '.join(venues) if venues else 'None'}")
print(f"   Total Venues: {3 + len(venues)}")
print()

print("="*60)
print("🎯 PREDATOR MODE ACTIVE")
print("   • Lower profit threshold = More opportunities")
print("   • Faster scanning = Better fills")
print("   • More venues = More arbitrage")
print("   • MCP + Swarm = Smart safety net")
print("="*60)
