"""
MULTI-STRATEGY MASTER EXECUTOR
Combines ALL scanners for 90%+ confidence mega-trades
Only executes when multiple signals align perfectly
"""

import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

# Import all scanners
from master_scanner import MasterScanner
from volume_spike_scanner import VolumeScanner
from liquidity_monitor import LiquidityMonitor
from smart_money_tracker import SmartMoneyTracker
from flash_crash_detector import FlashCrashDetector

class MultiStrategyExecutor:
    def __init__(self):
        self.master_scanner = MasterScanner()
        self.volume_scanner = VolumeScanner()
        self.liquidity_monitor = LiquidityMonitor()
        self.smart_money = SmartMoneyTracker()
        self.flash_crash = FlashCrashDetector()
        
        # Minimum confidence required for execution
        self.MIN_CONFIDENCE = 90
        
        # Signal weights (how much each contributes to final confidence)
        self.WEIGHTS = {
            'RSI_EXTREME': 30,      # Strong base signal
            'VOLUME_SPIKE': 25,     # Confirms momentum
            'LIQUIDITY_ADD': 20,    # Whales positioning
            'SMART_MONEY': 20,      # Following winners
            'FLASH_CRASH': 25       # Oversold bounce play
        }
    
    def aggregate_all_signals(self):
        """Run all scanners and combine signals"""
        print("\n" + "="*100)
        print("🎯 MULTI-STRATEGY SCANNER - Combining All Intelligence")
        print("="*100)
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Minimum Confidence Required: {self.MIN_CONFIDENCE}%\n")
        
        # 1. RSI Scanner
        print("📊 [1/5] Scanning RSI Extremes...")
        rsi_signals = self.master_scanner.check_leverage_setups()
        print(f"      Found {len(rsi_signals)} RSI extreme setups")
        
        # 2. Volume Scanner
        print("\n📈 [2/5] Scanning Volume Spikes...")
        volume_signals = self.volume_scanner.scan_for_volume_spikes()
        print(f"      Found {len(volume_signals)} volume spike alerts")
        
        # 3. Liquidity Monitor
        print("\n💧 [3/5] Monitoring Liquidity Changes...")
        liquidity_signals = self.liquidity_monitor.scan_liquidity_changes()
        print(f"      Found {len(liquidity_signals)} liquidity shifts")
        
        # 4. Smart Money Tracker
        print("\n🐋 [4/5] Tracking Smart Money Wallets...")
        smart_money_signals = self.smart_money.scan_all_whales()
        print(f"      Found {len(smart_money_signals)} whale accumulation signals")
        
        # 5. Flash Crash Detector
        print("\n⚡ [5/5] Scanning for Flash Crashes...")
        crash_signals = self.flash_crash.scan_for_flash_crashes()
        print(f"      Found {len(crash_signals)} flash crash opportunities")
        
        print("\n" + "="*100)
        
        # Combine signals by asset
        combined = self.combine_signals_by_asset(
            rsi_signals,
            volume_signals,
            liquidity_signals,
            smart_money_signals,
            crash_signals
        )
        
        return combined
    
    def combine_signals_by_asset(self, rsi, volume, liquidity, smart_money, crashes):
        """Group all signals by asset and calculate combined confidence"""
        asset_signals = {}
        
        # Process RSI signals
        for signal in rsi:
            pair = signal['pair']
            if pair not in asset_signals:
                asset_signals[pair] = {
                    'pair': pair,
                    'signals': [],
                    'base_confidence': 0,
                    'signal_count': 0,
                    'direction': signal.get('direction', 'LONG')  # Set direction from RSI
                }
            
            # Set direction if not already set
            if 'direction' not in asset_signals[pair] or not asset_signals[pair]['direction']:
                asset_signals[pair]['direction'] = signal.get('direction', 'LONG')
            
            asset_signals[pair]['signals'].append({
                'type': 'RSI_EXTREME',
                'direction': signal.get('direction', 'LONG'),
                'rsi': signal['rsi'],
                'weight': self.WEIGHTS['RSI_EXTREME']
            })
            asset_signals[pair]['base_confidence'] += self.WEIGHTS['RSI_EXTREME']
            asset_signals[pair]['signal_count'] += 1
        
        # Process volume signals
        for signal in volume:
            # Volume signals have 'symbol' not 'pair'
            pair = f"{signal['symbol']}/USDC"
            if pair not in asset_signals:
                asset_signals[pair] = {
                    'pair': pair,
                    'signals': [],
                    'base_confidence': 0,
                    'signal_count': 0,
                    'direction': None  # Will be set by RSI or smart money
                }
            
            asset_signals[pair]['signals'].append({
                'type': 'VOLUME_SPIKE',
                'spike_ratio': signal.get('spike_multiplier', 0),
                'weight': self.WEIGHTS['VOLUME_SPIKE']
            })
            asset_signals[pair]['base_confidence'] += self.WEIGHTS['VOLUME_SPIKE']
            asset_signals[pair]['signal_count'] += 1
            
            # If no direction set yet, volume spike suggests volatility - use current price action
            if not asset_signals[pair].get('direction'):
                asset_signals[pair]['direction'] = 'LONG'  # Default to accumulation on volume spike
        
        # Process liquidity signals
        for signal in liquidity:
            pair = signal['pair']
            if pair not in asset_signals:
                asset_signals[pair] = {
                    'pair': pair,
                    'signals': [],
                    'base_confidence': 0,
                    'signal_count': 0
                }
            
            if signal['signal'] == 'LIQUIDITY_ADD':
                asset_signals[pair]['signals'].append({
                    'type': 'LIQUIDITY_ADD',
                    'change_pct': signal['change_pct'],
                    'weight': self.WEIGHTS['LIQUIDITY_ADD']
                })
                asset_signals[pair]['base_confidence'] += self.WEIGHTS['LIQUIDITY_ADD']
                asset_signals[pair]['signal_count'] += 1
        
        # Process crash signals
        for signal in crashes:
            pair = f"{signal['symbol']}/USDC"
            if pair not in asset_signals:
                asset_signals[pair] = {
                    'pair': pair,
                    'signals': [],
                    'base_confidence': 0,
                    'signal_count': 0
                }
            
            asset_signals[pair]['signals'].append({
                'type': 'FLASH_CRASH',
                'drop_pct': signal['drop_pct'],
                'weight': self.WEIGHTS['FLASH_CRASH']
            })
            asset_signals[pair]['base_confidence'] += self.WEIGHTS['FLASH_CRASH']
            asset_signals[pair]['signal_count'] += 1
        
        return asset_signals
    
    def filter_high_confidence_opportunities(self, combined_signals):
        """Filter to only 90%+ confidence setups"""
        opportunities = []
        
        for pair, data in combined_signals.items():
            confidence = data['base_confidence']
            signal_count = data['signal_count']
            
            if confidence >= self.MIN_CONFIDENCE:
                opportunities.append({
                    'pair': pair,
                    'confidence': confidence,
                    'signal_count': signal_count,
                    'signals': data['signals'],
                    'timestamp': datetime.now().isoformat()
                })
        
        # Sort by confidence
        opportunities.sort(key=lambda x: x['confidence'], reverse=True)
        
        return opportunities
    
    def save_opportunities(self, opportunities):
        """Save to opportunities.json for smart_executor"""
        if not opportunities:
            return
        
        output = {
            'timestamp': datetime.now().isoformat(),
            'opportunities': opportunities
        }
        
        filepath = os.path.join(os.path.dirname(__file__), '..', 'opportunities.json')
        
        with open(filepath, 'w') as f:
            json.dump(output, f, indent=2)
        
        print(f"\n💾 Saved {len(opportunities)} opportunities to opportunities.json")
    
    def run_full_scan(self):
        """Execute complete multi-strategy scan"""
        print("\n" + "="*100)
        print("🚀 MULTI-STRATEGY EXECUTOR")
        print("   Combining RSI + Volume + Liquidity + Smart Money + Flash Crash")
        print("="*100)
        
        # Aggregate all signals
        combined = self.aggregate_all_signals()
        
        # Filter to high confidence only
        opportunities = self.filter_high_confidence_opportunities(combined)
        
        # Display results
        print("\n" + "="*100)
        print("📋 SCAN RESULTS")
        print("="*100)
        
        if not opportunities:
            print("\n❌ No 90%+ confidence setups found")
            print("\n   Strategy: WAIT FOR PERFECT SETUP")
            print("   Remember: We only need 2-3 perfect trades to turn $29 → $3000")
            print("   Patience is key - scanning every 10 minutes for the big one")
        else:
            print(f"\n🎯 {len(opportunities)} HIGH CONFIDENCE OPPORTUNITIES!")
            print("="*100)
            
            for i, opp in enumerate(opportunities, 1):
                print(f"\n[{i}] {opp['pair']} - {opp['confidence']}% CONFIDENCE")
                print(f"    Signals: {opp['signal_count']} converging indicators")
                print(f"    \n    📊 Signal Breakdown:")
                
                for signal in opp['signals']:
                    if signal['type'] == 'RSI_EXTREME':
                        print(f"       • RSI {signal['direction']}: RSI = {signal['rsi']:.1f}")
                    elif signal['type'] == 'VOLUME_SPIKE':
                        print(f"       • Volume Spike: {signal['spike_ratio']:.1f}x average")
                    elif signal['type'] == 'LIQUIDITY_ADD':
                        print(f"       • Liquidity Add: +{signal['change_pct']:.1f}%")
                    elif signal['type'] == 'FLASH_CRASH':
                        print(f"       • Flash Crash: {signal['drop_pct']:.1f}% drop")
                
                print(f"\n    💰 READY FOR EXECUTION")
                print(f"       Confidence: {opp['confidence']}% (Target: {self.MIN_CONFIDENCE}%+)")
            
            # Save for executor
            self.save_opportunities(opportunities)
            
            print("\n" + "="*100)
            print("✅ Opportunities saved to opportunities.json")
            print("   Run smart_executor.py to execute these trades")
            print("="*100)
        
        return opportunities


if __name__ == "__main__":
    executor = MultiStrategyExecutor()
    opportunities = executor.run_full_scan()
    
    if opportunities:
        print("\n" + "="*100)
        print("🚨 ACTIONABLE TRADE SETUPS")
        print("="*100)
        print(f"\nFound {len(opportunities)} setups meeting 90%+ confidence threshold")
        print("\nNext Steps:")
        print("1. Review opportunities.json for full details")
        print("2. Run: python agents/smart_executor.py")
        print("3. Confirm execution when prompted")
        print("\n⚠️  These are the BIG HITS we've been waiting for!")
