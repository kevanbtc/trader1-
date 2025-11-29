#!/usr/bin/env python3
"""
🔥 LIVE TRADING MONITOR 🔥
Real-time visual dashboard for trading activity
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime, timezone
from collections import deque

# Color codes for Windows CMD
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'

def clear_screen():
    """Clear terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def format_time(seconds):
    """Format seconds into human-readable time"""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}m"
    else:
        return f"{seconds/3600:.1f}h"

def format_usd(amount):
    """Format USD amount with color"""
    if amount > 0:
        return f"{Colors.GREEN}+${amount:.2f}{Colors.RESET}"
    elif amount < 0:
        return f"{Colors.RED}-${abs(amount):.2f}{Colors.RESET}"
    else:
        return f"${amount:.2f}"

def draw_box(title, content, width=78):
    """Draw a fancy box around content"""
    lines = [
        "┌" + "─" * (width - 2) + "┐",
        f"│ {Colors.BOLD}{title}{Colors.RESET}" + " " * (width - len(title) - 4) + "│"
    ]
    
    for line in content:
        padding = width - len(line) - 4
        lines.append(f"│ {line}" + " " * padding + " │")
    
    lines.append("└" + "─" * (width - 2) + "┘")
    return "\n".join(lines)

def get_latest_session():
    """Get the most recent session log"""
    logs_dir = Path(__file__).parent / 'logs'
    if not logs_dir.exists():
        return None
    
    session_files = list(logs_dir.glob('session_*.json'))
    if not session_files:
        return None
    
    latest = max(session_files, key=lambda p: p.stat().st_mtime)
    try:
        with open(latest, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None

def read_env():
    """Read current .env configuration"""
    env_file = Path(__file__).parent / '.env'
    config = {}
    
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()
    
    return config

def main():
    """Main monitoring loop"""
    print(f"{Colors.CYAN}Initializing Live Trading Monitor...{Colors.RESET}")
    time.sleep(1)
    
    # Track statistics
    scan_history = deque(maxlen=20)  # Last 20 scans
    opportunity_history = deque(maxlen=100)  # Last 100 opportunities
    trade_history = deque(maxlen=50)  # Last 50 trades
    
    while True:
        clear_screen()
        
        # Header
        print(f"{Colors.BOLD}{Colors.CYAN}{'='*78}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.YELLOW}🐉 TRADING DRAGON - LIVE MONITOR{Colors.RESET}".center(88))
        print(f"{Colors.BOLD}{Colors.CYAN}{'='*78}{Colors.RESET}")
        print()
        
        # Read configuration
        env_config = read_env()
        
        # Configuration Panel
        config_content = [
            f"Mode: {Colors.BOLD}{env_config.get('TRADING_MODE', 'UNKNOWN')}{Colors.RESET}",
            f"Paper Mode: {Colors.RED if env_config.get('ENABLE_PAPER_MODE', 'false') == 'true' else Colors.GREEN}{'ENABLED' if env_config.get('ENABLE_PAPER_MODE', 'false') == 'true' else 'DISABLED'}{Colors.RESET}",
            f"MCP Intelligence: {Colors.GREEN if env_config.get('ENABLE_MCP', 'false') == 'true' else Colors.RED}{'ENABLED' if env_config.get('ENABLE_MCP', 'false') == 'true' else 'DISABLED'}{Colors.RESET}",
            f"Swarm: {Colors.GREEN if env_config.get('ENABLE_SWARM', 'false') == 'true' else Colors.RED}{'ENABLED' if env_config.get('ENABLE_SWARM', 'false') == 'true' else 'DISABLED'}{Colors.RESET}",
            f"Max Position: ${env_config.get('MAX_POSITION_USD', 'N/A')} | Min Profit: ${env_config.get('MIN_PROFIT_USD', 'N/A')}",
            f"Scan Interval: {env_config.get('SCAN_INTERVAL_MS', 'N/A')}ms | Max Gas: {env_config.get('MAX_GAS_GWEI', 'N/A')} Gwei"
        ]
        
        print(draw_box("⚙️  CONFIGURATION", config_content))
        print()
        
        # Session Status
        session = get_latest_session()
        
        if session:
            session_content = [
                f"Session ID: {session.get('session_id', 'N/A')}",
                f"Started: {session.get('start_time', 'N/A')}",
                f"Duration: {format_time(session.get('duration_minutes', 0) * 60)}",
                f"Opportunities Detected: {Colors.YELLOW}{session.get('opportunities_detected', 0)}{Colors.RESET}",
                f"Trades Executed: {Colors.GREEN}{session.get('trades_executed', 0)}{Colors.RESET}",
                f"Session PnL: {format_usd(session.get('session_pnl_usd', 0))}"
            ]
            
            print(draw_box("📊 CURRENT SESSION", session_content))
            print()
            
            # Daily Performance
            daily_pnl = session.get('daily_pnl_usd', 0)
            daily_date = session.get('daily_pnl_date', 'N/A')
            
            daily_content = [
                f"Date: {daily_date}",
                f"Total PnL: {format_usd(daily_pnl)}",
                f"Win Rate: {session.get('win_rate', 0):.1f}%",
                f"Total Trades: {session.get('total_trades', 0)}"
            ]
            
            print(draw_box("💰 DAILY PERFORMANCE", daily_content))
            print()
            
        else:
            print(f"{Colors.YELLOW}⏳ Waiting for first session data...{Colors.RESET}")
            print()
        
        # Activity Log (last few events)
        print(f"{Colors.BOLD}📝 RECENT ACTIVITY{Colors.RESET}")
        print("─" * 78)
        
        if session and session.get('trades'):
            print(f"{Colors.GREEN}Recent trades found!{Colors.RESET}")
            for i, trade in enumerate(session['trades'][-5:], 1):  # Last 5 trades
                print(f"  {i}. {trade.get('timestamp', 'N/A')} - {trade.get('pair', 'N/A')}")
                print(f"     PnL: {format_usd(trade.get('pnl_usd', 0))} | Gas: ${trade.get('gas_cost_usd', 0):.3f}")
        else:
            print(f"{Colors.YELLOW}  No trades executed yet. Market scanning in progress...{Colors.RESET}")
        
        print()
        print("─" * 78)
        print(f"{Colors.CYAN}Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.RESET}")
        print(f"{Colors.MAGENTA}Press Ctrl+C to exit monitor{Colors.RESET}")
        
        # Refresh every 2 seconds
        time.sleep(2)

if __name__ == "__main__":
    # Enable ANSI colors on Windows
    if os.name == 'nt':
        os.system('color')
        # Enable ANSI escape sequences
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.GREEN}✅ Monitor stopped.{Colors.RESET}")
        sys.exit(0)
