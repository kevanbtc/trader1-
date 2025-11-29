"""
KRAKEN BALANCE CHECKER
Verifies your Kraken account balance after transfer
"""

import os
import hmac
import hashlib
import base64
import urllib.parse
import time
import requests
from dotenv import load_dotenv

load_dotenv()

# ═══════════════════════════════════════════════════════════════════════════
# KRAKEN API CREDENTIALS
# ═══════════════════════════════════════════════════════════════════════════

API_KEY = os.getenv("KRAKEN_API_KEY")
API_SECRET = os.getenv("KRAKEN_API_SECRET")
API_URL = "https://api.kraken.com"

# ═══════════════════════════════════════════════════════════════════════════
# SIGN REQUEST
# ═══════════════════════════════════════════════════════════════════════════

def sign(endpoint, data):
    """Generate Kraken API signature"""
    postdata = urllib.parse.urlencode(data)
    encoded = (str(data['nonce']) + postdata).encode()
    message = endpoint.encode() + hashlib.sha256(encoded).digest()
    signature = hmac.new(base64.b64decode(API_SECRET), message, hashlib.sha512)
    return base64.b64encode(signature.digest()).decode()

# ═══════════════════════════════════════════════════════════════════════════
# GET BALANCE
# ═══════════════════════════════════════════════════════════════════════════

def get_balance():
    """Fetch Kraken account balance"""
    endpoint = "/0/private/Balance"
    nonce = str(int(time.time() * 1000000))
    
    data = {"nonce": nonce}
    headers = {
        "API-Key": API_KEY,
        "API-Sign": sign(endpoint, data)
    }
    
    response = requests.post(API_URL + endpoint, data=data, headers=headers)
    return response.json()

# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

print("🦑 KRAKEN BALANCE CHECKER")
print("="*70)

result = get_balance()

if result.get("error"):
    print(f"❌ Error: {result['error']}")
else:
    balances = result.get("result", {})
    
    if not balances:
        print("💰 Balance: $0.00")
        print("   (No assets detected)")
    else:
        print("💰 Account Balances:\n")
        
        total_value_usd = 0.0
        
        # ETH variants
        eth_variants = ["XETH", "ETH", "ETH2", "ETH2.S"]
        eth_total = 0.0
        
        for currency, amount in balances.items():
            amount_float = float(amount)
            
            if amount_float > 0.0000001:  # Filter dust
                
                # Group ETH variants
                if any(currency.startswith(variant) for variant in eth_variants):
                    eth_total += amount_float
                    continue
                
                # USD stablecoins
                if currency in ["ZUSD", "USD", "USDT", "USDC"]:
                    print(f"   {currency:10} {amount_float:>12.4f} USD")
                    total_value_usd += amount_float
                
                # Other assets
                else:
                    print(f"   {currency:10} {amount_float:>12.8f}")
        
        # Display ETH total
        if eth_total > 0:
            print(f"   {'ETH (all)':10} {eth_total:>12.8f} ETH")
            # Rough USD estimate (use current ETH price if needed)
            eth_usd_estimate = eth_total * 3500  # Approximate ETH price
            total_value_usd += eth_usd_estimate
        
        print(f"\n   {'TOTAL VALUE':10} ~${total_value_usd:>12.2f} USD")
        
print("\n" + "="*70)

# Show transfer status hint
print("\n💡 If balance hasn't updated:")
print("   - Arbitrum → Kraken takes ~10 minutes")
print("   - Check TX: https://arbiscan.io/")
print("   - Kraken deposit history: https://www.kraken.com/u/funding/deposit")
