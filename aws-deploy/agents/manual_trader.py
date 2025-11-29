"""
MANUAL TRADE EXECUTOR - For When You Want To GO NOW
Bypass all scanners and execute immediately on your command
"""

import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from professional_risk_manager import ProfessionalRiskManager
from execution_engine import ExecutionEngine

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

class ManualTrader:
    """Execute trades manually when YOU see the opportunity"""
    
    def __init__(self):
        self.risk_manager = ProfessionalRiskManager()
        self.execution_engine = ExecutionEngine()
    
    def execute_now(self, token, direction, confidence=95):
        """
        EXECUTE TRADE RIGHT NOW
        
        Args:
            token: 'ARB', 'OP', 'ETH', etc
            direction: 'LONG' or 'SHORT'
            confidence: Your confidence level (85-100)
        """
        
        print("\n" + "="*80)
        print(f"🚀 MANUAL TRADE EXECUTION")
        print("="*80)
        print(f"Token: {token}")
        print(f"Direction: {direction}")
        print(f"Confidence: {confidence}%")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80 + "\n")
        
        # Risk check
        allowed, reason, size_usd, size_pct = self.risk_manager.check_trade_allowed(confidence)
        
        if not allowed:
            print(f"❌ TRADE BLOCKED")
            print(f"Reason: {reason}")
            print(f"\n💡 Check risk manager status:")
            print(self.risk_manager.get_status_report())
            return False
        
        print(f"✅ RISK CHECK PASSED")
        print(f"Position Size: ${size_usd:.2f} ({size_pct*100:.1f}%)")
        
        # Confirm
        print(f"\n{'='*80}")
        print(f"⚠️  ABOUT TO EXECUTE LIVE TRADE")
        print(f"{'='*80}")
        print(f"Token: {token}")
        print(f"Direction: {direction}")
        print(f"Size: ${size_usd:.2f}")
        print(f"Confidence: {confidence}%")
        print(f"\nThis will use REAL MONEY from your wallet!")
        print(f"Wallet: 0x63d48340AB2c1E0e244F2987962C69A1C06d1e68")
        
        confirm = input(f"\nType 'YES' to confirm: ")
        
        if confirm.upper() != 'YES':
            print(f"\n❌ Trade cancelled")
            return False
        
        # Execute
        print(f"\n🚀 EXECUTING...")
        
        result = self.execution_engine.execute_swap(
            token,
            direction,
            size_usd,
            confidence
        )
        
        if result['success']:
            print(f"\n✅ TRADE EXECUTED!")
            print(f"TX Hash: {result['tx_hash']}")
            print(f"Link: https://arbiscan.io/tx/{result['tx_hash']}")
            
            # Record with risk manager
            entry_price = result.get('entry_price', 0)
            self.risk_manager.record_trade_open(
                token,
                direction,
                entry_price,
                size_usd,
                confidence
            )
            
            return True
        else:
            print(f"\n❌ EXECUTION FAILED")
            print(f"Reason: {result.get('reason', 'Unknown')}")
            return False

def main():
    """Manual trading interface"""
    trader = ManualTrader()
    
    print("\n" + "="*80)
    print("🎯 MANUAL TRADE EXECUTOR")
    print("="*80)
    print("\nAvailable tokens: ARB, OP, ETH, LINK, MATIC")
    print("Directions: LONG (buy) or SHORT (sell)")
    print("Confidence: 85-100 (higher = bigger position)")
    print("\nExample commands:")
    print("  'ARB LONG 95' - Buy ARB with 95% confidence")
    print("  'OP SHORT 90' - Short OP with 90% confidence")
    print("  'status' - Check risk manager status")
    print("  'quit' - Exit")
    print("="*80 + "\n")
    
    while True:
        try:
            cmd = input("Enter command: ").strip().upper()
            
            if cmd == 'QUIT':
                print("\n👋 Exiting manual trader")
                break
            
            elif cmd == 'STATUS':
                print(trader.risk_manager.get_status_report())
            
            elif cmd == 'ARB NOW' or cmd == 'OP NOW':
                # Quick execute current opportunities
                token = cmd.split()[0]
                print(f"\n🚀 Quick executing {token} LONG with 90% confidence")
                trader.execute_now(token, 'LONG', 90)
            
            else:
                parts = cmd.split()
                if len(parts) >= 2:
                    token = parts[0]
                    direction = parts[1]
                    confidence = int(parts[2]) if len(parts) > 2 else 90
                    
                    trader.execute_now(token, direction, confidence)
                else:
                    print("Invalid command. Use: TOKEN DIRECTION [CONFIDENCE]")
        
        except KeyboardInterrupt:
            print("\n\n👋 Exiting manual trader")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
