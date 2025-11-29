"""
MCP (Market Context Protocol) Intelligence Core
Advanced pattern recognition, mathematical prediction, and multi-source analysis
Integrates technical indicators, news sentiment, economic data, and social trends
"""

import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from web3 import Web3
import requests
import json


@dataclass
class MarketSignal:
    """Unified market signal from MCP analysis"""
    signal_type: str  # BULLISH, BEARISH, NEUTRAL
    strength: float  # 0-100 confidence score
    timeframe: str  # SHORT (5m-1h), MEDIUM (1h-4h), LONG (4h-24h)
    sources: List[str]  # Technical, News, Social, Economic
    reasoning: str
    timestamp: datetime


@dataclass
class PatternDetection:
    """Detected chart pattern"""
    pattern_name: str
    confidence: float
    expected_direction: str  # UP, DOWN, CONSOLIDATION
    entry_price: float
    target_price: float
    stop_loss: float
    timeframe: str


@dataclass
class TrendAnalysis:
    """Comprehensive trend analysis"""
    primary_trend: str  # UPTREND, DOWNTREND, SIDEWAYS
    strength: float  # 0-100
    support_levels: List[float]
    resistance_levels: List[float]
    key_trendlines: List[Tuple[float, float]]  # (slope, intercept)
    volume_trend: str  # INCREASING, DECREASING, STABLE


