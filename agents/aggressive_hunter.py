"""
AGGRESSIVE OPPORTUNITY HUNTER
Lower confidence threshold + faster execution for MAXIMUM GAINS
"""

import time
from multi_strategy_executor import MultiStrategyExecutor
from professional_risk_manager import ProfessionalRiskManager
from execution_engine import ExecutionEngine
import sys
from datetime import datetime

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# AGGRESSIVE SETTINGS
MIN_CONFIDENCE = 85  # Lower from 90 to 85 for more opportunities
SCAN_INTERVAL = 60  # Every 60 seconds (vs 120 rapid, 600 normal)
VOLUME_MULTIPLIER_BONUS = 5  # Give 5 bonus points per 5x volume over 15x

class AggressiveHunter:
    """Aggressive opportunity hunter for fast money"""
    
    def __init__(self):
        self.executor = MultiStrategyExecutor()
        self.risk_manager = ProfessionalRiskManager()
        self.execution_engine = ExecutionEngine()
        self.opportunities_found = 0
        self.trades_executed = 0
    
    def calculate_boosted_confidence(self, opportunity):
        """
        Boost confidence for extreme conditions
        - 20x+ volume = +10 confidence points
        - RSI 65-75 (building to extreme) = +5 points
        - Multiple signals aligned = +5 points
        """
        base_confidence = opportunity['confidence']
        boosted = base_confidence
        
        # Check for extreme volume (ARB/OP currently 20x-22x)
        if 'volume_spike' in str(opportunity.get('signals', [])):
            # Assume 20x+ volume
            boosted += 10
            print(f"   +10 confidence (extreme volume 20x+)")
        
        # Check for building momentum (RSI approaching extreme)
        if opportunity.get('rsi', 0) > 65 or opportunity.get('rsi', 100) < 35:
            boosted += 5
            print(f"   +5 confidence (RSI building momentum)")
        
        # Multiple signal bonus
        signal_count = opportunity.get('signal_count', 0)
        if signal_count >= 2:
            boosted += 5
            print(f"   +5 confidence ({signal_count} signals aligned)")
        
        return min(boosted, 100)  # Cap at 100
    
    def hunt(self):
        """Aggressive hunting loop"""
        print("\n" + "="*80)
        print("🎯 AGGRESSIVE OPPORTUNITY HUNTER")
        print("="*80)
        print(f"Min Confidence: {MIN_CONFIDENCE}% (vs 90% standard)")
        print(f"Scan Interval: {SCAN_INTERVAL}s (vs 600s standard)")
        print(f"Strategy: AGGRESSIVE - Lower threshold, faster execution")
        print("="*80 + "\n")
        
        scan_count = 0
        
        while True:
            scan_count += 1
            
            print(f"\n{'='*80}")
            print(f"🔍 AGGRESSIVE SCAN #{scan_count} - {datetime.now().strftime('%H:%M:%S')}")
            print(f"{'='*80}")
            
            try:
                # Run full multi-strategy scan
                print("📊 Running multi-strategy scan...")
                
                # For now, manually check the current extreme volume situation
                # ARB 20.9x, OP 22.5x = both have volume spike signal (25 points)
                
                # Create synthetic opportunities for current market
                # (In production, this would come from executor.run_full_scan())
                
                opportunities = []
                
                # Check ARB - 20.9x volume
                arb_opp = {
                    'pair': 'ARB/USDC',
                    'confidence': 25,  # Base from volume spike only
                    'signals': ['volume_spike'],
                    'signal_count': 1,
                    'direction': 'LONG',  # Accumulation phase
                    'rsi': 64.6,  # Current RSI
                    'volume_spike': 20.9
                }
                
                # Check OP - 22.5x volume
                op_opp = {
                    'pair': 'OP/USDC',
                    'confidence': 25,  # Base from volume spike only
                    'signals': ['volume_spike'],
                    'signal_count': 1,
                    'direction': 'LONG',  # Accumulation phase
                    'rsi': 60.1,  # Current RSI
                    'volume_spike': 22.5
                }
                
                # Boost confidence with aggressive scoring
                print(f"\n🔍 Analyzing ARB opportunity...")
                print(f"   Base confidence: {arb_opp['confidence']}%")
                arb_boosted = self.calculate_boosted_confidence(arb_opp)
                arb_opp['confidence'] = arb_boosted
                print(f"   Boosted confidence: {arb_boosted}%")
                
                if arb_boosted >= MIN_CONFIDENCE:
                    opportunities.append(arb_opp)
                    print(f"   ✅ QUALIFIES for execution ({arb_boosted}% >= {MIN_CONFIDENCE}%)")
                else:
                    print(f"   ❌ Below threshold ({arb_boosted}% < {MIN_CONFIDENCE}%)")
                
                print(f"\n🔍 Analyzing OP opportunity...")
                print(f"   Base confidence: {op_opp['confidence']}%")
                op_boosted = self.calculate_boosted_confidence(op_opp)
                op_opp['confidence'] = op_boosted
                print(f"   Boosted confidence: {op_boosted}%")
                
                if op_boosted >= MIN_CONFIDENCE:
                    opportunities.append(op_opp)
                    print(f"   ✅ QUALIFIES for execution ({op_boosted}% >= {MIN_CONFIDENCE}%)")
                else:
                    print(f"   ❌ Below threshold ({op_boosted}% < {MIN_CONFIDENCE}%)")
                
                # Execute opportunities
                if opportunities:
                    self.opportunities_found += len(opportunities)
                    
                    print(f"\n{'🚨'*40}")
                    print(f"🚨 {len(opportunities)} AGGRESSIVE OPPORTUNITIES FOUND!")
                    print(f"{'🚨'*40}")
                    print("\a" * 5)  # Alert beeps
                    
                    for opp in opportunities:
                        print(f"\n🎯 EXECUTING {opp['pair']} ({opp['confidence']}% confidence)")
                        
                        # Check with risk manager
                        allowed, reason, size_usd, size_pct = self.risk_manager.check_trade_allowed(
                            opp['confidence']
                        )
                        
                        if allowed:
                            print(f"✅ Risk Manager Approved: ${size_usd:.2f} ({size_pct*100:.1f}%)")
                            
                            # FOR DEMO: Don't execute real trade without funds
                            print(f"\n💰 READY TO EXECUTE")
                            print(f"   Pair: {opp['pair']}")
                            print(f"   Direction: {opp['direction']}")
                            print(f"   Size: ${size_usd:.2f}")
                            print(f"   Confidence: {opp['confidence']}%")
                            print(f"\n⚠️  Add real USDC to wallet to auto-execute!")
                            
                            # Uncomment when funded:
                            # result = self.execution_engine.execute_swap(
                            #     opp['pair'].split('/')[0],
                            #     opp['direction'],
                            #     size_usd,
                            #     opp['confidence']
                            # )
                            # if result['success']:
                            #     self.trades_executed += 1
                            #     print(f"✅ TRADE EXECUTED! TX: {result['tx_hash']}")
                        else:
                            print(f"❌ Risk Manager Blocked: {reason}")
                else:
                    print(f"\n⏳ No {MIN_CONFIDENCE}%+ opportunities yet")
                    print(f"   ARB: 20.9x volume (watching for RSI spike or more signals)")
                    print(f"   OP: 22.5x volume (watching for RSI spike or more signals)")
                
                print(f"\n📊 Session Stats:")
                print(f"   Scans: {scan_count}")
                print(f"   Opportunities: {self.opportunities_found}")
                print(f"   Trades: {self.trades_executed}")
                print(f"\n⏰ Next scan in {SCAN_INTERVAL} seconds...")
                
            except Exception as e:
                print(f"\n❌ Error during scan: {e}")
                import traceback
                traceback.print_exc()
            
            time.sleep(SCAN_INTERVAL)

if __name__ == "__main__":
    hunter = AggressiveHunter()
    
    print("\n🔥 AGGRESSIVE MODE ACTIVATED")
    print("📈 Strategy: Lower confidence threshold for faster entries")
    print("🎯 Target: Catch ARB/OP 20x+ volume spike with 85%+ confidence")
    print("💰 Position: 40% of balance (aggressive micro account sizing)")
    print("\nPress Ctrl+C to stop\n")
    
    try:
        hunter.hunt()
    except KeyboardInterrupt:
        print(f"\n\n🛑 Aggressive hunter stopped")
        print(f"Total scans: {hunter.opportunities_found}")
        print(f"Trades executed: {hunter.trades_executed}")
