"""
Check ETH wallet balance and recent transactions
Verifies if the $8 ETH deposit was sent/received
"""

from web3 import Web3
import os
from dotenv import load_dotenv

load_dotenv()

# Your wallet address
WALLET = "0x5fc04257775C875d07cb18466361871FE53b53E"

# Multiple RPC endpoints
RPCS = {
    "Arbitrum": "https://arb1.arbitrum.io/rpc",
    "Ethereum": "https://eth.llamarpc.com",
    "Base": "https://mainnet.base.org"
}

def check_eth_balance():
    """Check ETH balance on all chains"""
    print("\n" + "="*60)
    print("🔍 CHECKING ETH BALANCES ACROSS CHAINS")
    print("="*60)
    print(f"Wallet: {WALLET}")
    print()
    
    total_usd = 0
    eth_price = 3400  # Approximate
    
    for chain, rpc in RPCS.items():
        try:
            w3 = Web3(Web3.HTTPProvider(rpc))
            balance_wei = w3.eth.get_balance(WALLET)
            balance_eth = w3.from_wei(balance_wei, 'ether')
            balance_usd = float(balance_eth) * eth_price
            
            if balance_eth > 0:
                print(f"✅ {chain:12s}: {balance_eth:.6f} ETH (${balance_usd:.2f})")
                total_usd += balance_usd
            else:
                print(f"   {chain:12s}: 0 ETH")
        except Exception as e:
            print(f"❌ {chain:12s}: Error - {e}")
    
    print()
    print(f"💰 Total ETH value: ${total_usd:.2f}")
    
    if total_usd < 5:
        print()
        print("⚠️  WARNING: Less than $5 in ETH found")
        print("    The $8 ETH deposit may not have been sent")
        print("    or was sent to a different address")
    
    print("="*60)
    print()

if __name__ == "__main__":
    check_eth_balance()
