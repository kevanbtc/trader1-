#!/usr/bin/env python3
"""Test Kraken API credential loading"""

from dotenv import load_dotenv
import os

load_dotenv()

key = os.environ.get('KRAKEN_API_KEY')
secret = os.environ.get('KRAKEN_API_SECRET')

print("=" * 60)
print("🔧 KRAKEN API CREDENTIAL TEST")
print("=" * 60)
print()

if key:
    print(f"✅ API Key loaded: {len(key)} characters")
    print(f"   First 10 chars: {key[:10]}")
else:
    print("❌ API Key is NULL")

if secret:
    print(f"✅ API Secret loaded: {len(secret)} characters")
    print(f"   First 10 chars: {secret[:10]}")
else:
    print("❌ API Secret is NULL")

print()
print("=" * 60)

if key and secret:
    print("✅ Ready for LIVE trading!")
else:
    print("❌ Cannot trade - missing credentials")
