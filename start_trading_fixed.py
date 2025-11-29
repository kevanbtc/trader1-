#!/usr/bin/env python3
"""
🐉 Trading Dragon - Direct Launch Script
Bypasses Jupyter notebook, runs trading session directly
"""

import sys
import json
import os
import asyncio
import pandas as pd
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv  # type: ignore
except ImportError:
    load_dotenv = None

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from agents.defi_price_feed import DeFiPriceFeed, ArbitrageOpportunity
from agents.defi_execution_engine import DeFiExecutionEngine, TradeOrder
from agents.trading_supervisor import TradingSupervisor, AlertLevel
from agents.price_validator import PriceValidator

# ===== Output emoji safety (for Windows redirection) =====
def _is_utf8_environment():
    encs = [getattr(sys.stdout, 'encoding', None), os.environ.get('PYTHONIOENCODING', ''), sys.getdefaultencoding()]
    return any(e and 'utf' in str(e).lower() for e in encs)


def _env_flag(name: str, default: None | bool = None) -> None | bool:
    val = os.environ.get(name)
    if val is None:
        return default
    v = val.strip().lower()
    if v in ('1', 'true', 'yes', 'on'):
        return True
    if v in ('0', 'false', 'no', 'off'):
        return False
    return default


_ALLOW_EMOJI = _env_flag('TRADING_EMOJI_OUTPUT', None)
if _ALLOW_EMOJI is None:
    _ALLOW_EMOJI = _is_utf8_environment()

_EMOJI_MAP = {
    '🐉': '[TRADER]',
    '📋': '[CFG]',
    '✅': '[OK]',
    '💰': '[$]',
    '🤖': '[BOTS]',
    '🔗': '[RPC]',
    '🔍': '[CHK]',
    '❌': '[X]',
    '🚀': '[INIT]',
    '🔥': '[START]',
    '⚠️': '[WARN]',
    '📊': '[STATS]',
    '📁': '[FILE]'
}


def out(msg: str = ""):
    if not _ALLOW_EMOJI:
        for emo, repl in _EMOJI_MAP.items():
            msg = msg.replace(emo, repl)
        try:
            msg = msg.encode('ascii', 'ignore').decode('ascii')
        except Exception:
            pass
    print(msg)

# Configuration
out("=" * 80)
out("🐉 TRADING DRAGON - DIRECT LAUNCH")
out("=" * 80)
out()

# Load config
out("📋 Loading configuration & environment...")

# Ensure we load .env from project root regardless of invocation CWD
project_root = Path(__file__).parent
env_path = project_root / '.env'

# FORCE LOAD .ENV - Manual parsing as fallback
if env_path.exists():
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

# Also try dotenv library
if load_dotenv:
    load_dotenv(dotenv_path=env_path, override=True)
else:
    out("⚠️ python-dotenv not installed (manual parsing used)")

