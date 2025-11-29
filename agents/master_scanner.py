"""
MASTER SCANNER - Patient Hunter for BIG HITS
Strategy: Turn $29 → $300 → $3000 with just 2-3 perfect trades
NO rushed trades. Only execute on 80%+ confidence setups.
"""

import os
import sys
import time
import json
from datetime import datetime, timedelta
from web3 import Web3
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

# Ensure UTF-8 capable console on Windows for emoji/logs
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Arbitrum RPC (multi-provider with failover)
try:
    from .rpc_utils import get_arbitrum_w3  # type: ignore
except Exception:
    from agents.rpc_utils import get_arbitrum_w3  # type: ignore
w3 = get_arbitrum_w3()

# Trading wallet
WALLET_ADDRESS = os.getenv("WALLET_ADDRESS")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")

# Contract addresses
UNISWAP_V3_FACTORY = "0x1F98431c8aD98523631AE4a59f267346ea31F984"
WETH = "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1"
USDC = "0xaf88d065e77c8cC2239327C5EDb3A432268e5831"
ARB = "0x912CE59144191C1204E64559FE8253a0e49E6548"

# Pool ABI (minimal)
POOL_ABI = [
    {
        "inputs": [],
        "name": "slot0",
        "outputs": [
            {"internalType": "uint160", "name": "sqrtPriceX96", "type": "uint160"},
            {"internalType": "int24", "name": "tick", "type": "int24"},
            {"internalType": "uint16", "name": "observationIndex", "type": "uint16"},
            {"internalType": "uint16", "name": "observationCardinality", "type": "uint16"},
            {"internalType": "uint16", "name": "observationCardinalityNext", "type": "uint16"},
            {"internalType": "uint8", "name": "feeProtocol", "type": "uint8"},
            {"internalType": "bool", "name": "unlocked", "type": "bool"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "liquidity",
        "outputs": [{"internalType": "uint128", "name": "", "type": "uint128"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "token0",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "token1",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# Factory ABI
FACTORY_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "tokenA", "type": "address"},
            {"internalType": "address", "name": "tokenB", "type": "address"},
            {"internalType": "uint24", "name": "fee", "type": "uint24"}
        ],
        "name": "getPool",
        "outputs": [{"internalType": "address", "name": "pool", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "token0", "type": "address"},
            {"indexed": True, "internalType": "address", "name": "token1", "type": "address"},
            {"indexed": True, "internalType": "uint24", "name": "fee", "type": "uint24"},
            {"indexed": False, "internalType": "int24", "name": "tickSpacing", "type": "int24"},
            {"indexed": False, "internalType": "address", "name": "pool", "type": "address"}
        ],
        "name": "PoolCreated",
        "type": "event"
    }
]

# ERC20 ABI
ERC20_ABI = [
    {
        "constant": True,
        "inputs": [],
        "name": "name",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
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
        "constant": True,
        "inputs": [],
        "name": "totalSupply",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function"
    }
]


class MasterScanner:
    def __init__(self):
        self.factory = w3.eth.contract(
            address=Web3.to_checksum_address(UNISWAP_V3_FACTORY),
            abi=FACTORY_ABI
        )
        self.opportunities = []
        self.last_scan_time = None
        self.scan_count = 0
        
    def get_pool_price(self, pool_address):
        """Get price from Uniswap V3 pool"""
        try:
            pool = w3.eth.contract(
                address=Web3.to_checksum_address(pool_address),
                abi=POOL_ABI
            )
            slot0 = pool.functions.slot0().call()
            liquidity = pool.functions.liquidity().call()
            
            sqrtPriceX96 = slot0[0]
            price = (sqrtPriceX96 / (2**96)) ** 2
            
            return price, liquidity
        except Exception as e:
            return None, None
    
    def check_new_pools(self):
        """Scan for newly created pools (simplified - disabled for now)"""
        # New token sniping is high risk and complex
        # Focus on leverage trading which has better odds
        return []
    
    def check_leverage_setups(self):
        """Check technical analysis for high-confidence leverage trades"""
        try:
            import requests
            
            pairs = [
                ('ETH/USD', 'ETH'),
                ('BTC/USD', 'BTC'),
                ('ARB/USD', 'ARB'),
                ('SOL/USD', 'SOL'),
                ('AVAX/USD', 'AVAX'),
                ('OP/USD', 'OP')
            ]
            
            opportunities = []
            for pair_name, symbol in pairs:
                # Get hourly data from CryptoCompare
                url = f'https://min-api.cryptocompare.com/data/v2/histohour?fsym={symbol}&tsym=USD&limit=100'
                response = requests.get(url, timeout=10)
                if response.status_code != 200:
                    continue
                
                data = response.json()
                if data.get('Response') != 'Success':
                    continue
                    
                candles = data['Data']['Data']
                if len(candles) < 100:
                    continue
                closes = [float(c['close']) for c in candles]  # Close prices
                
                # Simple RSI calculation
                changes = [closes[i] - closes[i-1] for i in range(1, len(closes))]
                gains = [c if c > 0 else 0 for c in changes]
                losses = [-c if c < 0 else 0 for c in changes]
                
                avg_gain = sum(gains[-14:]) / 14
                avg_loss = sum(losses[-14:]) / 14
                
                if avg_loss == 0:
                    rsi = 100
                else:
                    rs = avg_gain / avg_loss
                    rsi = 100 - (100 / (1 + rs))
                
                current_price = closes[-1]
                
                # Simple rules for 80%+ confidence
                # LONG: RSI < 25 (extremely oversold)
                # SHORT: RSI > 75 (extremely overbought)
                
                if rsi < 25:
                    opportunities.append({
                        'type': 'LEVERAGE_LONG',
                        'pair': pair_name,
                        'confidence': 80,
                        'reason': f'Extremely oversold - RSI {rsi:.1f}',
                        'price': current_price,
                        'timestamp': datetime.now().isoformat()
                    })
                elif rsi > 75:
                    opportunities.append({
                        'type': 'LEVERAGE_SHORT',
                        'pair': pair_name,
                        'confidence': 80,
                        'reason': f'Extremely overbought - RSI {rsi:.1f}',
                        'price': current_price,
                        'timestamp': datetime.now().isoformat()
                    })
            
            return opportunities
        except Exception as e:
            print(f"Error checking leverage: {e}")
            return []
    
    def check_whale_activity(self):
        """Monitor whale wallets for large buys (simplified)"""
        # TODO: Implement whale tracking
        # For now, return empty - this needs event monitoring
        return []
    
    def scan_all(self):
        """Run all scans and consolidate opportunities"""
        self.scan_count += 1
        print(f"\n{'='*80}")
        print(f"🔍 MASTER SCAN #{self.scan_count} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}")
        
        # Run all scanners
        new_pools = self.check_new_pools()
        leverage_setups = self.check_leverage_setups()
        whale_activity = self.check_whale_activity()
        
        # Consolidate
        all_opportunities = new_pools + leverage_setups + whale_activity
        
        # Filter to only 80%+ confidence
        high_confidence = [opp for opp in all_opportunities if opp.get('confidence', 0) >= 80]
        
        print(f"\n📊 Scan Results:")
        print(f"   New Token Launches: {len(new_pools)}")
        print(f"   Leverage Setups: {len(leverage_setups)}")
        print(f"   Whale Activity: {len(whale_activity)}")
        print(f"   🎯 HIGH CONFIDENCE (80%+): {len(high_confidence)}")
        
        if high_confidence:
            print(f"\n{'='*80}")
            print(f"🚨 ACTIONABLE OPPORTUNITIES FOUND!")
            print(f"{'='*80}")
            for i, opp in enumerate(high_confidence, 1):
                print(f"\n#{i} - {opp['type']} ({opp['confidence']}% confidence)")
                if opp['type'] == 'NEW_TOKEN_LAUNCH':
                    print(f"   Token: {opp['symbol']} ({opp['name']})")
                    print(f"   Liquidity: ${opp['liquidity_usd']:,.0f}")
                    print(f"   Pool: {opp['pool'][:10]}...")
                elif 'LEVERAGE' in opp['type']:
                    print(f"   Pair: {opp['pair']}")
                    print(f"   Reason: {opp['reason']}")
            
            # Save to file for manual review
            with open('opportunities.json', 'w') as f:
                json.dump(high_confidence, f, indent=2)
            
            print(f"\n💾 Saved to opportunities.json")
            print(f"⚠️  REVIEW BEFORE EXECUTING - These are your BIG HIT candidates")
        else:
            print(f"\n✋ No 80%+ opportunities yet. Patience pays.")
        
        self.last_scan_time = datetime.now()
        return high_confidence
    
    def run_continuous(self, scan_interval_minutes=10):
        """Run continuous scanning every N minutes"""
        print(f"🚀 MASTER SCANNER ACTIVE")
        print(f"Strategy: Patient hunter - only execute 80%+ confidence trades")
        print(f"Goal: $29 → $300 → $3000 with 2-3 BIG HITS")
        print(f"Scan Interval: Every {scan_interval_minutes} minutes")
        print(f"\nPress Ctrl+C to stop\n")
        
        try:
            while True:
                opportunities = self.scan_all()
                
                # If we found something, alert and wait for manual action
                if opportunities:
                    print(f"\n🔔 ALERT: {len(opportunities)} high-confidence opportunities!")
                    print(f"🛑 Review opportunities.json and decide whether to execute")
                
                # Wait for next scan
                print(f"\n⏳ Next scan in {scan_interval_minutes} minutes...")
                time.sleep(scan_interval_minutes * 60)
                
        except KeyboardInterrupt:
            print(f"\n\n🛑 Scanner stopped by user")
            print(f"Total scans completed: {self.scan_count}")
            if self.opportunities:
                print(f"Total opportunities found: {len(self.opportunities)}")


if __name__ == "__main__":
    scanner = MasterScanner()
    scanner.run_continuous(scan_interval_minutes=10)
