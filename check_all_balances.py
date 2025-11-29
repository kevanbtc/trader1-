"""
CHECK ALL WALLET BALANCES
Shows balances across Arbitrum, BSC, and Kraken
"""

import os
from web3 import Web3
from dotenv import load_dotenv
import requests
import hmac
import hashlib
import base64
import urllib.parse
import time

load_dotenv()

WALLET_ADDRESS = os.getenv("WALLET_ADDRESS")
WALLET_PRIVATE_KEY = os.getenv("WALLET_PRIVATE_KEY")

print("=" * 70)
print("WALLET BALANCE CHECK - ALL CHAINS")
print("=" * 70)
print(f"\nWallet: {WALLET_ADDRESS}\n")

# ═══════════════════════════════════════════════════════════════════════════
# ARBITRUM
# ═══════════════════════════════════════════════════════════════════════════

print("🔵 ARBITRUM ONE")
print("-" * 70)

arb_rpc = os.getenv("ARB_RPC_1", "https://arb1.arbitrum.io/rpc")
w3_arb = Web3(Web3.HTTPProvider(arb_rpc))

if w3_arb.is_connected():
    # ETH balance
    eth_balance_wei = w3_arb.eth.get_balance(WALLET_ADDRESS)
    eth_balance = float(w3_arb.from_wei(eth_balance_wei, 'ether'))
    eth_usd = eth_balance * 3500  # Approx ETH price
    
    print(f"   ETH:  {eth_balance:.6f} ETH (~${eth_usd:.2f} USD)")
    
    # USDC balance (Arbitrum USDC: 0xaf88d065e77c8cC2239327C5EDb3A432268e5831)
    usdc_address = Web3.to_checksum_address("0xaf88d065e77c8cC2239327C5EDb3A432268e5831")
    usdc_abi = [{"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"},{"constant":True,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"type":"function"}]
    
    try:
        usdc_contract = w3_arb.eth.contract(address=usdc_address, abi=usdc_abi)
        usdc_balance_raw = usdc_contract.functions.balanceOf(WALLET_ADDRESS).call()
        usdc_decimals = usdc_contract.functions.decimals().call()
        usdc_balance = usdc_balance_raw / (10 ** usdc_decimals)
        print(f"   USDC: {usdc_balance:.2f} USDC")
    except Exception as e:
        print(f"   USDC: Error reading ({str(e)[:50]})")
    
    arb_total = eth_usd + usdc_balance
    print(f"\n   TOTAL: ~${arb_total:.2f} USD")
else:
    print("   ❌ Not connected")

# ═══════════════════════════════════════════════════════════════════════════
# BSC (BINANCE SMART CHAIN)
# ═══════════════════════════════════════════════════════════════════════════

print("\n🟡 BSC (BINANCE SMART CHAIN)")
print("-" * 70)

bsc_rpc = os.getenv("BSC_RPC_1", "https://bsc-dataseed1.binance.org")
w3_bsc = Web3(Web3.HTTPProvider(bsc_rpc))

if w3_bsc.is_connected():
    # BNB balance
    bnb_balance_wei = w3_bsc.eth.get_balance(WALLET_ADDRESS)
    bnb_balance = float(w3_bsc.from_wei(bnb_balance_wei, 'ether'))
    bnb_usd = bnb_balance * 600  # Approx BNB price
    
    print(f"   BNB:  {bnb_balance:.6f} BNB (~${bnb_usd:.2f} USD)")
    
    # USDC balance (BSC USDC: 0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d)
    usdc_bsc_address = Web3.to_checksum_address("0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d")
    usdc_abi = [{"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"},{"constant":True,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"type":"function"}]
    
    try:
        usdc_bsc_contract = w3_bsc.eth.contract(address=usdc_bsc_address, abi=usdc_abi)
        usdc_bsc_balance_raw = usdc_bsc_contract.functions.balanceOf(WALLET_ADDRESS).call()
        usdc_bsc_decimals = usdc_bsc_contract.functions.decimals().call()
        usdc_bsc_balance = usdc_bsc_balance_raw / (10 ** usdc_bsc_decimals)
        print(f"   USDC: {usdc_bsc_balance:.2f} USDC")
    except Exception as e:
        print(f"   USDC: Error reading ({str(e)[:50]})")
        usdc_bsc_balance = 0
    
    bsc_total = bnb_usd + usdc_bsc_balance
    print(f"\n   TOTAL: ~${bsc_total:.2f} USD")
else:
    print("   ❌ Not connected")
    bsc_total = 0
    usdc_bsc_balance = 0

# ═══════════════════════════════════════════════════════════════════════════
# KRAKEN
# ═══════════════════════════════════════════════════════════════════════════

print("\n🦑 KRAKEN CEX")
print("-" * 70)

API_KEY = os.getenv("KRAKEN_API_KEY")
API_SECRET = os.getenv("KRAKEN_API_SECRET")
API_URL = "https://api.kraken.com"

def sign(endpoint, data):
    postdata = urllib.parse.urlencode(data)
    encoded = (str(data['nonce']) + postdata).encode()
    message = endpoint.encode() + hashlib.sha256(encoded).digest()
    signature = hmac.new(base64.b64decode(API_SECRET), message, hashlib.sha512)
    return base64.b64encode(signature.digest()).decode()

endpoint = "/0/private/Balance"
nonce = str(int(time.time() * 1000000))
data = {"nonce": nonce}
headers = {
    "API-Key": API_KEY,
    "API-Sign": sign(endpoint, data)
}

try:
    response = requests.post(API_URL + endpoint, data=data, headers=headers, timeout=10)
    result = response.json()
    
    if result.get("error"):
        print(f"   ❌ Error: {result['error']}")
        kraken_total = 0
    else:
        balances = result.get("result", {})
        
        if not balances:
            print("   Empty (no assets)")
            kraken_total = 0
        else:
            kraken_total = 0
            
            for currency, amount in balances.items():
                amount_float = float(amount)
                
                if amount_float > 0.0000001:
                    # ETH variants
                    if any(currency.startswith(v) for v in ["XETH", "ETH", "ETH2"]):
                        eth_val = amount_float * 3500
                        print(f"   ETH:  {amount_float:.8f} ETH (~${eth_val:.2f} USD)")
                        kraken_total += eth_val
                    
                    # USD stablecoins
                    elif currency in ["ZUSD", "USD", "USDT", "USDC"]:
                        print(f"   {currency}: {amount_float:.4f} USD")
                        kraken_total += amount_float
                    
                    # Other
                    else:
                        print(f"   {currency}: {amount_float:.8f}")
            
            print(f"\n   TOTAL: ~${kraken_total:.2f} USD")
except Exception as e:
    print(f"   ❌ Connection error: {str(e)[:50]}")
    kraken_total = 0

# ═══════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("GRAND TOTAL ACROSS ALL ACCOUNTS")
print("=" * 70)

grand_total = arb_total + bsc_total + kraken_total

print(f"\n   Arbitrum:  ${arb_total:.2f}")
print(f"   BSC:       ${bsc_total:.2f}")
print(f"   Kraken:    ${kraken_total:.2f}")
print(f"\n   TOTAL:     ${grand_total:.2f} USD")

print("\n" + "=" * 70)

if usdc_bsc_balance > 0:
    print("\n💡 NOTE: You have USDC on BSC!")
    print(f"   ${usdc_bsc_balance:.2f} USDC is sitting on Binance Smart Chain")
    print(f"   This is NOT the same as Arbitrum funds")
    print(f"   BSC wallet needs BNB for gas to move USDC")
