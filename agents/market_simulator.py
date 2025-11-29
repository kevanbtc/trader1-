"""
Realistic Market Simulator for Paper Trading
Generates diverse, lifelike market conditions with varied spreads, volatility, and trends
"""

import asyncio
import numpy as np
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class MarketRegime(Enum):
    """Market behavior patterns"""
    BULL_TRENDING = "bull_trending"      # Strong upward momentum
    BEAR_TRENDING = "bear_trending"      # Strong downward momentum
    SIDEWAYS_TIGHT = "sideways_tight"    # Low volatility range
    SIDEWAYS_CHOPPY = "sideways_choppy"  # High volatility range
    FLASH_CRASH = "flash_crash"          # Sudden drop
    FLASH_PUMP = "flash_pump"            # Sudden spike
    LOW_LIQUIDITY = "low_liquidity"      # Wide spreads, erratic
    HIGH_ACTIVITY = "high_activity"      # Tight spreads, frequent updates


@dataclass
class SimulatedPool:
    """DEX pool with realistic behavior"""
    dex_name: str
    token_pair: str
    base_price: float
    liquidity_usd: float
    spread_bps: int
    last_update: datetime
    price_drift: float = 0.0
    volume_24h: float = 0.0


@dataclass
class SimulatedOpportunity:
    """Arbitrage opportunity with realistic constraints"""
    token_pair: str
    buy_dex: str
    sell_dex: str
    buy_price: float
    sell_price: float
    spread_bps: int
    expected_profit_usd: float
    gas_cost_usd: float
    net_profit_usd: float
    available_liquidity: float
    timestamp: datetime
    market_regime: str
    confidence: float  # 0-1, affected by volatility


