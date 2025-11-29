"""
Multi-Hop Triangular Arbitrage Engine
Detects A→B→C→A cycles across multiple DEXes
Uses graph theory to find profitable paths
Example: USDC→ETH (Uniswap) → ARB (Sushiswap) → USDC (Curve)
"""

import asyncio
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from itertools import permutations
import networkx as nx
from web3 import Web3

@dataclass
class HopPath:
    """Represents a multi-hop trading path"""
    tokens: List[str]  # e.g., ["USDC", "WETH", "ARB", "USDC"]
    dexes: List[str]   # e.g., ["Uniswap", "Sushiswap", "Curve"]
    amounts: List[float]  # Amount at each hop
    prices: List[float]   # Price at each hop
    profit_usd: float
    profit_bps: int
    gas_cost_usd: float
    net_profit_usd: float
    total_hops: int
    execution_route: List[Dict]  # Detailed route for execution

@dataclass
class TriangularOpportunity:
    """A complete triangular arbitrage opportunity"""
    path: HopPath
    confidence_score: float  # 0-100 from MCP/Swarm
    liquidity_depth: Dict[str, float]  # Liquidity at each hop
    slippage_estimate: float  # Expected slippage %
    execution_time_ms: int  # Estimated execution time
    timestamp: datetime
    priority: str  # LOW, MEDIUM, HIGH, CRITICAL