class MCPIntelligence:
    """
    Market Context Protocol - The Dragon's Brain
    Analyzes everything before making trading decisions
    """
    
    def __init__(self, chain: str = "ARBITRUM", rpc_url: str = None):
        self.chain = chain
        # Prefer multi-provider proxy for resilience; allow explicit override
        if rpc_url:
            self.rpc_url = rpc_url
            self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        else:
            self.rpc_url = None
            try:
                from .rpc_utils import get_arbitrum_w3  # type: ignore
            except Exception:
                from agents.rpc_utils import get_arbitrum_w3  # type: ignore
            self.w3 = get_arbitrum_w3()
        
        # Price history cache (for technical analysis)
        self.price_history: Dict[str, pd.DataFrame] = {}
        
        # Market context state
        self.current_sentiment = "NEUTRAL"
        self.market_regime = "NORMAL"  # NORMAL, HIGH_VOLATILITY, LOW_LIQUIDITY
        self.macro_signals: List[MarketSignal] = []
        
        # Configuration
        self.lookback_periods = {
            'SHORT': 100,    # 100 data points for short-term
            'MEDIUM': 500,   # 500 for medium-term
            'LONG': 2000     # 2000 for long-term trends
        }
        
    def calculate_technical_indicators(self, prices: pd.DataFrame) -> Dict:
        """
        Calculate comprehensive technical indicators
        RSI, MACD, Bollinger Bands, ATR, OBV, etc.
        """
        if len(prices) < 50:
            return {}
        
        indicators = {}
        
        # RSI (Relative Strength Index)
        delta = prices['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        indicators['rsi'] = 100 - (100 / (1 + rs.iloc[-1]))
        
        # MACD (Moving Average Convergence Divergence)
        ema_12 = prices['close'].ewm(span=12).mean()
        ema_26 = prices['close'].ewm(span=26).mean()
        macd_line = ema_12 - ema_26
        signal_line = macd_line.ewm(span=9).mean()
        indicators['macd'] = macd_line.iloc[-1]
        indicators['macd_signal'] = signal_line.iloc[-1]
        indicators['macd_histogram'] = (macd_line - signal_line).iloc[-1]
        
        # Bollinger Bands
        sma_20 = prices['close'].rolling(window=20).mean()
        std_20 = prices['close'].rolling(window=20).std()
        indicators['bb_upper'] = (sma_20 + 2 * std_20).iloc[-1]
        indicators['bb_middle'] = sma_20.iloc[-1]
        indicators['bb_lower'] = (sma_20 - 2 * std_20).iloc[-1]
        indicators['bb_width'] = ((indicators['bb_upper'] - indicators['bb_lower']) / 
                                   indicators['bb_middle']) * 100
        
        # ATR (Average True Range) - volatility
        high_low = prices['high'] - prices['low']
        high_close = abs(prices['high'] - prices['close'].shift())
        low_close = abs(prices['low'] - prices['close'].shift())
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        indicators['atr'] = true_range.rolling(window=14).mean().iloc[-1]
        
        # Volume analysis
        if 'volume' in prices.columns:
            indicators['volume_ma'] = prices['volume'].rolling(window=20).mean().iloc[-1]
            indicators['volume_current'] = prices['volume'].iloc[-1]
            indicators['volume_ratio'] = indicators['volume_current'] / indicators['volume_ma']
        
        # Moving averages
        indicators['ma_50'] = prices['close'].rolling(window=50).mean().iloc[-1]
        indicators['ma_200'] = prices['close'].rolling(window=200).mean().iloc[-1] if len(prices) >= 200 else None
        
        return indicators
    
    def detect_chart_patterns(self, prices: pd.DataFrame) -> List[PatternDetection]:
        """
        Detect classic chart patterns
        Head & Shoulders, Triangles, Flags, Breakouts, etc.
        """
        patterns = []
        
        if len(prices) < 50:
            return patterns
        
        current_price = prices['close'].iloc[-1]
        recent_high = prices['high'].iloc[-20:].max()
        recent_low = prices['low'].iloc[-20:].min()
        price_range = recent_high - recent_low
        
        # BREAKOUT PATTERN
        # Check if price is breaking above recent resistance
        resistance = prices['high'].iloc[-50:-5].quantile(0.95)
        if current_price > resistance * 1.01:  # 1% above resistance
            patterns.append(PatternDetection(
                pattern_name="BREAKOUT_ABOVE_RESISTANCE",
                confidence=0.75,
                expected_direction="UP",
                entry_price=current_price,
                target_price=current_price * 1.02,  # 2% target
                stop_loss=resistance * 0.99,
                timeframe="SHORT"
            ))
        
        # BREAKDOWN PATTERN
        support = prices['low'].iloc[-50:-5].quantile(0.05)
        if current_price < support * 0.99:  # 1% below support
            patterns.append(PatternDetection(
                pattern_name="BREAKDOWN_BELOW_SUPPORT",
                confidence=0.75,
                expected_direction="DOWN",
                entry_price=current_price,
                target_price=current_price * 0.98,  # 2% target
                stop_loss=support * 1.01,
                timeframe="SHORT"
            ))
        
        # CONSOLIDATION / RANGE-BOUND
        if price_range / current_price < 0.02:  # Less than 2% range
            patterns.append(PatternDetection(
                pattern_name="TIGHT_CONSOLIDATION",
                confidence=0.80,
                expected_direction="CONSOLIDATION",
                entry_price=current_price,
                target_price=(recent_high + recent_low) / 2,
                stop_loss=recent_low * 0.98,
                timeframe="SHORT"
            ))
        
        # MEAN REVERSION
        ma_20 = prices['close'].rolling(window=20).mean().iloc[-1]
        deviation = abs(current_price - ma_20) / ma_20
        if deviation > 0.03:  # More than 3% from MA
            direction = "DOWN" if current_price > ma_20 else "UP"
            patterns.append(PatternDetection(
                pattern_name="MEAN_REVERSION_OPPORTUNITY",
                confidence=0.70,
                expected_direction=direction,
                entry_price=current_price,
                target_price=ma_20,
                stop_loss=current_price * (1.02 if direction == "DOWN" else 0.98),
                timeframe="MEDIUM"
            ))
        
        return patterns
    
    def calculate_trend_lines(self, prices: pd.DataFrame) -> TrendAnalysis:
        """
        Calculate support/resistance levels and trendlines
        Uses mathematical regression and pivot points
        """
        if len(prices) < 50:
            return TrendAnalysis(
                primary_trend="SIDEWAYS",
                strength=0,
                support_levels=[],
                resistance_levels=[],
                key_trendlines=[],
                volume_trend="STABLE"
            )
        
        current_price = prices['close'].iloc[-1]
        
        # Calculate primary trend using linear regression
        x = np.arange(len(prices))
        y = prices['close'].values
        slope, intercept = np.polyfit(x, y, 1)
        
        # Determine trend direction and strength
        price_change = (y[-1] - y[0]) / y[0]
        if slope > 0 and price_change > 0.02:
            primary_trend = "UPTREND"
            strength = min(abs(price_change) * 1000, 100)
        elif slope < 0 and price_change < -0.02:
            primary_trend = "DOWNTREND"
            strength = min(abs(price_change) * 1000, 100)
        else:
            primary_trend = "SIDEWAYS"
            strength = 50
        
        # Calculate support/resistance using pivot points
        recent_highs = prices['high'].iloc[-50:].nlargest(5).values
        recent_lows = prices['low'].iloc[-50:].nsmallest(5).values
        
        resistance_levels = sorted(set([round(h, 2) for h in recent_highs]))[-3:]
        support_levels = sorted(set([round(l, 2) for l in recent_lows]))[:3]
        
        # Volume trend
        if 'volume' in prices.columns and len(prices) >= 20:
            recent_volume = prices['volume'].iloc[-10:].mean()
            older_volume = prices['volume'].iloc[-30:-10].mean()
            if recent_volume > older_volume * 1.2:
                volume_trend = "INCREASING"
            elif recent_volume < older_volume * 0.8:
                volume_trend = "DECREASING"
            else:
                volume_trend = "STABLE"
        else:
            volume_trend = "STABLE"
        
        return TrendAnalysis(
            primary_trend=primary_trend,
            strength=strength,
            support_levels=support_levels,
            resistance_levels=resistance_levels,
            key_trendlines=[(slope, intercept)],
            volume_trend=volume_trend
        )
    
    async def fetch_news_sentiment(self, token: str) -> float:
        """
        Fetch news sentiment from multiple sources
        Returns sentiment score: -1 (bearish) to +1 (bullish)
        """
        # Placeholder - would integrate with:
        # - CryptoCompare News API
        # - CoinGecko trending
        # - Twitter/X API for mentions
        # - Reddit sentiment from r/cryptocurrency
        
        try:
            # Example: Check if token is trending
            # In production, use real API calls
            sentiment_score = 0.0  # Neutral by default
            
            # Simulate sentiment based on time (demo)
            hour = datetime.now().hour
            if 9 <= hour <= 16:  # "Market hours" tend bullish
                sentiment_score = 0.3
            elif hour >= 22 or hour <= 6:  # Night tends bearish
                sentiment_score = -0.2
            
            return sentiment_score
        except Exception as e:
            print(f"⚠️  News sentiment fetch failed: {e}")
            return 0.0
    
    async def fetch_economic_indicators(self) -> Dict:
        """
        Fetch macro economic indicators
        VIX (fear index), DXY (dollar strength), gas prices, etc.
        """
        indicators = {
            'risk_on': True,  # Risk-on vs risk-off environment
            'liquidity': 'NORMAL',  # HIGH, NORMAL, LOW
            'macro_trend': 'NEUTRAL'  # BULLISH, BEARISH, NEUTRAL
        }
        
        try:
            # Check Arbitrum gas prices as proxy for network activity
            gas_price = self.w3.eth.gas_price / 1e9  # Gwei
            
            if gas_price > 0.1:  # High gas = high activity = risk-on
                indicators['risk_on'] = True
                indicators['liquidity'] = 'HIGH'
            elif gas_price < 0.01:  # Low gas = low activity = risk-off
                indicators['risk_on'] = False
                indicators['liquidity'] = 'LOW'
            
            # In production, would also fetch:
            # - ETH/USD price trend (crypto market sentiment)
            # - BTC dominance (altcoin season indicator)
            # - Total Value Locked in DeFi protocols
            # - Funding rates on perpetual futures
            
        except Exception as e:
            print(f"⚠️  Economic indicators fetch failed: {e}")
        
        return indicators
    
    async def calculate_prediction_score(self, token_pair: str, 
                                         current_price: float,
                                         opportunity_type: str) -> Tuple[float, str]:
        """
        Calculate mathematical prediction score for opportunity
        Combines multiple models and signals into single confidence score
        
        Returns: (score 0-100, reasoning text)
        """
        scores = []
        reasons = []
        
        # 1. Technical Analysis Score
        if token_pair in self.price_history and len(self.price_history[token_pair]) > 50:
            prices = self.price_history[token_pair]
            indicators = self.calculate_technical_indicators(prices)
            
            tech_score = 50  # Start neutral
            
            # RSI analysis
            if 'rsi' in indicators:
                if indicators['rsi'] < 30:  # Oversold
                    tech_score += 15
                    reasons.append("RSI oversold (bullish)")
                elif indicators['rsi'] > 70:  # Overbought
                    tech_score -= 15
                    reasons.append("RSI overbought (bearish)")
            
            # MACD analysis
            if 'macd' in indicators and 'macd_signal' in indicators:
                if indicators['macd'] > indicators['macd_signal']:
                    tech_score += 10
                    reasons.append("MACD bullish crossover")
                else:
                    tech_score -= 10
                    reasons.append("MACD bearish")
            
            # Bollinger Bands
            if 'bb_upper' in indicators and 'bb_lower' in indicators:
                if current_price <= indicators['bb_lower']:
                    tech_score += 15
                    reasons.append("Price at lower Bollinger Band")
                elif current_price >= indicators['bb_upper']:
                    tech_score -= 15
                    reasons.append("Price at upper Bollinger Band")
            
            scores.append(max(0, min(100, tech_score)))
        
        # 2. Pattern Recognition Score
        if token_pair in self.price_history:
            patterns = self.detect_chart_patterns(self.price_history[token_pair])
            if patterns:
                pattern_score = sum(p.confidence * 100 for p in patterns) / len(patterns)
                scores.append(pattern_score)
                reasons.append(f"Detected {len(patterns)} patterns")
        
        # 3. Trend Analysis Score
        if token_pair in self.price_history:
            trend = self.calculate_trend_lines(self.price_history[token_pair])
            trend_score = 50
            
            if trend.primary_trend == "UPTREND" and opportunity_type == "BUY":
                trend_score += trend.strength * 0.3
                reasons.append(f"Strong {trend.primary_trend}")
            elif trend.primary_trend == "DOWNTREND" and opportunity_type == "SELL":
                trend_score += trend.strength * 0.3
                reasons.append(f"Strong {trend.primary_trend}")
            
            # Check if near support/resistance
            if trend.support_levels and any(abs(current_price - s) / s < 0.01 for s in trend.support_levels):
                trend_score += 15
                reasons.append("Near support level")
            
            scores.append(max(0, min(100, trend_score)))
        
        # 4. Sentiment Score
        sentiment = await self.fetch_news_sentiment(token_pair)
        sentiment_score = 50 + (sentiment * 50)  # Convert -1/+1 to 0-100
        scores.append(sentiment_score)
        if sentiment > 0.2:
            reasons.append("Positive market sentiment")
        elif sentiment < -0.2:
            reasons.append("Negative market sentiment")
        
        # 5. Economic/Macro Score
        economic = await self.fetch_economic_indicators()
        macro_score = 50
        if economic['risk_on']:
            macro_score += 20
            reasons.append("Risk-on environment")
        if economic['liquidity'] == 'HIGH':
            macro_score += 15
            reasons.append("High liquidity")
        elif economic['liquidity'] == 'LOW':
            macro_score -= 15
            reasons.append("Low liquidity warning")
        scores.append(macro_score)
        
        # Calculate weighted average
        if scores:
            final_score = sum(scores) / len(scores)
        else:
            final_score = 50  # Neutral if no data
        
        reasoning = " | ".join(reasons[:5]) if reasons else "Limited analysis data"
        
        return (final_score, reasoning)
    
    async def analyze_opportunity(self, token_pair: str, 
                                  buy_price: float, 
                                  sell_price: float,
                                  spread_bps: int) -> MarketSignal:
        """
        Full MCP analysis of arbitrage opportunity
        Combines all data sources and mathematical models
        """
        # Calculate prediction score
        prediction_score, reasoning = await self.calculate_prediction_score(
            token_pair, 
            buy_price, 
            "ARBITRAGE"
        )
        
        # Adjust score based on spread size
        spread_bonus = min(spread_bps / 10, 20)  # Up to 20 points for large spreads
        final_score = min(100, prediction_score + spread_bonus)
        
        # Determine signal type
        if final_score >= 70:
            signal_type = "BULLISH"
            timeframe = "SHORT"
        elif final_score >= 50:
            signal_type = "NEUTRAL"
            timeframe = "MEDIUM"
        else:
            signal_type = "BEARISH"
            timeframe = "LONG"
        
        # Add spread info to reasoning
        full_reasoning = f"Spread: {spread_bps} BPS | {reasoning}"
        
        return MarketSignal(
            signal_type=signal_type,
            strength=final_score,
            timeframe=timeframe,
            sources=["Technical", "Pattern", "Trend", "Sentiment", "Economic"],
            reasoning=full_reasoning,
            timestamp=datetime.utcnow()
        )
    
    def update_price_history(self, token_pair: str, 
                            timestamp: datetime,
                            open_price: float,
                            high: float,
                            low: float,
                            close: float,
                            volume: float = 0):
        """
        Update price history for technical analysis
        Maintains rolling window of historical data
        """
        if token_pair not in self.price_history:
            self.price_history[token_pair] = pd.DataFrame(columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume'
            ])
        
        new_row = pd.DataFrame([{
            'timestamp': timestamp,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        }])
        
        self.price_history[token_pair] = pd.concat([
            self.price_history[token_pair],
            new_row
        ], ignore_index=True)
        
        # Keep only recent data (last 2000 data points)
        if len(self.price_history[token_pair]) > self.lookback_periods['LONG']:
            self.price_history[token_pair] = self.price_history[token_pair].iloc[-self.lookback_periods['LONG']:]
    
    def get_trade_recommendation(self, signal: MarketSignal, 
                                 net_profit_usd: float) -> bool:
        """
        Final recommendation: should we execute this trade?
        Applies conservative filters based on MCP analysis
        """
        # Minimum score threshold
        if signal.strength < 55:
            return False
        
        # Must have positive expected profit
        if net_profit_usd <= 0:
            return False
        
        # Higher threshold for bearish signals
        if signal.signal_type == "BEARISH" and signal.strength < 65:
            return False
        
        # Risk-off environment requires higher confidence
        if self.market_regime == "HIGH_VOLATILITY" and signal.strength < 70:
            return False
        
        # All checks passed
        return True


