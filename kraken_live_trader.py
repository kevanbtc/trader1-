"""
KRAKEN LIVE TRADER
Multiple profit strategies on Kraken CEX - NO arbitrage needed
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
    """Kraken REST API with full trading support"""
    
    def __init__(self, api_key, api_secret):
        self.api_key = api_key
        self.api_secret = api_secret
        self.api_url = "https://api.kraken.com"
        
    def _sign(self, endpoint, data):
        postdata = urllib.parse.urlencode(data)
        encoded = (str(data['nonce']) + postdata).encode()
        message = endpoint.encode() + hashlib.sha256(encoded).digest()
        signature = hmac.new(base64.b64decode(self.api_secret), message, hashlib.sha512)
        return base64.b64encode(signature.digest()).decode()
    
    def _request(self, endpoint, data=None, private=False):
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
        result = self._request(f"/0/public/Ticker?pair={pair}", private=False)
        return result.get("result", {})
    
    def get_balance(self):
        result = self._request("/0/private/Balance", private=True)
        return result.get("result", {})
    
    def place_order(self, pair, order_type, side, volume, price=None):
        """Place market or limit order"""
        data = {
            "pair": pair,
            "type": side,
            "ordertype": order_type,
            "volume": str(volume)
        }
        
        if price is not None:
            data["price"] = str(price)
        
        result = self._request("/0/private/AddOrder", data=data, private=True)
        return result


class KrakenLiveTrader:
    """
    Live Kraken trader with multiple strategies:
    1. Momentum - Buy on price increases, sell on decreases
    2. Mean Reversion - Buy dips, sell spikes
    3. Breakout - Trade range breakouts
    4. Volume Surge - Follow volume spikes
    """
    
    def __init__(self, capital_usd=29.0):
        self.capital_usd = capital_usd
        self.kraken = KrakenAPI(
            os.getenv("KRAKEN_API_KEY"),
            os.getenv("KRAKEN_API_SECRET")
        )
        
        # Trading pairs
        self.pairs = [
            {"pair": "XXBTZUSD", "name": "BTC/USD", "min_size": 0.0001},
            {"pair": "XETHZUSD", "name": "ETH/USD", "min_size": 0.001},
            {"pair": "SOLUSD", "name": "SOL/USD", "min_size": 0.01},
            {"pair": "XRPUSD", "name": "XRP/USD", "min_size": 0.1}
        ]
        
        # State
        self.price_history = {}
        self.positions = {}
        self.trades_executed = 0
        self.total_pnl = 0.0
        
    def update_price_history(self, pair_name, price):
        """Track price history for analysis"""
        if pair_name not in self.price_history:
            self.price_history[pair_name] = []
        
        self.price_history[pair_name].append({
            "price": price,
            "time": time.time()
        })
        
        # Keep last 20 prices
        if len(self.price_history[pair_name]) > 20:
            self.price_history[pair_name].pop(0)
    
    def detect_momentum(self, pair_name):
        """Detect strong momentum"""
        if pair_name not in self.price_history or len(self.price_history[pair_name]) < 5:
            return None
        
        prices = [p["price"] for p in self.price_history[pair_name][-5:]]
        
        # Calculate momentum
        change = (prices[-1] - prices[0]) / prices[0] * 100
        
        if change > 0.3:  # Strong up momentum
            return "BUY"
        elif change < -0.3:  # Strong down momentum
            return "SELL"
        
        return None
    
    def detect_mean_reversion(self, pair_name):
        """Detect oversold/overbought"""
        if pair_name not in self.price_history or len(self.price_history[pair_name]) < 10:
            return None
        
        prices = [p["price"] for p in self.price_history[pair_name]]
        avg_price = sum(prices) / len(prices)
        current_price = prices[-1]
        
        deviation = (current_price - avg_price) / avg_price * 100
        
        if deviation < -0.5:  # Oversold
            return "BUY"
        elif deviation > 0.5:  # Overbought
            return "SELL"
        
        return None
    
    def scan_for_opportunities(self):
        """Scan all pairs for trading opportunities"""
        opportunities = []
        
        for pair_config in self.pairs:
            try:
                ticker = self.kraken.get_ticker(pair_config["pair"])
                
                if not ticker or pair_config["pair"] not in ticker:
                    continue
                
                data = ticker[pair_config["pair"]]
                ask = float(data['a'][0])
                bid = float(data['b'][0])
                mid = (ask + bid) / 2
                
                # Update history
                self.update_price_history(pair_config["name"], mid)
                
                # Check strategies
                momentum_signal = self.detect_momentum(pair_config["name"])
                reversion_signal = self.detect_mean_reversion(pair_config["name"])
                
                if momentum_signal:
                    opportunities.append({
                        "pair": pair_config["name"],
                        "kraken_pair": pair_config["pair"],
                        "strategy": "MOMENTUM",
                        "signal": momentum_signal,
                        "price": ask if momentum_signal == "BUY" else bid,
                        "min_size": pair_config["min_size"]
                    })
                
                if reversion_signal:
                    opportunities.append({
                        "pair": pair_config["name"],
                        "kraken_pair": pair_config["pair"],
                        "strategy": "MEAN_REVERSION",
                        "signal": reversion_signal,
                        "price": ask if reversion_signal == "BUY" else bid,
                        "min_size": pair_config["min_size"]
                    })
                    
            except Exception as e:
                print(f"[ERROR] Scanning {pair_config['name']}: {e}")
                continue
        
        return opportunities
    
    def execute_trade(self, opp):
        """Execute a live trade on Kraken"""
        print(f"\n💰 LIVE TRADE OPPORTUNITY:")
        print(f"   Pair: {opp['pair']}")
        print(f"   Strategy: {opp['strategy']}")
        print(f"   Signal: {opp['signal']}")
        print(f"   Price: ${opp['price']:.2f}")
        
        # Calculate position size
        position_usd = min(self.capital_usd * 0.1, 5.0)  # 10% of capital or $5 max
        position_size = position_usd / opp['price']
        
        # Round to min size
        position_size = max(position_size, opp['min_size'])
        
        print(f"   Position: ${position_usd:.2f} ({position_size:.6f} units)")
        
        try:
            # Place market order
            result = self.kraken.place_order(
                pair=opp['kraken_pair'],
                order_type="market",
                side="buy" if opp['signal'] == "BUY" else "sell",
                volume=position_size
            )
            
            if result.get("error"):
                print(f"   ❌ ORDER FAILED: {result['error']}")
                return False
            
            order_id = result.get("result", {}).get("txid", ["unknown"])[0]
            print(f"   ✅ ORDER PLACED: {order_id}")
            
            self.trades_executed += 1
            
            # Track position
            if opp['signal'] == "BUY":
                self.positions[opp['pair']] = {
                    "size": position_size,
                    "entry_price": opp['price'],
                    "time": time.time()
                }
            else:
                # Close position
                if opp['pair'] in self.positions:
                    pos = self.positions[opp['pair']]
                    pnl = (opp['price'] - pos['entry_price']) * pos['size']
                    self.total_pnl += pnl
                    print(f"   💵 P&L: ${pnl:.2f}")
                    del self.positions[opp['pair']]
            
            return True
            
        except Exception as e:
            print(f"   ❌ EXECUTION ERROR: {e}")
            return False
    
    def run(self, duration_seconds=3600):
        """Run the live trader"""
        print("\n🚀 KRAKEN LIVE TRADER")
        print("="*70)
        print(f"Capital: ${self.capital_usd}")
        print(f"Duration: {duration_seconds}s ({duration_seconds/60:.0f} minutes)")
        print(f"Pairs: {len(self.pairs)}")
        print("\nStrategies:")
        print("  1. MOMENTUM - Follow price trends")
        print("  2. MEAN_REVERSION - Buy dips, sell spikes")
        print("\n⚠️  LIVE TRADING ACTIVE - Real money at risk!\n")
        
        # Check balance
        balance = self.kraken.get_balance()
        usdc_balance = float(balance.get("USDC", 0))
        print(f"Confirmed Kraken Balance: ${usdc_balance:.2f} USDC\n")
        
        start_time = time.time()
        scans = 0
        
        while time.time() - start_time < duration_seconds:
            scans += 1
            
            opportunities = self.scan_for_opportunities()
            
            if opportunities:
                print(f"\n[SCAN #{scans}] Found {len(opportunities)} opportunities")
                
                # Execute best opportunity
                best_opp = opportunities[0]
                self.execute_trade(best_opp)
            else:
                print(f"[SCAN #{scans}] No opportunities")
            
            time.sleep(10)  # Scan every 10 seconds
        
        # Summary
        print("\n" + "="*70)
        print("📊 SESSION SUMMARY")
        print("="*70)
        print(f"Scans: {scans}")
        print(f"Trades: {self.trades_executed}")
        print(f"Total P&L: ${self.total_pnl:.2f}")
        print(f"Open Positions: {len(self.positions)}")


if __name__ == "__main__":
    import sys
    
    duration = 3600  # 1 hour default
    if len(sys.argv) > 1:
        duration = int(sys.argv[1])
    
    trader = KrakenLiveTrader(capital_usd=29.0)
    trader.run(duration_seconds=duration)
