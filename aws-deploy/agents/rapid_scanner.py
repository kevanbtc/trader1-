"""
RAPID SCANNER - Every 2 minutes during active moves
Catches fast-moving setups
"""

import sys
import time
from datetime import datetime

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from multi_strategy_executor import MultiStrategyExecutor

def rapid_scan():
    """Run scan every 2 minutes"""
    executor = MultiStrategyExecutor()
    scan_count = 0
    
    print("\n" + "="*100)
    print("⚡ RAPID SCANNER - Active Move Detected!")
    print("="*100)
    print("ARB & OP pumping with 14x-16x volume")
    print("Scanning every 2 minutes to catch the peak\n")
    
    try:
        while True:
            scan_count += 1
            print(f"\n{'='*100}")
            print(f"⚡ RAPID SCAN #{scan_count} - {datetime.now().strftime('%H:%M:%S')}")
            print(f"{'='*100}")
            
            opportunities = executor.run_full_scan()
            
            if opportunities:
                print("\n" + "🚨"*40)
                print("🚨 90%+ CONFIDENCE HIT! CHECK opportunities.json")
                print("🚨"*40)
                # Alert sound
                print("\a" * 5)
                time.sleep(30)  # Wait 30s after finding opportunity
            
            print(f"\n⏰ Next rapid scan in 2 minutes... (Scan #{scan_count + 1})")
            time.sleep(120)  # 2 minutes
            
    except KeyboardInterrupt:
        print(f"\n\n🛑 Rapid scanner stopped after {scan_count} scans")

if __name__ == "__main__":
    rapid_scan()
