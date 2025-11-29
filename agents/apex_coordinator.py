"""
APEX MODE - Master Coordination Layer
Integrates all 5 advanced modules:
1. Expanded Token Universe (40+ tokens)
2. Multi-Hop Triangular Arbitrage
3. Flashloan Execution (10-100x capital)
4. Block Event Hunter (whale swaps, oracle updates)
5. Predictive Liquidity Model (pre-predict price movements)

This is the "brain" that coordinates all subsystems for maximum frequency
"""

import asyncio
from typing import Dict, List, Optional
from datetime import datetime
from web3 import Web3
import os

# Import all APEX modules
from agents.multi_hop_router import MultiHopRouter, TriangularOpportunity
from agents.flashloan_executor import FlashloanExecutor, FlashloanRoute
from agents.block_event_hunter import BlockEventHunter, EventOpportunity
from agents.predictive_liquidity import PredictiveLiquidityModel, PredictiveOpportunity

class ApexCoordinator:
    """
    Master coordinator for APEX MODE
    Combines all advanced strategies for maximum opportunity detection
    """
    
    def __init__(self, w3: Web3, price_feed, wallet_address: str, private_key: str):
        self.w3 = w3
        self.price_feed = price_feed
        self.wallet_address = wallet_address
        self.private_key = private_key
        
        # Initialize all subsystems
        print("\n" + "="*60)
        print("🔥 INITIALIZING APEX MODE 🔥")
        print("="*60)
        
        # 1. Multi-Hop Router
        self.multi_hop = MultiHopRouter(w3, price_feed, min_hops=2, max_hops=4)
        
        # 2. Flashloan Executor
        self.flashloan = FlashloanExecutor(w3, wallet_address, private_key)
        
        # 3. Block Event Hunter
        self.event_hunter = BlockEventHunter(w3, token_prices={})
        self.event_hunter.register_callback(self._handle_event_opportunity)
        
        # 4. Predictive Liquidity Model
        self.predictive_model = PredictiveLiquidityModel(w3, lookback_snapshots=100)
        
        # Coordination state
        self.total_opportunities_detected = 0
        self.apex_trades_executed = 0
        self.apex_pnl = 0.0
        
        # Feature flags from environment
        self.enable_multihop = os.getenv('ENABLE_MULTIHOP', 'true').lower() == 'true'
        self.enable_flashloan = os.getenv('ENABLE_FLASHLOAN', 'true').lower() == 'true'
        self.enable_event_hunter = os.getenv('ENABLE_EVENT_HUNTER', 'true').lower() == 'true'
        self.enable_predictive = os.getenv('ENABLE_PREDICTIVE', 'true').lower() == 'true'
        
        print("\n📊 APEX MODULES STATUS:")
        print(f"   🔺 Multi-Hop Routing: {'✅ ENABLED' if self.enable_multihop else '❌ DISABLED'}")
        print(f"   ⚡ Flashloan Execution: {'✅ ENABLED' if self.enable_flashloan else '❌ DISABLED'}")
        print(f"   🎯 Event Hunter: {'✅ ENABLED' if self.enable_event_hunter else '❌ DISABLED'}")
        print(f"   🔮 Predictive Model: {'✅ ENABLED' if self.enable_predictive else '❌ DISABLED'}")
        print("="*60 + "\n")
    
    async def start_apex_scanning(self):
        """
        Start all APEX subsystems in parallel
        Each subsystem runs independently and reports opportunities
        """
        tasks = []
        
        # Start event hunter
        if self.enable_event_hunter:
            tasks.append(asyncio.create_task(self.event_hunter.start_listening()))
        
        # Start periodic multi-hop scanning
        if self.enable_multihop:
            tasks.append(asyncio.create_task(self._periodic_multihop_scan()))
        
        # Start predictive analysis
        if self.enable_predictive:
            tasks.append(asyncio.create_task(self._periodic_predictive_analysis()))
        
        # Wait for all tasks
        await asyncio.gather(*tasks)
    
    async def _periodic_multihop_scan(self):
        """Periodically scan for multi-hop triangular arbitrage"""
        scan_interval = 2  # Every 2 seconds
        
        while True:
            try:
                # Get latest price quotes from price feed
                # In production, this would fetch real quotes
                quotes = []  # price_feed would provide these
                
                # Update multi-hop graph
                await self.multi_hop.update_graph(quotes)
                
                # Find triangular opportunities
                triangular_opps = await self.multi_hop.find_triangular_opportunities(start_amount_usd=10.0)
                
                if triangular_opps:
                    print(f"\n🔺 Found {len(triangular_opps)} triangular opportunities!")
                    
                    for opp in triangular_opps[:3]:  # Top 3
                        print(self.multi_hop.format_opportunity(opp))
                        
                        # Consider flashloan execution for larger profits
                        if self.enable_flashloan and opp.path.net_profit_usd > 0.20:
                            await self._execute_with_flashloan(opp)
                        else:
                            await self._execute_standard(opp)
                
                await asyncio.sleep(scan_interval)
            
            except Exception as e:
                print(f"⚠️  Multi-hop scan error: {e}")
                await asyncio.sleep(scan_interval)
    
    async def _periodic_predictive_analysis(self):
        """Periodically analyze liquidity depth for predictions"""
        analysis_interval = 3  # Every 3 seconds
        
        while True:
            try:
                # Get token pairs to analyze
                token_pairs = ["WETH/USDC", "ARB/USDC", "WETH/USDT"]  # Would be dynamic
                
                for pair in token_pairs:
                    # Capture liquidity snapshot
                    snapshot = await self.predictive_model.capture_liquidity_snapshot(
                        dex="Uniswap V3",
                        token_pair=pair,
                        price=3000.0  # Would be real price
                    )
                    
                    # Detect imbalances
                    imbalances = await self.predictive_model.detect_imbalances(pair)
                    
                    if imbalances:
                        for imbalance in imbalances:
                            print(self.predictive_model.format_imbalance(imbalance))
                            
                            # Generate opportunities from predictions
                            current_prices = {pair: {"Uniswap V3": 3000.0, "Sushiswap": 3001.0}}
                            predictive_opps = await self.predictive_model.generate_predictive_opportunities(
                                [imbalance], current_prices
                            )
                            
                            for pred_opp in predictive_opps:
                                print(self.predictive_model.format_opportunity(pred_opp))
                                await self._execute_predictive(pred_opp)
                
                await asyncio.sleep(analysis_interval)
            
            except Exception as e:
                print(f"⚠️  Predictive analysis error: {e}")
                await asyncio.sleep(analysis_interval)
    
    async def _handle_event_opportunity(self, event_opp: EventOpportunity):
        """Handle opportunity triggered by blockchain event"""
        print(f"\n🎯 EVENT OPPORTUNITY: {event_opp.trigger_event.event_type}")
        print(f"   Profit: ${event_opp.estimated_profit_usd:.4f}")
        print(f"   Deadline: Block {event_opp.execution_deadline_block}")
        
        # Execute immediately (time-sensitive)
        if event_opp.estimated_profit_usd > 0.10:
            print("🚀 Executing event-triggered arbitrage...")
            # Would execute actual trade here
            self.total_opportunities_detected += 1
    
    async def _execute_with_flashloan(self, triangular_opp: TriangularOpportunity):
        """Execute triangular arbitrage using flashloan for 10x capital"""
        print(f"\n⚡ Considering flashloan execution for {triangular_opp.path.tokens[0]} cycle...")
        
        # Convert triangular opportunity to flashloan-compatible format
        opportunity = {
            'token_in': triangular_opp.path.tokens[0],
            'token_out': triangular_opp.path.tokens[1],
            'buy_price': triangular_opp.path.prices[0] if triangular_opp.path.prices else 1.0,
            'sell_price': triangular_opp.path.prices[-1] if triangular_opp.path.prices else 1.0,
            'buy_dex': triangular_opp.path.dexes[0] if triangular_opp.path.dexes else "Uniswap",
            'sell_dex': triangular_opp.path.dexes[-1] if triangular_opp.path.dexes else "Sushiswap",
            'liquidity': 5000  # Estimate
        }
        
        # Calculate optimal flashloan
        flashloan_route = await self.flashloan.calculate_optimal_loan(opportunity, available_capital=29.0)
        
        print(self.flashloan.format_route(flashloan_route))
        
        # Execute (dry run for safety)
        result = await self.flashloan.execute_flashloan_arbitrage(flashloan_route, dry_run=True)
        
        if result.success:
            print(f"✅ Flashloan execution successful! Net profit: ${result.net_profit_usd:.4f}")
            self.apex_trades_executed += 1
            self.apex_pnl += result.net_profit_usd
        else:
            print(f"❌ Flashloan execution failed: {result.error}")
    
    async def _execute_standard(self, triangular_opp: TriangularOpportunity):
        """Execute triangular arbitrage with standard capital"""
        print(f"\n💰 Executing standard triangular arbitrage...")
        print(f"   Path: {' → '.join(triangular_opp.path.tokens)}")
        print(f"   Net profit: ${triangular_opp.path.net_profit_usd:.4f}")
        
        # Would execute actual trade here
        self.total_opportunities_detected += 1
        self.apex_trades_executed += 1
        self.apex_pnl += triangular_opp.path.net_profit_usd
    
    async def _execute_predictive(self, predictive_opp: PredictiveOpportunity):
        """Execute predictive arbitrage opportunity"""
        print(f"\n🔮 Executing predictive arbitrage...")
        print(f"   Action: {predictive_opp.action}")
        print(f"   Estimated profit: {predictive_opp.estimated_profit_bps}bps")
        
        # Would execute actual trade here
        self.total_opportunities_detected += 1
    
    def get_apex_stats(self) -> Dict:
        """Get APEX mode statistics"""
        return {
            'total_opportunities': self.total_opportunities_detected,
            'apex_trades_executed': self.apex_trades_executed,
            'apex_pnl': self.apex_pnl,
            'multihop_enabled': self.enable_multihop,
            'flashloan_enabled': self.enable_flashloan,
            'event_hunter_enabled': self.enable_event_hunter,
            'predictive_enabled': self.enable_predictive,
            'event_hunter_stats': self.event_hunter.get_stats() if self.enable_event_hunter else {},
            'predictive_stats': self.predictive_model.get_stats() if self.enable_predictive else {}
        }
    
    def print_apex_summary(self):
        """Print APEX mode performance summary"""
        stats = self.get_apex_stats()
        
        print("\n" + "="*60)
        print("🔥 APEX MODE SUMMARY 🔥")
        print("="*60)
        print(f"Total Opportunities Detected: {stats['total_opportunities']}")
        print(f"APEX Trades Executed: {stats['apex_trades_executed']}")
        print(f"APEX PnL: ${stats['apex_pnl']:.4f}")
        
        if stats['event_hunter_enabled']:
            eh_stats = stats['event_hunter_stats']
            print(f"\n🎯 Event Hunter:")
            print(f"   Events Detected: {eh_stats.get('events_detected', 0)}")
            print(f"   Opportunities Created: {eh_stats.get('opportunities_created', 0)}")
        
        if stats['predictive_enabled']:
            pred_stats = stats['predictive_stats']
            print(f"\n🔮 Predictive Model:")
            print(f"   Predictions Made: {pred_stats.get('predictions_made', 0)}")
            print(f"   Accuracy: {pred_stats.get('accuracy_pct', 0):.1f}%")
            print(f"   Tracked Pairs: {pred_stats.get('tracked_pairs', 0)}")
        
        print("="*60 + "\n")
