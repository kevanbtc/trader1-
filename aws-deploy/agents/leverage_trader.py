#!/usr/bin/env python3
"""
LEVERAGE TRADING BOT - Use GMX or other perps to get 10-50x leverage.

THE MATH:
- $29 capital with 20x leverage = $580 position size
- 5% price move = $29 profit (100% gain)
- 10% price move = $58 profit (200% gain)
- But 5% wrong direction = LIQUIDATED (lose all $29)

Strategy:
1. Use technical indicators (RSI, MACD, Bollinger) to find high-probability setups
2. Only trade when ALL indicators align
3. Use tight stop losses (2-3%)
4. Take profits at 5-10%
5. Win rate only needs to be 40% to be profitable with 2:1 risk/reward

This is how traders turn $100 into $10,000 in a week.
"""

import os
from web3 import Web3
from decimal import Decimal
import asyncio
from dataclasses import dataclass
from typing import Optional
import statistics

@dataclass
class TradeSignal:
    """Trading signal with confidence score."""
    pair: str
    direction: str  # "LONG" or "SHORT"
    confidence: float  # 0-100
    entry_price: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    leverage: int
    position_size_usd: Decimal
    expected_profit_usd: Decimal
    risk_reward_ratio: float

class TechnicalAnalyzer:
    """Analyzes price data for high-probability trades."""
    
    def __init__(self, w3: Web3):
        self.w3 = w3
        
    async def get_price_history(self, token_address: str, periods: int = 100) -> list:
        """Get historical prices for technical analysis.
        
        For now, we'll use Uniswap V3 TWAP (Time Weighted Average Price).
        In production, you'd want to fetch from a price oracle or API.
        """
        # TODO: Implement real price fetching
        # For demo, return fake data
        import random
        base = 2000
        prices = []
        for i in range(periods):
            change = random.uniform(-20, 20)
            base = base + change
            prices.append(float(base))
        return prices
    
    def calculate_rsi(self, prices: list, period: int = 14) -> float:
        """Calculate Relative Strength Index.
        
        RSI < 30 = Oversold (BUY signal)
        RSI > 70 = Overbought (SELL signal)
        """
        if len(prices) < period + 1:
            return 50.0
            
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        
        gains = [d if d > 0 else 0 for d in deltas[-period:]]
        losses = [-d if d < 0 else 0 for d in deltas[-period:]]
        
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        
        if avg_loss == 0:
            return 100.0
            
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def calculate_macd(self, prices: list) -> tuple:
        """Calculate MACD (Moving Average Convergence Divergence).
        
        MACD crosses above signal = BUY
        MACD crosses below signal = SELL
        """
        if len(prices) < 26:
            return (0, 0, 0)
            
        # EMA calculation
        def ema(data, period):
            multiplier = 2 / (period + 1)
            ema_value = data[0]
            for price in data[1:]:
                ema_value = (price - ema_value) * multiplier + ema_value
            return ema_value
        
        ema_12 = ema(prices[-12:], 12)
        ema_26 = ema(prices[-26:], 26)
        
        macd_line = ema_12 - ema_26
        signal_line = macd_line * 0.9  # Simplified
        histogram = macd_line - signal_line
        
        return (macd_line, signal_line, histogram)
    
    def calculate_bollinger_bands(self, prices: list, period: int = 20) -> tuple:
        """Calculate Bollinger Bands.
        
        Price touches lower band = BUY
        Price touches upper band = SELL
        """
        if len(prices) < period:
            return (0, 0, 0)
            
        recent = prices[-period:]
        sma = statistics.mean(recent)
        std = statistics.stdev(recent)
        
        upper = sma + (2 * std)
        lower = sma - (2 * std)
        
        return (upper, sma, lower)
    
    async def analyze_pair(self, pair_name: str, current_price: Decimal, capital_usd: Decimal) -> Optional[TradeSignal]:
        """Analyze a trading pair for entry signals.
        
        Returns TradeSignal if high-confidence setup found.
        """
        print(f"\n📊 Analyzing {pair_name}...")
        
        # Get price history (last 100 periods)
        prices = await self.get_price_history(pair_name, 100)
        current = float(current_price)
        
        # Calculate indicators
        rsi = self.calculate_rsi(prices)
        macd, signal, histogram = self.calculate_macd(prices)
        upper_bb, middle_bb, lower_bb = self.calculate_bollinger_bands(prices)
        
        print(f"  RSI: {rsi:.1f}")
        print(f"  MACD: {macd:.2f} | Signal: {signal:.2f} | Hist: {histogram:.2f}")
        print(f"  BB: Upper {upper_bb:.2f} | Mid {middle_bb:.2f} | Lower {lower_bb:.2f}")
        print(f"  Current Price: ${current:.2f}")
        
        # LONG SETUP: Oversold + MACD bullish + Near lower BB
        long_score = 0
        if rsi < 35:
            long_score += 40
            print("  ✅ RSI oversold")
        if histogram > 0:
            long_score += 30
            print("  ✅ MACD bullish")
        if current < lower_bb * 1.02:
            long_score += 30
            print("  ✅ Near lower Bollinger Band")
        
        # SHORT SETUP: Overbought + MACD bearish + Near upper BB
        short_score = 0
        if rsi > 65:
            short_score += 40
            print("  ✅ RSI overbought")
        if histogram < 0:
            short_score += 30
            print("  ✅ MACD bearish")
        if current > upper_bb * 0.98:
            short_score += 30
            print("  ✅ Near upper Bollinger Band")
        
        # Need 70+ confidence to trade
        if long_score >= 70:
            direction = "LONG"
            confidence = long_score
            entry = Decimal(str(current))
            stop_loss = entry * Decimal("0.97")  # 3% stop
            take_profit = entry * Decimal("1.10")  # 10% target
        elif short_score >= 70:
            direction = "SHORT"
            confidence = short_score
            entry = Decimal(str(current))
            stop_loss = entry * Decimal("1.03")  # 3% stop
            take_profit = entry * Decimal("0.90")  # 10% target
        else:
            print(f"  ❌ No high-confidence setup (Long: {long_score}, Short: {short_score})")
            return None
        
        # Calculate position sizing with leverage
        leverage = 20 if confidence >= 80 else 10
        position_size = capital_usd * leverage
        
        risk_amount = abs(entry - stop_loss) / entry
        reward_amount = abs(take_profit - entry) / entry
        risk_reward = float(reward_amount / risk_amount)
        
        expected_profit = float(capital_usd * leverage * reward_amount)
        
        print(f"\n  🎯 {direction} SIGNAL | Confidence: {confidence}%")
        print(f"  Entry: ${entry:.2f}")
        print(f"  Stop: ${stop_loss:.2f} | Target: ${take_profit:.2f}")
        print(f"  Leverage: {leverage}x | Position: ${position_size:.2f}")
        print(f"  Risk/Reward: {risk_reward:.1f}:1")
        print(f"  Expected Profit: ${expected_profit:.2f}")
        
        return TradeSignal(
            pair=pair_name,
            direction=direction,
            confidence=confidence,
            entry_price=entry,
            stop_loss=stop_loss,
            take_profit=take_profit,
            leverage=leverage,
            position_size_usd=position_size,
            expected_profit_usd=Decimal(str(expected_profit)),
            risk_reward_ratio=risk_reward
        )
    
    async def scan_for_setups(self, capital_usd: Decimal) -> list:
        """Scan multiple pairs for high-probability trade setups."""
        # Major volatile pairs good for leverage trading
        pairs = [
            ("ETH/USD", Decimal("2934")),
            ("BTC/USD", Decimal("97450")),
            ("ARB/USD", Decimal("0.21")),
            ("SOL/USD", Decimal("245")),
        ]
        
        signals = []
        
        for pair_name, current_price in pairs:
            signal = await self.analyze_pair(pair_name, current_price, capital_usd)
            if signal:
                signals.append(signal)
        
        # Sort by confidence * risk/reward
        signals.sort(key=lambda x: x.confidence * x.risk_reward_ratio, reverse=True)
        
        return signals


