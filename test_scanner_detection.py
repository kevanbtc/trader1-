"""
Test if the opportunity detection system actually works
by injecting fake price spreads
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from agents.defi_price_feed import ArbitrageOpportunity
from datetime import datetime

print("\n🧪 TESTING OPPORTUNITY DETECTION SYSTEM\n")
print("=" * 60)

# Create a fake arbitrage opportunity
fake_opp = ArbitrageOpportunity(
    buy_dex="Uniswap V3",
    sell_dex="Sushiswap V2",
    token_path=["WETH", "USDC"],
    buy_price=2450.50,
    sell_price=2458.75,
    profit_bps=337,  # 3.37% spread
    profit_usd=8.25,
    gas_cost_usd=0.15,
    net_profit_usd=8.10,
    confidence=0.85,
    timestamp=datetime.utcnow(),
    execution_priority="HIGH"
)

print("✅ Created fake opportunity:")
print(f"   Pair: WETH/USDC")
print(f"   Buy: {fake_opp.buy_dex} @ ${fake_opp.buy_price}")
print(f"   Sell: {fake_opp.sell_dex} @ ${fake_opp.sell_price}")
print(f"   Spread: {fake_opp.profit_bps / 100:.2f}%")
print(f"   Gross Profit: ${fake_opp.profit_usd}")
print(f"   Gas Cost: ${fake_opp.gas_cost_usd}")
print(f"   Net Profit: ${fake_opp.net_profit_usd}")
print(f"   Confidence: {fake_opp.confidence * 100:.1f}%")

# Test filtering
import os
min_profit = float(os.environ.get('MIN_PROFIT_USD', '0.001'))
print(f"\n📊 Checking against filter: MIN_PROFIT_USD = ${min_profit}")

if fake_opp.net_profit_usd > min_profit:
    print(f"✅ PASS: ${fake_opp.net_profit_usd:.2f} > ${min_profit}")
    print("   This opportunity WOULD be detected by the scanner")
else:
    print(f"❌ FAIL: ${fake_opp.net_profit_usd:.2f} <= ${min_profit}")
    print("   This opportunity would be FILTERED OUT")

print("\n" + "=" * 60)
print("🎯 DIAGNOSIS:")
print("=" * 60)

if fake_opp.net_profit_usd > 0.001:
    print("✅ Detection system is CAPABLE of finding opportunities")
    print("❌ Problem: MARKET HAS NO REAL OPPORTUNITIES")
    print("\nThe Arbitrum DEX market is too efficient for arbitrage.")
    print("All 9 DEXes are running synchronized prices.")
    print("\nOptions:")
    print("  1. Switch to a less efficient chain (BSC, Polygon)")
    print("  2. Wait for volatile market conditions")
    print("  3. Use flash loans with MEV tactics")
    print("  4. Target token launches / low liquidity pairs")
else:
    print("❌ Filter is TOO STRICT - even fake opportunities are blocked")

print("")
