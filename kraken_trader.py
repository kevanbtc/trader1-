"""
Kraken CEX Trading Bot
Scans for arbitrage opportunities on Kraken exchange
"""

import os
import sys
import time
import hmac
import hashlib
import base64
import urllib.parse
import requests
from datetime import datetime
from typing import Dict, List, Optional, Tuple
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
    
    def get_tradable_pairs(self) -> dict:
        """Get all tradable asset pairs"""
        return self._request('/0/public/AssetPairs')
    
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
    
    def get_open_orders(self) -> dict:
        """Get open orders"""
        return self._request('/0/private/OpenOrders', private=True)


class KrakenArbitrageScanner:
    """Scan Kraken for triangular arbitrage opportunities"""
    
    def __init__(self, api: KrakenAPI, min_profit_pct: float = 0.5):
        self.api = api
        self.min_profit_pct = min_profit_pct
        self.pairs_cache = None
        self.last_cache_update = 0
        
    def get_pairs(self) -> dict:
        """Get tradable pairs (cached)"""
        now = time.time()
        if self.pairs_cache is None or now - self.last_cache_update > 3600:
            self.pairs_cache = self.api.get_tradable_pairs()
            self.last_cache_update = now
        return self.pairs_cache
    
    def find_triangular_paths(self, base: str = "USD") -> List[Tuple[str, str, str]]:
        """Find triangular arbitrage paths starting/ending with base currency"""
        pairs = self.get_pairs()
        paths = []
        
        # Build graph of available pairs
        graph = {}
        for pair_name, pair_info in pairs.items():
            if pair_info.get('status') != 'online':
                continue
                
            base_asset = pair_info['base']
            quote_asset = pair_info['quote']
            
            if base_asset not in graph:
                graph[base_asset] = []
            graph[base_asset].append((quote_asset, pair_name))
        
        # Find paths: BASE -> A -> B -> BASE
        if base not in graph:
            return paths
        
        for asset_a, pair1 in graph.get(base, []):
            for asset_b, pair2 in graph.get(asset_a, []):
                if asset_b == base:
                    continue
                for return_asset, pair3 in graph.get(asset_b, []):
                    if return_asset == base:
                        paths.append((pair1, pair2, pair3))
        
        return paths
    
    def calculate_triangular_profit(self, path: Tuple[str, str, str], prices: dict, amount: float = 1000) -> dict:
        """Calculate profit for triangular arbitrage path"""
        pair1, pair2, pair3 = path
        
        try:
            # Get ask prices (buying)
            price1_ask = float(prices[pair1]['a'][0])  # Buy first leg
            price2_ask = float(prices[pair2]['a'][0])  # Buy second leg
            price3_bid = float(prices[pair3]['b'][0])  # Sell third leg
            
            # Calculate amount after each trade
            amount_after_1 = amount / price1_ask  # Buy asset A
            amount_after_2 = amount_after_1 / price2_ask  # Buy asset B
            amount_after_3 = amount_after_2 * price3_bid  # Sell back to USD
            
            profit = amount_after_3 - amount
            profit_pct = (profit / amount) * 100
            
            return {
                'path': path,
                'profit_usd': profit,
                'profit_pct': profit_pct,
                'start_amount': amount,
                'end_amount': amount_after_3,
                'prices': {
                    pair1: price1_ask,
                    pair2: price2_ask,
                    pair3: price3_bid
                }
            }
        except (KeyError, ValueError, ZeroDivisionError):
            return None
    
    def scan(self, base: str = "USD", test_amount: float = 1000) -> List[dict]:
        """Scan for triangular arbitrage opportunities"""
        paths = self.find_triangular_paths(base)
        
        if not paths:
            return []
        
        # Get all pair names for price query
        all_pairs = set()
        for path in paths:
            all_pairs.update(path)
        
        # Get prices
        try:
            prices = self.api.get_ticker(list(all_pairs))
        except Exception as e:
            print(f"❌ Error fetching prices: {e}")
            return []
        
        # Calculate profits
        opportunities = []
        for path in paths:
            result = self.calculate_triangular_profit(path, prices, test_amount)
            if result and result['profit_pct'] >= self.min_profit_pct:
                opportunities.append(result)
        
        # Sort by profit percentage
        opportunities.sort(key=lambda x: x['profit_pct'], reverse=True)
        
        return opportunities


