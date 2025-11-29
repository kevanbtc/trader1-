"""
CONTINUOUS HUNTER - 24/7 Scanner Running Every 10 Minutes
Watches for 90%+ confidence setups and alerts immediately
"""

import os
import sys
import time
import json
from datetime import datetime

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from multi_strategy_executor import MultiStrategyExecutor

class ContinuousHunter:
    def __init__(self):
        self.executor = MultiStrategyExecutor()
        self.scan_count = 0
        self.last_signals = {
            'rsi': 0,
            'volume': 0,
            'liquidity': 0,
            'smart_money': 0,
            'flash_crash': 0
        }
        
    def print_banner(self):
        """Print startup banner"""
        print("\n" + "="*100)
        print("🎯 CONTINUOUS HUNTER - PATIENT MODE ACTIVATED")
        print("="*100)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Strategy: Turn $29 → $3000 with 2-3 PERFECT 90%+ confidence trades")
        print(f"Scan Interval: Every 10 minutes")
        print(f"Target: RSI Extreme + Volume Spike + Liquidity Surge = 90%+ CONFIDENCE")
        print("="*100)
        print("\n💡 Watching for the BIG HIT - patience is key!\n")
        
    def run_scan(self):
        """Run one complete scan cycle"""
        self.scan_count += 1
        
        print("\n" + "="*100)
        print(f"🔍 SCAN #{self.scan_count} - {datetime.now().strftime('%H:%M:%S')}")
        print("="*100)
        
        try:
            opportunities = self.executor.run_full_scan()
            
            if opportunities:
                print("\n" + "🚨"*30)
                print("🚨 ALERT! ALERT! ALERT! 🚨")
                print(f"🚨 {len(opportunities)} HIGH CONFIDENCE SETUPS FOUND! 🚨")
                print("🚨"*30)
                
                for opp in opportunities:
                    print(f"\n💰 {opp['pair']} - {opp['confidence']}% CONFIDENCE")
                    print(f"   Signals: {opp['signal_count']} indicators aligned")
                    for signal in opp['signals']:
                        print(f"   ✅ {signal['type']}")
                
                print("\n🎯 opportunities.json saved!")
                print("🎯 Run: python agents/smart_executor.py to EXECUTE")
                
                # Beep to alert
                print("\a" * 3)
                
            else:
                print("\n⏳ No 90%+ setups yet - PATIENCE MODE")
                print("   Current market signals:")
                print(f"   - RSI Extremes: Waiting for <25 or >75")
                print(f"   - Volume Spikes: Monitoring for 5x+ activity")
                print(f"   - Liquidity: Tracking whale movements")
                print(f"   - Smart Money: Following profitable wallets")
                print(f"   - Flash Crashes: Ready to catch dips")
                
        except Exception as e:
            print(f"\n❌ Error during scan: {e}")
            import traceback
            traceback.print_exc()
    
    def run_continuous(self):
        """Run scanner continuously every 10 minutes"""
        self.print_banner()
        
        try:
            while True:
                self.run_scan()
                
                # Wait 10 minutes
                print(f"\n⏰ Next scan in 10 minutes... (Scan #{self.scan_count + 1} at {datetime.now().replace(microsecond=0, second=0, minute=(datetime.now().minute + 10) % 60).strftime('%H:%M')})")
                print("   Press Ctrl+C to stop")
                
                time.sleep(600)  # 10 minutes
                
        except KeyboardInterrupt:
            print("\n\n" + "="*100)
            print("🛑 HUNTER STOPPED")
            print("="*100)
            print(f"Total Scans: {self.scan_count}")
            print(f"Duration: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("\nTo restart: python agents/continuous_hunter.py")
            print("="*100)

if __name__ == "__main__":
    hunter = ContinuousHunter()
    hunter.run_continuous()