class MultiHopRouter:
    """
    Graph-based multi-hop arbitrage detector
    Builds liquidity graph, finds cycles, validates profitability
    """
    
    def __init__(self, w3: Web3, price_feed, min_hops: int = 2, max_hops: int = 4):
        self.w3 = w3
        self.price_feed = price_feed
        self.min_hops = min_hops
        self.max_hops = max_hops
        
        # Build liquidity graph
        self.graph = nx.DiGraph()
        self.token_pairs: Dict[Tuple[str, str], List[Dict]] = {}  # (token_a, token_b) -> [dex_quotes]
        
        # Configuration
        self.min_cycle_profit_usd = float(os.environ.get('MIN_MULTIHOP_PROFIT_USD', '0.05'))
        self.max_gas_per_hop = 150000  # Gas estimate per hop
        self.base_gas_price_gwei = 0.1  # Arbitrum gas price
        
        print(f"🔺 Multi-Hop Router initialized: {min_hops}-{max_hops} hops, min profit ${self.min_cycle_profit_usd}")
    
    async def update_graph(self, price_quotes: List):
        """Update liquidity graph with latest price quotes"""
        self.graph.clear()
        self.token_pairs.clear()
        
        for quote in price_quotes:
            token_in = quote.token_in
            token_out = quote.token_out
            
            # Add edge to graph (weighted by negative log of price for pathfinding)
            weight = -1 * (quote.amount_out / quote.amount_in) if quote.amount_in > 0 else float('inf')
            self.graph.add_edge(token_in, token_out, weight=weight, quote=quote, dex=quote.dex)
            
            # Store quote for pair
            pair = (token_in, token_out)
            if pair not in self.token_pairs:
                self.token_pairs[pair] = []
            self.token_pairs[pair].append({
                'dex': quote.dex,
                'price': quote.price,
                'amount_out': quote.amount_out,
                'liquidity': quote.liquidity,
                'quote': quote
            })
    
    async def find_triangular_opportunities(self, start_amount_usd: float = 10.0) -> List[TriangularOpportunity]:
        """
        Find all profitable triangular arbitrage cycles
        Uses networkx to detect cycles, then validates profitability
        """
        opportunities = []
        
        # Get all tokens in graph
        all_tokens = list(self.graph.nodes())
        
        # Prioritize stable/blue-chip starting points for capital efficiency
        priority_tokens = ['USDC', 'USDT', 'WETH', 'DAI', 'USDC.e']
        start_tokens = [t for t in priority_tokens if t in all_tokens] + \
                       [t for t in all_tokens if t not in priority_tokens]
        
        for start_token in start_tokens[:20]:  # Limit search space
            # Find cycles of length 2-4 (including return to start)
            for cycle_length in range(self.min_hops + 1, self.max_hops + 2):  # +1 because cycle includes return
                cycles = await self._find_cycles_of_length(start_token, cycle_length)
                
                for cycle in cycles:
                    # Validate cycle profitability
                    opportunity = await self._validate_cycle(cycle, start_amount_usd)
                    if opportunity and opportunity.path.net_profit_usd > self.min_cycle_profit_usd:
                        opportunities.append(opportunity)
        
        # Sort by net profit descending
        opportunities.sort(key=lambda x: x.path.net_profit_usd, reverse=True)
        return opportunities[:50]  # Return top 50
    
    async def _find_cycles_of_length(self, start_token: str, length: int) -> List[List[str]]:
        """Find all cycles starting from start_token with specific length"""
        cycles = []
        
        # Simple DFS to find cycles
        def dfs(current: str, path: List[str], remaining: int):
            if remaining == 0:
                if current == start_token and len(path) > 2:
                    cycles.append(path[:])
                return
            
            if current not in self.graph:
                return
            
            for neighbor in self.graph.successors(current):
                if neighbor not in path or (neighbor == start_token and remaining == 1):
                    path.append(neighbor)
                    dfs(neighbor, path, remaining - 1)
                    path.pop()
        
        dfs(start_token, [start_token], length - 1)
        return cycles
    
    async def _validate_cycle(self, cycle: List[str], start_amount_usd: float) -> Optional[TriangularOpportunity]:
        """Validate if cycle is profitable after gas costs"""
        if len(cycle) < 3:  # Must have at least 2 hops + return
            return None
        
        # Simulate execution
        current_amount = start_amount_usd
        hop_amounts = [current_amount]
        hop_prices = []
        hop_dexes = []
        execution_route = []
        
        for i in range(len(cycle) - 1):
            token_in = cycle[i]
            token_out = cycle[i + 1]
            
            # Get best quote for this hop
            pair = (token_in, token_out)
            if pair not in self.token_pairs or not self.token_pairs[pair]:
                return None  # No liquidity for this hop
            
            # Select best DEX for this hop
            best_quote = max(self.token_pairs[pair], key=lambda x: x['amount_out'])
            
            # Calculate output amount
            output_amount = current_amount * best_quote['price']
            
            hop_amounts.append(output_amount)
            hop_prices.append(best_quote['price'])
            hop_dexes.append(best_quote['dex'])
            execution_route.append({
                'token_in': token_in,
                'token_out': token_out,
                'dex': best_quote['dex'],
                'amount_in': current_amount,
                'amount_out': output_amount,
                'pool': best_quote['quote'].pool_address if hasattr(best_quote['quote'], 'pool_address') else None
            })
            
            current_amount = output_amount
        
        # Calculate profit
        final_amount = current_amount
        gross_profit = final_amount - start_amount_usd
        
        # Estimate gas cost
        num_hops = len(cycle) - 1
        gas_cost = self._estimate_gas_cost(num_hops)
        
        net_profit = gross_profit - gas_cost
        profit_bps = int((net_profit / start_amount_usd) * 10000) if start_amount_usd > 0 else 0
        
        if net_profit <= 0:
            return None
        
        # Calculate confidence score (simple heuristic)
        liquidity_scores = [q['liquidity'] / 10000 for q in 
                           [max(self.token_pairs[(cycle[i], cycle[i+1])], key=lambda x: x['liquidity']) 
                            for i in range(len(cycle) - 1)]]
        avg_liquidity_score = sum(liquidity_scores) / len(liquidity_scores) if liquidity_scores else 0
        confidence = min(100, max(0, avg_liquidity_score * 100))
        
        # Build HopPath
        path = HopPath(
            tokens=cycle,
            dexes=hop_dexes,
            amounts=hop_amounts,
            prices=hop_prices,
            profit_usd=gross_profit,
            profit_bps=profit_bps,
            gas_cost_usd=gas_cost,
            net_profit_usd=net_profit,
            total_hops=num_hops,
            execution_route=execution_route
        )
        
        # Determine priority
        if net_profit > 1.0:
            priority = "CRITICAL"
        elif net_profit > 0.5:
            priority = "HIGH"
        elif net_profit > 0.2:
            priority = "MEDIUM"
        else:
            priority = "LOW"
        
        return TriangularOpportunity(
            path=path,
            confidence_score=confidence,
            liquidity_depth={cycle[i]: liquidity_scores[i] for i in range(len(liquidity_scores))},
            slippage_estimate=0.5,  # 0.5% slippage estimate
            execution_time_ms=num_hops * 200,  # 200ms per hop
            timestamp=datetime.now(),
            priority=priority
        )
    
    def _estimate_gas_cost(self, num_hops: int) -> float:
        """Estimate gas cost in USD for multi-hop trade"""
        total_gas = num_hops * self.max_gas_per_hop
        gas_cost_eth = (total_gas * self.base_gas_price_gwei) / 1e9
        eth_price_usd = 3000  # Approximate ETH price
        return gas_cost_eth * eth_price_usd
    
    def format_opportunity(self, opp: TriangularOpportunity) -> str:
        """Format triangular opportunity for display"""
        path_str = " → ".join(opp.path.tokens)
        dex_str = " → ".join(opp.path.dexes)
        return f"""
🔺 TRIANGULAR ARBITRAGE
Path: {path_str}
DEXes: {dex_str}
Start: ${opp.path.amounts[0]:.2f}
End: ${opp.path.amounts[-1]:.2f}
Gross Profit: ${opp.path.profit_usd:.4f} ({opp.path.profit_bps} bps)
Gas Cost: ${opp.path.gas_cost_usd:.4f}
Net Profit: ${opp.path.net_profit_usd:.4f}
Confidence: {opp.confidence_score:.1f}%
Priority: {opp.priority}
Hops: {opp.path.total_hops}
"""

import os
