"""
Quick diagnostic to check ETH price feeds
"""

import requests

# Kraken
kraken = requests.get("https://api.kraken.com/0/public/Ticker?pair=XETHZUSD", timeout=5).json()
kraken_eth = kraken["result"]["XETHZUSD"]
kraken_ask = float(kraken_eth['a'][0])
kraken_bid = float(kraken_eth['b'][0])
kraken_mid = (kraken_ask + kraken_bid) / 2

# Binance
binance = requests.get("https://api.binance.com/api/3/ticker/price?symbol=ETHUSDT", timeout=5).json()
binance_price = float(binance["price"])

# Coinbase
coinbase = requests.get("https://api.coinbase.com/v2/prices/ETH-USD/spot", timeout=5).json()
coinbase_price = float(coinbase["data"]["amount"])

print(f"ETH Prices:")
print(f"  Kraken: ${kraken_mid:.2f} (ask: ${kraken_ask:.2f}, bid: ${kraken_bid:.2f})")
print(f"  Binance: ${binance_price:.2f}")
print(f"  Coinbase: ${coinbase_price:.2f}")
print(f"\nKraken/Binance ratio: {kraken_mid / binance_price:.2f}x")
print(f"Kraken/Coinbase ratio: {kraken_mid / coinbase_price:.2f}x")