async def main():
    """Run leverage trading analyzer."""
    from dotenv import load_dotenv
    load_dotenv()
    
    w3 = Web3(Web3.HTTPProvider("https://arb1.arbitrum.io/rpc"))
    
    print("=" * 70)
    print("🎯 LEVERAGE TRADING ANALYZER")
    print("=" * 70)
    print("Strategy: 10-20x leverage on high-probability technical setups")
    print("Win Rate Target: 40%+ with 2:1+ risk/reward")
    print("=" * 70)
    
    analyzer = TechnicalAnalyzer(w3)
    
    capital = Decimal("29")
    print(f"\n💰 Capital: ${capital}")
    print(f"🔍 Scanning for trade setups...\n")
    
    signals = await analyzer.scan_for_setups(capital)
    
    if signals:
        print(f"\n✅ Found {len(signals)} high-probability setups:\n")
        for i, signal in enumerate(signals, 1):
            print(f"#{i} {signal.pair} {signal.direction}")
            print(f"   Confidence: {signal.confidence}% | R:R {signal.risk_reward:.1f}:1")
            print(f"   Entry: ${signal.entry_price} | Stop: ${signal.stop_loss}")
            print(f"   Position: ${signal.position_size_usd} ({signal.leverage}x)")
            print(f"   Expected: ${signal.expected_profit_usd:.2f}\n")
        
        best = signals[0]
        print(f"🎯 BEST TRADE: {best.pair} {best.direction}")
        print(f"   Risk ${float(capital * Decimal('0.03')):.2f} to make ${float(best.expected_profit_usd):.2f}")
    else:
        print("❌ No high-confidence setups found. Wait for better entry.")


if __name__ == "__main__":
    asyncio.run(main())
