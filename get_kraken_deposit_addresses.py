"""
GET KRAKEN DEPOSIT ADDRESS
Fetches deposit addresses for various assets
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

API_KEY = os.getenv("KRAKEN_API_KEY")
API_SECRET = os.getenv("KRAKEN_API_SECRET")
API_URL = "https://api.kraken.com"

def sign(endpoint, data):
    """Generate Kraken API signature"""
    postdata = urllib.parse.urlencode(data)
    encoded = (str(data['nonce']) + postdata).encode()
    message = endpoint.encode() + hashlib.sha256(encoded).digest()
    signature = hmac.new(base64.b64decode(API_SECRET), message, hashlib.sha512)
    return base64.b64encode(signature.digest()).decode()

def get_deposit_methods(asset):
    """Get available deposit methods for an asset"""
    endpoint = "/0/private/DepositMethods"
    nonce = str(int(time.time() * 1000000))
    
    data = {
        "nonce": nonce,
        "asset": asset
    }
    
    headers = {
        "API-Key": API_KEY,
        "API-Sign": sign(endpoint, data)
    }
    
    response = requests.post(API_URL + endpoint, data=data, headers=headers)
    return response.json()

def get_deposit_address(asset, method):
    """Get deposit address for an asset and method"""
    endpoint = "/0/private/DepositAddresses"
    nonce = str(int(time.time() * 1000000))
    
    data = {
        "nonce": nonce,
        "asset": asset,
        "method": method
    }
    
    headers = {
        "API-Key": API_KEY,
        "API-Sign": sign(endpoint, data)
    }
    
    response = requests.post(API_URL + endpoint, data=data, headers=headers)
    return response.json()

print("=" * 70)
print("KRAKEN DEPOSIT ADDRESSES")
print("=" * 70)

# Assets we want to deposit
assets = {
    "USDC": "USD Coin",
    "USDT": "Tether",
    "ETH": "Ethereum"
}

for asset_code, asset_name in assets.items():
    print(f"\n📥 {asset_name} ({asset_code})")
    print("-" * 70)
    
    # Get deposit methods
    methods_result = get_deposit_methods(asset_code)
    
    if methods_result.get("error"):
        print(f"   ❌ Error: {methods_result['error']}")
        continue
    
    methods = methods_result.get("result", [])
    
    if not methods:
        print(f"   ⚠️  No deposit methods available")
        continue
    
    # Show available methods
    print(f"   Available networks:")
    for i, method in enumerate(methods, 1):
        method_name = method.get("method", "Unknown")
        print(f"      {i}. {method_name}")
    
    # Get address for first method
    if methods:
        first_method = methods[0].get("method")
        
        print(f"\n   Getting address for {first_method}...")
        
        addr_result = get_deposit_address(asset_code, first_method)
        
        if addr_result.get("error"):
            print(f"   ❌ Error: {addr_result['error']}")
        else:
            addresses = addr_result.get("result", [])
            
            if addresses:
                for addr in addresses:
                    address = addr.get("address", "N/A")
                    tag = addr.get("tag")
                    
                    print(f"\n   ✅ DEPOSIT ADDRESS:")
                    print(f"      Address: {address}")
                    if tag:
                        print(f"      Tag/Memo: {tag}")
                    
                    # Show network info
                    if "network" in addr:
                        print(f"      Network: {addr['network']}")
                    
                    # Warning about minimum
                    print(f"\n      ⚠️  Check minimum deposit amount on Kraken")
                    print(f"      ⚠️  Wrong network = loss of funds!")
            else:
                print(f"   ⚠️  No addresses returned")

print("\n" + "=" * 70)
print("\n💡 IMPORTANT NOTES:")
print("   1. ALWAYS verify network matches (e.g., Arbitrum USDC → Arbitrum on Kraken)")
print("   2. Check minimum deposit amounts")
print("   3. Small test transfer first ($1-5)")
print("   4. Wait 10-30 minutes for confirmation")
print("\n" + "=" * 70)
