"""
Safety Controls and Risk Management
Automated circuit breakers, kill switches, and emergency procedures
"""

import json
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import asyncio

@dataclass
class RiskMetrics:
    """Current risk metrics"""
    total_capital: float
    current_equity: float
    total_pnl: float
    pnl_pct: float
    current_drawdown: float
    max_drawdown: float
    consecutive_losses: int
    hourly_loss: float
    daily_loss: float
    total_trades: int
    win_rate: float
    gas_spent: float

class RiskManager:
    """
    Monitors trading activity and enforces risk limits
    Automatic circuit breakers and emergency procedures
    """
    
    def __init__(self, config_path: str = "../config/aggressive_overnight_bots.json"):
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        # Initialize state
        self.initial_capital = self.config['capital_allocation']['active_trading_usd']
        self.current_equity = self.initial_capital
        self.trades: List[Dict] = []
        self.peak_equity = self.initial_capital
        self.emergency_shutdown_triggered = False
        
        # Risk limits
        self.limits = self.config['global_controls']['emergency_shutdown_triggers']
        
        # Tracking
        self.last_hour_start = datetime.utcnow()
        self.hourly_pnl = 0
        self.daily_pnl = 0
    
    def record_trade(self, trade_result: Dict):
        """Record a completed trade"""
        self.trades.append({
            'timestamp': datetime.utcnow(),
            'success': trade_result['success'],
            'pnl': trade_result['net_profit_usd'],
            'gas_cost': trade_result['gas_cost_usd']
        })
        
        # Update equity
        self.current_equity += trade_result['net_profit_usd']
        self.hourly_pnl += trade_result['net_profit_usd']
        self.daily_pnl += trade_result['net_profit_usd']
        
        # Update peak
        if self.current_equity > self.peak_equity:
            self.peak_equity = self.current_equity
    
    def get_risk_metrics(self) -> RiskMetrics:
        """Calculate current risk metrics"""
        total_pnl = self.current_equity - self.initial_capital
        pnl_pct = (total_pnl / self.initial_capital) * 100
        
        # Drawdown
        current_drawdown = self.current_equity - self.peak_equity
        max_drawdown = min([t['pnl'] for t in self.trades], default=0)
        max_dd_pct = (max_drawdown / self.initial_capital) * 100
        
        # Consecutive losses
        consecutive_losses = 0
        for trade in reversed(self.trades):
            if not trade['success']:
                consecutive_losses += 1
            else:
                break
        
        # Win rate
        if self.trades:
            wins = sum(1 for t in self.trades if t['success'])
            win_rate = (wins / len(self.trades)) * 100
        else:
            win_rate = 0
        
        # Gas spent
        gas_spent = sum(t['gas_cost'] for t in self.trades)
        
        return RiskMetrics(
            total_capital=self.initial_capital,
            current_equity=self.current_equity,
            total_pnl=total_pnl,
            pnl_pct=pnl_pct,
            current_drawdown=current_drawdown,
            max_drawdown=max_dd_pct,
            consecutive_losses=consecutive_losses,
            hourly_loss=self.hourly_pnl if self.hourly_pnl < 0 else 0,
            daily_loss=self.daily_pnl if self.daily_pnl < 0 else 0,
            total_trades=len(self.trades),
            win_rate=win_rate,
            gas_spent=gas_spent
        )
    
    def check_risk_limits(self) -> tuple[bool, List[str]]:
        """
        Check if any risk limits are breached
        
        Returns:
            (should_shutdown, list_of_violations)
        """
        metrics = self.get_risk_metrics()
        violations = []
        
        # Max portfolio drawdown
        if abs(metrics.max_drawdown) > self.limits['max_portfolio_drawdown_pct']:
            violations.append(f"Max drawdown exceeded: {metrics.max_drawdown:.1f}% > {self.limits['max_portfolio_drawdown_pct']}%")
        
        # Max hourly loss
        if abs(metrics.hourly_loss) > self.limits['max_hourly_loss_usd']:
            violations.append(f"Hourly loss limit exceeded: ${abs(metrics.hourly_loss):.2f} > ${self.limits['max_hourly_loss_usd']}")
        
        # Consecutive failed trades
        if metrics.consecutive_losses >= self.limits['consecutive_failed_trades']:
            violations.append(f"Too many consecutive losses: {metrics.consecutive_losses} >= {self.limits['consecutive_failed_trades']}")
        
        should_shutdown = len(violations) > 0
        
        return should_shutdown, violations
    
    def check_profit_targets(self) -> tuple[bool, str]:
        """
        Check if profit targets reached for size reduction or exit
        
        Returns:
            (should_act, action_type)
        """
        metrics = self.get_risk_metrics()
        profit_targets = self.config['global_controls']['profit_taking']
        
        if metrics.pnl_pct >= profit_targets['full_exit_at_profit_pct']:
            return True, "FULL_EXIT"
        elif metrics.pnl_pct >= profit_targets['reduce_size_at_profit_pct']:
            return True, "REDUCE_SIZE"
        
        return False, "NONE"
    
    async def emergency_shutdown(self, reason: str):
        """
        Execute emergency shutdown procedure
        """
        if self.emergency_shutdown_triggered:
            return  # Already shut down
        
        self.emergency_shutdown_triggered = True
        
        print("\n" + "="*80)
        print("🚨 EMERGENCY SHUTDOWN INITIATED")
        print("="*80)
        print(f"Reason: {reason}")
        print(f"Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print()
        
        # Log shutdown
        shutdown_log = {
            'timestamp': datetime.utcnow().isoformat(),
            'reason': reason,
            'metrics': {
                'total_trades': len(self.trades),
                'total_pnl': self.current_equity - self.initial_capital,
                'current_equity': self.current_equity
            }
        }
        
        with open('../logs/emergency_shutdowns.log', 'a') as f:
            f.write(json.dumps(shutdown_log) + '\n')
        
        print("✅ Shutdown logged")
        print("✅ All trading activity halted")
        print()
        print("⚠️  DO NOT RESTART without reviewing:")
        print("   1. Trade logs")
        print("   2. Error messages")
        print("   3. Market conditions")
        print("   4. Bot configurations")
        print("="*80)
    
    async def monitor_loop(self, check_interval_seconds: int = 30):
        """
        Continuous monitoring loop
        Checks risk limits periodically
        """
        print(f"🛡️  Risk monitor started (check interval: {check_interval_seconds}s)")
        
        while not self.emergency_shutdown_triggered:
            try:
                # Check risk limits
                should_shutdown, violations = self.check_risk_limits()
                
                if should_shutdown:
                    violation_msg = "; ".join(violations)
                    await self.emergency_shutdown(f"Risk limit breached: {violation_msg}")
                    break
                
                # Check profit targets
                should_act, action = self.check_profit_targets()
                
                if should_act:
                    metrics = self.get_risk_metrics()
                    print(f"\n💰 Profit target reached: {action}")
                    print(f"   Current P&L: ${metrics.total_pnl:.2f} ({metrics.pnl_pct:.2f}%)")
                    
                    if action == "FULL_EXIT":
                        await self.emergency_shutdown(f"Target profit reached: {metrics.pnl_pct:.2f}%")
                        break
                    elif action == "REDUCE_SIZE":
                        print(f"   Recommended: Reduce position sizes by 50%")
                
                # Reset hourly counter if needed
                if datetime.utcnow() - self.last_hour_start > timedelta(hours=1):
                    self.hourly_pnl = 0
                    self.last_hour_start = datetime.utcnow()
                
                await asyncio.sleep(check_interval_seconds)
                
            except Exception as e:
                print(f"❌ Error in risk monitor: {e}")
                await asyncio.sleep(5)
    
    def print_status(self):
        """Print current risk status"""
        metrics = self.get_risk_metrics()
        
        print("\n" + "="*80)
        print("🛡️  RISK MONITOR STATUS")
        print("="*80)
        print(f"Capital: ${metrics.total_capital:,.2f}")
        print(f"Current Equity: ${metrics.current_equity:,.2f}")
        print(f"Total P&L: ${metrics.total_pnl:,.2f} ({metrics.pnl_pct:+.2f}%)")
        print(f"Max Drawdown: {metrics.max_drawdown:.2f}% (Limit: {self.limits['max_portfolio_drawdown_pct']}%)")
        print(f"Consecutive Losses: {metrics.consecutive_losses} (Limit: {self.limits['consecutive_failed_trades']})")
        print(f"Hourly Loss: ${abs(metrics.hourly_loss):.2f} (Limit: ${self.limits['max_hourly_loss_usd']})")
        print(f"Total Trades: {metrics.total_trades}")
        print(f"Win Rate: {metrics.win_rate:.1f}%")
        print(f"Gas Spent: ${metrics.gas_spent:.2f}")
        print()
        
        # Status indicators
        should_shutdown, violations = self.check_risk_limits()
        
        if should_shutdown:
            print("🚨 STATUS: RISK LIMITS BREACHED")
            for v in violations:
                print(f"   ⚠️  {v}")
        else:
            print("✅ STATUS: All risk limits OK")
        
        print("="*80)


# Example usage
async def main():
    """Test risk manager"""
    risk_manager = RiskManager()
    
    print("🛡️  Risk Management System Initialized")
    risk_manager.print_status()
    
    # Simulate some trades
    print("\n📊 Simulating trades...")
    
    # Winning trade
    risk_manager.record_trade({
        'success': True,
        'net_profit_usd': 50,
        'gas_cost_usd': 2
    })
    
    # Losing trade
    risk_manager.record_trade({
        'success': False,
        'net_profit_usd': -30,
        'gas_cost_usd': 2
    })
    
    risk_manager.print_status()
    
    # Check limits
    should_shutdown, violations = risk_manager.check_risk_limits()
    if should_shutdown:
        print(f"\n🚨 Would trigger shutdown: {violations}")
    else:
        print("\n✅ All systems operational")

if __name__ == "__main__":
    asyncio.run(main())
