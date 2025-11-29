#!/usr/bin/env python3
"""
🤖 AUTONOMOUS MASTER CONTROLLER
State-of-the-art autonomous trading orchestration
Coordinates ALL subsystems for fully hands-free operation
"""

import os
import sys
import json
import asyncio
import signal
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, List
from dataclasses import dataclass, asdict

# Ensure project imports work
sys.path.insert(0, str(Path(__file__).parent))

from agents.defi_price_feed import DeFiPriceFeed
from agents.defi_execution_engine import DeFiExecutionEngine
from agents.trading_supervisor import TradingSupervisor
from agents.mcp_intelligence import MCPIntelligence
from agents.swarm_coordinator import SwarmCoordinator
from agents.intel_ingestor import IntelIngestor
from agents.risk_guardian import RiskGuardian
from agents.gas_sentinel import GasSentinel
from agents.liquidity_monitor import LiquidityMonitor
from agents.flash_crash_detector import FlashCrashDetector
from agents.professional_risk_manager import ProfessionalRiskManager
from agents.smart_executor import SmartExecutor
from agents.position_monitor import PositionMonitor

# APEX subsystems
from agents.apex_coordinator import ApexCoordinator
from agents.multi_hop_router import MultiHopRouter
from agents.flashloan_executor import FlashloanExecutor
from agents.block_event_hunter import BlockEventHunter
from agents.predictive_liquidity import PredictiveLiquidity

# Monitoring
from agents.oracle_validator import OracleValidator
from agents.price_validator import PriceValidator
from agents.smart_money_tracker import SmartMoneyTracker
from agents.whale_shadow_trader import WhaleShadowTrader
from agents.volume_spike_scanner import VolumeSpikeScanner
from agents.strategy_reverse_engineer import StrategyReverseEngineer


@dataclass
class SystemHealth:
    """Comprehensive system health metrics"""
    timestamp: str
    uptime_seconds: float
    total_opportunities: int
    total_trades: int
    session_pnl_usd: float
    win_rate: float
    gas_efficiency: float
    rpc_health: str
    intelligence_status: Dict[str, bool]
    risk_status: str
    subsystem_status: Dict[str, str]
    
    def to_dict(self):
        return asdict(self)


