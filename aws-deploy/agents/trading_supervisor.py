"""
⚡ UNYKORN SYSTEMS - TRADING SUPERVISOR DAEMON
FETCHER-X: NightShift Supervisor with Kill-Switch

Purpose: Monitor trading engine health and enforce safety limits
Features:
- Real-time health monitoring
- Automatic kill-switch activation
- Balance tracking
- Error detection
- Telegram/Discord alerts
- Performance metrics
- Circuit breakers
"""

import asyncio
import time
import json
import os
import sys
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import aiohttp
from web3 import Web3
import logging

logger = logging.getLogger(__name__)


# ===== Logging/Emoji safety for Windows & redirected logs =====
def _is_utf8_environment() -> bool:
    try:
        encs = {
            'stdout': getattr(sys.stdout, 'encoding', None),
            'stderr': getattr(sys.stderr, 'encoding', None),
            'default': sys.getdefaultencoding(),
            'io': os.environ.get('PYTHONIOENCODING', '')
        }
        return any(e and 'utf' in e.lower() for e in encs.values())
    except Exception:
        return False


def _env_flag(name: str, default: Optional[bool] = None) -> Optional[bool]:
    """Read tri-state env flag: 1/true => True, 0/false => False, else default"""
    val = os.environ.get(name)
    if val is None:
        return default
    val = val.strip().lower()
    if val in ('1', 'true', 'yes', 'on'):
        return True
    if val in ('0', 'false', 'no', 'off'):
        return False
    return default


ALLOW_EMOJI_LOGS = _env_flag('SUPERVISOR_EMOJI_LOGS', None)
if ALLOW_EMOJI_LOGS is None:
    # Auto mode: allow emojis only when environment is UTF-8 friendly
    ALLOW_EMOJI_LOGS = _is_utf8_environment()


_EMOJI_MAP = {
    '🛡️': '[SUP]',
    '✅': '[OK]',
    '❌': '[X]',
    '⚠️': '[WARN]',
    '🚨': '[ALERT]',
    '📱': '[TG]',
    '📢': '[DISCORD]',
    '⛔': '[STOP]',
    '❓': '?',
    '🚀': '[START]',
    '📊': '[STATS]'
}


def _sanitize_text(msg: Any) -> Any:
    """Replace problematic emojis with ASCII fallbacks when emojis are disabled.
    Works on strings; returns input unchanged for non-strings.
    """
    if ALLOW_EMOJI_LOGS or not isinstance(msg, str):
        return msg
    for emo, repl in _EMOJI_MAP.items():
        msg = msg.replace(emo, repl)
    # Drop any remaining non-ASCII to avoid cp1252/charmap failures
    try:
        msg = msg.encode('ascii', 'ignore').decode('ascii')
    except Exception:
        pass
    return msg


class EmojiSanitizingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            # Sanitize message and any %-format args
            record.msg = _sanitize_text(record.msg)
            if record.args:
                if isinstance(record.args, dict):
                    record.args = {k: _sanitize_text(v) for k, v in record.args.items()}
                elif isinstance(record.args, tuple):
                    record.args = tuple(_sanitize_text(a) for a in record.args)
                else:
                    record.args = _sanitize_text(record.args)
        except Exception:
            # Never block logs
            pass
        return True


# Attach filter once for this module's logger
logger.addFilter(EmojiSanitizingFilter())


