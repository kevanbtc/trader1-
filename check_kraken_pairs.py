#!/usr/bin/env python3
"""Check if Kraken has USDC trading pairs"""
import requests

pairs_to_check = ['BTCUSDC', 'ETHUSDC', 'SOLUSDC', 'XRPUSDC']

print("\n🔍 CHECKING KRAKEN USDC PAIRS...")
print("=" * 60)

for pair in pairs_to_check:
    try:
        url = f'https://api.kraken.com/0/public/Ticker?pair={pair}'
        r = requests.get(url, timeout=5)
        data = r.json()
        
        if data.get('error') and data['error']:
            print(f'❌ {pair}: ERROR - {data["error"]}')
        elif data.get('result'):
            result_key = list(data['result'].keys())[0]
            price = data['result'][result_key]['c'][0]
            volume = data['result'][result_key]['v'][1]  # 24h volume
            print(f'✅ {pair} (Kraken: {result_key})')
            print(f'   Price: ${price}')
            print(f'   24h Volume: {volume} units')
        else:
            print(f'❌ {pair}: NOT FOUND')
    except Exception as e:
        print(f'❌ {pair}: {e}')
    print()

print("=" * 60)
