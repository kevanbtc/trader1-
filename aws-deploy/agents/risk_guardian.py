"""
Risk Guardian - Ultimate Loss Prevention System
Multi-layer validation to ensure we never execute losing trades
"""

import asyncio
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class RiskLevel(Enum):
    """Trade risk assessment"""
    SAFE = "safe"              # High confidence, execute
    MODERATE = "moderate"      # Acceptable with caution
    HIGH = "high"              # Risky, skip unless exceptional
    EXTREME = "extreme"        # Never execute


@dataclass
class RiskAssessment:
    """Comprehensive risk evaluation"""
    risk_level: RiskLevel
    probability_of_success: float  # 0-1
    expected_value: float          # Risk-adjusted profit
    red_flags: List[str]           # Warning signals
    green_flags: List[str]         # Positive signals
    recommendation: str            # EXECUTE, SKIP, REDUCE_SIZE
    confidence_score: float        # 0-100
    reasoning: str


@dataclass
class TradeOutcome:
    """Historical trade result"""
    timestamp: datetime
    token_pair: str
    expected_profit: float
    actual_profit: float
    success: bool
    market_regime: str
    confidence: float


class RiskGuardian:
    """
    Loss prevention through intelligent pre-trade validation
    Combines statistical analysis, pattern recognition, and risk models
    """
    
    def __init__(self):
        # Trade history for learning
        self.trade_history: List[TradeOutcome] = []
        
        # Performance tracking
        self.consecutive_losses = 0
        self.consecutive_wins = 0
        self.total_trades = 0
        self.winning_trades = 0
        
        # Risk thresholds (configurable)
        self.min_confidence = 0.60         # Require 60%+ confidence
        self.min_expected_value = 3.0      # $3+ risk-adjusted profit
        self.max_consecutive_losses = 3    # Stop after 3 losses
        self.min_win_rate = 0.70           # Target 70%+ wins
        
        # Regime-specific learned patterns
        self.regime_performance: Dict[str, Dict] = {}
        
    def calculate_probability_of_success(self, 
                                         confidence: float,
                                         spread_bps: int,
                                         market_regime: str,
                                         net_profit: float) -> float:
        """
        Calculate actual probability of successful execution
        Accounts for slippage, gas spikes, failed txns
        """
        # Start with base confidence
        prob = confidence
        
        # Adjust for spread size (wider = more room for error)
        if spread_bps >= 100:
            prob *= 1.05  # Large spreads more forgiving
        elif spread_bps < 30:
            prob *= 0.90  # Tight spreads risky
        
        # Adjust for regime volatility
        volatile_regimes = ['flash_crash', 'flash_pump', 'low_liquidity']
        if market_regime in volatile_regimes:
            prob *= 0.70  # Much higher failure rate in chaos
        elif market_regime in ['sideways_tight', 'high_activity']:
            prob *= 1.10  # Stable conditions favorable
        
        # Adjust for profit size (small profits = less margin for error)
        if net_profit < 5:
            prob *= 0.85  # Risky when profits are thin
        elif net_profit > 20:
            prob *= 1.05  # Good cushion
        
        # Learn from history
        if market_regime in self.regime_performance:
            regime_stats = self.regime_performance[market_regime]
            historical_win_rate = regime_stats.get('win_rate', 0.5)
            # Blend historical with calculated
            prob = (prob * 0.7) + (historical_win_rate * 0.3)
        
        # Account for consecutive losses (psychological + real correlation)
        if self.consecutive_losses >= 2:
            prob *= 0.80  # Something may be wrong
        
        # Cap probability
        prob = max(0.0, min(1.0, prob))
        
        return prob
    
    def calculate_expected_value(self,
                                 net_profit: float,
                                 probability: float,
                                 gas_cost: float) -> float:
        """
        Risk-adjusted expected value
        EV = (P(win) × profit) - (P(loss) × cost)
        """
        # Expected win
        expected_win = probability * net_profit
        
        # Expected loss (gas + potential slippage)
        slippage_risk = gas_cost * 2  # Assume 2x gas in worst case
        expected_loss = (1 - probability) * slippage_risk
        
        # Net expected value
        ev = expected_win - expected_loss
        
        return ev
    
    def identify_red_flags(self,
                          spread_bps: int,
                          confidence: float,
                          market_regime: str,
                          net_profit: float,
                          liquidity: float) -> List[str]:
        """Detect warning signals"""
        flags = []
        
        # Confidence issues
        if confidence < 0.50:
            flags.append("LOW_CONFIDENCE: <50%")
        elif confidence < 0.65:
            flags.append("MODERATE_CONFIDENCE: <65%")
        
        # Profit margin issues
        if net_profit < 2:
            flags.append("THIN_MARGINS: <$2 profit")
        
        # Spread issues
        if spread_bps < 20:
            flags.append("TIGHT_SPREAD: <20 BPS")
        elif spread_bps > 500:
            flags.append("EXTREME_SPREAD: >500 BPS (price instability)")
        
        # Regime issues
        dangerous_regimes = ['flash_crash', 'flash_pump', 'low_liquidity']
        if market_regime in dangerous_regimes:
            flags.append(f"VOLATILE_REGIME: {market_regime}")
        
        # Liquidity issues
        if liquidity < 5000:
            flags.append("LOW_LIQUIDITY: <$5k available")
        
        # Consecutive losses
        if self.consecutive_losses >= 2:
            flags.append(f"LOSING_STREAK: {self.consecutive_losses} consecutive")
        
        # Performance issues
        if self.total_trades >= 10:
            current_win_rate = self.winning_trades / self.total_trades
            if current_win_rate < self.min_win_rate:
                flags.append(f"LOW_WIN_RATE: {current_win_rate:.1%} < {self.min_win_rate:.1%}")
        
        return flags
    
    def identify_green_flags(self,
                            spread_bps: int,
                            confidence: float,
                            market_regime: str,
                            net_profit: float) -> List[str]:
        """Detect positive signals"""
        flags = []
        
        # High confidence
        if confidence >= 0.85:
            flags.append("HIGH_CONFIDENCE: ≥85%")
        elif confidence >= 0.75:
            flags.append("GOOD_CONFIDENCE: ≥75%")
        
        # Good profits
        if net_profit >= 10:
            flags.append("STRONG_PROFIT: ≥$10")
        elif net_profit >= 5:
            flags.append("GOOD_PROFIT: ≥$5")
        
        # Healthy spread
        if 50 <= spread_bps <= 200:
            flags.append("OPTIMAL_SPREAD: 50-200 BPS")
        
        # Favorable regime
        good_regimes = ['sideways_tight', 'high_activity', 'bull_trending']
        if market_regime in good_regimes:
            flags.append(f"FAVORABLE_REGIME: {market_regime}")
        
        # Winning streak
        if self.consecutive_wins >= 3:
            flags.append(f"WINNING_STREAK: {self.consecutive_wins} consecutive")
        
        # Good historical performance
        if self.total_trades >= 10:
            current_win_rate = self.winning_trades / self.total_trades
            if current_win_rate >= 0.80:
                flags.append(f"STRONG_WIN_RATE: {current_win_rate:.1%}")
        
        return flags
    
    async def assess_trade(self,
                          token_pair: str,
                          spread_bps: int,
                          confidence: float,
                          net_profit: float,
                          gas_cost: float,
                          market_regime: str,
                          liquidity: float) -> RiskAssessment:
        """
        Comprehensive pre-trade risk assessment
        """
        # Calculate success probability
        prob_success = self.calculate_probability_of_success(
            confidence, spread_bps, market_regime, net_profit
        )
        
        # Calculate expected value
        expected_value = self.calculate_expected_value(
            net_profit, prob_success, gas_cost
        )
        
        # Identify flags
        red_flags = self.identify_red_flags(
            spread_bps, confidence, market_regime, net_profit, liquidity
        )
        green_flags = self.identify_green_flags(
            spread_bps, confidence, market_regime, net_profit
        )
        
        # Determine risk level
        risk_level = self._calculate_risk_level(
            prob_success, expected_value, len(red_flags), len(green_flags)
        )
        
        # Generate recommendation
        recommendation = self._generate_recommendation(
            risk_level, prob_success, expected_value, red_flags
        )
        
        # Confidence score (0-100)
        confidence_score = min(100, prob_success * 100 + len(green_flags) * 5 - len(red_flags) * 5)
        
        # Reasoning
        reasoning = self._generate_reasoning(
            prob_success, expected_value, red_flags, green_flags, risk_level
        )
        
        return RiskAssessment(
            risk_level=risk_level,
            probability_of_success=prob_success,
            expected_value=expected_value,
            red_flags=red_flags,
            green_flags=green_flags,
            recommendation=recommendation,
            confidence_score=confidence_score,
            reasoning=reasoning
        )
    
    def _calculate_risk_level(self, prob: float, ev: float, 
                              red_count: int, green_count: int) -> RiskLevel:
        """Determine overall risk level"""
        # Extreme risk conditions
        if prob < 0.40 or ev < 0 or red_count >= 4:
            return RiskLevel.EXTREME
        
        # High risk
        if prob < 0.60 or ev < 2 or red_count >= 3:
            return RiskLevel.HIGH
        
        # Moderate risk
        if prob < 0.75 or ev < 5 or red_count >= 2:
            return RiskLevel.MODERATE
        
        # Safe trade
        return RiskLevel.SAFE
    
    def _generate_recommendation(self, risk_level: RiskLevel,
                                 prob: float, ev: float,
                                 red_flags: List[str]) -> str:
        """Generate trade recommendation"""
        # Never execute extreme risk
        if risk_level == RiskLevel.EXTREME:
            return "SKIP"
        
        # Skip high risk unless exceptional
        if risk_level == RiskLevel.HIGH:
            if prob > 0.70 and ev > 8:
                return "REDUCE_SIZE"
            return "SKIP"
        
        # Check for blocking conditions
        if self.consecutive_losses >= self.max_consecutive_losses:
            return "SKIP"  # Circuit breaker
        
        if "LOW_WIN_RATE" in str(red_flags):
            return "SKIP"  # Performance issue
        
        # Execute safe and moderate trades
        if risk_level == RiskLevel.SAFE:
            return "EXECUTE"
        
        if risk_level == RiskLevel.MODERATE and prob >= 0.65:
            return "EXECUTE"
        
        return "SKIP"
    
    def _generate_reasoning(self, prob: float, ev: float,
                           red_flags: List[str], green_flags: List[str],
                           risk_level: RiskLevel) -> str:
        """Generate human-readable reasoning"""
        parts = []
        
        parts.append(f"P(success)={prob:.1%}")
        parts.append(f"EV=${ev:.2f}")
        
        if red_flags:
            parts.append(f"{len(red_flags)} risks")
        if green_flags:
            parts.append(f"{len(green_flags)} positives")
        
        parts.append(f"Risk: {risk_level.value}")
        
        return " | ".join(parts)
    
    def record_outcome(self, outcome: TradeOutcome):
        """Learn from trade results"""
        self.trade_history.append(outcome)
        self.total_trades += 1
        
        if outcome.success:
            self.winning_trades += 1
            self.consecutive_wins += 1
            self.consecutive_losses = 0
        else:
            self.consecutive_wins = 0
            self.consecutive_losses += 1
        
        # Update regime-specific stats
        regime = outcome.market_regime
        if regime not in self.regime_performance:
            self.regime_performance[regime] = {
                'trades': 0,
                'wins': 0,
                'total_profit': 0.0
            }
        
        stats = self.regime_performance[regime]
        stats['trades'] += 1
        if outcome.success:
            stats['wins'] += 1
        stats['total_profit'] += outcome.actual_profit
        stats['win_rate'] = stats['wins'] / stats['trades']
    
    def get_statistics(self) -> Dict:
        """Return performance statistics"""
        win_rate = self.winning_trades / self.total_trades if self.total_trades > 0 else 0
        
        return {
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'win_rate': win_rate,
            'consecutive_wins': self.consecutive_wins,
            'consecutive_losses': self.consecutive_losses,
            'regime_performance': self.regime_performance
        }


