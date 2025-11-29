"""
FLASH CRASH DETECTOR - Catch violent drops and ride the bounce
Detects 10%+ drops in minutes on legit tokens
Tight stop loss (3%), target 20-50% bounce
"""

import os
import sys
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

CRYPTOCOMPARE_BASE = "https://min-api.cryptocompare.com/data"

# Only trade flash crashes on established tokens
MONITORED_TOKENS = [
    {'symbol': 'ETH', 'name': 'Ethereum', 'min_liquidity': 10_000_000},
    {'symbol': 'BTC', 'name': 'Bitcoin', 'min_liquidity': 50_000_000},
    {'symbol': 'ARB', 'name': 'Arbitrum', 'min_liquidity': 5_000_000},
    {'symbol': 'SOL', 'name': 'Solana', 'min_liquidity': 5_000_000},
    {'symbol': 'AVAX', 'name': 'Avalanche', 'min_liquidity': 3_000_000},
    {'symbol': 'LINK', 'name': 'Chainlink', 'min_liquidity': 3_000_000},
    {'symbol': 'UNI', 'name': 'Uniswap', 'min_liquidity': 3_000_000},
    {'symbol': 'AAVE', 'name': 'Aave', 'min_liquidity': 2_000_000}
]

class FlashCrashDetector:
    def __init__(self):
        self.price_history = {}
        
    def get_minute_candles(self, symbol, limit=30):
        """Get minute-level price data"""
        try:
            url = f"{CRYPTOCOMPARE_BASE}/v2/histominute"
            params = {
                'fsym': symbol,
                'tsym': 'USDC',
                'limit': limit
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('Response') == 'Success':
                    candles = data['Data']['Data']
                    return [
                        {
                            'time': candle['time'],
                            'open': candle['open'],
                            'high': candle['high'],
                            'low': candle['low'],
                            'close': candle['close'],
                            'volume': candle['volumeto']
                        }
                        for candle in candles
                    ]
            
            return []
            
        except Exception as e:
            print(f"Error fetching minute candles for {symbol}: {e}")
            return []
    
    def detect_flash_crash(self, symbol, candles):
        """Detect sudden price drops"""
        if len(candles) < 10:
            return None
        
        # Check last 5-10 minutes for violent drops
        recent_candles = candles[-10:]
        
        # Find highest price in last 10 minutes
        high_5min = max(c['high'] for c in recent_candles[-5:])
        high_10min = max(c['high'] for c in recent_candles)
        
        # Current price
        current_price = recent_candles[-1]['close']
        
        # Calculate drops
        drop_5min = ((high_5min - current_price) / high_5min) * 100
        drop_10min = ((high_10min - current_price) / high_10min) * 100
        
        # Flash crash criteria
        if drop_5min >= 10:
            return {
                'symbol': symbol,
                'drop_pct': drop_5min,
                'timeframe': '5min',
                'high_price': high_5min,
                'current_price': current_price,
                'candles': recent_candles
            }
        
        elif drop_10min >= 15:
            return {
                'symbol': symbol,
                'drop_pct': drop_10min,
                'timeframe': '10min',
                'high_price': high_10min,
                'current_price': current_price,
                'candles': recent_candles
            }
        
        return None
    
    def calculate_bounce_probability(self, crash_data):
        """Estimate probability of bounce based on crash characteristics"""
        drop_pct = crash_data['drop_pct']
        candles = crash_data['candles']
        
        # Calculate average volume
        avg_volume = sum(c['volume'] for c in candles[-5:]) / 5
        
        # More violent drops often bounce harder
        confidence = 50
        
        if drop_pct >= 20:
            confidence += 25  # Massive overextension
        elif drop_pct >= 15:
            confidence += 15
        elif drop_pct >= 10:
            confidence += 10
        
        # High volume on drop = more likely panic selling = better bounce
        current_volume = candles[-1]['volume']
        if current_volume > avg_volume * 2:
            confidence += 10
        
        # Cap at 80% (flash crash trading is risky)
        confidence = min(80, confidence)
        
        return confidence
    
    def scan_for_flash_crashes(self):
        """Scan all monitored tokens for flash crashes"""
        print("\n" + "="*80)
        print("⚡ FLASH CRASH DETECTOR - Catching Violent Drops")
        print("="*80)
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Scanning {len(MONITORED_TOKENS)} established tokens...")
        
        crashes = []
        
        for token in MONITORED_TOKENS:
            symbol = token['symbol']
            name = token['name']
            
            candles = self.get_minute_candles(symbol, limit=30)
            
            if not candles:
                print(f"   ⚪ {symbol} ({name}): No data")
                continue
            
            crash = self.detect_flash_crash(symbol, candles)
            
            if crash:
                confidence = self.calculate_bounce_probability(crash)
                
                print(f"\n   🔴 {symbol} ({name}): FLASH CRASH DETECTED!")
                print(f"      Drop: {crash['drop_pct']:.1f}% in {crash['timeframe']}")
                print(f"      High: ${crash['high_price']:.2f}")
                print(f"      Now: ${crash['current_price']:.2f}")
                print(f"      Bounce Probability: {confidence}%")
                
                crashes.append({
                    'symbol': symbol,
                    'name': name,
                    'drop_pct': crash['drop_pct'],
                    'timeframe': crash['timeframe'],
                    'high_price': crash['high_price'],
                    'current_price': crash['current_price'],
                    'confidence': confidence,
                    'timestamp': datetime.now().isoformat()
                })
            else:
                # Show current price movement
                if len(candles) >= 5:
                    price_5min_ago = candles[-5]['close']
                    current = candles[-1]['close']
                    change = ((current - price_5min_ago) / price_5min_ago) * 100
                    
                    if abs(change) > 3:
                        indicator = "🟢" if change > 0 else "🔴"
                        print(f"   {indicator} {symbol} ({name}): {change:+.2f}% (5min)")
                    else:
                        print(f"   ⚪ {symbol} ({name}): {change:+.2f}% (stable)")
        
        return crashes
    
    def get_trade_recommendation(self, crash):
        """Generate trading strategy for flash crash"""
        if crash['confidence'] < 60:
            return None
        
        entry_price = crash['current_price']
        stop_loss = entry_price * 0.97  # Tight 3% stop
        
        # Target based on drop severity
        if crash['drop_pct'] >= 20:
            target_1 = entry_price * 1.30  # 30% bounce
            target_2 = entry_price * 1.50  # 50% bounce
        elif crash['drop_pct'] >= 15:
            target_1 = entry_price * 1.25
            target_2 = entry_price * 1.40
        else:
            target_1 = entry_price * 1.20
            target_2 = entry_price * 1.30
        
        return {
            'action': 'BUY_BOUNCE',
            'entry': entry_price,
            'stop_loss': stop_loss,
            'target_1': target_1,
            'target_2': target_2,
            'risk': f'{((entry_price - stop_loss) / entry_price) * 100:.1f}%',
            'reward_1': f'{((target_1 - entry_price) / entry_price) * 100:.1f}%',
            'reward_2': f'{((target_2 - entry_price) / entry_price) * 100:.1f}%',
            'position_size': 'SMALL (Flash crashes are high risk)',
            'time_horizon': '1-6 hours'
        }


if __name__ == "__main__":
    detector = FlashCrashDetector()
    
    crashes = detector.scan_for_flash_crashes()
    
    if crashes:
        print("\n" + "="*80)
        print(f"🚨 {len(crashes)} FLASH CRASH DETECTED!")
        print("="*80)
        
        for crash in crashes:
            rec = detector.get_trade_recommendation(crash)
            if rec:
                print(f"\n{crash['symbol']} - {crash['name']}")
                print(f"  Crashed: {crash['drop_pct']:.1f}% in {crash['timeframe']}")
                print(f"  Confidence: {crash['confidence']}%")
                print(f"\n  📊 BOUNCE PLAY:")
                print(f"     Entry: ${rec['entry']:.2f}")
                print(f"     Stop Loss: ${rec['stop_loss']:.2f} (Risk: {rec['risk']})")
                print(f"     Target 1: ${rec['target_1']:.2f} (Reward: {rec['reward_1']}) - Take 50%")
                print(f"     Target 2: ${rec['target_2']:.2f} (Reward: {rec['reward_2']}) - Take remaining")
                print(f"     Position: {rec['position_size']}")
                print(f"     Horizon: {rec['time_horizon']}")
                print(f"\n  ⚠️  TIGHT STOP REQUIRED - Exit immediately if stop hit")
    else:
        print("\n" + "="*80)
        print("✅ No flash crashes detected")
        print("="*80)
        print("\nFlash crashes are rare but profitable when caught")
        print("This scanner should run every 1-5 minutes for best results")
