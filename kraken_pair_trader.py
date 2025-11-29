"""
Kraken Direct Pair Trading Bot
Trades on price spreads between bid/ask on single pairs
More realistic than triangular arbitrage on efficient exchanges
"""

import os
import time
import hmac
import hashlib
import base64
import urllib.parse
import requests
from datetime import datetime
from typing import Dict, List, Optional
import json
from dotenv import load_dotenv

load_dotenv()

class KrakenAPI:
    """Kraken REST API client"""
    
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://api.kraken.com"
        self.session = requests.Session()
        
    def _sign(self, urlpath: str, data: dict, nonce: str) -> str:
        """Generate authentication signature"""
        postdata = urllib.parse.urlencode(data)
        encoded = (str(nonce) + postdata).encode()
        message = urlpath.encode() + hashlib.sha256(encoded).digest()
        
        signature = hmac.new(
            base64.b64decode(self.api_secret),
            message,
            hashlib.sha512
        )
        return base64.b64encode(signature.digest()).decode()
    
    def _request(self, endpoint: str, data: dict = None, private: bool = False) -> dict:
        """Make API request"""
        url = f"{self.base_url}{endpoint}"
        
        if private:
            if data is None:
                data = {}
            data['nonce'] = str(int(time.time() * 1000))
            
            headers = {
                'API-Key': self.api_key,
                'API-Sign': self._sign(endpoint, data, data['nonce'])
            }
            response = self.session.post(url, headers=headers, data=data)
        else:
            response = self.session.get(url, params=data)
        
        result = response.json()
        
        if result.get('error'):
            raise Exception(f"Kraken API error: {result['error']}")
        
        return result.get('result', {})
    
    def get_ticker(self, pairs: List[str]) -> dict:
        """Get current prices for pairs"""
        return self._request('/0/public/Ticker', {'pair': ','.join(pairs)})
    
    def get_balance(self) -> dict:
        """Get account balances"""
        return self._request('/0/private/Balance', private=True)
    
    def get_ohlc(self, pair: str, interval: int = 1) -> dict:
        """Get OHLC data"""
        return self._request('/0/public/OHLC', {'pair': pair, 'interval': interval})
    
    def place_order(self, pair: str, side: str, volume: float, price: Optional[float] = None) -> dict:
        """Place market or limit order"""
        data = {
            'pair': pair,
            'type': side,  # 'buy' or 'sell'
            'ordertype': 'market' if price is None else 'limit',
            'volume': str(volume)
        }
        
        if price:
            data['price'] = str(price)
        
        return self._request('/0/private/AddOrder', data, private=True)