class MarketSimulator:
    """
    Generates realistic market scenarios with diversity
    """
    
    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)
        
        # Market state
        self.current_regime = MarketRegime.SIDEWAYS_TIGHT
        self.regime_start_time = datetime.utcnow()
        self.regime_duration = timedelta(minutes=random.randint(5, 20))
        
        # Price tracking
        self.base_prices = {
            'WETH/USDC': 3000.0,
            'WBTC/USDC': 65000.0,
            'ARB/USDC': 1.2,
            'LINK/USDC': 15.0,
            'UNI/USDC': 8.0,
        }
        
        # DEX pools with different characteristics
        self.pools: Dict[str, List[SimulatedPool]] = {}
        self._initialize_pools()
        
        # Statistics
        self.opportunities_generated = 0
        self.regime_changes = 0
        
    def _initialize_pools(self):
        """Create diverse DEX pools with varying characteristics"""
        dex_configs = [
            {'name': 'Uniswap_V3', 'liquidity_mult': 1.0, 'spread_mult': 1.0},
            {'name': 'Sushiswap', 'liquidity_mult': 0.6, 'spread_mult': 1.3},
            {'name': 'Balancer', 'liquidity_mult': 0.4, 'spread_mult': 1.5},
            {'name': 'Curve', 'liquidity_mult': 1.2, 'spread_mult': 0.8},
            {'name': 'Camelot', 'liquidity_mult': 0.3, 'spread_mult': 2.0},
        ]
        
        for token_pair, base_price in self.base_prices.items():
            self.pools[token_pair] = []
            
            for dex_config in dex_configs:
                # Vary liquidity and spreads per DEX
                base_liquidity = random.uniform(50000, 500000) * dex_config['liquidity_mult']
                base_spread = int(random.uniform(5, 30) * dex_config['spread_mult'])
                
                pool = SimulatedPool(
                    dex_name=dex_config['name'],
                    token_pair=token_pair,
                    base_price=base_price,
                    liquidity_usd=base_liquidity,
                    spread_bps=base_spread,
                    last_update=datetime.utcnow(),
                    volume_24h=random.uniform(10000, 1000000)
                )
                self.pools[token_pair].append(pool)
    
    def _update_regime(self):
        """Transition to new market regime"""
        now = datetime.utcnow()
        if now - self.regime_start_time > self.regime_duration:
            # Choose new regime with weighted probabilities
            regimes = [
                (MarketRegime.SIDEWAYS_TIGHT, 0.25),
                (MarketRegime.SIDEWAYS_CHOPPY, 0.20),
                (MarketRegime.BULL_TRENDING, 0.15),
                (MarketRegime.BEAR_TRENDING, 0.15),
                (MarketRegime.HIGH_ACTIVITY, 0.10),
                (MarketRegime.LOW_LIQUIDITY, 0.08),
                (MarketRegime.FLASH_CRASH, 0.04),
                (MarketRegime.FLASH_PUMP, 0.03),
            ]
            
            regime_choices = [r for r, _ in regimes]
            regime_weights = [w for _, w in regimes]
            
            self.current_regime = random.choices(regime_choices, weights=regime_weights)[0]
            self.regime_start_time = now
            self.regime_duration = timedelta(minutes=random.randint(3, 25))
            self.regime_changes += 1
            
            print(f"📊 REGIME CHANGE → {self.current_regime.value.upper()} "
                  f"(duration: {self.regime_duration.seconds // 60}m)")
    
    def _apply_regime_effects(self, pool: SimulatedPool) -> Tuple[float, int, float]:
        """
        Apply market regime to pool pricing
        Returns: (price_adjustment, spread_adjustment, liquidity_mult)
        """
        regime = self.current_regime
        
        if regime == MarketRegime.BULL_TRENDING:
            # Steady upward drift with moderate spreads
            drift = random.uniform(0.0001, 0.0005)
            spread_mult = random.uniform(0.8, 1.2)
            liquidity_mult = 1.1
            
        elif regime == MarketRegime.BEAR_TRENDING:
            # Steady downward drift with wider spreads
            drift = random.uniform(-0.0005, -0.0001)
            spread_mult = random.uniform(1.1, 1.5)
            liquidity_mult = 0.9
            
        elif regime == MarketRegime.SIDEWAYS_TIGHT:
            # Minimal drift, tight spreads
            drift = random.uniform(-0.0001, 0.0001)
            spread_mult = random.uniform(0.7, 0.9)
            liquidity_mult = 1.2
            
        elif regime == MarketRegime.SIDEWAYS_CHOPPY:
            # Random walk, moderate spreads
            drift = random.uniform(-0.0003, 0.0003)
            spread_mult = random.uniform(1.0, 1.4)
            liquidity_mult = 1.0
            
        elif regime == MarketRegime.FLASH_CRASH:
            # Sharp downward spike
            drift = random.uniform(-0.002, -0.0005)
            spread_mult = random.uniform(2.0, 4.0)
            liquidity_mult = 0.4
            
        elif regime == MarketRegime.FLASH_PUMP:
            # Sharp upward spike
            drift = random.uniform(0.0005, 0.002)
            spread_mult = random.uniform(2.0, 4.0)
            liquidity_mult = 0.5
            
        elif regime == MarketRegime.LOW_LIQUIDITY:
            # Wide spreads, erratic prices
            drift = random.uniform(-0.0004, 0.0004)
            spread_mult = random.uniform(2.5, 5.0)
            liquidity_mult = 0.3
            
        elif regime == MarketRegime.HIGH_ACTIVITY:
            # Tight spreads, frequent small moves
            drift = random.uniform(-0.0002, 0.0002)
            spread_mult = random.uniform(0.5, 0.8)
            liquidity_mult = 1.5
            
        else:
            drift = 0.0
            spread_mult = 1.0
            liquidity_mult = 1.0
        
        return drift, spread_mult, liquidity_mult
    
    def _update_pool_prices(self):
        """Update all pool prices based on current regime"""
        for token_pair, pools in self.pools.items():
            # Base price evolution (affects all pools for this pair)
            base_drift, _, _ = self._apply_regime_effects(pools[0])
            base_price = pools[0].base_price * (1 + base_drift)
            
            # Add micro-noise so pools diverge
            for pool in pools:
                drift, spread_mult, liquidity_mult = self._apply_regime_effects(pool)
                
                # Update price with drift + noise
                noise = random.gauss(0, 0.0001)
                pool.base_price = base_price * (1 + noise)
                
                # Update spread based on regime
                new_spread = int(pool.spread_bps * spread_mult)
                pool.spread_bps = max(1, min(500, new_spread))  # Clamp 1-500 BPS
                
                # Update liquidity
                pool.liquidity_usd *= liquidity_mult
                pool.liquidity_usd = max(1000, pool.liquidity_usd)  # Min $1k
                
                pool.last_update = datetime.utcnow()
    
    def _find_arbitrage_opportunities(self) -> List[SimulatedOpportunity]:
        """Scan for profitable arbitrage across pools"""
        opportunities = []
        
        for token_pair, pools in self.pools.items():
            # Compare all pool pairs
            for i, buy_pool in enumerate(pools):
                for sell_pool in pools[i+1:]:
                    # Calculate effective prices with spread
                    buy_price = buy_pool.base_price * (1 + buy_pool.spread_bps / 10000)
                    sell_price = sell_pool.base_price * (1 - sell_pool.spread_bps / 10000)
                    
                    # Check both directions
                    for direction in [(buy_pool, sell_pool, buy_price, sell_price),
                                      (sell_pool, buy_pool, sell_price, buy_price)]:
                        bp, sp, bprice, sprice = direction
                        
                        if sprice > bprice:
                            spread_bps = int((sprice - bprice) / bprice * 10000)
                            
                            if spread_bps >= 10:  # Min 10 BPS to be interesting
                                # Calculate profits
                                trade_size = min(bp.liquidity_usd, sp.liquidity_usd) * 0.1  # 10% of pool
                                gross_profit = (sprice - bprice) * (trade_size / bprice)
                                
                                # Gas cost varies by regime
                                base_gas = 0.50  # USD
                                if self.current_regime == MarketRegime.LOW_LIQUIDITY:
                                    gas_cost = base_gas * random.uniform(2.0, 5.0)
                                elif self.current_regime == MarketRegime.HIGH_ACTIVITY:
                                    gas_cost = base_gas * random.uniform(1.5, 3.0)
                                else:
                                    gas_cost = base_gas * random.uniform(0.8, 1.5)
                                
                                net_profit = gross_profit - gas_cost
                                
                                # Confidence affected by volatility
                                if self.current_regime in [MarketRegime.FLASH_CRASH, 
                                                           MarketRegime.FLASH_PUMP,
                                                           MarketRegime.LOW_LIQUIDITY]:
                                    confidence = random.uniform(0.3, 0.6)
                                elif self.current_regime == MarketRegime.SIDEWAYS_TIGHT:
                                    confidence = random.uniform(0.8, 0.95)
                                else:
                                    confidence = random.uniform(0.6, 0.85)
                                
                                if net_profit > 0:
                                    opportunities.append(SimulatedOpportunity(
                                        token_pair=token_pair,
                                        buy_dex=bp.dex_name,
                                        sell_dex=sp.dex_name,
                                        buy_price=bprice,
                                        sell_price=sprice,
                                        spread_bps=spread_bps,
                                        expected_profit_usd=gross_profit,
                                        gas_cost_usd=gas_cost,
                                        net_profit_usd=net_profit,
                                        available_liquidity=trade_size,
                                        timestamp=datetime.utcnow(),
                                        market_regime=self.current_regime.value,
                                        confidence=confidence
                                    ))
        
        return opportunities
    
    async def generate_opportunities(self, count: int = 10) -> List[SimulatedOpportunity]:
        """
        Generate diverse arbitrage opportunities
        Returns mix of profitable and marginal opportunities
        """
        all_opportunities = []
        
        for _ in range(count):
            # Maybe transition regime
            self._update_regime()
            
            # Update market
            self._update_pool_prices()
            
            # Find opportunities
            opps = self._find_arbitrage_opportunities()
            
            if opps:
                # Pick 1-3 opportunities
                sample_size = min(len(opps), random.randint(1, 3))
                selected = random.sample(opps, sample_size)
                all_opportunities.extend(selected)
                self.opportunities_generated += len(selected)
            
            # Small delay to simulate real scanning
            await asyncio.sleep(random.uniform(0.5, 2.0))
        
        return all_opportunities
    
    def get_statistics(self) -> Dict:
        """Return simulation statistics"""
        return {
            'current_regime': self.current_regime.value,
            'regime_changes': self.regime_changes,
            'opportunities_generated': self.opportunities_generated,
            'active_pools': sum(len(pools) for pools in self.pools.values()),
            'token_pairs': len(self.base_prices),
        }


