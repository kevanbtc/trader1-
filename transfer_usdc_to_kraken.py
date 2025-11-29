"""
TRANSFER USDC FROM ARBITRUM TO KRAKEN
Sends USDC tokens to Kraken deposit address
"""

import os
from web3 import Web3
from dotenv import load_dotenv
from decimal import Decimal

load_dotenv()

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

WALLET_ADDRESS = os.getenv("WALLET_ADDRESS")
WALLET_PRIVATE_KEY = os.getenv("WALLET_PRIVATE_KEY")

# Kraken deposit address (same for all tokens)
KRAKEN_DEPOSIT = Web3.to_checksum_address("0x7f6991a490f064e8eee0815ce60b7ef370fdb7c7")

# Arbitrum USDC contract
USDC_ADDRESS = Web3.to_checksum_address("0xaf88d065e77c8cC2239327C5EDb3A432268e5831")

# Arbitrum RPC
ARB_RPC = os.getenv("ARB_RPC_1", "https://arb1.arbitrum.io/rpc")

# ERC20 ABI (minimal for transfer)
ERC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function"
    },
    {
        "constant": False,
        "inputs": [
            {"name": "_to", "type": "address"},
            {"name": "_value", "type": "uint256"}
        ],
        "name": "transfer",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function"
    }
]

# ═══════════════════════════════════════════════════════════════════════════
# CONNECT TO ARBITRUM
# ═══════════════════════════════════════════════════════════════════════════

print("🌐 Connecting to Arbitrum...")
w3 = Web3(Web3.HTTPProvider(ARB_RPC))

if not w3.is_connected():
    print("❌ Failed to connect to Arbitrum")
    exit(1)

print(f"✅ Connected to Arbitrum (Chain ID: {w3.eth.chain_id})")

# ═══════════════════════════════════════════════════════════════════════════
# GET USDC CONTRACT
# ═══════════════════════════════════════════════════════════════════════════

usdc = w3.eth.contract(address=USDC_ADDRESS, abi=ERC20_ABI)
decimals = usdc.functions.decimals().call()

print(f"\n💵 USDC Contract: {USDC_ADDRESS}")
print(f"   Decimals: {decimals}")

# ═══════════════════════════════════════════════════════════════════════════
# CHECK BALANCES
# ═══════════════════════════════════════════════════════════════════════════

print(f"\n💰 Checking balances...")
print(f"   Wallet: {WALLET_ADDRESS}")

# USDC balance
usdc_balance_raw = usdc.functions.balanceOf(WALLET_ADDRESS).call()
usdc_balance = Decimal(str(usdc_balance_raw)) / Decimal(str(10 ** decimals))

print(f"   USDC: {usdc_balance} USDC")

if usdc_balance == 0:
    print("❌ No USDC balance!")
    exit(1)

# ETH balance (for gas)
eth_balance_wei = w3.eth.get_balance(WALLET_ADDRESS)
eth_balance = Decimal(str(w3.from_wei(eth_balance_wei, 'ether')))

print(f"   ETH:  {eth_balance} ETH (for gas)")

if eth_balance < Decimal("0.0001"):
    print("❌ Not enough ETH for gas!")
    exit(1)

# ═══════════════════════════════════════════════════════════════════════════
# TRANSFER AMOUNT
# ═══════════════════════════════════════════════════════════════════════════

# Transfer ALL USDC
transfer_amount = usdc_balance
transfer_amount_raw = int(usdc_balance * Decimal(str(10 ** decimals)))

print(f"\n📤 Transfer plan:")
print(f"   From: {WALLET_ADDRESS}")
print(f"   To: {KRAKEN_DEPOSIT}")
print(f"   Amount: {transfer_amount} USDC")
print(f"   Network: Arbitrum One")
print(f"   Token: USDC (native)")

# ═══════════════════════════════════════════════════════════════════════════
# ESTIMATE GAS
# ═══════════════════════════════════════════════════════════════════════════

print(f"\n⛽ Estimating gas...")

try:
    gas_estimate = usdc.functions.transfer(
        KRAKEN_DEPOSIT,
        transfer_amount_raw
    ).estimate_gas({'from': WALLET_ADDRESS})
    
    gas_price = w3.eth.gas_price
    estimated_cost_wei = gas_estimate * gas_price
    estimated_cost_eth = Decimal(str(w3.from_wei(estimated_cost_wei, 'ether')))
    
    print(f"   Gas limit: {gas_estimate}")
    print(f"   Gas price: {w3.from_wei(gas_price, 'gwei')} Gwei")
    print(f"   Estimated cost: {estimated_cost_eth} ETH (~${float(estimated_cost_eth) * 3500:.2f})")
    
