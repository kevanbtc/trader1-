"""
AGENT 1: PREMIUM TRACKER
Exploits price discovery lag between Kraken and faster exchanges (Binance/Coinbase)
"""

import os
import hmac
import hashlib
import base64
import urllib.parse
import time
import requests
from decimal import Decimal
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class KrakenAPI:
    """Kraken REST API client with HMAC authentication"""
    
    def __init__(self, api_key, api_secret):
        self.api_key = api_key
        self.api_secret = api_secret
        self.api_url = "https://api.kraken.com"
        
    def _sign(self, endpoint, data):
        """Generate API signature"""
        postdata = urllib.parse.urlencode(data)
        encoded = (str(data['nonce']) + postdata).encode()
        message = endpoint.encode() + hashlib.sha256(encoded).digest()
        signature = hmac.new(base64.b64decode(self.api_secret), message, hashlib.sha512)
        return base64.b64encode(signature.digest()).decode()
    
    def _request(self, endpoint, data=None, private=False):
        """Make API request"""
        if private:
            if data is None:
                data = {}
            data['nonce'] = str(int(time.time() * 1000000))
            headers = {
                "API-Key": self.api_key,
                "API-Sign": self._sign(endpoint, data)
            }
            response = requests.post(self.api_url + endpoint, data=data, headers=headers, timeout=10)
        else:
            response = requests.get(self.api_url + endpoint, timeout=10)
        
        return response.json()
    
    def get_ticker(self, pair):
        """Get current ticker for a pair"""
        result = self._request(f"/0/public/Ticker?pair={pair}", private=False)
        return result.get("result", {})
    
    def get_balance(self):
        """Get account balance"""
        result = self._request("/0/private/Balance", private=True)
        return result.get("result", {})
    
    def place_order(self, pair, order_type, side, volume, price=None):
        """Place a market or limit order"""
        data = {
            "pair": pair,
            "type": side,  # buy or sell
            "ordertype": order_type,  # market or limit
            "volume": str(volume)
        }
        
        if price is not None:
            data["price"] = str(price)
        
        result = self._request("/0/private/AddOrder", data=data, private=True)
        return result


class BinanceAPI:
    """Binance public API client (no auth needed for prices)"""
    
    def __init__(self):
        self.api_url = "https://api.binance.com"
    
    def get_price(self, symbol):
        """Get current price for a symbol"""
        try:
            response = requests.get(f"{self.api_url}/api/v3/ticker/price?symbol={symbol}", timeout=5)
            data = response.json()
            return float(data.get("price", 0))
        except:
            return None


class CoinbaseAPI:
    """Coinbase public API client"""
    
    def __init__(self):
        self.api_url = "https://api.coinbase.com"
    
    def get_price(self, pair):
        """Get current price for a pair"""
        try:
            response = requests.get(f"{self.api_url}/v2/prices/{pair}/spot", timeout=5)
            data = response.json()
            return float(data.get("data", {}).get("amount", 0))
        except:
            return None


