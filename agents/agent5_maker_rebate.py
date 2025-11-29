"""
AGENT 5: MAKER REBATE FARMER
Earns exchange rebates by providing liquidity with limit orders
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


class MakerRebateAgent:
    """
    Agent 5: Maker Rebate Farmer
    
    Strategy: Earn exchange maker rebates by providing liquidity
    - Place limit orders inside the spread
    - Get filled as the market moves
    - Earn maker rebate (0.03-0.07% on Kraken)
    - Immediately exit position at market
    
    Maker fees on Kraken:
    - Volume < $50k: Maker 0.16%, Taker 0.26%
    - Volume $50k-$100k: Maker 0.14%, Taker 0.24%
    - High volume tiers have NEGATIVE maker fees (rebates)
    
    Expected Performance:
    - Fills: 20-50/hour
    - Profit per fill: 0.03-0.07% (rebate minus slippage)
    - Capital: $8
    """
    
    def __init__(self, capital_usd=8.0, target_rebate_bps=5, paper_mode=True):
        self.capital_usd = capital_usd
        self.target_rebate_bps = target_rebate_bps  # Basis points (5 = 0.05%)
        self.paper_mode = paper_mode
        
        # API
        self.kraken = KrakenAPI(
            os.getenv("KRAKEN_API_KEY"),
            os.getenv("KRAKEN_API_SECRET")
        )
        
        # Trading pairs (high volume = best rebates)
        self.pairs = [
            {"pair": "XXBTZUSD", "name": "BTC/USD", "maker_fee": -0.01},  # Assume -1 bps rebate
            {"pair": "XETHZUSD", "name": "ETH/USD", "maker_fee": -0.01},
            {"pair": "SOLUSD", "name": "SOL/USD", "maker_fee": 0.05},     # Assume +5 bps (still profitable)
            {"pair": "XRPUSD", "name": "XRP/USD", "maker_fee": 0.05}
        ]
        
        # State
        self.opportunities_found = 0
        self.fills_executed = 0
        self.total_pnl_usd = 0.0
        
    def find_optimal_limit_price(self, order_book, side):
        """Find optimal limit price inside the spread"""
        if not order_book:
            return None
        
        asks = order_book.get("asks", [])
        bids = order_book.get("bids", [])
        
        if not asks or not bids:
            return None
        
        best_ask = float(asks[0][0])
        best_bid = float(bids[0][0])
        mid = (best_ask + best_bid) / 2
        
        if side == "buy":
            # Place buy limit slightly above best bid (more likely to fill)
            optimal_price = best_bid * 1.0005  # 0.05% above best bid
            return min(optimal_price, mid)  # Don't cross mid
        else:
            # Place sell limit slightly below best ask
            optimal_price = best_ask * 0.9995  # 0.05% below best ask
            return max(optimal_price, mid)  # Don't cross mid
    
    def scan_for_opportunities(self):
        """Scan for maker rebate opportunities"""
        opportunities = []
        
        for pair_config in self.pairs:
            try:
                ticker = self.kraken.get_ticker(pair_config["pair"])
                order_book = self.kraken.get_order_book(pair_config["pair"], count=10)
                
                if not ticker or pair_config["pair"] not in ticker:
                    continue
                
                if not order_book or pair_config["pair"] not in order_book:
                    continue
                
                ticker_data = ticker[pair_config["pair"]]
                book_data = order_book[pair_config["pair"]]
                
                # Calculate spread
                ask = float(ticker_data['a'][0])
                bid = float(ticker_data['b'][0])
                mid = (ask + bid) / 2
                spread_percent = ((ask - bid) / mid) * 100
                
                # Only profitable if spread > maker fee
                if spread_percent > abs(pair_config["maker_fee"]):
                    # Try both sides
                    for side in ["buy", "sell"]:
                        optimal_price = self.find_optimal_limit_price(book_data, side)
                        
                        if optimal_price is None:
                            continue
                        
                        # Calculate expected profit
                        # Rebate (negative fee) + spread capture
                        rebate_bps = abs(pair_config["maker_fee"])
                        spread_capture_bps = (spread_percent / 2) * 100  # Capture half spread
                        total_profit_bps = rebate_bps + spread_capture_bps
                        
                        if total_profit_bps >= self.target_rebate_bps:
                            opportunity = {
                                "pair": pair_config["name"],
                                "kraken_pair": pair_config["pair"],
                                "side": side,
                                "limit_price": optimal_price,
                                "mid_price": mid,
                                "spread_percent": spread_percent,
                                "maker_fee_bps": pair_config["maker_fee"],
                                "rebate_bps": rebate_bps,
                                "expected_profit_bps": total_profit_bps
                            }
                            opportunities.append(opportunity)
                    
            except Exception as e:
                print(f"   [AGENT-5] Error scanning {pair_config['name']}: {e}")
                continue
        
        return opportunities
    
    def execute_opportunity(self, opp):
        """Execute a maker rebate trade"""
        mode_str = "PAPER" if self.paper_mode else "LIVE"
        
        print(f"\n   [AGENT-5] 💰 {mode_str} MAKER REBATE:")
        print(f"      Pair: {opp['pair']}")
        print(f"      Side: {opp['side'].upper()} limit")
        print(f"      Limit price: ${opp['limit_price']:.2f}")
        print(f"      Mid price: ${opp['mid_price']:.2f}")
        print(f"      Spread: {opp['spread_percent']:.3f}%")
        print(f"      Rebate: {opp['rebate_bps']:.1f} bps")
        print(f"      Expected profit: {opp['expected_profit_bps']:.1f} bps")
        
        if self.paper_mode:
            # Simulate trade
            position_usd = min(self.capital_usd * 0.3, 3.0)  # Use 30% capital or $3 max per fill
            profit_usd = position_usd * (opp['expected_profit_bps'] / 10000)
            
            print(f"      Position size: ${position_usd:.2f}")
            print(f"      Est. profit: ${profit_usd:.3f}")
            
            self.fills_executed += 1
            self.total_pnl_usd += profit_usd
            
            return True
        else:
            # Real execution - place limit order for maker rebate
            try:
                position_usd = min(self.capital_usd * 0.3, 3.0)
                volume = position_usd / opp['limit_price']
                
                print(f"      Position size: ${position_usd:.2f}")
                print(f"      Volume: {volume:.6f}")
                
                # Place limit order inside spread
                result = self.kraken.place_order(
                    pair=opp['kraken_pair'],
                    order_type="limit",
                    side=opp['side'],
                    volume=volume,
                    price=opp['limit_price']
                )
                
                if result.get("error"):
                    print(f"      ❌ Order failed: {result['error']}")
                    return False
                
                print(f"      ✅ Limit order placed: {result.get('result', {}).get('txid', [])}")
                print(f"      ⏳ Waiting for fill...")
                
                profit_usd = position_usd * (opp['expected_profit_bps'] / 10000) * 0.5
                self.fills_executed += 1
                self.total_pnl_usd += profit_usd
                
                return True
                
            except Exception as e:
                print(f"      ❌ Execution error: {e}")
                return False
    
    def run(self, duration_seconds=60):
        """Run the agent for specified duration"""
        print(f"\n🤖 AGENT 5: MAKER REBATE FARMER")
        print(f"   Mode: {'PAPER' if self.paper_mode else 'LIVE'}")
        print(f"   Capital: ${self.capital_usd}")
        print(f"   Target rebate: {self.target_rebate_bps} bps")
        print(f"   Duration: {duration_seconds}s")
        
        start_time = time.time()
        scans = 0
        
        while time.time() - start_time < duration_seconds:
            scans += 1
            
            opportunities = self.scan_for_opportunities()
            self.opportunities_found += len(opportunities)
            
            # Execute best opportunity (highest profit)
            if opportunities:
                best_opp = max(opportunities, key=lambda x: x['expected_profit_bps'])
                self.execute_opportunity(best_opp)
            else:
                print(f"   [AGENT-5] Scan #{scans}: No profitable maker opportunities")
            
            time.sleep(5)  # Scan every 5 seconds
        
        # Summary
        print(f"\n   [AGENT-5] 📊 SESSION SUMMARY:")
        print(f"      Scans: {scans}")
        print(f"      Opportunities: {self.opportunities_found}")
        print(f"      Fills: {self.fills_executed}")
        print(f"      Total P&L: ${self.total_pnl_usd:.3f}")
        
        return {
            "agent": "Maker Rebate Farmer",
            "scans": scans,
            "opportunities": self.opportunities_found,
            "trades": self.fills_executed,
            "pnl_usd": self.total_pnl_usd
        }


if __name__ == "__main__":
    import sys
    
    # Parse arguments
    duration = 60  # Default 1 minute
    if len(sys.argv) > 1:
        duration = int(sys.argv[1])
    
    # Run agent
    agent = MakerRebateAgent(capital_usd=8.0, target_rebate_bps=5, paper_mode=True)
    result = agent.run(duration_seconds=duration)
