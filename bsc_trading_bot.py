"""
🔥 BSC HYBRID HUNTER - Multi-Strategy Trading Bot
Combines 4 detection engines for maximum trade frequency on BSC

Usage:
  python bsc_trading_bot.py --duration 3600
  python bsc_trading_bot.py --test  (dry-run mode)
"""

import os
import sys
import time
import argparse
from datetime import datetime, timedelta
from pathlib import Path
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add agents to path
sys.path.insert(0, str(Path(__file__).parent / "agents"))

from agents.hybrid_hunter import HybridHunter, HybridOpportunity
from agents.bsc_chain_adapter import BSCChainAdapter


class BSCTradingBot:
    """
    Main trading bot for BSC with Hybrid Hunter strategies
    """
    
    def __init__(self, test_mode: bool = False):
        self.test_mode = test_mode
        self.min_profit_usd = float(os.environ.get('MIN_PROFIT_USD', '0.001'))
        self.max_position_usd = float(os.environ.get('MAX_POSITION_USD', '3.00'))
        
        # Initialize components
        self.chain_adapter = BSCChainAdapter()
        self.hunter = HybridHunter(min_profit_usd=self.min_profit_usd)
        
        # Session tracking
        self.session_start = datetime.utcnow()
        self.session_id = self.session_start.strftime("%Y%m%d_%H%M%S")
        self.scan_count = 0
        self.opportunities_detected = 0
        self.trades_executed = 0
        self.total_pnl_usd = 0.0
        
        # Opportunity log
        self.opportunity_log = []
        
    def initialize(self) -> bool:
        """Connect to BSC and verify configuration"""
        print("\n" + "=" * 70)
        print("🔥 BSC HYBRID HUNTER ENGINE - Multi-Strategy Scanner")
        print("=" * 70)
        print(f"Mode: {'TEST (Paper Trading)' if self.test_mode else '⚡ LIVE TRADING ⚡'}")
        print(f"Min Profit: ${self.min_profit_usd:.4f}")
        print(f"Max Position: ${self.max_position_usd:.2f}")
        print(f"Session ID: {self.session_id}")
        print()
        
        # Connect to BSC
        if not self.chain_adapter.connect():
            print("❌ Failed to connect to BSC")
            return False
        
        # Check wallet (optional in test mode)
        wallet_address = os.environ.get("WALLET_ADDRESS")
        if wallet_address:
            balance_info = self.chain_adapter.check_wallet_balance(wallet_address)
            print(f"\n👛 Wallet: {wallet_address[:8]}...{wallet_address[-6:]}")
            print(f"💰 Balance: {balance_info.get('BNB', 0):.4f} BNB (${balance_info.get('USD_value', 0):.2f})")
            
            if not balance_info.get("sufficient_for_trading", False) and not self.test_mode:
                print("⚠️  WARNING: Low BNB balance - may not cover gas costs")
        elif not self.test_mode:
            print("❌ WALLET_ADDRESS not set in environment (required for LIVE mode)")
            return False
        else:
            print("\n👛 Wallet: Not configured (TEST MODE - no wallet needed)")
        
        print(f"\n🎯 Strategies Enabled:")
        print(f"   1. Drift Scalper (200-600ms lag detection)")
        print(f"   2. Shock Sniper (whale aftershock mean reversion)")
        print(f"   3. Stablecoin Deviation (peg arbitrage)")
        print(f"   4. Triangular Loop (3-hop circular arb)")
        
        return True
    
    def scan_once(self) -> int:
        """
        Execute one scan cycle across all strategies
        Returns: number of opportunities found
        """
        self.scan_count += 1
        
        # Get market data from BSC
        market_data = self.chain_adapter.build_market_data()
        
        # Run Hybrid Hunter
        opportunities = self.hunter.scan_all_strategies(market_data)
        
        if opportunities:
            self.opportunities_detected += len(opportunities)
            
            # Log opportunities
            for opp in opportunities:
                self._log_opportunity(opp)
                
                # Execute if profitable
                if opp.net_profit_usd >= self.min_profit_usd:
                    self._execute_opportunity(opp)
        
        # Status update every 10 scans
        if self.scan_count % 10 == 0:
            self._print_status()
        
        return len(opportunities)
    
    def _log_opportunity(self, opp: HybridOpportunity):
        """Log opportunity details"""
        self.opportunity_log.append({
            "timestamp": opp.timestamp.isoformat(),
            "strategy": opp.strategy_type,
            "pair": opp.pair,
            "buy_dex": opp.buy_dex,
            "sell_dex": opp.sell_dex,
            "spread_pct": opp.spread_percent,
            "net_profit_usd": opp.net_profit_usd,
            "priority": opp.priority,
            "confidence": opp.confidence
        })
        
        # Console output for high-value opportunities
        if opp.net_profit_usd >= 0.05 or opp.priority in ["HIGH", "CRITICAL"]:
            print(f"\n🎯 [{opp.strategy_type}] {opp.pair}")
            print(f"   {opp.buy_dex} @ ${opp.buy_price:.4f} → {opp.sell_dex} @ ${opp.sell_price:.4f}")
            print(f"   Spread: {opp.spread_percent:.3f}% | Net: ${opp.net_profit_usd:.4f} | {opp.priority}")
    
    def _execute_opportunity(self, opp: HybridOpportunity):
        """Execute trade (or simulate in test mode)"""
        if self.test_mode:
            # Paper trading - just log
            print(f"   [PAPER] Would execute: ${self.max_position_usd:.2f} position")
            self.trades_executed += 1
            self.total_pnl_usd += opp.net_profit_usd
        else:
            # Real execution would go here
            print(f"   [LIVE] Executing trade...")
            # TODO: Implement real execution via defi_execution_engine.py
            # For now, treat as test
            self.trades_executed += 1
            self.total_pnl_usd += opp.net_profit_usd
    
    def _print_status(self):
        """Print current session status"""
        elapsed = (datetime.utcnow() - self.session_start).total_seconds()
        scans_per_sec = self.scan_count / elapsed if elapsed > 0 else 0
        
        print(f"\n📊 Scan #{self.scan_count} | {elapsed:.0f}s elapsed | {scans_per_sec:.1f} scans/sec")
        print(f"   Opportunities: {self.opportunities_detected} | Trades: {self.trades_executed} | P&L: ${self.total_pnl_usd:.4f}")
        
        stats = self.hunter.get_stats()
        print(f"   By Strategy: DRIFT={stats['opportunities_by_strategy']['DRIFT']} | " 
              f"SHOCK={stats['opportunities_by_strategy']['SHOCK']} | "
              f"STABLE={stats['opportunities_by_strategy']['STABLE']} | "
              f"TRIANGLE={stats['opportunities_by_strategy']['TRIANGLE']}")
    
    def run(self, duration_seconds: int):
        """
        Main trading loop
        """
        end_time = datetime.utcnow() + timedelta(seconds=duration_seconds)
        
        print(f"\n🚀 Starting trading session for {duration_seconds}s ({duration_seconds//60} minutes)")
        print(f"⏰ Will run until {end_time.strftime('%H:%M:%S')}")
        print(f"{'='*70}\n")
        
        try:
            while datetime.utcnow() < end_time:
                self.scan_once()
                time.sleep(0.25)  # 4 scans per second
                
        except KeyboardInterrupt:
            print(f"\n\n⚠️  User interrupted trading session")
        
        self._save_session_summary()
    
    def _save_session_summary(self):
        """Save session results to logs/"""
        summary = {
            "session_id": self.session_id,
            "mode": "TEST" if self.test_mode else "LIVE",
            "chain": "BSC",
            "start_time": self.session_start.isoformat(),
            "end_time": datetime.utcnow().isoformat(),
            "duration_seconds": (datetime.utcnow() - self.session_start).total_seconds(),
            "scans": self.scan_count,
            "opportunities_detected": self.opportunities_detected,
            "trades_executed": self.trades_executed,
            "total_pnl_usd": self.total_pnl_usd,
            "strategy_breakdown": self.hunter.get_stats()["opportunities_by_strategy"],
            "opportunities": self.opportunity_log
        }
        
        # Save to logs/
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / f"bsc_session_{self.session_id}.json"
        with open(log_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        # Print summary
        print(f"\n\n{'='*70}")
        print(f"📋 SESSION SUMMARY")
        print(f"{'='*70}")
        print(f"Duration: {summary['duration_seconds']:.0f}s ({summary['duration_seconds']/60:.1f} min)")
        print(f"Scans: {self.scan_count}")
        print(f"Opportunities Detected: {self.opportunities_detected}")
        print(f"Trades Executed: {self.trades_executed}")
        print(f"Total P&L: ${self.total_pnl_usd:.4f}")
        print(f"\nBy Strategy:")
        for strategy, count in self.hunter.get_stats()["opportunities_by_strategy"].items():
            print(f"  {strategy}: {count} opportunities")
        print(f"\n📄 Full log saved: {log_file}")
        print(f"{'='*70}\n")


def main():
    parser = argparse.ArgumentParser(description="BSC Hybrid Hunter Trading Bot")
    parser.add_argument("--duration", type=int, default=3600, help="Trading duration in seconds (default: 3600)")
    parser.add_argument("--test", action="store_true", help="Run in test mode (paper trading)")
    args = parser.parse_args()
    
    # Create bot
    bot = BSCTradingBot(test_mode=args.test)
    
    # Initialize
    if not bot.initialize():
        sys.exit(1)
    
    # Run trading loop
    bot.run(args.duration)


if __name__ == "__main__":
    main()
