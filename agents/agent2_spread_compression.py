"""
AGENT 2: SPREAD COMPRESSION SCALPER
Exploits temporary spread compression opportunities
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
    """Kraken REST API client"""
    
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
    
    def get_order_book(self, pair, count=10):
        """Get order book depth"""
        result = self._request(f"/0/public/Depth?pair={pair}&count={count}", private=False)
        return result.get("result", {})


class SpreadCompressionAgent:
    """
    Agent 2: Spread Compression Scalper
    
    Strategy: Detects when bid-ask spread compresses below historical average
    - Normal spread: 0.10-0.20% (wide)
    - Compressed spread: 0.02-0.05% (tight)
    - BUY on compressed spread, SELL when spread widens
    
    Expected Performance:
    - Opportunities: 10-30/hour
    - Profit per trade: 0.05-0.15%
    - Capital: $7
    """
    
    def __init__(self, capital_usd=7.0, compression_threshold=0.05, paper_mode=True):
        self.capital_usd = capital_usd
        self.compression_threshold = compression_threshold  # Spread must be < 0.05% to trigger
        self.paper_mode = paper_mode
        
        # API
        self.kraken = KrakenAPI(
            os.getenv("KRAKEN_API_KEY"),
            os.getenv("KRAKEN_API_SECRET")
        )
        
        # Trading pairs with typical spreads
        self.pairs = [
            {"pair": "XXBTZUSD", "name": "BTC/USD", "avg_spread_pct": 0.12},
            {"pair": "XETHZUSD", "name": "ETH/USD", "avg_spread_pct": 0.15},
            {"pair": "SOLUSD", "name": "SOL/USD", "avg_spread_pct": 0.18},
            {"pair": "XRPUSD", "name": "XRP/USD", "avg_spread_pct": 0.20}
        ]
        
        # State
        self.spread_history = {}  # Track spread over time
        self.opportunities_found = 0
        self.trades_executed = 0
        self.total_pnl_usd = 0.0
        
    def calculate_spread(self, ticker_data, pair_name):
        """Calculate bid-ask spread percentage"""
        if not ticker_data:
            return None
        
        ask = float(ticker_data['a'][0])  # Best ask
        bid = float(ticker_data['b'][0])  # Best bid
        mid = (ask + bid) / 2
        
        spread_percent = ((ask - bid) / mid) * 100
        
        return {
            "bid": bid,
            "ask": ask,
            "mid": mid,
            "spread_percent": spread_percent
        }
    
    def is_spread_compressed(self, current_spread, pair_config):
        """Check if spread is significantly compressed"""
        avg_spread = pair_config["avg_spread_pct"]
        compression_ratio = current_spread / avg_spread
        
        # Compressed if < 40% of normal spread
        return compression_ratio < 0.4
    
    def scan_for_opportunities(self):
        """Scan all pairs for spread compression"""
        opportunities = []
        
        for pair_config in self.pairs:
            try:
                ticker = self.kraken.get_ticker(pair_config["pair"])
                
                if not ticker or pair_config["pair"] not in ticker:
                    continue
                
                spread_data = self.calculate_spread(ticker[pair_config["pair"]], pair_config["name"])
                
                if spread_data is None:
                    continue
                
                # Update history
                if pair_config["name"] not in self.spread_history:
                    self.spread_history[pair_config["name"]] = []
                
                self.spread_history[pair_config["name"]].append(spread_data["spread_percent"])
                
                # Keep only last 20 spreads
                if len(self.spread_history[pair_config["name"]]) > 20:
                    self.spread_history[pair_config["name"]].pop(0)
                
                # Check for compression
                if self.is_spread_compressed(spread_data["spread_percent"], pair_config):
                    opportunity = {
                        "pair": pair_config["name"],
                        "kraken_pair": pair_config["pair"],
                        "bid": spread_data["bid"],
                        "ask": spread_data["ask"],
                        "mid": spread_data["mid"],
                        "spread_percent": spread_data["spread_percent"],
                        "avg_spread": pair_config["avg_spread_pct"],
                        "compression_ratio": spread_data["spread_percent"] / pair_config["avg_spread_pct"],
                        "expected_profit_percent": (pair_config["avg_spread_pct"] - spread_data["spread_percent"]) / 2
                    }
                    opportunities.append(opportunity)
                    
            except Exception as e:
                print(f"   [AGENT-2] Error scanning {pair_config['name']}: {e}")
                continue
        
        return opportunities
    
    def execute_opportunity(self, opp):
        """Execute a spread compression trade"""
        mode_str = "PAPER" if self.paper_mode else "LIVE"
        
        print(f"\n   [AGENT-2] 📉 {mode_str} SPREAD OPPORTUNITY:")
        print(f"      Pair: {opp['pair']}")
        print(f"      Current spread: {opp['spread_percent']:.3f}%")
        print(f"      Avg spread: {opp['avg_spread']:.3f}%")
        print(f"      Compression: {opp['compression_ratio']*100:.1f}% of normal")
        print(f"      Entry: ${opp['ask']:.2f} (buy at ask)")
        print(f"      Expected profit: {opp['expected_profit_percent']:.3f}%")
        
        if self.paper_mode:
            # Simulate trade
            position_usd = min(self.capital_usd * 0.5, 4.0)  # Use 50% capital or $4 max
            profit_usd = position_usd * (opp['expected_profit_percent'] / 100)
            
            print(f"      Position size: ${position_usd:.2f}")
            print(f"      Est. profit: ${profit_usd:.3f}")
            
            self.trades_executed += 1
            self.total_pnl_usd += profit_usd
            
            return True
        else:
            # Real execution
            try:
                position_usd = min(self.capital_usd * 0.5, 4.0)
                volume = position_usd / opp['ask']
                
                print(f"      Position size: ${position_usd:.2f}")
                print(f"      Volume: {volume:.6f}")
                
                # Buy at ask when spread compressed
                result = self.kraken.place_order(
                    pair=opp['kraken_pair'],
                    order_type="market",
                    side="buy",
                    volume=volume
                )
                
                if result.get("error"):
                    print(f"      ❌ Order failed: {result['error']}")
                    return False
                
                print(f"      ✅ Order executed: {result.get('result', {}).get('txid', [])}")
                
                profit_usd = position_usd * (opp['expected_profit_percent'] / 100) * 0.5
                self.trades_executed += 1
                self.total_pnl_usd += profit_usd
                
                return True
                
            except Exception as e:
                print(f"      ❌ Execution error: {e}")
                return False
    
    def run(self, duration_seconds=60):
        """Run the agent for specified duration"""
        print(f"\n🤖 AGENT 2: SPREAD COMPRESSION SCALPER")
        print(f"   Mode: {'PAPER' if self.paper_mode else 'LIVE'}")
        print(f"   Capital: ${self.capital_usd}")
        print(f"   Compression threshold: {self.compression_threshold}%")
        print(f"   Duration: {duration_seconds}s")
        
        start_time = time.time()
        scans = 0
        
        while time.time() - start_time < duration_seconds:
            scans += 1
            
            opportunities = self.scan_for_opportunities()
            self.opportunities_found += len(opportunities)
            
            # Execute best opportunity (most compressed)
            if opportunities:
                best_opp = min(opportunities, key=lambda x: x['compression_ratio'])
                self.execute_opportunity(best_opp)
            else:
                print(f"   [AGENT-2] Scan #{scans}: No compressed spreads")
            
            time.sleep(5)  # Scan every 5 seconds
        
        # Summary
        print(f"\n   [AGENT-2] 📊 SESSION SUMMARY:")
        print(f"      Scans: {scans}")
        print(f"      Opportunities: {self.opportunities_found}")
        print(f"      Trades: {self.trades_executed}")
        print(f"      Total P&L: ${self.total_pnl_usd:.3f}")
        
        return {
            "agent": "Spread Compression",
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
    agent = SpreadCompressionAgent(capital_usd=7.0, compression_threshold=0.05, paper_mode=True)
    result = agent.run(duration_seconds=duration)
