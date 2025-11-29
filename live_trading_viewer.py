#!/usr/bin/env python3
"""
🎬 LIVE TRADING VIEWER
Real-time display of trading activity with beautiful formatting
"""

import os
import sys
import time
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import subprocess

# Color codes for terminal
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'
    GRAY = '\033[90m'

def clear_screen():
    """Clear terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    """Print the dashboard header"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 100}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}                           🎬 LIVE TRADING VIEWER - Real-Time Activity{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 100}{Colors.END}\n")

def format_usd(amount: float) -> str:
    """Format USD amount with color"""
    if amount > 0:
        return f"{Colors.GREEN}${amount:,.4f}{Colors.END}"
    elif amount < 0:
        return f"{Colors.RED}${amount:,.4f}{Colors.END}"
    else:
        return f"${amount:,.4f}"

def format_percentage(pct: float) -> str:
    """Format percentage with color"""
    if pct > 0:
        return f"{Colors.GREEN}{pct:+.2f}%{Colors.END}"
    elif pct < 0:
        return f"{Colors.RED}{pct:+.2f}%{Colors.END}"
    else:
        return f"{pct:.2f}%"

def format_timestamp(ts: str) -> str:
    """Format timestamp nicely"""
    try:
        dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        return dt.strftime('%H:%M:%S')
    except:
        return ts

def get_latest_session() -> Optional[Dict]:
    """Get the most recent session file"""
    logs_dir = Path('logs')
    if not logs_dir.exists():
        return None
    
    session_files = list(logs_dir.glob('session_*.json'))
    if not session_files:
        return None
    
    latest = max(session_files, key=lambda p: p.stat().st_mtime)
    try:
        with open(latest, 'r') as f:
            return json.load(f)
    except:
        return None

def get_latest_ledger() -> Optional[Dict]:
    """Get the most recent ledger file"""
    logs_dir = Path('logs')
    if not logs_dir.exists():
        return None
    
    ledger_files = list(logs_dir.glob('ledger_*.json'))
    if not ledger_files:
        return None
    
    latest = max(ledger_files, key=lambda p: p.stat().st_mtime)
    try:
        with open(latest, 'r') as f:
            return json.load(f)
    except:
        return None

def display_session_summary(session: Dict):
    """Display session overview"""
    print(f"{Colors.BOLD}{Colors.YELLOW}📊 SESSION OVERVIEW{Colors.END}")
    print(f"{'─' * 100}")
    
    mode = session.get('mode', 'UNKNOWN')
    mode_color = Colors.GREEN if mode == 'LIVE' else Colors.YELLOW
    print(f"  Mode: {mode_color}{mode}{Colors.END}")
    print(f"  Started: {format_timestamp(session.get('start_time', 'N/A'))}")
    print(f"  Duration: {session.get('actual_elapsed_str', 'N/A')}")
    print(f"  Scans: {session.get('scans_completed', 0):,}")
    print(f"  Opportunities: {session.get('opportunities_detected', 0):,}")
    print(f"  Trades: {session.get('trades_executed', 0)}")
    
    risk = session.get('risk', {})
    pnl = risk.get('session_pnl_usd', 0)
    print(f"  P&L: {format_usd(pnl)}")
    print()

def display_recent_scans(ledger: Dict, count: int = 10):
    """Display recent scan results"""
    print(f"{Colors.BOLD}{Colors.CYAN}🔍 RECENT SCANS (Last {count}){Colors.END}")
    print(f"{'─' * 100}")
    
    scans = ledger.get('scans', [])
    if not scans:
        print(f"  {Colors.GRAY}No scans yet...{Colors.END}\n")
        return
    
    recent_scans = scans[-count:]
    
    for scan in recent_scans:
        scan_num = scan.get('scan_number', 0)
        timestamp = format_timestamp(scan.get('timestamp', ''))
        opp_count = scan.get('opportunities_found', 0)
        
        if opp_count > 0:
            print(f"  {Colors.GREEN}✓{Colors.END} Scan #{scan_num} @ {timestamp} - {Colors.GREEN}{opp_count} opportunities{Colors.END}")
        else:
            print(f"  {Colors.GRAY}○{Colors.END} Scan #{scan_num} @ {timestamp} - {Colors.GRAY}Market quiet{Colors.END}")
    
    print()

def display_opportunities(ledger: Dict, count: int = 15):
    """Display recent opportunities"""
    print(f"{Colors.BOLD}{Colors.GREEN}💎 OPPORTUNITIES DETECTED (Last {count}){Colors.END}")
    print(f"{'─' * 100}")
    
    opportunities = ledger.get('opportunities', [])
    if not opportunities:
        print(f"  {Colors.GRAY}No opportunities detected yet...{Colors.END}\n")
        return
    
    recent_opps = opportunities[-count:]
    
    for opp in recent_opps:
        timestamp = format_timestamp(opp.get('timestamp', ''))
        pair = opp.get('pair', 'UNKNOWN')
        spread_pct = opp.get('spread_percent', 0)
        profit_usd = opp.get('estimated_profit_usd', 0)
        buy_dex = opp.get('buy_dex', 'N/A')
        sell_dex = opp.get('sell_dex', 'N/A')
        
        spread_color = Colors.GREEN if spread_pct > 0.5 else Colors.YELLOW
        print(f"  {Colors.CYAN}⚡{Colors.END} {timestamp} | {Colors.BOLD}{pair}{Colors.END}")
        print(f"     Spread: {spread_color}{spread_pct:.2f}%{Colors.END} | Profit: {format_usd(profit_usd)}")
        print(f"     Route: {buy_dex} → {sell_dex}")
    
    print()

