"""
ARBITRUM → KRAKEN ETH TRANSFER
Sends ETH from Arbitrum wallet to Kraken deposit address
"""

import os
from web3 import Web3
from dotenv import load_dotenv
from decimal import Decimal
import time

load_dotenv()

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

# Source wallet (Arbitrum)
WALLET_ADDRESS = os.getenv("WALLET_ADDRESS")
WALLET_PRIVATE_KEY = os.getenv("WALLET_PRIVATE_KEY")

# Destination (Kraken ETH deposit address) - checksummed
KRAKEN_ETH_DEPOSIT = Web3.to_checksum_address("0x7f6991a490f064e8eee0815ce60b7ef370fdb7c7")

# Arbitrum RPC
ARB_RPC = os.getenv("ARB_RPC_1", "https://arb1.arbitrum.io/rpc")

# Transfer settings - MAXIMUM TRANSFER MODE
LEAVE_FOR_GAS = Decimal("0.0005")  # Minimum possible reserve
SAFETY_BUFFER = Decimal("0.0001")  # Minimal safety margin

# ═══════════════════════════════════════════════════════════════════════════
# WEB3 CONNECTION
# ═══════════════════════════════════════════════════════════════════════════

print("🌐 Connecting to Arbitrum...")
w3 = Web3(Web3.HTTPProvider(ARB_RPC))

if not w3.is_connected():
    print("❌ Failed to connect to Arbitrum RPC")
    exit(1)

print(f"✅ Connected to Arbitrum (Chain ID: {w3.eth.chain_id})")

# ═══════════════════════════════════════════════════════════════════════════
# BALANCE CHECK
# ═══════════════════════════════════════════════════════════════════════════

print(f"\n💰 Checking wallet balance...")
print(f"   Source: {WALLET_ADDRESS}")

balance_wei = w3.eth.get_balance(WALLET_ADDRESS)
balance_eth = Decimal(str(w3.from_wei(balance_wei, 'ether')))

print(f"   Balance: {balance_eth} ETH")

if balance_eth < LEAVE_FOR_GAS + SAFETY_BUFFER:
    print(f"❌ Balance too low. Need at least {LEAVE_FOR_GAS + SAFETY_BUFFER} ETH")
    exit(1)

# ═══════════════════════════════════════════════════════════════════════════
# CALCULATE TRANSFER AMOUNT
# ═══════════════════════════════════════════════════════════════════════════

# Estimate gas for ETH transfer (Arbitrum needs higher limit)
gas_estimate = 100000  # Arbitrum requires higher gas limit
gas_price = w3.eth.gas_price
estimated_gas_cost_wei = gas_estimate * gas_price
estimated_gas_cost_eth = Decimal(str(w3.from_wei(estimated_gas_cost_wei, 'ether')))

print(f"\n⛽ Gas estimate:")
print(f"   Gas limit: {gas_estimate}")
print(f"   Gas price: {w3.from_wei(gas_price, 'gwei')} Gwei")
print(f"   Estimated cost: {estimated_gas_cost_eth} ETH")

# Calculate transfer amount (leave gas reserve)
reserve_eth = LEAVE_FOR_GAS + estimated_gas_cost_eth + SAFETY_BUFFER
transfer_eth = balance_eth - reserve_eth

if transfer_eth <= 0:
    print(f"❌ Not enough balance after gas reserve")
    print(f"   Balance: {balance_eth} ETH")
    print(f"   Reserve needed: {reserve_eth} ETH")
    exit(1)

transfer_wei = w3.to_wei(float(transfer_eth), 'ether')

print(f"\n📤 Transfer plan:")
print(f"   From: {WALLET_ADDRESS}")
print(f"   To: {KRAKEN_ETH_DEPOSIT}")
print(f"   Amount: {transfer_eth} ETH")
print(f"   Reserve: {reserve_eth} ETH (for gas + buffer)")
print(f"   Remaining balance: {reserve_eth} ETH")

# ═══════════════════════════════════════════════════════════════════════════
# CONFIRMATION
# ═══════════════════════════════════════════════════════════════════════════

print(f"\n⚠️  CONFIRMATION REQUIRED")
print(f"   This will send {transfer_eth} ETH to Kraken")
print(f"   Destination: {KRAKEN_ETH_DEPOSIT}")
print(f"   ETA: ~10 minutes (Arbitrum → Kraken)")

confirmation = input("\n   Type 'SEND' to execute transfer: ")

if confirmation.strip().upper() != "SEND":
    print("❌ Transfer cancelled")
    exit(0)

# ═══════════════════════════════════════════════════════════════════════════
# BUILD TRANSACTION
# ═══════════════════════════════════════════════════════════════════════════

print(f"\n🔨 Building transaction...")

nonce = w3.eth.get_transaction_count(WALLET_ADDRESS)

transaction = {
    'from': WALLET_ADDRESS,
    'to': KRAKEN_ETH_DEPOSIT,
    'value': transfer_wei,
    'gas': gas_estimate,
    'gasPrice': gas_price,
    'nonce': nonce,
    'chainId': w3.eth.chain_id
}

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
        print(f"   Actual gas cost: {actual_gas_cost_eth} ETH")
        
        # Check new balance
        time.sleep(2)
        new_balance_wei = w3.eth.get_balance(WALLET_ADDRESS)
        new_balance_eth = Decimal(str(w3.from_wei(new_balance_wei, 'ether')))
        
        print(f"\n💰 New wallet balance: {new_balance_eth} ETH")
        print(f"\n📥 Kraken deposit:")
        print(f"   Amount sent: {transfer_eth} ETH")
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
print("3. Launch trading: python kraken_swarm.py")
print("="*70)