async def demo_risk_guardian():
    """Demonstrate Risk Guardian"""
    print("=" * 80)
    print("🛡️  RISK GUARDIAN - LOSS PREVENTION DEMO")
    print("=" * 80)
    
    guardian = RiskGuardian()
    
    # Test various scenarios
    scenarios = [
        {
            'name': 'SAFE: High confidence + good profit',
            'token_pair': 'WETH/USDC',
            'spread_bps': 120,
            'confidence': 0.85,
            'net_profit': 12.0,
            'gas_cost': 0.80,
            'market_regime': 'sideways_tight',
            'liquidity': 50000
        },
        {
            'name': 'RISKY: Low confidence + thin margins',
            'token_pair': 'ARB/USDC',
            'spread_bps': 25,
            'confidence': 0.45,
            'net_profit': 1.50,
            'gas_cost': 0.70,
            'market_regime': 'sideways_choppy',
            'liquidity': 10000
        },
        {
            'name': 'EXTREME: Flash crash with huge spread',
            'token_pair': 'UNI/USDC',
            'spread_bps': 850,
            'confidence': 0.35,
            'net_profit': 8.0,
            'gas_cost': 2.50,
            'market_regime': 'flash_crash',
            'liquidity': 5000
        },
    ]
    
    for scenario in scenarios:
        name = scenario.pop('name')
        print(f"\n{'='*80}")
        print(f"📋 {name}")
        print(f"{'='*80}")
        
        assessment = await guardian.assess_trade(**scenario)
        
        print(f"🎯 Recommendation: {assessment.recommendation}")
        print(f"📊 Risk Level: {assessment.risk_level.value.upper()}")
        print(f"💯 Confidence Score: {assessment.confidence_score:.1f}/100")
        print(f"📈 Success Probability: {assessment.probability_of_success:.1%}")
        print(f"💰 Expected Value: ${assessment.expected_value:.2f}")
        print(f"📝 Reasoning: {assessment.reasoning}")
        
        if assessment.red_flags:
            print(f"🚩 Red Flags ({len(assessment.red_flags)}):")
            for flag in assessment.red_flags:
                print(f"   - {flag}")
        
        if assessment.green_flags:
            print(f"✅ Green Flags ({len(assessment.green_flags)}):")
            for flag in assessment.green_flags:
                print(f"   - {flag}")
    
    print(f"\n{'='*80}")
    print("✅ Risk Guardian ready for integration")


if __name__ == "__main__":
    asyncio.run(demo_risk_guardian())
