#!/usr/bin/env python3
"""
🚀 TRADING SYSTEM LAUNCHER
Starts all components: Bot, Viewer, Wallet Tracker, and Monitor
"""

import subprocess
import sys
import time
from pathlib import Path

VENV_PYTHON = Path('.venv/Scripts/python.exe')

def print_banner():
    print("\n" + "="*80)
    print("              🚀 APEX TRADING SYSTEM - FULL LAUNCH")
    print("="*80 + "\n")

def launch_component(script: str, title: str, color: str = "Cyan"):
    """Launch a component in a new PowerShell window"""
    cmd = [
        'powershell',
        '-NoExit',
        '-Command',
        f"$host.UI.RawUI.WindowTitle = '{title}'; "
        f"Write-Host ' {title}' -ForegroundColor {color}; "
        f"Write-Host ''; "
        f"{VENV_PYTHON} {script}"
    ]
    
    subprocess.Popen(cmd, cwd=Path.cwd())
    time.sleep(0.8)
    print(f"  ✓ {title} launched")

def main():
    print_banner()
    
    # Check if venv exists
    if not VENV_PYTHON.exists():
        print("❌ Virtual environment not found!")
        print("   Run: python -m venv .venv")
        print("   Then: .venv\\Scripts\\pip install -r requirements.txt")
        sys.exit(1)
    
    # Launch components
    print("Starting components...\n")
    
    launch_component('wallet_tracker.py', '💼 WALLET TRACKER', 'Green')
    launch_component('live_trading_viewer.py', '🎬 LIVE VIEWER', 'Cyan')
    launch_component('live_monitor.py', '📊 MONITOR', 'Yellow')
    
    print("\n✅ All monitoring components launched!")
    print("\nStarting main trading bot (2 hours)...")
    print("  - Profit threshold: $0.02")
    print("  - Scan speed: 250ms (4x/sec)")
    print("  - Mode: Check .env for TRADING_MODE\n")
    
    # Run main bot in this window
    subprocess.run([str(VENV_PYTHON), 'start_trading.py', '--duration', '7200'])

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Launcher stopped by user\n")
        sys.exit(0)