def display_trades(session: Dict, count: int = 10):
    """Display recent trades"""
    print(f"{Colors.BOLD}{Colors.YELLOW}📈 RECENT TRADES (Last {count}){Colors.END}")
    print(f"{'─' * 100}")
    
    trades = session.get('trade_log', [])
    if not trades:
        print(f"  {Colors.GRAY}No trades executed yet...{Colors.END}\n")
        return
    
    recent_trades = trades[-count:]
    
    for trade in recent_trades:
        timestamp = format_timestamp(trade.get('timestamp', ''))
        pair = trade.get('pair', 'UNKNOWN')
        success = trade.get('success', False)
        profit = trade.get('net_profit_usd', 0)
        gas = trade.get('gas_cost_usd', 0)
        
        status_icon = f"{Colors.GREEN}✓{Colors.END}" if success else f"{Colors.RED}✗{Colors.END}"
        print(f"  {status_icon} {timestamp} | {Colors.BOLD}{pair}{Colors.END}")
        print(f"     Profit: {format_usd(profit)} | Gas: {format_usd(gas)}")
    
    print()

def display_statistics(session: Dict, ledger: Dict):
    """Display performance statistics"""
    print(f"{Colors.BOLD}{Colors.BLUE}📊 STATISTICS{Colors.END}")
    print(f"{'─' * 100}")
    
    # Session stats
    scans = session.get('scans_completed', 0)
    opportunities = session.get('opportunities_detected', 0)
    trades = session.get('trades_executed', 0)
    
    # Calculate rates
    if scans > 0:
        opp_rate = (opportunities / scans) * 100
        trade_rate = (trades / scans) * 100
    else:
        opp_rate = 0
        trade_rate = 0
    
    print(f"  Scan Frequency: ~{session.get('config', {}).get('scan_interval_ms', 0)}ms")
    print(f"  Opportunity Rate: {opp_rate:.2f}% ({opportunities}/{scans} scans)")
    print(f"  Trade Rate: {trade_rate:.2f}% ({trades}/{scans} scans)")
    
    # P&L stats
    risk = session.get('risk', {})
    pnl = risk.get('session_pnl_usd', 0)
    winning = risk.get('winning_trades', 0)
    losing = risk.get('losing_trades', 0)
    
    if (winning + losing) > 0:
        win_rate = (winning / (winning + losing)) * 100
        print(f"  Win Rate: {format_percentage(win_rate)} ({winning}W / {losing}L)")
    
    print(f"  Session P&L: {format_usd(pnl)}")
    print()

def display_wallet_info(session: Dict):
    """Display wallet information"""
    print(f"{Colors.BOLD}{Colors.CYAN}💼 WALLET{Colors.END}")
    print(f"{'─' * 100}")
    
    wallet = session.get('wallet_address', 'N/A')
    capital = session.get('config', {}).get('max_position_usd', 0)
    
    print(f"  Address: {wallet[:10]}...{wallet[-8:] if len(wallet) > 20 else ''}")
    print(f"  Trading Capital: ${capital:.2f}")
    print()

def main():
    """Main viewer loop"""
    print(f"\n{Colors.BOLD}{Colors.GREEN}Starting Live Trading Viewer...{Colors.END}\n")
    time.sleep(1)
    
    last_update = 0
    update_interval = 2  # seconds
    
    try:
        while True:
            current_time = time.time()
            
            # Only update every N seconds to avoid flicker
            if current_time - last_update < update_interval:
                time.sleep(0.5)
                continue
            
            last_update = current_time
            
            # Get latest data
            session = get_latest_session()
            ledger = get_latest_ledger()
            
            if not session and not ledger:
                clear_screen()
                print_header()
                print(f"{Colors.YELLOW}⚠️  Waiting for trading session to start...{Colors.END}\n")
                print(f"{Colors.GRAY}Start the trading bot with: python start_trading.py --duration 3600{Colors.END}\n")
                time.sleep(2)
                continue
            
            # Clear and redraw
            clear_screen()
            print_header()
            
            if session:
                display_session_summary(session)
                display_wallet_info(session)
            
            if ledger:
                display_recent_scans(ledger, count=8)
                display_opportunities(ledger, count=10)
            
            if session:
                display_trades(session, count=8)
                display_statistics(session, ledger or {})
            
            print(f"{Colors.GRAY}{'─' * 100}{Colors.END}")
            print(f"{Colors.GRAY}Last updated: {datetime.now().strftime('%H:%M:%S')} | Refreshing every {update_interval}s | Press Ctrl+C to exit{Colors.END}")
            
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}👋 Viewer stopped by user{Colors.END}\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Colors.RED}❌ Error: {e}{Colors.END}\n")
        sys.exit(1)

if __name__ == '__main__':
    main()
