"""
KRAKEN PREMIUM TRACKER (Agent A)
Monitors Kraken price lag vs Binance and executes arbitrage
Strategy #6 from the Kraken playbook
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
import json
from collections import deque

load_dotenv()

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

API_KEY = os.getenv("KRAKEN_API_KEY")
API_SECRET = os.getenv("KRAKEN_API_SECRET")
KRAKEN_API_URL = "https://api.kraken.com"
BINANCE_API_URL = "https://api.binance.com"

# Trading pairs (Kraken format → Binance format)
PAIRS = {
    "XXBTZUSD": "BTCUSDT",    # BTC/USD
    "XETHZUSD": "ETHUSDT",    # ETH/USD
    "SOLUSD": "SOLUSDT",      # SOL/USD
}

# Strategy parameters
MIN_PREMIUM = Decimal("0.0005")  # 0.05% minimum premium
MAX_PREMIUM = Decimal("0.002")    # 0.2% maximum premium
POSITION_SIZE_USD = Decimal("13.00")  # $13 per trade
SCAN_INTERVAL = 0.5  # 500ms between scans

# ═══════════════════════════════════════════════════════════════════════════
# KRAKEN API
# ═══════════════════════════════════════════════════════════════════════════

def sign_kraken(endpoint, data):
    """Generate Kraken API signature"""
    postdata = urllib.parse.urlencode(data)
    encoded = (str(data['nonce']) + postdata).encode()
    message = endpoint.encode() + hashlib.sha256(encoded).digest()
    signature = hmac.new(base64.b64decode(API_SECRET), message, hashlib.sha512)
    return base64.b64encode(signature.digest()).decode()

def kraken_public_request(endpoint, params=None):
    """Make Kraken public API request"""
    url = f"{KRAKEN_API_URL}{endpoint}"
    try:
        response = requests.get(url, params=params, timeout=5)
        return response.json()
    except Exception as e:
        return {"error": [str(e)]}

def kraken_private_request(endpoint, data):
    """Make Kraken private API request"""
    headers = {
        "API-Key": API_KEY,
        "API-Sign": sign_kraken(endpoint, data)
    }
    try:
        response = requests.post(
            f"{KRAKEN_API_URL}{endpoint}",
            data=data,
            headers=headers,
            timeout=5
        )
        return response.json()
    except Exception as e:
        return {"error": [str(e)]}

def get_kraken_price(pair):
    """Get current Kraken price"""
    result = kraken_public_request("/0/public/Ticker", {"pair": pair})
    
    if result.get("error"):
        return None
    
    data = result.get("result", {}).get(pair, {})
    
    if not data:
        return None
    
    # Get bid/ask
    bid = Decimal(str(data["b"][0]))
    ask = Decimal(str(data["a"][0]))
    
    return {
        "bid": bid,
        "ask": ask,
        "mid": (bid + ask) / 2,
        "timestamp": time.time()
    }

# ═══════════════════════════════════════════════════════════════════════════
# BINANCE API
# ═══════════════════════════════════════════════════════════════════════════

def get_binance_price(pair):
    """Get current Binance price"""
    try:
        response = requests.get(
            f"{BINANCE_API_URL}/api/v3/ticker/bookTicker",
            params={"symbol": pair},
            timeout=5
        )
        data = response.json()
        
        bid = Decimal(str(data["bidPrice"]))
        ask = Decimal(str(data["askPrice"]))
        
        return {
            "bid": bid,
            "ask": ask,
            "mid": (bid + ask) / 2,
            "timestamp": time.time()
        }
    except Exception as e:
        return None

# ═══════════════════════════════════════════════════════════════════════════
# PREMIUM DETECTOR
# ═══════════════════════════════════════════════════════════════════════════

class PremiumTracker:
    def __init__(self):
        self.price_history = {pair: deque(maxlen=20) for pair in PAIRS.keys()}
        self.opportunities = []
        self.stats = {
            "scans": 0,
            "opportunities_found": 0,
            "trades_executed": 0
        }
    
    def scan_premium(self, kraken_pair, binance_pair):
        """
        Check if Kraken is lagging behind Binance
        Returns opportunity if premium detected
        """
        # Get prices
        kraken = get_kraken_price(kraken_pair)
        binance = get_binance_price(binance_pair)
        
        if not kraken or not binance:
            return None
        
        # Calculate premium (how much Kraken lags)
        kraken_mid = kraken["mid"]
        binance_mid = binance["mid"]
        
        premium = (binance_mid - kraken_mid) / binance_mid
        
        # Store in history
        self.price_history[kraken_pair].append({
            "timestamp": time.time(),
            "kraken": kraken_mid,
            "binance": binance_mid,
            "premium": premium
        })
        
        # Check if premium is in range
        if MIN_PREMIUM <= premium <= MAX_PREMIUM:
            opportunity = {
                "pair": kraken_pair,
                "binance_pair": binance_pair,
                "kraken_price": kraken_mid,
                "binance_price": binance_mid,
                "premium": premium,
                "direction": "BUY",  # Buy on Kraken (cheaper)
                "kraken_ask": kraken["ask"],
                "timestamp": time.time()
            }
            
            self.opportunities.append(opportunity)
            self.stats["opportunities_found"] += 1
            
            return opportunity
        
        return None
    
    def scan_all_pairs(self):
        """Scan all trading pairs"""
        self.stats["scans"] += 1
        
        opportunities = []
        
        for kraken_pair, binance_pair in PAIRS.items():
            opp = self.scan_premium(kraken_pair, binance_pair)
            if opp:
                opportunities.append(opp)
        
        return opportunities

# ═══════════════════════════════════════════════════════════════════════════
# AGENT A - MAIN LOOP
# ═══════════════════════════════════════════════════════════════════════════

def run_agent_a(duration_seconds=120, mode="paper"):
    """
    Run Premium Tracker agent
    mode: "paper" or "live"
    """
    
    print("=" * 70)
    print("🦑 KRAKEN PREMIUM TRACKER (Agent A)")
    print("=" * 70)
    print(f"\nMode: {'📄 PAPER' if mode == 'paper' else '🔴 LIVE'}")
    print(f"Capital: ${POSITION_SIZE_USD}")
    print(f"Min Premium: {MIN_PREMIUM * 100:.2f}%")
    print(f"Max Premium: {MAX_PREMIUM * 100:.2f}%")
    print(f"Duration: {duration_seconds}s")
    print(f"Pairs: {len(PAIRS)}")
    
    tracker = PremiumTracker()
    
    start_time = time.time()
    next_scan = start_time
    
    print("\n" + "-" * 70)
    print("Starting scan...\n")
    
    try:
        while time.time() - start_time < duration_seconds:
            current_time = time.time()
            
            if current_time >= next_scan:
                # Scan for opportunities
                opportunities = tracker.scan_all_pairs()
                
                # Display scan result
                elapsed = int(current_time - start_time)
                print(f"[{elapsed}s] Scan #{tracker.stats['scans']} | "
                      f"Opportunities: {len(opportunities)}")
                
                # Show opportunities
                for opp in opportunities:
                    premium_pct = opp["premium"] * 100
                    print(f"   ✨ {opp['pair']}: "
                          f"Kraken ${opp['kraken_price']:.2f} vs "
                          f"Binance ${opp['binance_price']:.2f} | "
                          f"Premium: {premium_pct:.3f}%")
                
                next_scan = current_time + SCAN_INTERVAL
            
            time.sleep(0.1)
    
    except KeyboardInterrupt:
        print("\n⚠️  Stopped by user")
    
    # Summary
    duration = time.time() - start_time
    
    print("\n" + "=" * 70)
    print("📊 AGENT A SUMMARY")
    print("=" * 70)
    print(f"Duration: {duration:.1f}s")
    print(f"Scans: {tracker.stats['scans']}")
    print(f"Opportunities: {tracker.stats['opportunities_found']}")
    print(f"Trades: {tracker.stats['trades_executed']}")
    print(f"Capital: ${POSITION_SIZE_USD}")
    print("=" * 70)
    
    return tracker

# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    
    # Parse args
    duration = 120  # 2 minutes default
    mode = "paper"
    
    if "--duration" in sys.argv:
        idx = sys.argv.index("--duration")
        duration = int(sys.argv[idx + 1])
    
    if "--live" in sys.argv:
        mode = "live"
    
    run_agent_a(duration, mode)