# Example usage
async def demo_mcp():
    """Demo of MCP Intelligence"""
    mcp = MCPIntelligence(chain="ARBITRUM")
    
    print("=" * 80)
    print("🧠 MCP INTELLIGENCE - MARKET ANALYSIS DEMO")
    print("=" * 80)
    
    # Simulate price data
    token_pair = "WETH/USDC"
    for i in range(100):
        timestamp = datetime.utcnow() - timedelta(minutes=100-i)
        base_price = 2950
        price = base_price + np.random.randn() * 20
        
        mcp.update_price_history(
            token_pair=token_pair,
            timestamp=timestamp,
            open_price=price,
            high=price + abs(np.random.randn() * 5),
            low=price - abs(np.random.randn() * 5),
            close=price + np.random.randn() * 3,
            volume=1000 + np.random.randn() * 100
        )
    
    # Analyze opportunity
    signal = await mcp.analyze_opportunity(
        token_pair="WETH/USDC",
        buy_price=2950,
        sell_price=3000,
        spread_bps=170
    )
    
    print(f"\n📊 Signal: {signal.signal_type}")
    print(f"💪 Strength: {signal.strength:.1f}/100")
    print(f"⏱️  Timeframe: {signal.timeframe}")
    print(f"📝 Reasoning: {signal.reasoning}")
    print(f"✅ Recommendation: {'EXECUTE' if mcp.get_trade_recommendation(signal, 50) else 'SKIP'}")


if __name__ == "__main__":
    asyncio.run(demo_mcp())
