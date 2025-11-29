"""
Test Kraken Order Execution
Single test order to verify nonce system works before running live trader
"""

import os
import sys
from dotenv import load_dotenv
from nonce_manager import next_nonce
import hashlib
import hmac
import base64
import requests
import time

load_dotenv()

API_KEY = os.getenv("KRAKEN_API_KEY")
API_SECRET = os.getenv("KRAKEN_API_SECRET")
BASE_URL = "https://api.kraken.com"

def kraken_signature(urlpath, data, secret):
    """Generate Kraken API signature"""
    postdata = ''.join([f"{key}={data[key]}&" for key in sorted(data.keys())])[:-1]
    encoded = (str(data['nonce']) + postdata).encode()
    message = urlpath.encode() + hashlib.sha256(encoded).digest()
    signature = hmac.new(base64.b64decode(secret), message, hashlib.sha512)
    return base64.b64encode(signature.digest()).decode()

def test_balance():
    """Test private endpoint with account balance (read-only)"""
    print("\n🔍 Testing Kraken API with account balance request...")
    print("   (This is read-only, no orders will be placed)")
    
    nonce = next_nonce()
    print(f"   Using nonce: {nonce}")
    
    data = {'nonce': nonce}
    headers = {
        'API-Key': API_KEY,
        'API-Sign': kraken_signature('/0/private/Balance', data, API_SECRET)
    }
    
    response = requests.post(f"{BASE_URL}/0/private/Balance", headers=headers, data=data, timeout=10)
    result = response.json()
    
    if result.get('error'):
        print(f"   ❌ ERROR: {result['error']}")
        return False
    else:
        print(f"   ✅ SUCCESS! Nonce accepted by Kraken")
        print(f"   Account balances:")
        for currency, amount in result['result'].items():
            if float(amount) > 0:
                print(f"      {currency}: {amount}")
        return True

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🔥 KRAKEN NONCE VERIFICATION TEST")
    print("="*60)
    
    success = test_balance()
    
    print("\n" + "="*60)
    if success:
        print("✅ NONCE SYSTEM WORKING - Ready for live trading!")
        print("\nNext step: Run kraken_live_trader_v2.py --live")
    else:
        print("❌ NONCE STILL REJECTED - Needs higher boost")
        print("\nThe nonce needs to be boosted even more")
    print("="*60 + "\n")
    
    sys.exit(0 if success else 1)
