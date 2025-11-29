"""
VOLUME SPIKE SCANNER - Detect whale accumulation and big moves
When volume spikes 5x-10x above average = something big is coming
"""

import os
import sys
import requests
from datetime import datetime
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

class VolumeScanner:
    def __init__(self):
        self.base_url = "https://min-api.cryptocompare.com/data/v2"
        
    def get_volume_data(self, symbol, hours=24):
        """Get hourly volume data"""
        try:
            url = f"{self.base_url}/histohour?fsym={symbol}&tsym=USD&limit={hours}"
            response = requests.get(url, timeout=10)
            
            if response.status_code != 200:
                return None
                
            data = response.json()
            if data.get('Response') != 'Success':
                return None
                
            candles = data['Data']['Data']
            return candles
            
        except Exception as e:
            print(f"Error fetching volume for {symbol}: {e}")
            return None
    
    def calculate_volume_spike(self, candles):
        """Calculate if current volume is spiking vs average"""
        if not candles or len(candles) < 25:
            return None
            
        # Get volumes
        volumes = [float(c['volumefrom']) for c in candles]
        
        # Current volume (last hour)
        current_volume = volumes[-1]
        
        # Average of previous 24 hours (exclude current)
        avg_volume = sum(volumes[-25:-1]) / 24
        
        if avg_volume == 0:
            return None
            
        # Calculate spike multiplier
        spike_multiplier = current_volume / avg_volume
        
        return {
            'current_volume': current_volume,
            'avg_volume': avg_volume,
            'spike_multiplier': spike_multiplier,
            'is_spike': spike_multiplier >= 5.0  # 5x or more is a spike
        }
    
    def scan_for_volume_spikes(self):
        """Scan multiple pairs for volume spikes"""
        pairs = [
            ('ETH', 'Ethereum'),
            ('BTC', 'Bitcoin'),
            ('ARB', 'Arbitrum'),
            ('SOL', 'Solana'),
            ('AVAX', 'Avalanche'),
            ('OP', 'Optimism'),
            ('LINK', 'Chainlink'),
            ('UNI', 'Uniswap'),
            ('AAVE', 'Aave'),
            ('CRV', 'Curve')
        ]
        
        spikes = []
        
        print("=" * 80)
        print("📊 VOLUME SPIKE SCANNER")
        print("=" * 80)
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("\nLooking for 5x+ volume spikes (whale accumulation signals)\n")
        
        for symbol, name in pairs:
            candles = self.get_volume_data(symbol, hours=25)
            if not candles:
                continue
                
            analysis = self.calculate_volume_spike(candles)
            if not analysis:
                continue
                
            spike_mult = analysis['spike_multiplier']
            current_vol = analysis['current_volume']
            avg_vol = analysis['avg_volume']
            
            # Get current price
            price = float(candles[-1]['close'])
            
            if spike_mult >= 10:
                status = "🚨 EXTREME"
                color = "🔴"
            elif spike_mult >= 5:
                status = "⚠️  HIGH"
                color = "🟡"
            elif spike_mult >= 3:
                status = "📈 ELEVATED"
                color = "🟢"
            else:
                status = "✅ NORMAL"
                color = "⚪"
            
            print(f"{color} {name:12} ${price:>10,.2f}  Vol: {current_vol:>12,.0f}  Spike: {spike_mult:>5.1f}x  {status}")
            
            if analysis['is_spike']:
                spikes.append({
                    'symbol': symbol,
                    'name': name,
                    'price': price,
                    'current_volume': current_vol,
                    'avg_volume': avg_vol,
                    'spike_multiplier': spike_mult,
                    'timestamp': datetime.now().isoformat()
                })
        
        if spikes:
            print("\n" + "=" * 80)
            print(f"🚨 {len(spikes)} VOLUME SPIKES DETECTED - WHALE ACTIVITY!")
            print("=" * 80)
            for spike in spikes:
                print(f"\n{spike['name']} ({spike['symbol']})")
                print(f"  Price: ${spike['price']:,.2f}")
                print(f"  Current Volume: {spike['current_volume']:,.0f}")
                print(f"  Avg Volume: {spike['avg_volume']:,.0f}")
                print(f"  Spike: {spike['spike_multiplier']:.1f}x ABOVE NORMAL")
                print(f"  📊 Interpretation: Whales accumulating or big move incoming")
                
            return spikes
        else:
            print("\n" + "=" * 80)
            print("✋ No significant volume spikes detected")
            print("=" * 80)
            return []
    
    def get_recommendation(self, spike):
        """Get trading recommendation for a volume spike"""
        mult = spike['spike_multiplier']
        
        if mult >= 10:
            confidence = 85
            action = "STRONG BUY"
            reason = "Extreme volume spike (10x+) indicates major whale accumulation"
        elif mult >= 7:
            confidence = 75
            action = "BUY"
            reason = "High volume spike (7-10x) suggests big players entering"
        elif mult >= 5:
            confidence = 65
            action = "WATCH"
            reason = "Notable volume spike (5-7x) warrants close monitoring"
        else:
            confidence = 50
            action = "HOLD"
            reason = "Volume elevated but not extreme"
            
        return {
            'action': action,
            'confidence': confidence,
            'reason': reason,
            'symbol': spike['symbol'],
            'price': spike['price']
        }


if __name__ == "__main__":
    scanner = VolumeScanner()
    spikes = scanner.scan_for_volume_spikes()
    
    if spikes:
        print("\n" + "=" * 80)
        print("💡 TRADING RECOMMENDATIONS")
        print("=" * 80)
        
        for spike in spikes:
            rec = scanner.get_recommendation(spike)
            print(f"\n{rec['symbol']}: {rec['action']} ({rec['confidence']}% confidence)")
            print(f"  Reason: {rec['reason']}")
            print(f"  Entry: ${rec['price']:,.2f}")
            
            if rec['confidence'] >= 75:
                print(f"  🎯 HIGH CONFIDENCE - Consider position")