except Exception as e:
    print(f"   ⚠️  Estimation failed: {e}")
    gas_estimate = 100000  # Fallback
    gas_price = w3.eth.gas_price
    estimated_cost_eth = Decimal(str(w3.from_wei(gas_estimate * gas_price, 'ether')))
    print(f"   Using fallback gas: {gas_estimate}")

# ═══════════════════════════════════════════════════════════════════════════
# CONFIRMATION
# ═══════════════════════════════════════════════════════════════════════════

print(f"\n⚠️  CONFIRMATION REQUIRED")
print(f"   This will send {transfer_amount} USDC to Kraken")
print(f"   Destination: {KRAKEN_DEPOSIT}")
print(f"   Network: Arbitrum One (VERIFY THIS!)")
print(f"   ETA: ~10 minutes")
print(f"   Gas cost: ~{estimated_cost_eth} ETH")

confirmation = input("\n   Type 'SEND' to execute transfer: ")

if confirmation.strip().upper() != "SEND":
    print("❌ Transfer cancelled")
    exit(0)

# ═══════════════════════════════════════════════════════════════════════════
# BUILD TRANSACTION
# ═══════════════════════════════════════════════════════════════════════════

print(f"\n🔨 Building transaction...")

nonce = w3.eth.get_transaction_count(WALLET_ADDRESS)

# Build transfer function call
transfer_function = usdc.functions.transfer(
    KRAKEN_DEPOSIT,
    transfer_amount_raw
)

# Build transaction
transaction = transfer_function.build_transaction({
    'from': WALLET_ADDRESS,
    'gas': gas_estimate,
    'gasPrice': gas_price,
    'nonce': nonce,
    'chainId': w3.eth.chain_id
})

print(f"   Nonce: {nonce}")
print(f"   Chain ID: {w3.eth.chain_id}")

# ═══════════════════════════════════════════════════════════════════════════
# SIGN & SEND
# ═══════════════════════════════════════════════════════════════════════════

print(f"\n✍️  Signing transaction...")
signed_txn = w3.eth.account.sign_transaction(transaction, WALLET_PRIVATE_KEY)

print(f"🚀 Broadcasting to Arbitrum network...")
tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
tx_hash_hex = tx_hash.hex()

print(f"\n✅ TRANSACTION SENT!")
print(f"   TX Hash: {tx_hash_hex}")
print(f"   Explorer: https://arbiscan.io/tx/{tx_hash_hex}")

# ═══════════════════════════════════════════════════════════════════════════
# WAIT FOR CONFIRMATION
# ═══════════════════════════════════════════════════════════════════════════

print(f"\n⏳ Waiting for confirmation...")
print(f"   (This may take 15-30 seconds)")

try:
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    
    if receipt['status'] == 1:
        print(f"\n🎉 TRANSFER SUCCESSFUL!")
        print(f"   Block: {receipt['blockNumber']}")
        print(f"   Gas used: {receipt['gasUsed']}")
        
        actual_gas_cost_eth = Decimal(str(w3.from_wei(receipt['gasUsed'] * gas_price, 'ether')))
        print(f"   Actual gas cost: {actual_gas_cost_eth} ETH (~${float(actual_gas_cost_eth) * 3500:.2f})")
        
        print(f"\n📥 Kraken deposit:")
        print(f"   Amount sent: {transfer_amount} USDC")
        print(f"   Network: Arbitrum One")
        print(f"   ETA on Kraken: ~10 minutes")
        print(f"   Check: https://www.kraken.com/u/funding/deposit")
        
    else:
        print(f"\n❌ TRANSACTION FAILED!")
        print(f"   Receipt: {receipt}")
        
except Exception as e:
    print(f"\n⚠️  Error waiting for receipt: {e}")
    print(f"   Transaction may still succeed")
    print(f"   Check manually: https://arbiscan.io/tx/{tx_hash_hex}")

print("\n" + "="*70)
print("NEXT STEPS:")
print("1. Wait 10-15 minutes for Kraken to credit your account")
print("2. Check balance: python kraken_check_balance.py")
print("3. Total on Kraken: ~$37 ($29 USDC + $8 ETH)")
print("4. Ready to deploy Kraken trading swarm!")
print("="*70)
