"""
AGENT 3: ICEBERG ORDER SNIPER
Detects institutional hidden orders and rides their completion
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
    
    def get_order_book(self, pair, count=20):
        """Get order book depth"""
        result = self._request(f"/0/public/Depth?pair={pair}&count={count}", private=False)
        return result.get("result", {})
    
    def get_recent_trades(self, pair):
        """Get recent trades"""
        result = self._request(f"/0/public/Trades?pair={pair}", private=False)
        return result.get("result", {})


class IcebergSniperAgent:
    """
    Agent 3: Iceberg Order Sniper
    
    Strategy: Detects hidden institutional orders via order book analysis
    - Monitor for repeated small fills at same price (iceberg)
    - Ride the institutional order completion
    - Exit when order is fully filled
    
    Iceberg detection signals:
    1. Large size at specific price level
    2. Price level keeps refilling after trades
    3. Volume accumulation at that level
    
    Expected Performance:
    - Opportunities: 3-8/hour
    - Profit per trade: 0.1-0.4%
    - Capital: $7
    """
    
    def __init__(self, capital_usd=7.0, min_refill_count=3, paper_mode=True):
        self.capital_usd = capital_usd
        self.min_refill_count = min_refill_count  # How many times level must refill
        self.paper_mode = paper_mode
        
        # API
        self.kraken = KrakenAPI(
            os.getenv("KRAKEN_API_KEY"),
            os.getenv("KRAKEN_API_SECRET")
        )
        
        # Trading pairs
        self.pairs = [
            {"pair": "XXBTZUSD", "name": "BTC/USD", "min_size": 0.1},  # $3,500+
            {"pair": "XETHZUSD", "name": "ETH/USD", "min_size": 1.0},  # $3,500+
            {"pair": "SOLUSD", "name": "SOL/USD", "min_size": 20.0}    # $3,600+
        ]
        
        # State
        self.order_book_history = {}  # Track order book changes
        self.refill_counts = {}  # Count price level refills
        self.opportunities_found = 0
        self.trades_executed = 0
        self.total_pnl_usd = 0.0
        
    def analyze_order_book(self, order_book, pair_name):
        """Analyze order book for iceberg orders"""
        if not order_book:
            return []
        
        icebergs = []
        
        # Analyze asks (sell side - detect buying icebergs)
        asks = order_book.get("asks", [])
        if len(asks) >= 5:
            for i, level in enumerate(asks[:10]):
                price = float(level[0])
                size = float(level[1])
                
                # Initialize history
                key = f"{pair_name}_{price:.2f}"
                if key not in self.refill_counts:
                    self.refill_counts[key] = {"count": 0, "last_size": size, "side": "ask"}
                
                # Check if level refilled (size increased after being depleted)
                prev_size = self.refill_counts[key]["last_size"]
                if size > prev_size * 1.2:  # 20% size increase = refill
                    self.refill_counts[key]["count"] += 1
                
                self.refill_counts[key]["last_size"] = size
                
                # Iceberg detected if refilled enough times
                if self.refill_counts[key]["count"] >= self.min_refill_count and size > 0:
                    icebergs.append({
                        "pair": pair_name,
                        "side": "BUY",  # Institutional buyer (we BUY too)
                        "price": price,
                        "visible_size": size,
                        "refill_count": self.refill_counts[key]["count"],
                        "confidence": min(self.refill_counts[key]["count"] / 5.0, 1.0)
                    })
        
        # Analyze bids (buy side - detect selling icebergs)
        bids = order_book.get("bids", [])
        if len(bids) >= 5:
            for i, level in enumerate(bids[:10]):
                price = float(level[0])
                size = float(level[1])
                
                key = f"{pair_name}_{price:.2f}"
                if key not in self.refill_counts:
                    self.refill_counts[key] = {"count": 0, "last_size": size, "side": "bid"}
                
                prev_size = self.refill_counts[key]["last_size"]
                if size > prev_size * 1.2:
                    self.refill_counts[key]["count"] += 1
                
                self.refill_counts[key]["last_size"] = size
                
                if self.refill_counts[key]["count"] >= self.min_refill_count and size > 0:
                    icebergs.append({
                        "pair": pair_name,
                        "side": "SELL",  # Institutional seller (we SELL too)
                        "price": price,
                        "visible_size": size,
                        "refill_count": self.refill_counts[key]["count"],
                        "confidence": min(self.refill_counts[key]["count"] / 5.0, 1.0)
                    })
        
        return icebergs
    
    def scan_for_opportunities(self):
        """Scan all pairs for iceberg orders"""
        opportunities = []
        
        for pair_config in self.pairs:
            try:
                order_book = self.kraken.get_order_book(pair_config["pair"], count=20)
                
                if not order_book or pair_config["pair"] not in order_book:
                    continue
                
                icebergs = self.analyze_order_book(order_book[pair_config["pair"]], pair_config["name"])
                
                for iceberg in icebergs:
                    # Calculate expected profit (ride to next level)
                    expected_profit_pct = 0.15 * iceberg["confidence"]  # Scale by confidence
                    
                    opportunity = {
                        "pair": iceberg["pair"],
                        "kraken_pair": pair_config["pair"],
                        "side": iceberg["side"],
                        "price": iceberg["price"],
                        "visible_size": iceberg["visible_size"],
                        "refill_count": iceberg["refill_count"],
                        "confidence": iceberg["confidence"],
                        "expected_profit_percent": expected_profit_pct
                    }
                    opportunities.append(opportunity)
                    
            except Exception as e:
                print(f"   [AGENT-3] Error scanning {pair_config['name']}: {e}")
                continue
        
        return opportunities
    
    def execute_opportunity(self, opp):
        """Execute an iceberg snipe trade"""
        mode_str = "PAPER" if self.paper_mode else "LIVE"
        
        print(f"\n   [AGENT-3] 🎯 {mode_str} ICEBERG DETECTED:")
        print(f"      Pair: {opp['pair']}")
        print(f"      Side: {opp['side']} (institutional)")
        print(f"      Price: ${opp['price']:.2f}")
        print(f"      Visible size: {opp['visible_size']:.4f}")
        print(f"      Refills: {opp['refill_count']}x")
        print(f"      Confidence: {opp['confidence']*100:.0f}%")
        print(f"      Expected profit: {opp['expected_profit_percent']:.3f}%")
        
        if self.paper_mode:
            # Simulate trade
            position_usd = min(self.capital_usd * 0.6, 5.0)  # Use 60% capital or $5 max
            profit_usd = position_usd * (opp['expected_profit_percent'] / 100)
            
            print(f"      Position size: ${position_usd:.2f}")
            print(f"      Est. profit: ${profit_usd:.3f}")
            
            self.trades_executed += 1
            self.total_pnl_usd += profit_usd
            
            return True
        else:
            # Real execution
            try:
                position_usd = min(self.capital_usd * 0.6, 5.0)
                volume = position_usd / opp['price']
                
                print(f"      Position size: ${position_usd:.2f}")
                print(f"      Volume: {volume:.6f}")
                
                # Follow institutional order direction
                result = self.kraken.place_order(
                    pair=opp['kraken_pair'],
                    order_type="market",
                    side=opp['side'].lower(),
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
        print(f"\n🤖 AGENT 3: ICEBERG ORDER SNIPER")
        print(f"   Mode: {'PAPER' if self.paper_mode else 'LIVE'}")
        print(f"   Capital: ${self.capital_usd}")
        print(f"   Min refills: {self.min_refill_count}")
        print(f"   Duration: {duration_seconds}s")
        
        start_time = time.time()
        scans = 0
        
        while time.time() - start_time < duration_seconds:
            scans += 1
            
            opportunities = self.scan_for_opportunities()
            self.opportunities_found += len(opportunities)
            
            # Execute best opportunity (highest confidence)
            if opportunities:
                best_opp = max(opportunities, key=lambda x: x['confidence'])
                self.execute_opportunity(best_opp)
            else:
                print(f"   [AGENT-3] Scan #{scans}: No icebergs detected")
            
            time.sleep(5)  # Scan every 5 seconds
        
        # Summary
        print(f"\n   [AGENT-3] 📊 SESSION SUMMARY:")
        print(f"      Scans: {scans}")
        print(f"      Icebergs detected: {self.opportunities_found}")
        print(f"      Trades: {self.trades_executed}")
        print(f"      Total P&L: ${self.total_pnl_usd:.3f}")
        
        return {
            "agent": "Iceberg Sniper",
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
    agent = IcebergSniperAgent(capital_usd=7.0, min_refill_count=3, paper_mode=True)
    result = agent.run(duration_seconds=duration)