async def demo_simulator():
    """Demonstrate market simulator with varied scenarios"""
    print("=" * 80)
    print("🎭 REALISTIC MARKET SIMULATOR - DEMO")
    print("=" * 80)
    
    simulator = MarketSimulator(seed=42)
    
    # Generate 20 opportunities across multiple regime changes
    print("\n🔄 Generating diverse market scenarios...\n")
    opportunities = await simulator.generate_opportunities(count=20)
    
    print(f"\n📊 Generated {len(opportunities)} opportunities across regimes:\n")
    
    # Group by regime to show diversity
    by_regime = {}
    for opp in opportunities:
        regime = opp.market_regime
        if regime not in by_regime:
            by_regime[regime] = []
        by_regime[regime].append(opp)
    
    for regime, opps in by_regime.items():
        print(f"\n{regime.upper().replace('_', ' ')} ({len(opps)} opportunities):")
        for opp in opps[:3]:  # Show first 3
            profit_emoji = "💰" if opp.net_profit_usd > 5 else "💸"
            print(f"  {profit_emoji} {opp.token_pair}: "
                  f"{opp.buy_dex} → {opp.sell_dex} | "
                  f"Spread: {opp.spread_bps} BPS | "
                  f"Net: ${opp.net_profit_usd:.2f} | "
                  f"Confidence: {opp.confidence:.1%}")
    
    # Show statistics
    stats = simulator.get_statistics()
    print(f"\n📈 Simulation Statistics:")
    print(f"   Regime Changes: {stats['regime_changes']}")
    print(f"   Total Opportunities: {stats['opportunities_generated']}")
    print(f"   Active Pools: {stats['active_pools']}")
    print(f"   Token Pairs: {stats['token_pairs']}")
    
    print("\n✅ Simulator ready for paper trading integration")


if __name__ == "__main__":
    asyncio.run(demo_simulator())
