"""
Kraken Balance Dumper
Shows ALL assets in your Kraken account with exact naming
"""

import os
import base64
import hashlib
import hmac
import requests
from dotenv import load_dotenv
from nonce_manager import next_nonce

load_dotenv()

API_KEY = os.getenv("KRAKEN_API_KEY")
API_SECRET = os.getenv("KRAKEN_API_SECRET")
KRAKEN_BASE = "https://api.kraken.com"

def kraken_signature(urlpath, data, secret):
    """Generate Kraken API signature"""
    postdata = '&'.join([f"{key}={data[key]}" for key in sorted(data.keys())])
    encoded = (str(data['nonce']) + postdata).encode()
    message = urlpath.encode() + hashlib.sha256(encoded).digest()
    signature = hmac.new(base64.b64decode(secret), message, hashlib.sha512)
    return base64.b64encode(signature.digest()).decode()

def kraken_private(path, data=None):
    """Execute private API request"""
    if data is None:
        data = {}
    
    data['nonce'] = next_nonce()
    
    headers = {
        'API-Key': API_KEY,
        'API-Sign': kraken_signature(path, data, API_SECRET)
    }
    
    response = requests.post(KRAKEN_BASE + path, headers=headers, data=data, timeout=10)
    result = response.json()
    
    if result.get('error'):
        print(f"❌ ERROR: {result['error']}")
        return None
    
    return result

def main():
    print("\n" + "="*60)
    print("🔍 KRAKEN ACCOUNT BALANCE DUMP")
    print("="*60)
    print()
    
    result = kraken_private("/0/private/Balance")
    
    if not result:
        print("Failed to fetch balances")
        return
    
    balances = result.get("result", {})
    
    if not balances:
        print("No balances found in account")
        return
    
    print("Asset Name    | Amount           | Notes")
    print("-" * 60)
    
    total_usd_value = 0
    
    for asset, amount in sorted(balances.items()):
        amt = float(amount)
        if amt == 0:
            continue
        
        # Add helpful notes for common assets
        notes = {
            'ZUSD': '← Real U.S. Dollars (fiat)',
            'USDC': '← Circle USDC Stablecoin',
            'USDT': '← Tether USDT Stablecoin',
            'XXBT': '← Bitcoin',
            'XETH': '← Ethereum',
            'SOL': '← Solana',
            'XXRP': '← Ripple XRP',
            'ZEUR': '← Euros (fiat)',
        }
        
        note = notes.get(asset, '')
        
        print(f"{asset:12s}  | {amt:16.8f} {note}")
        
        # Rough USD value estimation
        if asset in ['ZUSD', 'USDC', 'USDT']:
            total_usd_value += amt
    
    print("-" * 60)
    print(f"\n💰 Total Stablecoin/USD Value: ${total_usd_value:.2f}")
    print()
    print("=" * 60)
    print()
    print("📋 IMPORTANT NOTES:")
    print()
    print("• ZUSD = Real U.S. dollars (Kraken's fiat currency)")
    print("• USDC = Circle's USDC stablecoin (ERC-20 token)")
    print("• Most deposits from banks go to ZUSD, not USDC")
    print("• Trading pairs use ZUSD for USD markets (e.g., XXBTZUSD)")
    print()
    print("✅ If you see ZUSD with your $29, update the trader to use ZUSD")
    print("✅ If you see USDC with your $29, the trader is already correct")
    print()
    print("=" * 60)
    print()

if __name__ == "__main__":
    main()