class AutonomousMaster:
    """
    Master orchestration controller for fully autonomous trading
    Manages all subsystems, health monitoring, and automatic recovery
    """
    
    def __init__(self):
        self.running = False
        self.start_time = datetime.now(timezone.utc)
        
        # Load environment
        self._load_env()
        
        # Initialize Web3
        from agents.rpc_utils import get_arbitrum_w3
        self.w3 = get_arbitrum_w3()
        
        # Statistics
        self.total_opportunities = 0
        self.total_trades = 0
        self.successful_trades = 0
        self.total_pnl_usd = 0.0
        self.total_gas_usd = 0.0
        
        # Subsystems (initialized in setup)
        self.price_feed: Optional[DeFiPriceFeed] = None
        self.execution_engine: Optional[DeFiExecutionEngine] = None
        self.supervisor: Optional[TradingSupervisor] = None
        self.mcp: Optional[MCPIntelligence] = None
        self.swarm: Optional[SwarmCoordinator] = None
        self.intel_ingestor: Optional[IntelIngestor] = None
        self.risk_guardian: Optional[RiskGuardian] = None
        self.gas_sentinel: Optional[GasSentinel] = None
        self.liquidity_monitor: Optional[LiquidityMonitor] = None
        self.flash_crash_detector: Optional[FlashCrashDetector] = None
        self.risk_manager: Optional[ProfessionalRiskManager] = None
        self.smart_executor: Optional[SmartExecutor] = None
        self.position_monitor: Optional[PositionMonitor] = None
        
        # APEX subsystems
        self.apex_coordinator: Optional[ApexCoordinator] = None
        self.multi_hop_router: Optional[MultiHopRouter] = None
        self.flashloan_executor: Optional[FlashloanExecutor] = None
        self.event_hunter: Optional[BlockEventHunter] = None
        self.predictive_liquidity: Optional[PredictiveLiquidity] = None
        
        # Advanced trackers
        self.oracle_validator: Optional[OracleValidator] = None
        self.price_validator: Optional[PriceValidator] = None
        self.smart_money_tracker: Optional[SmartMoneyTracker] = None
        self.whale_shadow: Optional[WhaleShadowTracker] = None
        self.volume_spike: Optional[VolumeSpikeScanner] = None
        self.strategy_analyzer: Optional[StrategyReverseEngineer] = None
        
        # Health tracking
        self.last_health_check = datetime.now(timezone.utc)
        self.health_check_interval = 30  # seconds
        
        # Signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _load_env(self):
        """Load environment configuration"""
        env_file = Path(__file__).parent / '.env'
        if env_file.exists():
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip()
        
        # Verify critical config
        self.trading_mode = os.getenv('TRADING_MODE', 'PAPER').upper()
        self.paper_mode = os.getenv('ENABLE_PAPER_MODE', 'false').lower() == 'true'
        self.wallet_address = os.getenv('WALLET_ADDRESS')
        self.wallet_private_key = os.getenv('WALLET_PRIVATE_KEY')
        
        if self.trading_mode == 'LIVE' and not self.wallet_private_key:
            raise ValueError("LIVE mode requires WALLET_PRIVATE_KEY in .env")
        
        # Intelligence flags
        self.enable_mcp = os.getenv('ENABLE_MCP', 'true').lower() == 'true'
        self.enable_swarm = os.getenv('ENABLE_SWARM', 'true').lower() == 'true'
        self.enable_intel_ingestor = os.getenv('ENABLE_INTEL_INGESTOR', 'true').lower() == 'true'
        
        # APEX flags
        self.enable_apex = os.getenv('ENABLE_APEX_MODE', 'true').lower() == 'true'
        self.enable_multihop = os.getenv('ENABLE_MULTIHOP', 'true').lower() == 'true'
        self.enable_flashloan = os.getenv('ENABLE_FLASHLOAN', 'true').lower() == 'true'
        self.enable_event_hunter = os.getenv('ENABLE_EVENT_HUNTER', 'true').lower() == 'true'
        self.enable_predictive = os.getenv('ENABLE_PREDICTIVE', 'true').lower() == 'true'
        
        # Trading parameters
        self.max_position_usd = float(os.getenv('MAX_POSITION_USD', '15.0'))
        self.min_profit_usd = float(os.getenv('MIN_PROFIT_USD', '0.02'))
        self.scan_interval_ms = int(os.getenv('SCAN_INTERVAL_MS', '250'))
        self.max_gas_gwei = float(os.getenv('MAX_GAS_GWEI', '0.020'))
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        print(f"\n🛑 Received shutdown signal {signum}")
        self.stop()
    
    async def initialize_subsystems(self):
        """Initialize all trading subsystems"""
        print("🚀 Initializing Autonomous Master Controller...")
        print("=" * 80)
        
        # Core trading components
        print("\n📊 Initializing Core Trading Components...")
        self.price_feed = DeFiPriceFeed(
            chain="ARBITRUM",
            rpc_url=os.getenv('ARB_RPC_1'),
            enable_mcp=self.enable_mcp
        )
        
        self.execution_engine = DeFiExecutionEngine(
            chain="ARBITRUM",
            paper_mode=self.paper_mode,
            rpc_url=None,
            private_key=self.wallet_private_key if not self.paper_mode else None
        )
        
        self.supervisor = TradingSupervisor(
            w3=self.w3,
            wallet_address=self.wallet_address,
            telegram_bot_token=os.getenv('TELEGRAM_BOT_TOKEN'),
            telegram_chat_id=os.getenv('TELEGRAM_CHAT_ID'),
            discord_webhook_url=os.getenv('DISCORD_WEBHOOK_URL'),
            max_drawdown_pct=15.0
        )
        
        # Intelligence layer
        if self.enable_mcp or self.enable_swarm or self.enable_intel_ingestor:
            print("\n🧠 Initializing Intelligence Layer...")
            
            if self.enable_mcp:
                self.mcp = MCPIntelligence(
                    confidence_threshold=float(os.getenv('MCP_CONFIDENCE_THRESHOLD', '0.55'))
                )
                print("  ✓ MCP Intelligence Online")
            
            if self.enable_swarm:
                self.swarm = SwarmCoordinator(
                    required_agreement=int(os.getenv('SWARM_REQUIRED_AGREEMENT', '2'))
                )
                print("  ✓ Swarm Intelligence Online")
            
            if self.enable_intel_ingestor:
                self.intel_ingestor = IntelIngestor()
                print("  ✓ Intel Ingestor Online")
        
        # Risk & Safety layer
        print("\n🛡️  Initializing Risk & Safety Layer...")
        self.risk_guardian = RiskGuardian(
            max_position_usd=self.max_position_usd,
            max_daily_loss_pct=3.0,
            max_session_loss_pct=1.0
        )
        
        self.gas_sentinel = GasSentinel(
            max_gas_gwei=self.max_gas_gwei,
            target_gas_gwei=self.max_gas_gwei * 0.5
        )
        
        self.liquidity_monitor = LiquidityMonitor(min_liquidity_usd=50000.0)
        self.flash_crash_detector = FlashCrashDetector(volatility_threshold=10.0)
        
        self.risk_manager = ProfessionalRiskManager(
            max_position_size_usd=self.max_position_usd,
            max_portfolio_risk_pct=5.0
        )
        
        print("  ✓ Risk Guardian Active")
        print("  ✓ Gas Sentinel Active")
        print("  ✓ Liquidity Monitor Active")
        print("  ✓ Flash Crash Detector Active")
        print("  ✓ Professional Risk Manager Active")
        
        # Execution layer
        print("\n⚡ Initializing Smart Execution Layer...")
        self.smart_executor = SmartExecutor(
            execution_engine=self.execution_engine,
            gas_sentinel=self.gas_sentinel
        )
        
        self.position_monitor = PositionMonitor(
            wallet_address=self.wallet_address,
            w3=self.w3
        )
        
        print("  ✓ Smart Executor Ready")
        print("  ✓ Position Monitor Active")
        
        # APEX subsystems
        if self.enable_apex:
            print("\n🔥 Initializing APEX Mode Subsystems...")
            
            self.apex_coordinator = ApexCoordinator()
            print("  ✓ APEX Coordinator Online")
            
            if self.enable_multihop:
                self.multi_hop_router = MultiHopRouter(
                    min_profit_usd=float(os.getenv('MIN_MULTIHOP_PROFIT_USD', '0.03'))
                )
                print("  ✓ Multi-Hop Router Active")
            
            if self.enable_flashloan:
                self.flashloan_executor = FlashloanExecutor(
                    min_profit_usd=float(os.getenv('MIN_FLASHLOAN_PROFIT_USD', '0.08')),
                    dry_run=True  # Safety: always start in dry-run
                )
                print("  ✓ Flashloan Executor Active (DRY-RUN)")
            
            if self.enable_event_hunter:
                self.event_hunter = BlockEventHunter()
                print("  ✓ Event Hunter Active")
            
            if self.enable_predictive:
                self.predictive_liquidity = PredictiveLiquidity()
                print("  ✓ Predictive Liquidity Model Active")
        
        # Advanced tracking
        print("\n📡 Initializing Advanced Tracking Systems...")
        self.price_validator = PriceValidator.from_env(self.w3)
        self.smart_money_tracker = SmartMoneyTracker()
        self.volume_spike = VolumeSpikeScanner()
        
        print("  ✓ Price Validator Online")
        print("  ✓ Smart Money Tracker Online")
        print("  ✓ Volume Spike Scanner Online")
        
        # Register opportunity callback
        self.price_feed.register_opportunity_callback(self._handle_opportunity)
        
        print("\n" + "=" * 80)
        print("✅ ALL SUBSYSTEMS INITIALIZED AND READY")
        print("=" * 80)
        print(f"\n🎯 Mode: {self.trading_mode}")
        print(f"💰 Max Position: ${self.max_position_usd}")
        print(f"💵 Min Profit: ${self.min_profit_usd}")
        print(f"⚡ Scan Interval: {self.scan_interval_ms}ms")
        print(f"⛽ Max Gas: {self.max_gas_gwei} Gwei")
        print(f"🧠 Intelligence: MCP={self.enable_mcp} | Swarm={self.enable_swarm} | Intel={self.enable_intel_ingestor}")
        print(f"🔥 APEX Mode: {self.enable_apex}")
        print()
    
    async def _handle_opportunity(self, opportunity):
        """Central opportunity handler with full validation pipeline"""
        self.total_opportunities += 1
        
        # Multi-layer validation
        passed_validation = True
        
        # 1. MCP Intelligence filter
        if self.mcp and self.enable_mcp:
            mcp_approved = await self.mcp.evaluate_opportunity(opportunity)
            if not mcp_approved:
                print(f"❌ MCP rejected: {opportunity}")
                return
        
        # 2. Swarm consensus
        if self.swarm and self.enable_swarm:
            swarm_approved = await self.swarm.vote_on_opportunity(opportunity)
            if not swarm_approved:
                print(f"❌ Swarm rejected: {opportunity}")
                return
        
        # 3. Risk Guardian check
        if self.risk_guardian:
            risk_approved = self.risk_guardian.validate_trade(
                amount_usd=opportunity.net_profit_usd,
                current_pnl=self.total_pnl_usd
            )
            if not risk_approved:
                print(f"❌ Risk Guardian blocked: {opportunity}")
                return
        
        # 4. Gas Sentinel check
        if self.gas_sentinel:
            gas_approved = await self.gas_sentinel.is_gas_acceptable()
            if not gas_approved:
                print(f"❌ Gas too high: {opportunity}")
                return
        
        # 5. Liquidity check
        if self.liquidity_monitor:
            liquidity_ok = await self.liquidity_monitor.check_liquidity(opportunity)
            if not liquidity_ok:
                print(f"❌ Insufficient liquidity: {opportunity}")
                return
        
        # 6. Flash crash detection
        if self.flash_crash_detector:
            is_crash = await self.flash_crash_detector.detect_crash(opportunity)
            if is_crash:
                print(f"⚠️  Flash crash detected, skipping: {opportunity}")
                return
        
        # Execute if all checks pass
        print(f"✅ All validations passed: {opportunity}")
        
        if opportunity.net_profit_usd >= self.min_profit_usd:
            result = await self.smart_executor.execute(opportunity)
            
            self.total_trades += 1
            if result.success:
                self.successful_trades += 1
                self.total_pnl_usd += result.net_profit_usd
                self.total_gas_usd += result.gas_cost_usd
                print(f"💰 Trade executed: ${result.net_profit_usd:.4f} profit")
            else:
                print(f"❌ Trade failed: {result.error_message}")
    
    async def health_check_loop(self):
        """Continuous health monitoring and auto-recovery"""
        while self.running:
            try:
                await asyncio.sleep(self.health_check_interval)
                
                health = await self.get_system_health()
                
                # Check for issues
                if health.risk_status == 'CRITICAL':
                    print("🚨 CRITICAL RISK STATUS - ENGAGING EMERGENCY PROTOCOLS")
                    await self.emergency_stop()
                
                # Log health
                if health.total_trades > 0 and health.total_trades % 10 == 0:
                    print(f"\n📊 Health Check: {health.total_trades} trades | "
                          f"{health.win_rate:.1f}% win rate | ${health.session_pnl_usd:.2f} PnL")
                
            except Exception as e:
                print(f"⚠️  Health check error: {e}")
    
    async def get_system_health(self) -> SystemHealth:
        """Get comprehensive system health snapshot"""
        uptime = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        win_rate = (self.successful_trades / self.total_trades * 100) if self.total_trades > 0 else 0.0
        gas_efficiency = (self.total_gas_usd / abs(self.total_pnl_usd) * 100) if self.total_pnl_usd != 0 else 0.0
        
        # Check subsystem status
        subsystems = {
            'price_feed': 'ONLINE' if self.price_feed else 'OFFLINE',
            'execution_engine': 'ONLINE' if self.execution_engine else 'OFFLINE',
            'supervisor': 'ONLINE' if self.supervisor else 'OFFLINE',
            'mcp': 'ONLINE' if self.mcp else 'DISABLED',
            'swarm': 'ONLINE' if self.swarm else 'DISABLED',
            'risk_guardian': 'ONLINE' if self.risk_guardian else 'OFFLINE',
            'gas_sentinel': 'ONLINE' if self.gas_sentinel else 'OFFLINE',
        }
        
        intelligence = {
            'mcp': self.enable_mcp and self.mcp is not None,
            'swarm': self.enable_swarm and self.swarm is not None,
            'intel_ingestor': self.enable_intel_ingestor and self.intel_ingestor is not None,
        }
        
        # Risk assessment
        risk_status = 'HEALTHY'
        if self.total_pnl_usd < -50:  # $50 loss threshold
            risk_status = 'CRITICAL'
        elif self.total_pnl_usd < -20:
            risk_status = 'WARNING'
        
        return SystemHealth(
            timestamp=datetime.now(timezone.utc).isoformat(),
            uptime_seconds=uptime,
            total_opportunities=self.total_opportunities,
            total_trades=self.total_trades,
            session_pnl_usd=self.total_pnl_usd,
            win_rate=win_rate,
            gas_efficiency=gas_efficiency,
            rpc_health='CONNECTED',
            intelligence_status=intelligence,
            risk_status=risk_status,
            subsystem_status=subsystems
        )
    
    async def run(self, duration_seconds: Optional[int] = None):
        """Run autonomous trading session"""
        self.running = True
        
        print("\n🤖 AUTONOMOUS MASTER CONTROLLER ACTIVATED")
        print("=" * 80)
        print(f"Start Time: {self.start_time.isoformat()}")
        if duration_seconds:
            print(f"Duration: {duration_seconds} seconds ({duration_seconds/3600:.1f} hours)")
        else:
            print("Duration: INDEFINITE (until manual stop)")
        print("=" * 80)
        
        try:
            # Start price feed monitoring
            feed_task = asyncio.create_task(
                self.price_feed.monitor_loop(
                    scan_interval_ms=self.scan_interval_ms,
                    max_position_usd=self.max_position_usd
                )
            )
            
            # Start supervisor
            supervisor_task = asyncio.create_task(
                self.supervisor.monitor_loop(interval_seconds=30)
            )
            
            # Start health monitoring
            health_task = asyncio.create_task(self.health_check_loop())
            
            # Run for specified duration or indefinitely
            if duration_seconds:
                await asyncio.sleep(duration_seconds)
            else:
                # Run until stopped externally
                while self.running:
                    await asyncio.sleep(1)
            
            # Graceful shutdown
            print("\n🛑 Initiating graceful shutdown...")
            self.price_feed.stop()
            
            await feed_task
            supervisor_task.cancel()
            health_task.cancel()
            
            # Final report
            await self.print_final_report()
            
        except KeyboardInterrupt:
            print("\n⚠️  Interrupted by user")
            self.stop()
        except Exception as e:
            print(f"\n❌ Fatal error: {e}")
            import traceback
            traceback.print_exc()
            await self.emergency_stop()
    
    async def emergency_stop(self):
        """Emergency shutdown procedures"""
        print("\n🚨 EMERGENCY STOP INITIATED")
        print("=" * 80)
        
        # Stop all trading
        if self.price_feed:
            self.price_feed.stop()
        
        # Close all positions (if implemented)
        if self.position_monitor:
            positions = await self.position_monitor.get_open_positions()
            if positions:
                print(f"⚠️  {len(positions)} open positions detected")
                # TODO: Implement emergency position closing
        
        # Save final state
        await self.print_final_report()
        
        self.running = False
    
    def stop(self):
        """Stop autonomous trading"""
        self.running = False
        print("🛑 Stop signal received")
    
    async def print_final_report(self):
        """Print comprehensive final report"""
        health = await self.get_system_health()
        
        print("\n" + "=" * 80)
        print("📊 AUTONOMOUS TRADING SESSION COMPLETE")
        print("=" * 80)
        print(f"Duration: {health.uptime_seconds/3600:.2f} hours")
        print(f"Opportunities Detected: {health.total_opportunities}")
        print(f"Trades Executed: {health.total_trades}")
        print(f"Successful Trades: {self.successful_trades}")
        print(f"Win Rate: {health.win_rate:.1f}%")
        print(f"Session P&L: ${health.session_pnl_usd:.4f}")
        print(f"Total Gas Cost: ${self.total_gas_usd:.4f}")
        print(f"Net P&L: ${health.session_pnl_usd - self.total_gas_usd:.4f}")
        print(f"Gas Efficiency: {health.gas_efficiency:.2f}%")
        print("\nSubsystem Status:")
        for name, status in health.subsystem_status.items():
            print(f"  {name}: {status}")
        print("=" * 80)
        
        # Save to file
        report_file = Path('logs') / f"autonomous_session_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
        report_file.parent.mkdir(exist_ok=True)
        
        with open(report_file, 'w') as f:
            json.dump(health.to_dict(), f, indent=2)
        
        print(f"\n📁 Full report saved: {report_file}")


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Autonomous Master Trading Controller')
    parser.add_argument('--duration', type=int, help='Duration in seconds (omit for indefinite)')
    args = parser.parse_args()
    
    master = AutonomousMaster()
    await master.initialize_subsystems()
    await master.run(duration_seconds=args.duration)


if __name__ == '__main__':
    asyncio.run(main())