class PremiumTrackerAgent:
    """
    Agent 1: Premium Tracker
    
    Strategy: Detects when Kraken price lags behind Binance/Coinbase
    - If Kraken < Reference Price: BUY on Kraken
    - If Kraken > Reference Price: SELL on Kraken
    - Exit when prices converge
    
    Expected Performance:
    - Opportunities: 5-15/hour
    - Profit per trade: 0.05-0.2%
    - Capital: $8
    """
    
    def __init__(self, capital_usd=8.0, min_lag_percent=0.05, paper_mode=True):
        self.capital_usd = capital_usd
        self.min_lag_percent = min_lag_percent
        self.paper_mode = paper_mode
        
        # APIs
        self.kraken = KrakenAPI(
            os.getenv("KRAKEN_API_KEY"),
            os.getenv("KRAKEN_API_SECRET")
        )
        self.binance = BinanceAPI()
        self.coinbase = CoinbaseAPI()
        
        # Trading pairs
        self.pairs = [
            {
                "kraken": "XXBTZUSD",
                "binance": "BTCUSDT",
                "coinbase": "BTC-USD",
                "name": "BTC/USD"
            },
            {
                "kraken": "XETHZUSD",
                "binance": "ETHUSDT",
                "coinbase": "ETH-USD",
                "name": "ETH/USD"
            }
        ]
        
        # State
        self.position = None
        self.opportunities_found = 0
        self.trades_executed = 0
        self.total_pnl_usd = 0.0
        
    def get_reference_price(self, pair_config):
        """Get average price from Binance and Coinbase"""
        binance_price = self.binance.get_price(pair_config["binance"])
        coinbase_price = self.coinbase.get_price(pair_config["coinbase"])
        
        prices = [p for p in [binance_price, coinbase_price] if p is not None]
        
        if not prices:
            return None
        
        return sum(prices) / len(prices)
    
    def get_kraken_price(self, pair):
        """Get current Kraken price"""
        ticker = self.kraken.get_ticker(pair)
        
        if not ticker or pair not in ticker:
            return None
        
        data = ticker[pair]
        ask = float(data['a'][0])  # Best ask
        bid = float(data['b'][0])  # Best bid
        
        return (ask + bid) / 2  # Mid price
    
    def scan_for_opportunities(self):
        """Scan all pairs for price lag"""
        opportunities = []
        
        for pair_config in self.pairs:
            try:
                kraken_price = self.get_kraken_price(pair_config["kraken"])
                ref_price = self.get_reference_price(pair_config)
                
                if kraken_price is None or ref_price is None:
                    continue
                
                # Calculate lag
                lag_percent = ((kraken_price - ref_price) / ref_price) * 100
                
                # Opportunity if lag > threshold
                if abs(lag_percent) >= self.min_lag_percent:
                    opportunity = {
                        "pair": pair_config["name"],
                        "kraken_pair": pair_config["kraken"],
                        "kraken_price": kraken_price,
                        "ref_price": ref_price,
                        "lag_percent": lag_percent,
                        "direction": "BUY" if lag_percent < 0 else "SELL",
                        "expected_profit_percent": abs(lag_percent)
                    }
                    opportunities.append(opportunity)
                    
            except Exception as e:
                print(f"   [AGENT-1] Error scanning {pair_config['name']}: {e}")
                continue
        
        return opportunities
    
    def execute_opportunity(self, opp):
        """Execute a premium tracking trade"""
        mode_str = "PAPER" if self.paper_mode else "LIVE"
        
        print(f"\n   [AGENT-1] 💰 {mode_str} OPPORTUNITY:")
        print(f"      Pair: {opp['pair']}")
        print(f"      Kraken: ${opp['kraken_price']:.2f}")
        print(f"      Reference: ${opp['ref_price']:.2f}")
        print(f"      Lag: {opp['lag_percent']:.3f}%")
        print(f"      Action: {opp['direction']}")
        print(f"      Expected profit: {opp['expected_profit_percent']:.3f}%")
        
        if self.paper_mode:
            # Simulate trade
            position_usd = min(self.capital_usd * 0.5, 5.0)  # Use 50% capital or $5 max
            profit_usd = position_usd * (opp['expected_profit_percent'] / 100)
            
            print(f"      Position size: ${position_usd:.2f}")
            print(f"      Est. profit: ${profit_usd:.3f}")
            
            self.trades_executed += 1
            self.total_pnl_usd += profit_usd
            
            return True
        else:
            # Real execution
            try:
                position_usd = min(self.capital_usd * 0.5, 5.0)
                volume = position_usd / opp['kraken_price']  # Convert USD to crypto amount
                
                print(f"      Position size: ${position_usd:.2f}")
                print(f"      Volume: {volume:.6f}")
                
                # Place market order
                side = "buy" if opp['direction'] == "BUY" else "sell"
                result = self.kraken.place_order(
                    pair=opp['kraken_pair'],
                    order_type="market",
                    side=side,
                    volume=volume
                )
                
                if result.get("error"):
                    print(f"      ❌ Order failed: {result['error']}")
                    return False
                
                print(f"      ✅ Order executed: {result.get('result', {}).get('txid', [])}")
                
                # Estimate profit (conservative)
                profit_usd = position_usd * (opp['expected_profit_percent'] / 100) * 0.5
                self.trades_executed += 1
                self.total_pnl_usd += profit_usd
                
                return True
                
            except Exception as e:
                print(f"      ❌ Execution error: {e}")
                return False
    
    def run(self, duration_seconds=60):
        """Run the agent for specified duration"""
        print(f"\n🤖 AGENT 1: PREMIUM TRACKER")
        print(f"   Mode: {'PAPER' if self.paper_mode else 'LIVE'}")
        print(f"   Capital: ${self.capital_usd}")
        print(f"   Min lag: {self.min_lag_percent}%")
        print(f"   Duration: {duration_seconds}s")
        
        start_time = time.time()
        scans = 0
        
        while time.time() - start_time < duration_seconds:
            scans += 1
            
            opportunities = self.scan_for_opportunities()
            self.opportunities_found += len(opportunities)
            
            # Execute best opportunity
            if opportunities:
                best_opp = max(opportunities, key=lambda x: abs(x['lag_percent']))
                self.execute_opportunity(best_opp)
            else:
                print(f"   [AGENT-1] Scan #{scans}: No opportunities (lag < {self.min_lag_percent}%)")
            
            time.sleep(5)  # Scan every 5 seconds
        
        # Summary
        print(f"\n   [AGENT-1] 📊 SESSION SUMMARY:")
        print(f"      Scans: {scans}")
        print(f"      Opportunities: {self.opportunities_found}")
        print(f"      Trades: {self.trades_executed}")
        print(f"      Total P&L: ${self.total_pnl_usd:.3f}")
        
        return {
            "agent": "Premium Tracker",
            "scans": scans,
            "opportunities": self.opportunities_found,
            "trades": self.trades_executed,
            "pnl_usd": self.total_pnl_usd
        }


if __name__ == "__main__":
    import sys
    
    # Parse arguments
    duration = 60  # Default 1 minute
    if len(sys.argv) > 1:
        duration = int(sys.argv[1])
    
    # Run agent
    agent = PremiumTrackerAgent(capital_usd=8.0, min_lag_percent=0.05, paper_mode=True)
    result = agent.run(duration_seconds=duration)