class SystemStatus(Enum):
    """System operational status"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY_STOP = "emergency_stop"
    OFFLINE = "offline"


class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class HealthCheck:
    """Health check result"""
    check_name: str
    status: SystemStatus
    message: str
    timestamp: int
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class KillSwitchCondition:
    """Condition that triggers kill-switch"""
    name: str
    threshold: float
    current_value: float
    breached: bool
    reasoning: str


class TradingSupervisor:
    """
    24/7 monitoring supervisor for trading engine.
    
    Monitors:
    - Account balance (detect drains)
    - Gas prices (prevent expensive trades)
    - Error rates (detect system issues)
    - Trade success rate
    - Network connectivity
    - RPC health
    
    Kill-Switch Triggers:
    - Balance drop >15% in 5 minutes
    - >5 consecutive failed trades
    - Error rate >50%
    - Gas price >5x normal
    - Manual emergency stop
    - Loss >$1000 in single trade
    - Total loss >$2000 in session
    """
    
    def __init__(
        self,
        w3: Web3,
        wallet_address: Optional[str],
        telegram_bot_token: Optional[str] = None,
        telegram_chat_id: Optional[str] = None,
        discord_webhook_url: Optional[str] = None,
        max_drawdown_pct: float = 15.0,
        max_session_loss_usd: float = 2000.0,
        max_single_loss_usd: float = 1000.0,
        max_consecutive_losses: int = 5,
        max_error_rate_pct: float = 50.0,
        max_gas_multiplier: float = 5.0
    ):
        """
        Initialize trading supervisor.
        
        Args:
            w3: Web3 instance
            wallet_address: Trading wallet to monitor
            telegram_bot_token: Telegram bot for alerts
            telegram_chat_id: Telegram chat for alerts
            discord_webhook_url: Discord webhook for logs
            max_drawdown_pct: Kill-switch threshold for balance drop
            max_session_loss_usd: Kill-switch threshold for total loss
            max_single_loss_usd: Kill-switch threshold for single trade loss
            max_consecutive_losses: Kill-switch threshold for consecutive losses
            max_error_rate_pct: Kill-switch threshold for error rate
            max_gas_multiplier: Kill-switch threshold for gas spike
        """
        self.w3 = w3
        self.wallet_address = None
        if wallet_address:
            try:
                self.wallet_address = Web3.to_checksum_address(wallet_address)
            except Exception:
                logger.warning("Invalid wallet address provided; balance checks disabled")
        self.telegram_bot_token = telegram_bot_token
        self.telegram_chat_id = telegram_chat_id
        self.discord_webhook_url = discord_webhook_url
        
        # Kill-switch thresholds
        self.max_drawdown_pct = max_drawdown_pct
        self.max_session_loss_usd = max_session_loss_usd
        self.max_single_loss_usd = max_single_loss_usd
        self.max_consecutive_losses = max_consecutive_losses
        self.max_error_rate_pct = max_error_rate_pct
        self.max_gas_multiplier = max_gas_multiplier
        
        # State tracking
        self.status = SystemStatus.HEALTHY
        self.kill_switch_active = False
        self.start_balance_eth = 0.0
        self.current_balance_eth = 0.0
        self.start_time = int(time.time())
        self.last_health_check = 0
        self.baseline_gas_price = 0.0
        
        # Performance metrics
        self.total_trades = 0
        self.successful_trades = 0
        self.failed_trades = 0
        self.total_errors = 0
        self.consecutive_losses = 0
        self.session_pnl_usd = 0.0
        
        # Health check history
        self.health_checks: List[HealthCheck] = []
        self.alerts_sent = 0
        
        logger.info(f"🛡️ Trading Supervisor initialized")
        logger.info(f"   Wallet: {wallet_address or 'N/A'}")
        logger.info(f"   Max drawdown: {max_drawdown_pct}%")
        logger.info(f"   Max session loss: ${max_session_loss_usd:,.0f}")
        logger.info(f"   Telegram: {'✅' if telegram_bot_token else '❌'}")
        logger.info(f"   Discord: {'✅' if discord_webhook_url else '❌'}")
    
    
    async def send_telegram_alert(
        self,
        message: str,
        level: AlertLevel = AlertLevel.INFO
    ):
        """Send alert via Telegram bot"""
        if not self.telegram_bot_token or not self.telegram_chat_id:
            return
        
        # Add emoji based on level
        emoji_map = {
            AlertLevel.INFO: "ℹ️",
            AlertLevel.WARNING: "⚠️",
            AlertLevel.ERROR: "❌",
            AlertLevel.CRITICAL: "🚨"
        }
        
        formatted_message = f"{emoji_map[level]} {message}"
        
        url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
        payload = {
            "chat_id": self.telegram_chat_id,
            "text": formatted_message,
            "parse_mode": "HTML"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        self.alerts_sent += 1
                        logger.info(f"📱 Telegram alert sent: {level.value}")
                    else:
                        logger.warning(f"⚠️ Telegram alert failed: {resp.status}")
        except Exception as e:
            logger.error(f"❌ Telegram error: {e}")
    
    
    async def send_discord_log(
        self,
        title: str,
        description: str,
        color: int = 0x00FF00,  # Green
        fields: Optional[Dict[str, str]] = None
    ):
        """Send embed log to Discord webhook"""
        if not self.discord_webhook_url:
            return
        
        embed = {
            "title": title,
            "description": description,
            "color": color,
            "timestamp": datetime.utcnow().isoformat(),
            "footer": {"text": "Unykorn Trading Engine"}
        }
        
        if fields:
            embed["fields"] = [
                {"name": name, "value": value, "inline": True}
                for name, value in fields.items()
            ]
        
        payload = {"embeds": [embed]}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.discord_webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status in (200, 204):
                        logger.info(f"📢 Discord log sent: {title}")
                    else:
                        logger.warning(f"⚠️ Discord log failed: {resp.status}")
        except Exception as e:
            logger.error(f"❌ Discord error: {e}")
    
    
    async def check_balance(self) -> HealthCheck:
        """Check wallet balance and detect drains"""
        try:
            if not self.wallet_address:
                return HealthCheck(
                    check_name="balance",
                    status=SystemStatus.HEALTHY,
                    message="Wallet not configured",
                    timestamp=int(time.time()),
                    details={}
                )
            current_balance = self.w3.eth.get_balance(self.wallet_address)
            self.current_balance_eth = Web3.from_wei(current_balance, 'ether')
            
            # Set baseline on first check
            if self.start_balance_eth == 0:
                self.start_balance_eth = self.current_balance_eth
            
            # Calculate drawdown
            if self.start_balance_eth > 0:
                drawdown_pct = (
                    (self.start_balance_eth - self.current_balance_eth) /
                    self.start_balance_eth * 100
                )
            else:
                drawdown_pct = 0.0
            
            status = SystemStatus.HEALTHY
            message = f"Balance: {self.current_balance_eth:.4f} ETH"
            
            # Check thresholds
            if drawdown_pct > self.max_drawdown_pct:
                status = SystemStatus.CRITICAL
                message = f"CRITICAL DRAWDOWN: {drawdown_pct:.1f}% loss"
                await self.trigger_kill_switch(
                    f"Balance drawdown exceeded {self.max_drawdown_pct}%"
                )
            elif drawdown_pct > self.max_drawdown_pct * 0.7:
                status = SystemStatus.WARNING
                message = f"High drawdown: {drawdown_pct:.1f}%"
            
            return HealthCheck(
                check_name="balance",
                status=status,
                message=message,
                timestamp=int(time.time()),
                details={
                    "current_eth": self.current_balance_eth,
                    "start_eth": self.start_balance_eth,
                    "drawdown_pct": drawdown_pct
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Balance check failed: {e}")
            return HealthCheck(
                check_name="balance",
                status=SystemStatus.CRITICAL,
                message=f"Balance check error: {e}",
                timestamp=int(time.time())
            )
    
    
    async def check_gas_price(self) -> HealthCheck:
        """Check gas prices for spikes"""
        try:
            current_gas = self.w3.eth.gas_price
            current_gas_gwei = Web3.from_wei(current_gas, 'gwei')
            
            # Set baseline on first check
            if self.baseline_gas_price == 0:
                self.baseline_gas_price = current_gas_gwei
            
            # Calculate multiplier
            gas_multiplier = 1.0
            if self.baseline_gas_price > 0:
                gas_multiplier = current_gas_gwei / self.baseline_gas_price
            
            status = SystemStatus.HEALTHY
            message = f"Gas: {current_gas_gwei:.4f} Gwei"
            
            # Check thresholds
            if gas_multiplier > self.max_gas_multiplier:
                status = SystemStatus.CRITICAL
                message = f"GAS SPIKE: {gas_multiplier:.1f}x baseline"
                await self.trigger_kill_switch(
                    f"Gas price spike: {current_gas_gwei:.2f} Gwei ({gas_multiplier:.1f}x baseline)"
                )
            elif gas_multiplier > self.max_gas_multiplier * 0.7:
                status = SystemStatus.WARNING
                message = f"High gas: {current_gas_gwei:.4f} Gwei"
            
            return HealthCheck(
                check_name="gas_price",
                status=status,
                message=message,
                timestamp=int(time.time()),
                details={
                    "current_gwei": current_gas_gwei,
                    "baseline_gwei": self.baseline_gas_price,
                    "multiplier": gas_multiplier
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Gas price check failed: {e}")
            return HealthCheck(
                check_name="gas_price",
                status=SystemStatus.WARNING,
                message=f"Gas check error: {e}",
                timestamp=int(time.time())
            )
    
    
    async def check_trade_performance(self) -> HealthCheck:
        """Check trade success rate"""
        if self.total_trades == 0:
            return HealthCheck(
                check_name="trade_performance",
                status=SystemStatus.HEALTHY,
                message="No trades yet",
                timestamp=int(time.time())
            )
        
        success_rate = self.successful_trades / self.total_trades * 100
        error_rate = self.total_errors / self.total_trades * 100
        
        status = SystemStatus.HEALTHY
        message = f"Success: {success_rate:.1f}%, Errors: {error_rate:.1f}%"
        
        # Check consecutive losses
        if self.consecutive_losses >= self.max_consecutive_losses:
            status = SystemStatus.CRITICAL
            message = f"CONSECUTIVE LOSSES: {self.consecutive_losses} in a row"
            await self.trigger_kill_switch(
                f"{self.consecutive_losses} consecutive losses"
            )
        elif self.consecutive_losses >= self.max_consecutive_losses * 0.7:
            status = SystemStatus.WARNING
            message = f"High consecutive losses: {self.consecutive_losses}"
        
        # Check error rate
        if error_rate > self.max_error_rate_pct:
            status = SystemStatus.CRITICAL
            message = f"HIGH ERROR RATE: {error_rate:.1f}%"
            await self.trigger_kill_switch(
                f"Error rate {error_rate:.1f}% exceeded threshold"
            )
        
        return HealthCheck(
            check_name="trade_performance",
            status=status,
            message=message,
            timestamp=int(time.time()),
            details={
                "total_trades": self.total_trades,
                "successful": self.successful_trades,
                "failed": self.failed_trades,
                "success_rate": success_rate,
                "error_rate": error_rate,
                "consecutive_losses": self.consecutive_losses
            }
        )
    
    
    async def check_session_pnl(self) -> HealthCheck:
        """Check total session P&L"""
        status = SystemStatus.HEALTHY
        message = f"Session P&L: ${self.session_pnl_usd:,.2f}"
        
        # Check loss threshold
        if self.session_pnl_usd < -self.max_session_loss_usd:
            status = SystemStatus.CRITICAL
            message = f"SESSION LOSS LIMIT: ${abs(self.session_pnl_usd):,.2f}"
            await self.trigger_kill_switch(
                f"Session loss ${abs(self.session_pnl_usd):,.2f} exceeded limit"
            )
        elif self.session_pnl_usd < -self.max_session_loss_usd * 0.7:
            status = SystemStatus.WARNING
            message = f"High session loss: ${abs(self.session_pnl_usd):,.2f}"
        
        return HealthCheck(
            check_name="session_pnl",
            status=status,
            message=message,
            timestamp=int(time.time()),
            details={"session_pnl_usd": self.session_pnl_usd}
        )
    
    
    async def perform_health_checks(self) -> List[HealthCheck]:
        """Perform all health checks"""
        self.last_health_check = int(time.time())
        
        checks = await asyncio.gather(
            self.check_balance(),
            self.check_gas_price(),
            self.check_trade_performance(),
            self.check_session_pnl()
        )
        
        # Store in history (keep last 100)
        self.health_checks.extend(checks)
        self.health_checks = self.health_checks[-100:]
        
        # Update system status (worst status wins)
        status_priority = {
            SystemStatus.HEALTHY: 0,
            SystemStatus.WARNING: 1,
            SystemStatus.CRITICAL: 2,
            SystemStatus.EMERGENCY_STOP: 3
        }
        
        worst_status = max(
            (check.status for check in checks),
            key=lambda s: status_priority.get(s, 0)
        )
        
        self.status = worst_status
        
        return checks
    
    
    async def trigger_kill_switch(self, reason: str):
        """Activate emergency stop"""
        if self.kill_switch_active:
            return  # Already triggered
        
        self.kill_switch_active = True
        self.status = SystemStatus.EMERGENCY_STOP
        
        logger.critical(f"🚨 KILL-SWITCH ACTIVATED: {reason}")
        
        # Send critical alerts
        await self.send_telegram_alert(
            f"<b>🚨 KILL-SWITCH ACTIVATED</b>\n\n"
            f"Reason: {reason}\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Balance: {self.current_balance_eth:.4f} ETH\n"
            f"Session P&L: ${self.session_pnl_usd:,.2f}\n\n"
            f"⛔ Trading halted. Manual restart required.",
            level=AlertLevel.CRITICAL
        )
        
        await self.send_discord_log(
            title="🚨 EMERGENCY STOP",
            description=f"Kill-switch activated: {reason}",
            color=0xFF0000,  # Red
            fields={
                "Balance": f"{self.current_balance_eth:.4f} ETH",
                "Session P&L": f"${self.session_pnl_usd:,.2f}",
                "Total Trades": str(self.total_trades),
                "Status": "HALTED"
            }
        )
    
    
    async def monitor_loop(self, interval_seconds: int = 30):
        """Main monitoring loop"""
        logger.info(f"🛡️ Supervisor monitoring started (interval: {interval_seconds}s)")
        # Prime balance before sending startup notification
        try:
            await self.check_balance()
        except Exception:
            pass
        
        # Send startup notification
        await self.send_telegram_alert(
            f"<b>🚀 Trading Engine Started</b>\n\n"
            f"Wallet: {self.wallet_address}\n"
            f"Balance: {self.current_balance_eth:.4f} ETH\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            level=AlertLevel.INFO
        )
        
        while not self.kill_switch_active:
            try:
                # Perform health checks
                checks = await self.perform_health_checks()
                
                # Log status
                status_emoji = {
                    SystemStatus.HEALTHY: "✅",
                    SystemStatus.WARNING: "⚠️",
                    SystemStatus.CRITICAL: "🚨"
                }
                
                logger.info(
                    f"{status_emoji.get(self.status, '❓')} System Status: {self.status.value}"
                )
                
                for check in checks:
                    if check.status != SystemStatus.HEALTHY:
                        logger.warning(f"   {check.check_name}: {check.message}")
                
                # Send warnings via Telegram
                for check in checks:
                    if check.status == SystemStatus.WARNING:
                        await self.send_telegram_alert(
                            f"⚠️ {check.check_name}: {check.message}",
                            level=AlertLevel.WARNING
                        )
                
                # Wait for next check
                await asyncio.sleep(interval_seconds)
                
            except Exception as e:
                logger.error(f"❌ Supervisor loop error: {e}")
                self.total_errors += 1
                await asyncio.sleep(interval_seconds)
        
        logger.critical(f"⛔ Supervisor monitoring stopped (kill-switch active)")
    
    
    def record_trade(
        self,
        success: bool,
        pnl_usd: float,
        error: Optional[str] = None
    ):
        """Record trade result for monitoring"""
        self.total_trades += 1
        
        if success:
            self.successful_trades += 1
            self.consecutive_losses = 0
        else:
            self.failed_trades += 1
            self.consecutive_losses += 1
        
        if error:
            self.total_errors += 1
        
        self.session_pnl_usd += pnl_usd
        
        # Check single trade loss threshold (schedule safely regardless of context)
        if pnl_usd < -self.max_single_loss_usd:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(
                    self.trigger_kill_switch(
                        f"Single trade loss ${abs(pnl_usd):,.2f} exceeded limit"
                    )
                )
            except RuntimeError:
                threading.Thread(
                    target=lambda: asyncio.run(
                        self.trigger_kill_switch(
                            f"Single trade loss ${abs(pnl_usd):,.2f} exceeded limit"
                        )
                    ),
                    daemon=True,
                ).start()
    
    
    def get_stats(self) -> Dict[str, Any]:
        """Get supervisor statistics"""
        uptime_seconds = int(time.time()) - self.start_time
        uptime_hours = uptime_seconds / 3600
        
        return {
            "status": self.status.value,
            "kill_switch_active": self.kill_switch_active,
            "uptime_hours": uptime_hours,
            "current_balance_eth": self.current_balance_eth,
            "start_balance_eth": self.start_balance_eth,
            "session_pnl_usd": self.session_pnl_usd,
            "total_trades": self.total_trades,
            "successful_trades": self.successful_trades,
            "failed_trades": self.failed_trades,
            "consecutive_losses": self.consecutive_losses,
            "total_errors": self.total_errors,
            "alerts_sent": self.alerts_sent,
            "last_health_check": self.last_health_check
        }


# ═══════════════════════════════════════════════════════════════
# USAGE EXAMPLE
# ═══════════════════════════════════════════════════════════════

async def demo_supervisor():
    """Demonstrate supervisor usage"""
    
    # Initialize Web3
    w3 = Web3(Web3.HTTPProvider("https://arb-mainnet.g.alchemy.com/v2/YOUR_KEY"))
    
    # Initialize supervisor
    supervisor = TradingSupervisor(
        w3=w3,
        wallet_address="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
        telegram_bot_token="YOUR_BOT_TOKEN",
        telegram_chat_id="YOUR_CHAT_ID",
        max_drawdown_pct=15.0,
        max_session_loss_usd=2000.0
    )
    
    # Start monitoring in background
    monitor_task = asyncio.create_task(supervisor.monitor_loop(interval_seconds=30))
    
    # Simulate trading
    await asyncio.sleep(5)
    supervisor.record_trade(success=True, pnl_usd=50.0)
    
    await asyncio.sleep(5)
    supervisor.record_trade(success=False, pnl_usd=-20.0)
    
    # Let it run for a bit
    await asyncio.sleep(60)
    
    # Print stats
    stats = supervisor.get_stats()
    print(f"\n📊 Supervisor Statistics:")
    print(f"   Status: {stats['status']}")
    print(f"   Uptime: {stats['uptime_hours']:.2f} hours")
    print(f"   Session P&L: ${stats['session_pnl_usd']:,.2f}")
    print(f"   Trades: {stats['total_trades']} ({stats['successful_trades']} wins)")


if __name__ == "__main__":
    asyncio.run(demo_supervisor())
