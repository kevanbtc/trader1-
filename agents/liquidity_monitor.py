"""
DEX LIQUIDITY MONITOR - Detect massive liquidity changes
Large adds = whales positioning for pumps
Large removes = whales exiting before dumps
"""

import os
import sys
import requests
from datetime import datetime
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

# CryptoCompare API base
CRYPTOCOMPARE_BASE = "https://min-api.cryptocompare.com/data"

# Major DEX pairs to monitor on Arbitrum
MONITORED_PAIRS = [
    {'symbol': 'ETH/USDC', 'base': 'ETH', 'quote': 'USDC'},
    {'symbol': 'ARB/USDC', 'base': 'ARB', 'quote': 'USDC'},
    {'symbol': 'BTC/USDC', 'base': 'BTC', 'quote': 'USDC'},
    {'symbol': 'LINK/USDC', 'base': 'LINK', 'quote': 'USDC'},
    {'symbol': 'UNI/USDC', 'base': 'UNI', 'quote': 'USDC'},
    {'symbol': 'AAVE/USDC', 'base': 'AAVE', 'quote': 'USDC'}
]

class LiquidityMonitor:
    def __init__(self):
        self.last_volume_snapshot = {}
        
    def get_24h_volume(self, symbol_from, symbol_to='USDC'):
        """Get 24h trading volume from CryptoCompare"""
        try:
            url = f"{CRYPTOCOMPARE_BASE}/pricemultifull"
            params = {
                'fsyms': symbol_from,
                'tsyms': symbol_to
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'RAW' in data and symbol_from in data['RAW']:
                    if symbol_to in data['RAW'][symbol_from]:
                        raw_data = data['RAW'][symbol_from][symbol_to]
                        volume_24h = raw_data.get('VOLUME24HOUR', 0)
                        volume_24h_to = raw_data.get('VOLUME24HOURTO', 0)
                        
                        return {
                            'volume_from': volume_24h,
                            'volume_to': volume_24h_to,
                            'success': True
                        }
            
            return {'volume_from': 0, 'volume_to': 0, 'success': False}
            
        except Exception as e:
            print(f"Error fetching volume for {symbol_from}: {e}")
            return {'volume_from': 0, 'volume_to': 0, 'success': False}
    
    def calculate_volume_change(self, current_volume, pair_key):
        """Calculate percentage change from last snapshot"""
        if pair_key not in self.last_volume_snapshot:
            self.last_volume_snapshot[pair_key] = current_volume
            return 0.0
        
        last_volume = self.last_volume_snapshot[pair_key]
        if last_volume == 0:
            return 0.0
        
        change_pct = ((current_volume - last_volume) / last_volume) * 100
        self.last_volume_snapshot[pair_key] = current_volume
        
        return change_pct
    
    def scan_liquidity_changes(self):
        """Scan all pairs for significant liquidity changes"""
        print("\n" + "="*80)
        print("💧 DEX LIQUIDITY MONITOR - Tracking Whale Liquidity Moves")
        print("="*80)
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Monitoring {len(MONITORED_PAIRS)} pairs...")
        
        signals = []
        
        for pair in MONITORED_PAIRS:
            symbol = pair['symbol']
            base = pair['base']
            
            volume_data = self.get_24h_volume(base)
            
            if not volume_data['success']:
                print(f"   ⚪ {symbol}: Data unavailable")
                continue
            
            current_volume = volume_data['volume_to']  # Volume in USDC
            pair_key = f"{base}_USDC"
            
            change_pct = self.calculate_volume_change(current_volume, pair_key)
            
            # Format volume
            volume_str = f"${current_volume:,.0f}" if current_volume >= 1000 else f"${current_volume:.2f}"
            
            if change_pct > 50:
                # Major liquidity increase
                print(f"   🟢 {symbol}: {volume_str} 24h volume")
                print(f"      ⬆️ +{change_pct:.1f}% from last check - LIQUIDITY SURGE!")
                
                signals.append({
                    'pair': symbol,
                    'volume_24h': current_volume,
                    'change_pct': change_pct,
                    'signal': 'LIQUIDITY_ADD',
                    'confidence': min(85, 60 + int(change_pct / 5)),
                    'reason': f'Volume increased {change_pct:.1f}% - whales adding liquidity',
                    'recommendation': 'WATCH - Potential setup for large move',
                    'timestamp': datetime.now().isoformat()
                })
                
            elif change_pct < -50:
                # Major liquidity decrease
                print(f"   🔴 {symbol}: {volume_str} 24h volume")
                print(f"      ⬇️ {change_pct:.1f}% from last check - LIQUIDITY DRAIN!")
                
                signals.append({
                    'pair': symbol,
                    'volume_24h': current_volume,
                    'change_pct': change_pct,
                    'signal': 'LIQUIDITY_REMOVE',
                    'confidence': min(85, 60 + int(abs(change_pct) / 5)),
                    'reason': f'Volume decreased {abs(change_pct):.1f}% - whales pulling liquidity',
                    'recommendation': 'AVOID - Potential rug or dump incoming',
                    'timestamp': datetime.now().isoformat()
                })
                
            elif abs(change_pct) > 20:
                # Moderate change
                direction = "⬆️" if change_pct > 0 else "⬇️"
                print(f"   🟡 {symbol}: {volume_str} 24h volume")
                print(f"      {direction} {change_pct:+.1f}% from last check")
                
            else:
                # Normal range
                print(f"   ⚪ {symbol}: {volume_str} 24h volume ({change_pct:+.1f}%)")
        
        return signals
    
    def get_recommendation(self, signal):
        """Convert liquidity signal to trading recommendation"""
        if signal['signal'] == 'LIQUIDITY_ADD':
            if signal['change_pct'] > 100:
                return {
                    'action': 'STRONG_WATCH',
                    'confidence': 85,
                    'reason': 'Massive liquidity add - whales positioning for big move',
                    'strategy': 'Wait for entry signal from other scanners'
                }
            elif signal['change_pct'] > 50:
                return {
                    'action': 'WATCH',
                    'confidence': 70,
                    'reason': 'Significant liquidity add - increased activity',
                    'strategy': 'Monitor for entry opportunity'
                }
        
        elif signal['signal'] == 'LIQUIDITY_REMOVE':
            if signal['change_pct'] < -75:
                return {
                    'action': 'AVOID',
                    'confidence': 85,
                    'reason': 'Severe liquidity drain - potential rug or major exit',
                    'strategy': 'Stay away or close existing positions'
                }
            elif signal['change_pct'] < -50:
                return {
                    'action': 'CAUTION',
                    'confidence': 70,
                    'reason': 'Significant liquidity removal - risk increasing',
                    'strategy': 'Reduce position size or exit'
                }
        
        return None


if __name__ == "__main__":
    monitor = LiquidityMonitor()
    
    print("\n🔄 Running liquidity scan...")
    print("Note: First run establishes baseline, subsequent runs show changes\n")
    
    signals = monitor.scan_liquidity_changes()
    
    if signals:
        print("\n" + "="*80)
        print(f"🚨 {len(signals)} LIQUIDITY SIGNALS DETECTED")
        print("="*80)
        
        for signal in signals:
            rec = monitor.get_recommendation(signal)
            if rec:
                print(f"\n{signal['pair']} - {signal['signal']}")
                print(f"  Change: {signal['change_pct']:+.1f}%")
                print(f"  Action: {rec['action']}")
                print(f"  Confidence: {rec['confidence']}%")
                print(f"  Reason: {rec['reason']}")
                print(f"  Strategy: {rec['strategy']}")
    else:
        print("\n" + "="*80)
        print("✅ All liquidity levels normal")
        print("="*80)
        print("\nRun this scanner periodically to detect changes")
        print("Large liquidity shifts often precede major price moves")
