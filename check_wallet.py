#!/usr/bin/env python3
"""Check actual wallet balance"""
from web3 import Web3
import os

# Connect to Arbitrum
from agents.rpc_config import RPCConfig
RPC = RPCConfig.get_rpc('ARBITRUM')
WALLET = "0x5fc05DA8cB29f08754ac120Ab6F4F6176774b53E"

# USDC on Arbitrum
USDC_ADDRESS = "0xaf88d065e77c8cC2239327C5EDb3A432268e5831"
USDT_ADDRESS = "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9"

w3 = Web3(Web3.HTTPProvider(RPC))

print("=" * 60)
print("WALLET BALANCE CHECK")
print("=" * 60)
print(f"Address: {WALLET}")
print()

# Get ETH balance
eth_balance = w3.eth.get_balance(WALLET) / 1e18
eth_price = 3500  # Approximate
eth_usd = eth_balance * eth_price

print(f"ETH:  {eth_balance:.6f} ETH")
print(f"      ~${eth_usd:.2f} USD")
print()

# Check USDC
usdc_abi = [{"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"},{"constant":True,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"type":"function"}]
try:
    usdc = w3.eth.contract(address=Web3.to_checksum_address(USDC_ADDRESS), abi=usdc_abi)
    usdc_balance = usdc.functions.balanceOf(Web3.to_checksum_address(WALLET)).call() / 1e6
    print(f"USDC: {usdc_balance:.2f} USDC")
except Exception as e:
    print(f"USDC: Error - {e}")

# Check USDT
try:
    usdt = w3.eth.contract(address=Web3.to_checksum_address(USDT_ADDRESS), abi=usdc_abi)
    usdt_balance = usdt.functions.balanceOf(Web3.to_checksum_address(WALLET)).call() / 1e6
    print(f"USDT: {usdt_balance:.2f} USDT")
except Exception as e:
    print(f"USDT: Error - {e}")

print()
total_usd = eth_usd
if 'usdc_balance' in locals():
    total_usd += usdc_balance
if 'usdt_balance' in locals():
    total_usd += usdt_balance
    
print(f"TOTAL ESTIMATED: ${total_usd:.2f} USD")
print("=" * 60)