# Load config file for capital/bot info only
cfg_path = project_root / 'config' / 'aggressive_overnight_bots.json'
with open(cfg_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

# READ EVERYTHING FROM ENV - CONFIG FILE IS INFORMATIONAL ONLY
env_mode = os.environ.get('TRADING_MODE', 'PAPER').upper()
paper_mode = os.environ.get('ENABLE_PAPER_MODE', 'false').lower() == 'true'
quick_test_run = os.environ.get('QUICK_TEST_RUN', '').strip().lower() == 'true'

# Intelligence flags from env
enable_mcp = os.environ.get('ENABLE_MCP', 'false').lower() == 'true'
enable_swarm = os.environ.get('ENABLE_SWARM', 'false').lower() == 'true'
enable_intel_ingestor = os.environ.get('ENABLE_INTEL_INGESTOR', 'false').lower() == 'true'

# Trading params from env
max_position_usd = float(os.environ.get('MAX_POSITION_USD', '10'))
min_profit_usd = float(os.environ.get('MIN_PROFIT_USD', '0.30'))
max_gas_gwei = float(os.environ.get('MAX_GAS_GWEI', '0.5'))
max_slippage_bps = int(os.environ.get('MAX_SLIPPAGE_BPS', '100'))
scan_interval_ms = int(os.environ.get('SCAN_INTERVAL_MS', '7000'))

# Config file info (for display only)
capital = config.get('capital_allocation', {}).get('active_trading_usd', 0)
bot_count = len(config.get('aggressive_bots', []))
rpc_url = config.get('chains', {}).get('ARBITRUM', {}).get('rpc_url')

out(f"✅ Configuration loaded from .env")
out(f"🎯 Trading Mode: {env_mode}")
out(f"🎮 Paper Mode: {'DISABLED' if not paper_mode else 'ENABLED'}")
out(f"🧠 MCP Intelligence: {'ENABLED' if enable_mcp else 'DISABLED'}")
out(f"🐝 Swarm Intelligence: {'ENABLED' if enable_swarm else 'DISABLED'}")
out(f"💰 Capital: ${capital:,.2f} | Bots: {bot_count}")
out(f"🔗 RPC: {rpc_url}")
out()

# Test RPC
out("🔍 Testing RPC connection...")
from agents.rpc_utils import get_arbitrum_w3  # type: ignore
w3 = get_arbitrum_w3()
try:
    block = w3.eth.block_number
    gas = w3.eth.gas_price / 1e9
    out(f"✅ Connected! Block: {block:,}, Gas: {gas:.4f} Gwei")
except Exception:
    out("❌ RPC connection failed!")
    sys.exit(1)

out()

# Initialize trading components
out("🚀 Initializing trading system...")
alchemy_rpc = os.getenv('ARB_RPC_1', 'http://127.0.0.1:8547')
# DeFiPriceFeed will print its own MCP/Swarm/Intel status
price_feed = DeFiPriceFeed(chain="ARBITRUM", rpc_url=alchemy_rpc, enable_mcp=enable_mcp)

# Live vs Paper mode logic
if env_mode == 'LIVE' and not paper_mode:
    out("🚀 LIVE MODE ENABLED — trades will be broadcast on-chain")
    paper_mode = False  # Force live
elif paper_mode or env_mode != 'LIVE':
    out("⚠️ Running in PAPER (simulation) mode. Set TRADING_MODE=LIVE and ENABLE_PAPER_MODE=false in .env for live execution.")
    paper_mode = True
if quick_test_run:
    out("🧪 QUICK_TEST_RUN active → forced 10s session")

# Get private key from environment for LIVE mode
private_key = os.environ.get('WALLET_PRIVATE_KEY') if not paper_mode else None
execution_engine = DeFiExecutionEngine(chain="ARBITRUM", paper_mode=paper_mode, rpc_url=None, private_key=private_key)
# Initialize price validator (uses env API keys if available)
validator = PriceValidator.from_env(w3)
out("✅ Price feed and execution engine initialized")
out()

# Initialize supervisor (reads tokens from environment if available)
wallet_address = os.environ.get('WALLET_ADDRESS')
telegram_bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
telegram_chat_id = os.environ.get('TELEGRAM_CHAT_ID')
discord_webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')

gc = config.get('global_controls', {})
monitor_cfg = gc.get('monitoring', {})
risk_cfg = gc.get('risk_layer', {})
health_check_interval = int(monitor_cfg.get('health_check_interval_seconds', 30))
alert_on_trade = bool(monitor_cfg.get('telegram_alert_on_trade', False))

supervisor = TradingSupervisor(
    w3=w3,
    wallet_address=wallet_address,
    telegram_bot_token=telegram_bot_token,
    telegram_chat_id=telegram_chat_id,
    discord_webhook_url=discord_webhook_url,
    max_drawdown_pct=float(config.get('global_controls', {}).get('emergency_shutdown_triggers', {}).get('max_portfolio_drawdown_pct', 15))
)
# Note: keep default loss thresholds from TradingSupervisor unless explicitly provided elsewhere

# Trading state
trade_log = []
opportunities_log = []

# ----- Risk Layer State -----
state_dir = Path('state')
state_dir.mkdir(exist_ok=True)
risk_state_file = state_dir / 'risk_state.json'
kill_switch_file = Path(risk_cfg.get('kill_switch_file', 'state/kill_switch.flag'))
max_session_loss_pct = float(risk_cfg.get('max_session_loss_pct', 1.0))
max_daily_loss_pct = float(risk_cfg.get('max_daily_loss_pct', 3.0))
equity_reference = risk_cfg.get('equity_reference', 'manual')
manual_equity_usd = float(risk_cfg.get('manual_equity_usd', capital))

def _load_risk_state() -> dict:
    if risk_state_file.exists():
        try:
            return json.loads(risk_state_file.read_text())
        except Exception:
            return {}
    return {}

def _save_risk_state(data: dict) -> None:
    try:
        risk_state_file.write_text(json.dumps(data, indent=2, sort_keys=True))
    except Exception:
        pass

def _today_key() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%d')

def _get_equity_start() -> float:
    # TODO: extend for wallet-based dynamic equity
    if equity_reference == 'manual':
        return manual_equity_usd
    return manual_equity_usd  # fallback

risk_state = _load_risk_state()
today_key = _today_key()
today_bucket = risk_state.get(today_key, {'daily_pnl_usd': 0.0})
session_pnl_usd = 0.0
equity_start = _get_equity_start()
kill_switch_reason: Optional[str] = None

# Opportunity handler
async def handle_opportunity(opp: ArbitrageOpportunity):
    """Handle detected arbitrage opportunity"""
    global session_pnl_usd, kill_switch_reason
    opportunities_log.append({
        'timestamp': opp.timestamp,
        'buy_dex': opp.buy_dex,
        'sell_dex': opp.sell_dex,
        'tokens': '/'.join(opp.token_path),
        'profit_bps': opp.profit_bps,
        'net_profit_usd': opp.net_profit_usd,
        'priority': opp.execution_priority
    })
    
    out(f"💎 Opportunity: {opp.buy_dex} → {opp.sell_dex} | "
        f"{'/'.join(opp.token_path)} | ${opp.net_profit_usd:.2f} net")

    # Gate execution with multi-source price validation (optional env toggle)
    enable_validation = _env_flag('ENABLE_PRICE_VALIDATION', True)
    use_swarm = _env_flag('ENABLE_SWARM_VALIDATION', False)
    if enable_validation:
        # Map token symbol to address using feed's registry (validate base asset e.g., WETH)
        base_symbol = opp.token_path[0]
        token_address = price_feed.tokens.get(base_symbol)
        if token_address:
            try:
                vres = await validator.validate_opportunity(
                    token_address=token_address,
                    on_chain_buy_price=opp.buy_price,
                    on_chain_sell_price=opp.sell_price,
                    spread_bps=float(opp.profit_bps),
                    expected_profit_usd=opp.net_profit_usd,
                    use_swarm=bool(use_swarm)
                )
                opportunities_log[-1]['validator'] = {
                    'is_valid': vres.is_valid,
                    'confidence': round(vres.confidence_score, 1),
                    'sources': f"{vres.sources_agreed}/{vres.sources_total}",
                    'reasoning': vres.reasoning[:140]
                }
                if not vres.is_valid:
                    out(f"⏭️  Skipping (validator): {vres.reasoning}")
                    return
            except Exception as e:
                out(f"⚠️  Validator error, proceeding without: {e}")
        else:
            out(f"⚠️  No token address mapping for {base_symbol}; skipping validation")
    
    # Execute if profitable enough (use global min_profit_usd from config)
    if opp.net_profit_usd > min_profit_usd and kill_switch_reason is None:
        # Check wallet balances and calculate trade amount dynamically
        max_position_usd = float(os.getenv('MAX_POSITION_USD', '25.0'))
        
        # Get balances for both tokens
        token_in_symbol = opp.token_path[0]
        token_out_symbol = opp.token_path[1]
        
        balance_in = execution_engine.get_token_balance(token_in_symbol) if not paper_mode else 1000
        balance_out = execution_engine.get_token_balance(token_out_symbol) if not paper_mode else 1000
        
        # Calculate USD values of balances
        balance_in_usd = balance_in * opp.buy_price if token_in_symbol == "WETH" else balance_in
        balance_out_usd = balance_out * opp.sell_price if token_out_symbol == "WETH" else balance_out
        
        # Determine which direction we can trade based on available balance
        can_sell_in = balance_in_usd >= max_position_usd * 0.5  # Need at least 50% of max position
        can_buy_in = balance_out_usd >= max_position_usd * 0.5
        
        if not can_sell_in and not can_buy_in:
            out(f"⏭️  Insufficient balance: {token_in_symbol}=${balance_in_usd:.2f}, {token_out_symbol}=${balance_out_usd:.2f}")
            return
        
        # Choose trade direction based on available balance
        if can_sell_in:
            # Normal direction: sell token_in, buy token_out
            trade_size_usd = min(max_position_usd, balance_in_usd * 0.9)  # Use 90% of balance for safety
            amount_in = trade_size_usd / opp.buy_price if token_in_symbol == "WETH" else trade_size_usd
        else:
            # Reverse direction: we have token_out, so swap the trade
            out(f"🔄 Reversing trade direction (have {token_out_symbol}, not {token_in_symbol})")
            token_in_symbol, token_out_symbol = token_out_symbol, token_in_symbol
            trade_size_usd = min(max_position_usd, balance_out_usd * 0.9)
            amount_in = trade_size_usd / opp.sell_price if token_in_symbol == "WETH" else trade_size_usd
            # Swap buy/sell dex too
            opp.buy_dex, opp.sell_dex = opp.sell_dex, opp.buy_dex
            opp.buy_price, opp.sell_price = opp.sell_price, opp.buy_price
        
        out(f"💰 Trade size: ${trade_size_usd:.2f} ({amount_in:.6f} {token_in_symbol})")
        
        order = TradeOrder(
            order_id=f"ORDER_{len(trade_log)+1:03d}",
            dex=opp.buy_dex,
            token_in=token_in_symbol,
            token_out=token_out_symbol,
            amount_in=amount_in,
            expected_amount_out=amount_in * opp.sell_price if token_in_symbol == "WETH" else amount_in / opp.sell_price,
            min_amount_out=amount_in * opp.sell_price * 0.99 if token_in_symbol == "WETH" else amount_in / opp.sell_price * 0.99,
            deadline_seconds=30,
            gas_price_gwei=0.5,
            use_flashbots=True
        )
        
        result = await execution_engine.execute_trade(order)
        
        trade_entry = {
            'timestamp': result.timestamp,
            'order_id': order.order_id,
            'dex': order.dex,
            'pair': f"{order.token_in}/{order.token_out}",
            'success': result.success,
            'gas_cost_usd': result.gas_cost_usd,
            'net_profit_usd': result.net_profit_usd,
            'execution_ms': result.execution_time_ms
        }
        trade_log.append(trade_entry)

        # ----- Update Risk State -----
        realized_pnl = result.net_profit_usd
        session_nonlocal = realized_pnl  # value for closure clarity (not used elsewhere directly)
        # Update aggregates
        session_pnl_usd += realized_pnl
        today_bucket['daily_pnl_usd'] = float(today_bucket.get('daily_pnl_usd', 0.0) + realized_pnl)

        # Compute drawdowns (only care about losses)
        session_dd_pct = (-session_pnl_usd / equity_start * 100.0) if session_pnl_usd < 0 else 0.0
        daily_dd_pct = (-today_bucket['daily_pnl_usd'] / equity_start * 100.0) if today_bucket['daily_pnl_usd'] < 0 else 0.0

        trade_entry['session_pnl_usd'] = session_pnl_usd
        trade_entry['session_drawdown_pct'] = round(session_dd_pct, 4)
        trade_entry['daily_pnl_usd'] = today_bucket['daily_pnl_usd']
        trade_entry['daily_drawdown_pct'] = round(daily_dd_pct, 4)

        # Persist incremental risk state
        risk_state[today_key] = today_bucket
        _save_risk_state(risk_state)

        # Check thresholds
        if kill_switch_reason is None:
            if session_dd_pct >= max_session_loss_pct:
                kill_switch_reason = f"Session loss limit hit: {session_dd_pct:.2f}% >= {max_session_loss_pct:.2f}%"
            elif daily_dd_pct >= max_daily_loss_pct:
                kill_switch_reason = f"Daily loss limit hit: {daily_dd_pct:.2f}% >= {max_daily_loss_pct:.2f}%"

            if kill_switch_reason:
                try:
                    kill_switch_file.parent.mkdir(exist_ok=True)
                    kill_switch_file.write_text(kill_switch_reason)
                except Exception:
                    pass
                supervisor.kill_switch_active = True
                out(f"⛔ Kill-switch engaged: {kill_switch_reason}")
        
        # Record with supervisor
        try:
            supervisor.record_trade(success=result.success, pnl_usd=result.net_profit_usd)
            if alert_on_trade and telegram_bot_token and telegram_chat_id:
                await supervisor.send_telegram_alert(
                    (
                        f"<b>Trade {order.order_id}</b> on {order.dex}\n"
                        f"Pair: {order.token_in}/{order.token_out}\n"
                        f"P&L: ${result.net_profit_usd:.2f} | Gas: ${result.gas_cost_usd:.2f}"
                    ),
                    level=AlertLevel.INFO if result.success else AlertLevel.WARNING
                )
        except Exception:
            pass

        status = "✅" if result.success else "❌"
        out(f"{status} Trade {order.order_id}: ${result.net_profit_usd:.2f} net profit")

# Register handler
price_feed.register_opportunity_callback(handle_opportunity)

def _resolve_duration_seconds() -> int:
    """Resolve session duration from environment with precedence:
    1) QUICK_TEST_RUN flag (10s)
    2) Config monitoring.session_minutes
    3) SESSION_DURATION_MINUTES env var
    4) Mode-based defaults (10m paper / 30m live)"""
    if quick_test_run:
        return 10
    # Config override first (explicit strategy intention)
    cfg_minutes = (
        config.get('global_controls', {})
              .get('monitoring', {})
              .get('session_minutes')
    )
    if cfg_minutes is not None:
        try:
            return max(1, int(float(cfg_minutes) * 60))
        except Exception:
            out(f"⚠️ Invalid config session_minutes='{cfg_minutes}', ignoring")
    # Env var next
    raw_env = os.environ.get('SESSION_DURATION_MINUTES')
    if raw_env:
        try:
            minutes = float(raw_env)
            if minutes <= 0:
                raise ValueError("SESSION_DURATION_MINUTES must be > 0")
            return max(1, int(minutes * 60))
        except Exception:
            out(f"⚠️ Invalid SESSION_DURATION_MINUTES='{raw_env}', falling back to defaults")
    # Defaults
    return 10 * 60 if paper_mode else 30 * 60

duration_seconds = _resolve_duration_seconds()

out("🔥 STARTING TRADING SESSION")
out("=" * 80)
def _format_duration(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds} seconds"
    if seconds < 600:
        return f"{seconds/60:.1f} minutes"
    if seconds < 3600:
        return f"{int(round(seconds/60))} minutes"
    hours = seconds/3600
    if hours < 10:
        return f"{hours:.1f} hours"
    return f"{int(round(hours))} hours"

out(f"Planned Duration: {_format_duration(duration_seconds)}")
if duration_seconds < 30 and not quick_test_run:
    out("⚠️ VERY SHORT SESSION (<30s) - check configuration")
out("Press Ctrl+C to stop early")
out("=" * 80)
out()

# Run trading session
async def run_trading_session():
    try:
        # Get max position and scan interval from env
        max_position_usd = float(os.getenv('MAX_POSITION_USD', '25.0'))
        scan_interval_ms = int(os.getenv('SCAN_INTERVAL_MS', '2000'))
        feed_task = asyncio.create_task(price_feed.monitor_loop(scan_interval_ms=scan_interval_ms, max_position_usd=max_position_usd))
        # Start supervisor monitoring
        sup_task = asyncio.create_task(supervisor.monitor_loop(interval_seconds=health_check_interval))

        start_ts = asyncio.get_event_loop().time()
        end_ts = start_ts + duration_seconds
        # Periodically check for kill-switch or time expiry
        while asyncio.get_event_loop().time() < end_ts:
            if supervisor.kill_switch_active:
                out("\n⛔ Kill-switch active. Stopping trading...")
                break
            # External file kill-switch check
            if kill_switch_file.exists() and not supervisor.kill_switch_active:
                try:
                    kill_switch_reason = kill_switch_file.read_text().strip() or 'external kill switch'
                except Exception:
                    kill_switch_reason = 'external kill switch'
                out("\n⛔ External kill-switch file detected. Stopping trading...")
                supervisor.kill_switch_active = True
                break
            await asyncio.sleep(1)

        price_feed.stop()
        try:
            await feed_task
        except Exception as e:
            out(f"\n⚠️  Price feed error: {e}")
            import traceback
            traceback.print_exc()
        # Allow supervisor to notice stop and exit
        if not supervisor.kill_switch_active:
            # one last check and then stop the supervisor task
            await asyncio.sleep(0.1)
        sup_task.cancel()
        try:
            await sup_task
        except asyncio.CancelledError:
            pass
    except KeyboardInterrupt:
        out("\n⚠️  Interrupted by user")
        price_feed.stop()

# Execute
session_start_wall = datetime.now(timezone.utc)
try:
    asyncio.run(run_trading_session())
except KeyboardInterrupt:
    out("\n⚠️  Session stopped by user")
actual_elapsed = int((datetime.now(timezone.utc) - session_start_wall).total_seconds())

out()
out("=" * 80)
out("📊 SESSION SUMMARY")
out("=" * 80)

# Results
out(f"Planned duration: {_format_duration(duration_seconds)}")
out(f"Actual elapsed: {_format_duration(actual_elapsed)}")
out(f"Opportunities detected: {len(opportunities_log)}")
out(f"Trades executed: {len(trade_log)}")
out(f"Session PnL: ${session_pnl_usd:.2f}")
out(f"Daily PnL (UTC {today_key}): ${today_bucket['daily_pnl_usd']:.2f}")
if kill_switch_reason:
    out(f"Kill-switch reason: {kill_switch_reason}")

if trade_log:
    successful = sum(1 for t in trade_log if t['success'])
    total_profit = sum(t['net_profit_usd'] for t in trade_log)
    total_gas = sum(t['gas_cost_usd'] for t in trade_log)
    
    out(f"Successful trades: {successful}/{len(trade_log)}")
    out(f"Win rate: {(successful/len(trade_log)*100):.1f}%")
    out(f"Total gas cost: ${total_gas:.2f}")
    out(f"Net P&L: ${total_profit:.2f}")
    out(f"Return: {(total_profit/capital*100):.3f}%")
else:
    out("No trades executed (market may be quiet)")

out()

# Save report
session_dd_pct_final = (-session_pnl_usd / equity_start * 100.0) if session_pnl_usd < 0 else 0.0
daily_dd_pct_final = (-today_bucket['daily_pnl_usd'] / equity_start * 100.0) if today_bucket['daily_pnl_usd'] < 0 else 0.0

report = {
    'session_start': datetime.now(timezone.utc).isoformat(),
    'planned_duration_seconds': duration_seconds,
    'actual_elapsed_seconds': actual_elapsed,
    'mode': 'LIVE' if not paper_mode else 'PAPER',
    'capital': capital,
    'opportunities_detected': len(opportunities_log),
    'trades_executed': len(trade_log),
    'trade_log': trade_log,
    'opportunities_log': opportunities_log,
    'risk': {
        'equity_start_usd': equity_start,
        'session_pnl_usd': session_pnl_usd,
        'daily_pnl_usd': today_bucket.get('daily_pnl_usd', 0.0),
        'session_drawdown_pct': round(session_dd_pct_final, 4),
        'daily_drawdown_pct': round(daily_dd_pct_final, 4),
        'max_session_loss_pct': max_session_loss_pct,
        'max_daily_loss_pct': max_daily_loss_pct,
        'kill_switch_engaged': bool(kill_switch_reason),
        'kill_switch_reason': kill_switch_reason
    }
}

report_file = f"logs/session_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
Path('logs').mkdir(exist_ok=True)
with open(report_file, 'w', encoding='utf-8') as f:
    json.dump(report, f, indent=2, default=str)

out(f"📁 Full report saved: {report_file}")
out()
out("✅ Session complete. Dragon returns to lair.")
out("=" * 80)



