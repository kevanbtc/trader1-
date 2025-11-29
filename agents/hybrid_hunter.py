"""
🔥 HYBRID HUNTER ENGINE - BSC Multi-Strategy Scanner
Combines 4 detection modules for maximum trade frequency

Strategies:
1. Drift Scalper - 200-600ms price lag between DEXes
2. Shock Sniper - Whale aftershock mean reversion
3. Stablecoin Arb - Peg deviation micro-trades (USDT/USDC/BUSD)
4. Triangular Loop - 3-hop circular arbitrage

Optimized for $1-$3 position sizes on BSC
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import json
from pathlib import Path

@dataclass
class HybridOpportunity:
    """Multi-strategy opportunity detection"""
    strategy_type: str  # "DRIFT", "SHOCK", "STABLE", "TRIANGLE"
    pair: str
    buy_dex: str
    sell_dex: str
    buy_price: float
    sell_price: float
    spread_percent: float
    estimated_profit_usd: float
    gas_cost_usd: float
    net_profit_usd: float
    confidence: float
    timestamp: datetime
    priority: str  # LOW, MEDIUM, HIGH, CRITICAL
    metadata: Dict  # Strategy-specific data


class DriftScalper:
    """
    Detects 200-600ms price lag between DEXes
    Exploits micro-mispricing during update delays
    """
    
    def __init__(self, max_lag_ms: int = 600):
        self.max_lag_ms = max_lag_ms
        self.price_history = {}  # DEX -> {token_pair -> (price, timestamp)}
        self.drift_threshold_pct = 0.01  # 0.01% minimum drift
        
    def update_price(self, dex: str, pair: str, price: float, timestamp: datetime):
        """Track price updates with timestamps"""
        if dex not in self.price_history:
            self.price_history[dex] = {}
        self.price_history[dex][pair] = (price, timestamp)
    
    def detect_drift(self, pair: str, min_profit_usd: float = 0.001) -> List[HybridOpportunity]:
        """
        Find price differences where one DEX is lagging
        Returns opportunities if drift > threshold and within time window
        """
        opportunities = []
        
        # Get all DEXes with this pair
        dex_prices = []
        for dex, pairs in self.price_history.items():
            if pair in pairs:
                price, timestamp = pairs[pair]
                age_ms = (datetime.utcnow() - timestamp).total_seconds() * 1000
                if age_ms <= self.max_lag_ms:
                    dex_prices.append((dex, price, timestamp))
        
        if len(dex_prices) < 2:
            return []
        
        # Compare all pairs
        for i in range(len(dex_prices)):
            for j in range(i + 1, len(dex_prices)):
                dex1, price1, ts1 = dex_prices[i]
                dex2, price2, ts2 = dex_prices[j]
                
                # Calculate drift
                spread_pct = abs((price2 - price1) / price1 * 100)
                
                if spread_pct >= self.drift_threshold_pct:
                    # Determine buy/sell based on which is cheaper
                    if price1 < price2:
                        buy_dex, buy_price = dex1, price1
                        sell_dex, sell_price = dex2, price2
                    else:
                        buy_dex, buy_price = dex2, price2
                        sell_dex, sell_price = dex1, price1
                    
                    # Estimate profit (simplified for $3 position)
                    position_size = 3.0
                    gross_profit = (sell_price - buy_price) / buy_price * position_size
                    gas_cost = 0.04  # BSC gas ~$0.02 per tx * 2 txs
                    net_profit = gross_profit - gas_cost
                    
                    if net_profit >= min_profit_usd:
                        # Calculate confidence based on time lag
                        time_diff_ms = abs((ts2 - ts1).total_seconds() * 1000)
                        confidence = 1.0 - (time_diff_ms / self.max_lag_ms)
                        
                        opportunities.append(HybridOpportunity(
                            strategy_type="DRIFT",
                            pair=pair,
                            buy_dex=buy_dex,
                            sell_dex=sell_dex,
                            buy_price=buy_price,
                            sell_price=sell_price,
                            spread_percent=spread_pct,
                            estimated_profit_usd=gross_profit,
                            gas_cost_usd=gas_cost,
                            net_profit_usd=net_profit,
                            confidence=confidence,
                            timestamp=datetime.utcnow(),
                            priority="HIGH" if net_profit > 0.05 else "MEDIUM",
                            metadata={"time_lag_ms": time_diff_ms}
                        ))
        
        return opportunities


class ShockSniper:
    """
    Detects whale trades and liquidity shocks
    Trades mean-reversion after temporary price dislocations
    """
    
    def __init__(self, shock_threshold_pct: float = 0.3):
        self.shock_threshold_pct = shock_threshold_pct
        self.baseline_prices = {}  # pair -> moving average
        self.shock_window_seconds = 10
        
    def update_baseline(self, pair: str, price: float):
        """Update moving average baseline"""
        if pair not in self.baseline_prices:
            self.baseline_prices[pair] = []
        
        self.baseline_prices[pair].append(price)
        
        # Keep only last 20 samples for MA
        if len(self.baseline_prices[pair]) > 20:
            self.baseline_prices[pair].pop(0)
    
    def detect_shock(self, pair: str, current_price: float, dex: str, 
                     min_profit_usd: float = 0.001) -> Optional[HybridOpportunity]:
        """
        Detect if current price deviates significantly from baseline
        Returns opportunity to trade mean-reversion
        """
        if pair not in self.baseline_prices or len(self.baseline_prices[pair]) < 5:
            return None
        
        baseline = sum(self.baseline_prices[pair]) / len(self.baseline_prices[pair])
        deviation_pct = abs((current_price - baseline) / baseline * 100)
        
        if deviation_pct >= self.shock_threshold_pct:
            # Shock detected - trade reversion
            position_size = 2.0  # Slightly smaller for shock trades
            
            # If price spiked up, we expect reversion down (sell signal)
            # If price dropped, we expect reversion up (buy signal)
            if current_price > baseline:
                # Sell at current high, buy back at baseline
                gross_profit = (current_price - baseline) / baseline * position_size
                direction = "SELL_SHOCK"
            else:
                # Buy at current low, sell at baseline
                gross_profit = (baseline - current_price) / current_price * position_size
                direction = "BUY_SHOCK"
            
            gas_cost = 0.04
            net_profit = gross_profit - gas_cost
            
            if net_profit >= min_profit_usd:
                return HybridOpportunity(
                    strategy_type="SHOCK",
                    pair=pair,
                    buy_dex=dex if direction == "BUY_SHOCK" else "REVERSION_TARGET",
                    sell_dex="REVERSION_TARGET" if direction == "BUY_SHOCK" else dex,
                    buy_price=current_price if direction == "BUY_SHOCK" else baseline,
                    sell_price=baseline if direction == "BUY_SHOCK" else current_price,
                    spread_percent=deviation_pct,
                    estimated_profit_usd=gross_profit,
                    gas_cost_usd=gas_cost,
                    net_profit_usd=net_profit,
                    confidence=min(deviation_pct / 2.0, 0.95),  # Higher deviation = higher confidence
                    timestamp=datetime.utcnow(),
                    priority="CRITICAL" if deviation_pct > 1.0 else "HIGH",
                    metadata={"shock_direction": direction, "baseline_price": baseline}
                )
        
        return None


class StablecoinDeviation:
    """
    Detects stablecoin peg deviations across DEXes
    Most consistent micro-profit strategy
    """
    
    def __init__(self, deviation_threshold_pct: float = 0.05):
        self.deviation_threshold_pct = deviation_threshold_pct  # 0.05% = 5 bps
        self.target_peg = 1.0
        
    def detect_deviations(self, stable_prices: Dict[str, Dict[str, float]], 
                          min_profit_usd: float = 0.001) -> List[HybridOpportunity]:
        """
        Check all stablecoins across all DEXes for peg deviations
        stable_prices = {stable_name: {dex_name: price}}
        """
        opportunities = []
        
        for stable, dex_prices in stable_prices.items():
            if len(dex_prices) < 2:
                continue
            
            # Find max and min prices
            dex_list = list(dex_prices.items())
            
            for i in range(len(dex_list)):
                for j in range(i + 1, len(dex_list)):
                    dex1, price1 = dex_list[i]
                    dex2, price2 = dex_list[j]
                    
                    # Check deviation from peg
                    spread = abs(price2 - price1)
                    spread_pct = (spread / self.target_peg) * 100
                    
                    if spread_pct >= self.deviation_threshold_pct:
                        # Stablecoin arbitrage opportunity
                        position_size = 3.0  # Max size for stable arb
                        
                        if price1 < price2:
                            buy_dex, buy_price = dex1, price1
                            sell_dex, sell_price = dex2, price2
                        else:
                            buy_dex, buy_price = dex2, price2
                            sell_dex, sell_price = dex1, price1
                        
                        gross_profit = spread * position_size
                        gas_cost = 0.04
                        net_profit = gross_profit - gas_cost
                        
                        if net_profit >= min_profit_usd:
                            opportunities.append(HybridOpportunity(
                                strategy_type="STABLE",
                                pair=f"{stable}/USD",
                                buy_dex=buy_dex,
                                sell_dex=sell_dex,
                                buy_price=buy_price,
                                sell_price=sell_price,
                                spread_percent=spread_pct,
                                estimated_profit_usd=gross_profit,
                                gas_cost_usd=gas_cost,
                                net_profit_usd=net_profit,
                                confidence=0.95,  # Stablecoin arb is high confidence
                                timestamp=datetime.utcnow(),
                                priority="HIGH" if net_profit > 0.02 else "MEDIUM",
                                metadata={"stable_name": stable, "deviation_from_peg": abs(buy_price - 1.0)}
                            ))
        
        return opportunities


class TriangularLoop:
    """
    Detects 3-hop circular arbitrage opportunities
    Example: USDC -> WETH -> WBNB -> USDC
    """
    
    def __init__(self):
        self.loops = [
            ("USDC", "WETH", "WBNB"),
            ("USDT", "WBNB", "BTCB"),
            ("BUSD", "WETH", "CAKE"),
            ("USDC", "WBNB", "XRP"),
        ]
        
    def detect_loops(self, prices: Dict[str, float], dex: str,
                     min_profit_usd: float = 0.001) -> List[HybridOpportunity]:
        """
        Check triangular paths for inefficiencies
        prices = {pair: price} e.g. {"USDC/WETH": 0.0003, "WETH/WBNB": 0.5, "WBNB/USDC": 250}
        """
        opportunities = []
        
        for token_a, token_b, token_c in self.loops:
            # Build the 3 pairs
            pair1 = f"{token_a}/{token_b}"
            pair2 = f"{token_b}/{token_c}"
            pair3 = f"{token_c}/{token_a}"
            
            if pair1 not in prices or pair2 not in prices or pair3 not in prices:
                continue
            
            # Calculate loop return
            start_amount = 3.0  # Start with $3
            
            # A -> B
            amount_b = start_amount * prices[pair1]
            
            # B -> C
            amount_c = amount_b * prices[pair2]
            
            # C -> A
            end_amount = amount_c * prices[pair3]
            
            gross_profit = end_amount - start_amount
            gas_cost = 0.06  # 3 hops = 3x gas
            net_profit = gross_profit - gas_cost
            
            if net_profit >= min_profit_usd:
                spread_pct = (gross_profit / start_amount) * 100
                
                opportunities.append(HybridOpportunity(
                    strategy_type="TRIANGLE",
                    pair=f"{token_a}-{token_b}-{token_c}",
                    buy_dex=dex,
                    sell_dex=dex,  # Same DEX for triangular
                    buy_price=start_amount,
                    sell_price=end_amount,
                    spread_percent=spread_pct,
                    estimated_profit_usd=gross_profit,
                    gas_cost_usd=gas_cost,
                    net_profit_usd=net_profit,
                    confidence=0.80,  # Triangular is moderately confident
                    timestamp=datetime.utcnow(),
                    priority="HIGH" if net_profit > 0.10 else "MEDIUM",
                    metadata={
                        "path": [token_a, token_b, token_c, token_a],
                        "amounts": [start_amount, amount_b, amount_c, end_amount]
                    }
                ))
        
        return opportunities


class HybridHunter:
    """
    Master coordinator for all 4 detection strategies
    Aggregates opportunities and prioritizes execution
    """
    
    def __init__(self, min_profit_usd: float = 0.001):
        self.drift_scalper = DriftScalper()
        self.shock_sniper = ShockSniper()
        self.stable_deviation = StablecoinDeviation()
        self.triangular_loop = TriangularLoop()
        self.min_profit_usd = min_profit_usd
        
        # Stats
        self.total_scans = 0
        self.opportunities_by_strategy = {
            "DRIFT": 0,
            "SHOCK": 0,
            "STABLE": 0,
            "TRIANGLE": 0
        }
        
    def scan_all_strategies(self, market_data: Dict) -> List[HybridOpportunity]:
        """
        Run all 4 detection strategies and aggregate opportunities
        
        market_data = {
            "prices": {dex: {pair: price}},
            "stables": {stable: {dex: price}},
            "timestamp": datetime
        }
        """
        self.total_scans += 1
        all_opportunities = []
        
        # 1. Drift Scalping
        for pair in market_data.get("pairs", []):
            drift_opps = self.drift_scalper.detect_drift(pair, self.min_profit_usd)
            all_opportunities.extend(drift_opps)
            self.opportunities_by_strategy["DRIFT"] += len(drift_opps)
        
        # 2. Shock Sniping
        for dex, pairs in market_data.get("prices", {}).items():
            for pair, price in pairs.items():
                self.shock_sniper.update_baseline(pair, price)
                shock_opp = self.shock_sniper.detect_shock(pair, price, dex, self.min_profit_usd)
                if shock_opp:
                    all_opportunities.append(shock_opp)
                    self.opportunities_by_strategy["SHOCK"] += 1
        
        # 3. Stablecoin Deviation
        stable_opps = self.stable_deviation.detect_deviations(
            market_data.get("stables", {}),
            self.min_profit_usd
        )
        all_opportunities.extend(stable_opps)
        self.opportunities_by_strategy["STABLE"] += len(stable_opps)
        
        # 4. Triangular Loops
        for dex, pairs in market_data.get("prices", {}).items():
            triangle_opps = self.triangular_loop.detect_loops(pairs, dex, self.min_profit_usd)
            all_opportunities.extend(triangle_opps)
            self.opportunities_by_strategy["TRIANGLE"] += len(triangle_opps)
        
        # Sort by priority and net profit
        priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        all_opportunities.sort(
            key=lambda x: (priority_order[x.priority], -x.net_profit_usd)
        )
        
        return all_opportunities
    
    def get_stats(self) -> Dict:
        """Return performance statistics"""
        return {
            "total_scans": self.total_scans,
            "opportunities_by_strategy": self.opportunities_by_strategy,
            "total_opportunities": sum(self.opportunities_by_strategy.values())
        }


# Example usage / testing
if __name__ == "__main__":
    print("🔥 Hybrid Hunter Engine - Multi-Strategy Scanner")
    print("=" * 60)
    
    hunter = HybridHunter(min_profit_usd=0.001)
    
    # Simulate market data
    market_data = {
        "prices": {
            "PancakeSwap": {
                "WBNB/USDC": 250.50,
                "WETH/USDC": 2450.00,
                "BTCB/USDC": 42000.00
            },
            "BiSwap": {
                "WBNB/USDC": 250.35,  # Slight drift
                "WETH/USDC": 2451.00,  # Drift
                "BTCB/USDC": 42010.00
            }
        },
        "stables": {
            "USDT": {
                "PancakeSwap": 0.9995,
                "BiSwap": 1.0008  # Deviation
            },
            "USDC": {
                "PancakeSwap": 1.0002,
                "BiSwap": 0.9991  # Deviation
            }
        },
        "pairs": ["WBNB/USDC", "WETH/USDC", "BTCB/USDC"],
        "timestamp": datetime.utcnow()
    }
    
    # Update drift prices
    for dex, pairs in market_data["prices"].items():
        for pair, price in pairs.items():
            hunter.drift_scalper.update_price(dex, pair, price, datetime.utcnow())
    
    # Scan
    opportunities = hunter.scan_all_strategies(market_data)
    
    print(f"\n✅ Found {len(opportunities)} opportunities:")
    for opp in opportunities:
        print(f"\n  [{opp.strategy_type}] {opp.pair}")
        print(f"  {opp.buy_dex} @ ${opp.buy_price:.4f} → {opp.sell_dex} @ ${opp.sell_price:.4f}")
        print(f"  Spread: {opp.spread_percent:.3f}% | Net: ${opp.net_profit_usd:.4f} | Priority: {opp.priority}")
    
    print(f"\n📊 Stats: {hunter.get_stats()}")
