"""
Real-time Opportunity Ledger Viewer
Shows every scan attempt and all opportunities found
"""
import time
from pathlib import Path
from datetime import datetime

ledger_path = Path("logs/opportunity_ledger.log")

print("=" * 80)
print("📊 OPPORTUNITY LEDGER - LIVE VIEW")
print("=" * 80)
print(f"Watching: {ledger_path}")
print("Updates every 2 seconds | Press Ctrl+C to exit")
print("=" * 80)
print()

last_size = 0
scan_count = 0
total_opportunities = 0

while True:
    try:
        if ledger_path.exists():
            current_size = ledger_path.stat().st_size
            
            if current_size > last_size:
                # Read new content
                with open(ledger_path, "r", encoding="utf-8") as f:
                    f.seek(last_size)
                    new_content = f.read()
                    
                    # Print new content
                    print(new_content, end="")
                    
                    # Count scans and opportunities
                    scan_count += new_content.count("🔍 SCAN #")
                    total_opportunities += new_content.count("✅ Found")
                    
                last_size = current_size
            
            # Print status every iteration
            print(f"\r⏱️  {datetime.now().strftime('%H:%M:%S')} | Scans: {scan_count} | Total Opportunities Found: {total_opportunities}", end="", flush=True)
        else:
            print(f"\r⏱️  Waiting for ledger file to be created...", end="", flush=True)
        
        time.sleep(2)
        
    except KeyboardInterrupt:
        print("\n\n✅ Ledger viewer stopped")
        break
    except Exception as e:
        print(f"\n⚠️  Error: {e}")
        time.sleep(2)
