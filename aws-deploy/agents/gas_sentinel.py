"""
Gas Sentinel Daemon - Continuous Gas Price Monitoring
Monitors gas prices in real-time and enforces trading thresholds
STOP execution if >1.2 Gwei, KILL-SWITCH if >3 Gwei

Used by: live_engine.py
Prevents: Trading during expensive gas periods, runaway gas costs
"""

import time
import threading
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
from web3 import Web3
import logging

logger = logging.getLogger(__name__)


class GasLevel(Enum):
    """Gas price severity levels"""
    NORMAL = "normal"           # <1.2 Gwei - safe to trade
    ELEVATED = "elevated"       # 1.2-2.0 Gwei - caution
    HIGH = "high"               # 2.0-3.0 Gwei - stop trading
    CRITICAL = "critical"       # >3.0 Gwei - kill-switch armed


@dataclass
class GasSnapshot:
    """Single gas price measurement"""
    timestamp: float
    gas_price_gwei: float
    source: str
    level: GasLevel
    
    def __str__(self):
        return f"{self.gas_price_gwei:.4f} Gwei ({self.level.value}) from {self.source}"


class GasSentinel:
    """
    Real-time gas monitoring daemon with trading controls
    
    Features:
    - Continuous monitoring (every 5-10 seconds)
    - Multi-source gas price aggregation
    - Automatic trading suspension at thresholds
    - Kill-switch trigger for critical levels
    - Statistical tracking and alerts
    
    Thresholds (configurable):
    - NORMAL:   <1.2 Gwei  → Trading enabled
    - ELEVATED: 1.2-2.0    → Trading enabled with warnings
    - HIGH:     2.0-3.0    → Trading STOPPED
    - CRITICAL: >3.0 Gwei  → KILL-SWITCH armed
    """
    
    def __init__(
        self,
        w3: Web3,
        check_interval_seconds: int = 10,
        normal_threshold_gwei: float = 1.2,
        elevated_threshold_gwei: float = 2.0,
        high_threshold_gwei: float = 3.0,
        alert_callback: Optional[Callable] = None
    ):
        """
        Initialize gas sentinel
        
        Args:
            w3: Web3 instance
            check_interval_seconds: How often to check gas (default 10s)
            normal_threshold_gwei: Below this = NORMAL (default 1.2)
            elevated_threshold_gwei: Below this = ELEVATED (default 2.0)
            high_threshold_gwei: Below this = HIGH (default 3.0)
            alert_callback: Function to call on threshold violations
        """
        self.w3 = w3
        self.check_interval = check_interval_seconds
        self.normal_threshold = normal_threshold_gwei
        self.elevated_threshold = elevated_threshold_gwei
        self.high_threshold = high_threshold_gwei
        self.alert_callback = alert_callback
        
        # State
        self.current_gas_gwei: float = 0.0
        self.current_level: GasLevel = GasLevel.NORMAL
        self.trading_enabled: bool = True
        self.kill_switch_armed: bool = False
        
        # History
        self.gas_history: List[GasSnapshot] = []
        self.max_history_size = 1000
        
        # Statistics
        self.total_checks = 0
        self.normal_count = 0
        self.elevated_count = 0
        self.high_count = 0
        self.critical_count = 0
        self.trading_stopped_count = 0
        self.kill_switch_triggered_count = 0
        
        # Threading
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        logger.info(
            f"Gas Sentinel initialized: "
            f"normal<{normal_threshold_gwei}, "
            f"elevated<{elevated_threshold_gwei}, "
            f"high<{high_threshold_gwei} Gwei"
        )
    
    def start(self):
        """Start gas monitoring daemon in background thread"""
        if self._running:
            logger.warning("Gas sentinel already running")
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        
        logger.info("Gas sentinel started")
    
    def stop(self):
        """Stop gas monitoring daemon"""
        if not self._running:
            return
        
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        
        logger.info("Gas sentinel stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop (runs in background thread)"""
        while self._running:
            try:
                self._check_gas()
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in gas monitoring loop: {e}")
                time.sleep(self.check_interval)
    
    def _check_gas(self):
        """Check current gas price and update state"""
        try:
            # Get gas price from chain
            gas_price_wei = self.w3.eth.gas_price
            gas_price_gwei = self.w3.from_wei(gas_price_wei, 'gwei')
            
            # Determine level
            level = self._classify_gas_level(float(gas_price_gwei))
            
            # Create snapshot
            snapshot = GasSnapshot(
                timestamp=time.time(),
                gas_price_gwei=float(gas_price_gwei),
                source="chain",
                level=level
            )
            
            # Update state
            with self._lock:
                old_level = self.current_level
                self.current_gas_gwei = float(gas_price_gwei)
                self.current_level = level
                self.total_checks += 1
                
                # Update statistics
                if level == GasLevel.NORMAL:
                    self.normal_count += 1
                elif level == GasLevel.ELEVATED:
                    self.elevated_count += 1
                elif level == GasLevel.HIGH:
                    self.high_count += 1
                elif level == GasLevel.CRITICAL:
                    self.critical_count += 1
                
                # Store history
                self.gas_history.append(snapshot)
                if len(self.gas_history) > self.max_history_size:
                    self.gas_history = self.gas_history[-self.max_history_size:]
                
                # Check for threshold violations
                self._handle_threshold_change(old_level, level, snapshot)
            
            logger.debug(f"Gas check: {snapshot}")
            
        except Exception as e:
            logger.error(f"Failed to check gas price: {e}")
    
    def _classify_gas_level(self, gas_gwei: float) -> GasLevel:
        """Classify gas price into severity level"""
        if gas_gwei >= self.high_threshold:
            return GasLevel.CRITICAL
        elif gas_gwei >= self.elevated_threshold:
            return GasLevel.HIGH
        elif gas_gwei >= self.normal_threshold:
            return GasLevel.ELEVATED
        else:
            return GasLevel.NORMAL
    
    def _handle_threshold_change(
        self,
        old_level: GasLevel,
        new_level: GasLevel,
        snapshot: GasSnapshot
    ):
        """Handle transition between gas levels"""
        if old_level == new_level:
            return
        
        # Level increased
        if new_level == GasLevel.ELEVATED and old_level == GasLevel.NORMAL:
            logger.warning(
                f"⚠️  GAS ELEVATED: {snapshot.gas_price_gwei:.4f} Gwei "
                f"(threshold: {self.normal_threshold} Gwei)"
            )
            self._send_alert("GAS_ELEVATED", snapshot)
        
        elif new_level == GasLevel.HIGH:
            logger.warning(
                f"🛑 GAS HIGH - TRADING STOPPED: {snapshot.gas_price_gwei:.4f} Gwei "
                f"(threshold: {self.elevated_threshold} Gwei)"
            )
            self.trading_enabled = False
            self.trading_stopped_count += 1
            self._send_alert("TRADING_STOPPED", snapshot)
        
        elif new_level == GasLevel.CRITICAL:
            logger.critical(
                f"🚨 GAS CRITICAL - KILL-SWITCH ARMED: {snapshot.gas_price_gwei:.4f} Gwei "
                f"(threshold: {self.high_threshold} Gwei)"
            )
            self.trading_enabled = False
            self.kill_switch_armed = True
            self.kill_switch_triggered_count += 1
            self._send_alert("KILL_SWITCH_ARMED", snapshot)
        
        # Level decreased
        elif new_level == GasLevel.ELEVATED and old_level == GasLevel.HIGH:
            logger.info(
                f"✓ Gas decreased to ELEVATED: {snapshot.gas_price_gwei:.4f} Gwei"
            )
            self._send_alert("GAS_DECREASED", snapshot)
        
        elif new_level == GasLevel.NORMAL:
            logger.info(
                f"✓ Gas back to NORMAL: {snapshot.gas_price_gwei:.4f} Gwei - Trading resumed"
            )
            self.trading_enabled = True
            self.kill_switch_armed = False
            self._send_alert("GAS_NORMAL", snapshot)
    
    def _send_alert(self, alert_type: str, snapshot: GasSnapshot):
        """Send alert via callback if configured"""
        if self.alert_callback:
            try:
                self.alert_callback(alert_type, snapshot)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")
    
    def is_trading_allowed(self) -> bool:
        """
        Check if trading is currently allowed based on gas prices
        
        Returns:
            True if gas is at safe levels, False otherwise
        """
        with self._lock:
            return self.trading_enabled and not self.kill_switch_armed
    
    def get_current_gas(self) -> float:
        """Get current gas price in Gwei"""
        with self._lock:
            return self.current_gas_gwei
    
    def get_current_level(self) -> GasLevel:
        """Get current gas severity level"""
        with self._lock:
            return self.current_level
    
    def force_check(self) -> GasSnapshot:
        """Force immediate gas check (bypasses interval)"""
        self._check_gas()
        with self._lock:
            return self.gas_history[-1] if self.gas_history else None
    
    def reset_kill_switch(self):
        """
        Manually reset kill-switch after critical gas event
        Use with caution - only reset when gas is confirmed safe
        """
        with self._lock:
            if self.current_level != GasLevel.CRITICAL:
                self.kill_switch_armed = False
                self.trading_enabled = True
                logger.info("Kill-switch manually reset")
            else:
                logger.error(
                    "Cannot reset kill-switch: gas still at CRITICAL level "
                    f"({self.current_gas_gwei:.4f} Gwei)"
                )
    
    def get_statistics(self) -> Dict:
        """Get comprehensive gas monitoring statistics"""
        with self._lock:
            if self.total_checks == 0:
                return {
                    "current_gas_gwei": 0.0,
                    "current_level": "unknown",
                    "trading_enabled": False,
                    "kill_switch_armed": False,
                    "total_checks": 0,
                }
            
            return {
                "current_gas_gwei": self.current_gas_gwei,
                "current_level": self.current_level.value,
                "trading_enabled": self.trading_enabled,
                "kill_switch_armed": self.kill_switch_armed,
                "total_checks": self.total_checks,
                "level_distribution": {
                    "normal": (self.normal_count / self.total_checks) * 100,
                    "elevated": (self.elevated_count / self.total_checks) * 100,
                    "high": (self.high_count / self.total_checks) * 100,
                    "critical": (self.critical_count / self.total_checks) * 100,
                },
                "trading_stopped_count": self.trading_stopped_count,
                "kill_switch_triggered_count": self.kill_switch_triggered_count,
                "avg_gas_gwei": sum(s.gas_price_gwei for s in self.gas_history) / len(self.gas_history)
                if self.gas_history else 0.0,
                "max_gas_gwei": max(s.gas_price_gwei for s in self.gas_history)
                if self.gas_history else 0.0,
                "min_gas_gwei": min(s.gas_price_gwei for s in self.gas_history)
                if self.gas_history else 0.0,
            }
    
    def get_recent_history(self, minutes: int = 10) -> List[GasSnapshot]:
        """Get gas snapshots from last N minutes"""
        cutoff_time = time.time() - (minutes * 60)
        with self._lock:
            return [s for s in self.gas_history if s.timestamp >= cutoff_time]
    
    def print_status(self):
        """Print current gas sentinel status"""
        stats = self.get_statistics()
        
        print("\n" + "="*80)
        print("GAS SENTINEL STATUS")
        print("="*80)
        
        # Current state
        status_icon = "✓" if stats['trading_enabled'] else "✗"
        kill_switch_icon = "🚨" if stats['kill_switch_armed'] else "  "
        
        print(f"\nCurrent Gas:     {stats['current_gas_gwei']:.4f} Gwei ({stats['current_level'].upper()})")
        print(f"Trading Enabled: {status_icon} {stats['trading_enabled']}")
        print(f"Kill-Switch:     {kill_switch_icon} {'ARMED' if stats['kill_switch_armed'] else 'Disarmed'}")
        
        # Thresholds
        print(f"\nThresholds:")
        print(f"  NORMAL   < {self.normal_threshold:.2f} Gwei")
        print(f"  ELEVATED < {self.elevated_threshold:.2f} Gwei")
        print(f"  HIGH     < {self.high_threshold:.2f} Gwei")
        print(f"  CRITICAL ≥ {self.high_threshold:.2f} Gwei")
        
        # Statistics
        if stats['total_checks'] > 0:
            print(f"\nStatistics ({stats['total_checks']} checks):")
            print(f"  Average:  {stats['avg_gas_gwei']:.4f} Gwei")
            print(f"  Min:      {stats['min_gas_gwei']:.4f} Gwei")
            print(f"  Max:      {stats['max_gas_gwei']:.4f} Gwei")
            
            print(f"\nLevel Distribution:")
            dist = stats['level_distribution']
            print(f"  NORMAL:   {dist['normal']:5.1f}%")
            print(f"  ELEVATED: {dist['elevated']:5.1f}%")
            print(f"  HIGH:     {dist['high']:5.1f}%")
            print(f"  CRITICAL: {dist['critical']:5.1f}%")
            
            print(f"\nAlerts:")
            print(f"  Trading Stopped:     {stats['trading_stopped_count']}")
            print(f"  Kill-Switch Triggers: {stats['kill_switch_triggered_count']}")
        
        print("="*80 + "\n")


# Example usage and testing
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    def alert_handler(alert_type: str, snapshot: GasSnapshot):
        """Example alert callback"""
        print(f"\n🔔 ALERT: {alert_type}")
        print(f"   Gas: {snapshot}")
    
    # Initialize Web3 (Arbitrum mainnet)
    rpc_url = os.getenv("ARBITRUM_RPC", "https://arb1.arbitrum.io/rpc")
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    
    print("Initializing gas sentinel...")
    sentinel = GasSentinel(
        w3=w3,
        check_interval_seconds=5,  # Check every 5 seconds
        normal_threshold_gwei=1.2,
        elevated_threshold_gwei=2.0,
        high_threshold_gwei=3.0,
        alert_callback=alert_handler
    )
    
    # Start monitoring
    sentinel.start()
    
    print("\nMonitoring gas prices for 30 seconds...")
    print("(On Arbitrum, gas is usually <0.1 Gwei, so thresholds won't trigger)")
    
    try:
        for i in range(6):
            time.sleep(5)
            
            # Force check and show result
            snapshot = sentinel.force_check()
            if snapshot:
                trading_allowed = "✓ TRADING ALLOWED" if sentinel.is_trading_allowed() else "✗ TRADING BLOCKED"
                print(f"\nCheck {i+1}: {snapshot.gas_price_gwei:.4f} Gwei - {trading_allowed}")
        
        # Show final status
        sentinel.print_status()
        
        # Show recent history
        recent = sentinel.get_recent_history(minutes=1)
        if recent:
            print("\nRecent Gas History (last 1 minute):")
            for snap in recent[-5:]:
                print(f"  {snap}")
        
    finally:
        sentinel.stop()
    
    print("\n✓ Gas sentinel test complete")