class KrakenTradingBot:
    """Main Kraken trading bot"""
    
    def __init__(self):
        self.api_key = os.getenv('KRAKEN_API_KEY')
        self.api_secret = os.getenv('KRAKEN_API_SECRET')
        self.min_profit_pct = float(os.getenv('MIN_PROFIT_PCT', '0.5'))
        self.test_mode = os.getenv('TRADING_MODE', 'TEST') == 'TEST'
        self.scan_interval = 5  # seconds
        
        if not self.api_key or not self.api_secret:
            raise ValueError("❌ KRAKEN_API_KEY and KRAKEN_API_SECRET must be set in .env")
        
        self.api = KrakenAPI(self.api_key, self.api_secret)
        self.scanner = KrakenArbitrageScanner(self.api, self.min_profit_pct)
        
        self.session_start = datetime.utcnow()
        self.opportunities_found = 0
        self.trades_executed = 0
    
    def check_balance(self):
        """Check account balance"""
        try:
            balances = self.api.get_balance()
            print("\n💰 Account Balances:")
            for asset, amount in balances.items():
                if float(amount) > 0:
                    print(f"   {asset}: {float(amount):.4f}")
        except Exception as e:
            print(f"⚠️  Could not fetch balance: {e}")
    
    def execute_opportunity(self, opp: dict) -> bool:
        """Execute triangular arbitrage trade"""
        if self.test_mode:
            print(f"   [PAPER] Would execute: ${opp['start_amount']:.2f} → ${opp['end_amount']:.2f}")
            return True
        
        # TODO: Implement real execution
        # 1. Place buy order on pair1
        # 2. Wait for fill
        # 3. Place buy order on pair2
        # 4. Wait for fill
        # 5. Place sell order on pair3
        # 6. Return success/failure
        
        print(f"   [LIVE] Trade execution not implemented yet")
        return False
    
    def run(self, duration_seconds: int = 300):
        """Run trading bot for specified duration"""
        mode_str = "📄 PAPER MODE" if self.test_mode else "⚡ LIVE TRADING"
        
        print("=" * 70)
        print("🦑 KRAKEN ARBITRAGE TRADING BOT")
        print("=" * 70)
        print(f"Mode: {mode_str}")
        print(f"Min Profit: {self.min_profit_pct}%")
        print(f"Scan Interval: {self.scan_interval}s")
        print(f"Duration: {duration_seconds}s ({duration_seconds / 60:.1f} minutes)")
        print()
        
        # Check balance
        self.check_balance()
        
        print(f"\n🚀 Starting arbitrage scanner...")
        print("=" * 70)
        
        start_time = time.time()
        end_time = start_time + duration_seconds
        scan_count = 0
        
        try:
            while time.time() < end_time:
                scan_count += 1
                print(f"\n[Scan #{scan_count}] {datetime.now().strftime('%H:%M:%S')}")
                
                # Scan for opportunities
                opportunities = self.scanner.scan(base="USD", test_amount=1000)
                
                if opportunities:
                    self.opportunities_found += len(opportunities)
                    
                    for opp in opportunities[:3]:  # Show top 3
                        print(f"\n🎯 Opportunity Found!")
                        print(f"   Path: {' → '.join(opp['path'])}")
                        print(f"   Profit: ${opp['profit_usd']:.2f} ({opp['profit_pct']:.3f}%)")
                        print(f"   Start: ${opp['start_amount']:.2f}")
                        print(f"   End: ${opp['end_amount']:.2f}")
                        
                        # Execute trade
                        if self.execute_opportunity(opp):
                            self.trades_executed += 1
                else:
                    print("   No opportunities found (spreads too small)")
                
                # Wait before next scan
                time.sleep(self.scan_interval)
        
        except KeyboardInterrupt:
            print("\n\n⚠️  User interrupted trading session")
        
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
    
    parser = argparse.ArgumentParser(description='Kraken Arbitrage Trading Bot')
    parser.add_argument('--duration', type=int, default=300, help='Trading duration in seconds')
    parser.add_argument('--test', action='store_true', help='Run in paper trading mode')
    
    args = parser.parse_args()
    
    # Override trading mode if --test flag is used
    if args.test:
        os.environ['TRADING_MODE'] = 'TEST'
    
    bot = KrakenTradingBot()
    bot.run(duration_seconds=args.duration)