class KrakenPairTrader:
    """Trade on Kraken using mean reversion / scalping strategies"""
    
    def __init__(self):
        self.api_key = os.getenv('KRAKEN_API_KEY')
        self.api_secret = os.getenv('KRAKEN_API_SECRET')
        self.test_mode = os.getenv('TRADING_MODE', 'TEST') != 'LIVE'
        self.min_spread_pct = 0.1  # 0.1% minimum spread
        
        if not self.api_key or not self.api_secret:
            raise ValueError("❌ KRAKEN_API_KEY and KRAKEN_API_SECRET must be set in .env")
        
        self.api = KrakenAPI(self.api_key, self.api_secret)
        
        # Focus on liquid pairs
        self.trading_pairs = [
            'XXBTZUSD',  # BTC/USD
            'XETHZUSD',  # ETH/USD
            'SOLUSD',    # SOL/USD
            'ADAUSD',    # ADA/USD
            'DOTUSD',    # DOT/USD
            'MATICUSD',  # MATIC/USD
        ]
        
        self.session_start = datetime.now()
        self.opportunities_found = 0
        self.trades_executed = 0
        self.position = None  # Current open position
    
    def get_balance_usd(self) -> float:
        """Get USD balance"""
        try:
            balances = self.api.get_balance()
            usd = float(balances.get('ZUSD', 0))
            usdt = float(balances.get('USDT', 0))
            return usd + usdt
        except:
            return 0.0
    
    def check_balance(self):
        """Check account balance"""
        try:
            balances = self.api.get_balance()
            print("\n💰 Account Balances:")
            total_usd = 0
            for asset, amount in balances.items():
                amt = float(amount)
                if amt > 0.0001:  # Filter dust
                    print(f"   {asset}: {amt:.6f}")
                    if asset in ['ZUSD', 'USDT']:
                        total_usd += amt
            print(f"\n   💵 Total USD: ${total_usd:.2f}")
            return total_usd
        except Exception as e:
            print(f"⚠️  Could not fetch balance: {e}")
            return 0.0
    
    def analyze_pair(self, pair: str, ticker: dict) -> Optional[dict]:
        """Analyze single pair for trading opportunity"""
        try:
            data = ticker[pair]
            
            bid = float(data['b'][0])  # Best bid (sell price)
            ask = float(data['a'][0])  # Best ask (buy price)
            last = float(data['c'][0])  # Last trade price
            spread = ask - bid
            spread_pct = (spread / ask) * 100
            
            # Volume in last 24h
            volume = float(data['v'][1])
            
            # Only trade if spread is reasonable and volume is high
            if spread_pct < self.min_spread_pct:
                return None
            
            if volume < 100:  # Low volume, skip
                return None
            
            return {
                'pair': pair,
                'bid': bid,
                'ask': ask,
                'last': last,
                'spread': spread,
                'spread_pct': spread_pct,
                'volume_24h': volume
            }
        except (KeyError, ValueError, ZeroDivisionError):
            return None
    
    def find_opportunities(self) -> List[dict]:
        """Scan all pairs for opportunities"""
        try:
            tickers = self.api.get_ticker(self.trading_pairs)
        except Exception as e:
            print(f"❌ Error fetching tickers: {e}")
            return []
        
        opportunities = []
        for pair in self.trading_pairs:
            if pair in tickers:
                opp = self.analyze_pair(pair, tickers)
                if opp:
                    opportunities.append(opp)
        
        opportunities.sort(key=lambda x: x['spread_pct'], reverse=True)
        return opportunities
    
    def execute_trade(self, opp: dict, usd_balance: float) -> bool:
        """Execute a scalping trade"""
        # Calculate position size (use 10% of balance, max $100)
        position_size_usd = min(usd_balance * 0.1, 100)
        
        if position_size_usd < 10:
            print(f"   ⚠️  Balance too low: ${usd_balance:.2f}")
            return False
        
        if self.test_mode:
            print(f"   [PAPER] Would buy {opp['pair']}: ${position_size_usd:.2f} @ ${opp['ask']:.2f}")
            print(f"   [PAPER] Would sell when price hits ${opp['ask'] * 1.002:.2f} (+0.2%)")
            return True
        
        # LIVE EXECUTION
        try:
            volume = position_size_usd / opp['ask']
            result = self.api.place_order(
                pair=opp['pair'],
                side='buy',
                volume=volume
            )
            print(f"   ✅ BUY ORDER: {opp['pair']} - {volume:.6f} @ ${opp['ask']:.2f}")
            print(f"   Order ID: {result.get('txid', ['N/A'])[0]}")
            
            self.position = {
                'pair': opp['pair'],
                'entry_price': opp['ask'],
                'volume': volume,
                'target_price': opp['ask'] * 1.005,  # Target 0.5% profit
                'stop_loss': opp['ask'] * 0.995  # Stop loss at -0.5%
            }
            return True
            
        except Exception as e:
            print(f"   ❌ Order failed: {e}")
            return False
    
    def check_position(self):
        """Check if we should close current position"""
        if not self.position or self.test_mode:
            return
        
        try:
            ticker = self.api.get_ticker([self.position['pair']])
            current_bid = float(ticker[self.position['pair']]['b'][0])
            
            # Check if we hit target or stop loss
            if current_bid >= self.position['target_price']:
                print(f"\n   🎯 TARGET HIT! Selling at ${current_bid:.2f}")
                self.api.place_order(
                    pair=self.position['pair'],
                    side='sell',
                    volume=self.position['volume']
                )
                profit = (current_bid - self.position['entry_price']) * self.position['volume']
                print(f"   💰 Profit: ${profit:.2f}")
                self.position = None
                
            elif current_bid <= self.position['stop_loss']:
                print(f"\n   🛑 STOP LOSS! Selling at ${current_bid:.2f}")
                self.api.place_order(
                    pair=self.position['pair'],
                    side='sell',
                    volume=self.position['volume']
                )
                loss = (current_bid - self.position['entry_price']) * self.position['volume']
                print(f"   📉 Loss: ${loss:.2f}")
                self.position = None
                
        except Exception as e:
            print(f"   ⚠️  Error checking position: {e}")
    
    def run(self, duration_seconds: int = 300):
        """Run trading bot"""
        mode_str = "📄 PAPER MODE" if self.test_mode else "⚡ LIVE TRADING"
        
        print("=" * 70)
        print("🦑 KRAKEN PAIR TRADING BOT")
        print("=" * 70)
        print(f"Mode: {mode_str}")
        print(f"Min Spread: {self.min_spread_pct}%")
        print(f"Pairs: {len(self.trading_pairs)}")
        print(f"Duration: {duration_seconds}s ({duration_seconds / 60:.1f} minutes)")
        
        usd_balance = self.check_balance()
        
        print(f"\n🚀 Starting pair scanner...")
        print("=" * 70)
        
        start_time = time.time()
        end_time = start_time + duration_seconds
        scan_count = 0
        
        try:
            while time.time() < end_time:
                scan_count += 1
                print(f"\n[Scan #{scan_count}] {datetime.now().strftime('%H:%M:%S')}")
                
                # Check existing position first
                self.check_position()
                
                # Don't open new position if we already have one
                if self.position:
                    print(f"   📊 Holding {self.position['pair']} - Entry: ${self.position['entry_price']:.2f}, Target: ${self.position['target_price']:.2f}")
                    time.sleep(5)
                    continue
                
                # Scan for new opportunities
                opportunities = self.find_opportunities()
                
                if opportunities:
                    self.opportunities_found += len(opportunities)
                    
                    for opp in opportunities[:3]:  # Show top 3
                        print(f"\n🎯 {opp['pair']}")
                        print(f"   Bid: ${opp['bid']:.2f} | Ask: ${opp['ask']:.2f} | Last: ${opp['last']:.2f}")
                        print(f"   Spread: ${opp['spread']:.4f} ({opp['spread_pct']:.3f}%)")
                        print(f"   Volume 24h: {opp['volume_24h']:.1f}")
                    
                    # Execute on best opportunity
                    if self.execute_trade(opportunities[0], usd_balance):
                        self.trades_executed += 1
                else:
                    print("   No opportunities (spreads too small)")
                
                time.sleep(5)
        
        except KeyboardInterrupt:
            print("\n\n⚠️  User interrupted trading session")
        
        # Close any open position
        if self.position and not self.test_mode:
            print(f"\n🛑 Closing open position on {self.position['pair']}...")
            try:
                self.api.place_order(
                    pair=self.position['pair'],
                    side='sell',
                    volume=self.position['volume']
                )
                print("   ✅ Position closed")
            except Exception as e:
                print(f"   ❌ Failed to close: {e}")
        
        # Summary
        elapsed = time.time() - start_time
        print("\n" + "=" * 70)
        print("📋 SESSION SUMMARY")
        print("=" * 70)
        print(f"Duration: {elapsed:.0f}s ({elapsed / 60:.1f} min)")
        print(f"Scans: {scan_count}")
        print(f"Opportunities Found: {self.opportunities_found}")
        print(f"Trades Executed: {self.trades_executed}")
        print("=" * 70)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Kraken Pair Trading Bot')
    parser.add_argument('--duration', type=int, default=300, help='Trading duration in seconds')
    parser.add_argument('--live', action='store_true', help='Run in LIVE trading mode (default: paper)')
    
    args = parser.parse_args()
    
    if args.live:
        os.environ['TRADING_MODE'] = 'LIVE'
    else:
        os.environ['TRADING_MODE'] = 'TEST'
    
    bot = KrakenPairTrader()
    bot.run(duration_seconds=args.duration)
