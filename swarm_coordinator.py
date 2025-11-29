"""
SWARM COORDINATOR
Master controller for the 5-agent profit generation swarm
"""

import sys
import time
import threading
from datetime import datetime
from queue import Queue
import importlib.util

# Import all agents
def import_agent(agent_file):
    """Dynamically import an agent module"""
    spec = importlib.util.spec_from_file_location("agent", agent_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SwarmCoordinator:
    """
    Swarm Coordinator
    
    Manages 5 profit-generating agents running in parallel:
    1. Premium Tracker - Price lag arbitrage
    2. Spread Compression - Mean reversion scalping
    3. Iceberg Sniper - Institutional order detection
    4. Tri-Loop Arbitrage - Currency triangulation
    5. Maker Rebate Farmer - Liquidity provision
    
    Features:
    - Parallel execution (all agents run simultaneously)
    - Capital allocation ($37 total, ~$7-8 per agent)
    - P&L aggregation
    - Performance monitoring
    - Emergency stop
    """
    
    def __init__(self, total_capital_usd=37.0, paper_mode=True):
        self.total_capital_usd = total_capital_usd
        self.paper_mode = paper_mode
        
        # Agent configurations
        self.agents = [
            {
                "name": "Agent 1: Premium Tracker",
                "file": "agents/agent1_premium_tracker.py",
                "class_name": "PremiumTrackerAgent",
                "capital": 8.0,
                "kwargs": {"capital_usd": 8.0, "min_lag_percent": 0.05, "paper_mode": paper_mode}
            },
            {
                "name": "Agent 2: Spread Compression",
                "file": "agents/agent2_spread_compression.py",
                "class_name": "SpreadCompressionAgent",
                "capital": 7.0,
                "kwargs": {"capital_usd": 7.0, "compression_threshold": 0.05, "paper_mode": paper_mode}
            },
            {
                "name": "Agent 3: Iceberg Sniper",
                "file": "agents/agent3_iceberg_sniper.py",
                "class_name": "IcebergSniperAgent",
                "capital": 7.0,
                "kwargs": {"capital_usd": 7.0, "min_refill_count": 3, "paper_mode": paper_mode}
            },
            {
                "name": "Agent 4: Tri-Loop Arbitrage",
                "file": "agents/agent4_tri_loop.py",
                "class_name": "TriLoopAgent",
                "capital": 7.0,
                "kwargs": {"capital_usd": 7.0, "min_profit_percent": 0.08, "paper_mode": paper_mode}
            },
            {
                "name": "Agent 5: Maker Rebate",
                "file": "agents/agent5_maker_rebate.py",
                "class_name": "MakerRebateAgent",
                "capital": 8.0,
                "kwargs": {"capital_usd": 8.0, "target_rebate_bps": 5, "paper_mode": paper_mode}
            }
        ]
        
        # State
        self.results = {}
        self.threads = []
        self.message_queue = Queue()
        self.emergency_stop = False
        
    def run_agent(self, agent_config, duration_seconds):
        """Run a single agent in a thread"""
        try:
            # Import agent module
            module = import_agent(agent_config["file"])
            agent_class = getattr(module, agent_config["class_name"])
            
            # Create agent instance
            agent = agent_class(**agent_config["kwargs"])
            
            # Run agent
            result = agent.run(duration_seconds=duration_seconds)
            
            # Store result
            self.results[agent_config["name"]] = result
            
        except Exception as e:
            print(f"\n❌ ERROR in {agent_config['name']}: {e}")
            self.results[agent_config["name"]] = {
                "agent": agent_config["name"],
                "error": str(e),
                "pnl_usd": 0.0
            }
    
    def run_swarm(self, duration_seconds=60):
        """Run all agents in parallel"""
        print("\n" + "="*80)
        print("🐝 PROFIT SWARM ACTIVATED")
        print("="*80)
        print(f"\nMode: {'PAPER TRADING' if self.paper_mode else '⚠️  LIVE TRADING'}")
        print(f"Total Capital: ${self.total_capital_usd}")
        print(f"Duration: {duration_seconds} seconds")
        print(f"Agents: {len(self.agents)}")
        print("\nCapital Allocation:")
        for agent in self.agents:
            print(f"   {agent['name']}: ${agent['capital']}")
        
        print(f"\n🚀 LAUNCHING AGENTS...")
        start_time = time.time()
        
        # Start all agents in parallel
        for agent_config in self.agents:
            thread = threading.Thread(
                target=self.run_agent,
                args=(agent_config, duration_seconds),
                daemon=True
            )
            thread.start()
            self.threads.append(thread)
            print(f"   ✓ {agent_config['name']} started")
        
        # Wait for all agents to complete
        print(f"\n⏳ Agents running for {duration_seconds} seconds...")
        for thread in self.threads:
            thread.join()
        
        elapsed = time.time() - start_time
        
        # Aggregate results
        print("\n" + "="*80)
        print("📊 SWARM PERFORMANCE REPORT")
        print("="*80)
        
        total_opportunities = 0
        total_trades = 0
        total_pnl = 0.0
        
        print("\nIndividual Agent Results:")
        print("-" * 80)
        
        for agent_config in self.agents:
            result = self.results.get(agent_config["name"], {})
            
            if "error" in result:
                print(f"\n{agent_config['name']}: ❌ FAILED")
                print(f"   Error: {result['error']}")
                continue
            
            opportunities = result.get("opportunities", 0)
            trades = result.get("trades", 0)
            pnl = result.get("pnl_usd", 0.0)
            
            total_opportunities += opportunities
            total_trades += trades
            total_pnl += pnl
            
            roi = (pnl / agent_config["capital"]) * 100 if agent_config["capital"] > 0 else 0
            
            print(f"\n{agent_config['name']}:")
            print(f"   Capital: ${agent_config['capital']}")
            print(f"   Opportunities: {opportunities}")
            print(f"   Trades: {trades}")
            print(f"   P&L: ${pnl:.3f}")
            print(f"   ROI: {roi:.2f}%")
        
        # Summary
        print("\n" + "="*80)
        print("SWARM SUMMARY")
        print("="*80)
        
        total_roi = (total_pnl / self.total_capital_usd) * 100 if self.total_capital_usd > 0 else 0
        hourly_pnl = (total_pnl / elapsed) * 3600 if elapsed > 0 else 0
        
        print(f"\nTotal Capital: ${self.total_capital_usd}")
        print(f"Total Opportunities: {total_opportunities}")
        print(f"Total Trades: {total_trades}")
        print(f"Total P&L: ${total_pnl:.3f}")
        print(f"Total ROI: {total_roi:.2f}%")
        print(f"Hourly P&L (projected): ${hourly_pnl:.3f}/hour")
        print(f"Elapsed Time: {elapsed:.1f}s")
        
        if self.paper_mode:
            print("\n" + "="*80)
            print("⚠️  NOTE: This was a PAPER TRADING simulation")
            print("="*80)
            print("\nTo run LIVE:")
            print("   1. Verify all agents are working correctly")
            print("   2. Ensure Kraken API has trading permissions")
            print("   3. Set paper_mode=False in SwarmCoordinator")
            print("   4. Start with small capital ($10-20) to test")
        
        return {
            "total_capital": self.total_capital_usd,
            "total_opportunities": total_opportunities,
            "total_trades": total_trades,
            "total_pnl": total_pnl,
            "total_roi": total_roi,
            "hourly_pnl": hourly_pnl,
            "elapsed": elapsed,
            "individual_results": self.results
        }


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Multi-Strategy Profit Swarm")
    parser.add_argument("--duration", type=int, default=60, help="Duration in seconds (default: 60)")
    parser.add_argument("--capital", type=float, default=37.0, help="Total capital in USD (default: 37)")
    parser.add_argument("--live", action="store_true", help="Run in LIVE mode (default: paper mode)")
    
    args = parser.parse_args()
    
    # Create coordinator
    coordinator = SwarmCoordinator(
        total_capital_usd=args.capital,
        paper_mode=not args.live
    )
    
    # Run swarm
    results = coordinator.run_swarm(duration_seconds=args.duration)
    
    return results


if __name__ == "__main__":
    main()
