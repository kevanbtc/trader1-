"""
WHALE SHADOW TRADER
Copy the exact moves of profitable whale wallets IN REAL-TIME
"""

import requests
import time
from datetime import datetime
from web3 import Web3
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.append('.')
from professional_risk_manager import ProfessionalRiskManager
from execution_engine import ExecutionEngine

# Top performing whale wallets on Arbitrum
WHALE_WALLETS = [
    {
        'address': '0x8315177aB297bA92A06054ce345C665a3Aa55545',
        'name': 'Arbitrum Whale 1',
        'win_rate': 75,
        'roi': '15x',
        'specialty': 'ARB accumulation'
    },
    {
        'address': '0x489ee077994f7dccd8dde57a00e8b0e53e0d7e8c',
        'name': 'GMX Trader',
        'win_rate': 80,
        'roi': '22x',
        'specialty': 'Leverage plays'
    },
    {
        'address': '0x47c031236e19d024b42f8AE6780E44A573170703',
        'name': 'DeFi Alpha',
        'win_rate': 70,
        'roi': '12x',
        'specialty': 'Early positions'
    }
]

# Arbitrum RPC
w3 = Web3(Web3.HTTPProvider('https://arb1.arbitrum.io/rpc'))

# Major token contracts
TOKENS = {
    '0x912CE59144191C1204E64559FE8253a0e49E6548': 'ARB',
    '0xaf88d065e77c8cC2239327C5EDb3A432268e5831': 'USDC',
    '0x82aF49447D8a07e3bd95BD0d56f35241523fBab1': 'WETH',
    '0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9': 'USDT',
    '0xf97f4df75117a78c1A5a0DBb814Af92458539FB4': 'LINK',
}

class WhaleShadowTrader:
    """Follow whale trades in real-time"""
    
    def __init__(self):
        self.risk_manager = ProfessionalRiskManager()
        self.execution_engine = ExecutionEngine()
        self.last_blocks = {}
        self.trades_copied = 0
    
    def get_latest_block(self):
        """Get latest block number"""
        return w3.eth.block_number
    
    def analyze_transaction(self, tx_hash):
        """Analyze a transaction to detect trades"""
        try:
            tx = w3.eth.get_transaction(tx_hash)
            receipt = w3.eth.get_transaction_receipt(tx_hash)
            
            if receipt['status'] != 1:
                return None  # Failed transaction
            
            # Check if it's a swap (look for Transfer events)
            if len(receipt['logs']) < 2:
                return None
            
            # Parse token transfers from logs
            transfers = []
            for log in receipt['logs']:
                if len(log['topics']) >= 3:  # Transfer event
                    token = log['address']
                    amount = int(log['data'], 16) if log['data'] != '0x' else 0
                    
                    if token in TOKENS and amount > 0:
                        transfers.append({
                            'token': TOKENS[token],
                            'address': token,
                            'amount': amount
                        })
            
            if len(transfers) >= 2:
                # Likely a swap
                token_in = transfers[0]
                token_out = transfers[1]
                
                return {
                    'type': 'SWAP',
                    'from_token': token_in['token'],
                    'to_token': token_out['token'],
                    'amount_in': token_in['amount'],
                    'amount_out': token_out['amount'],
                    'tx_hash': tx_hash.hex(),
                    'gas_used': receipt['gasUsed']
                }
            
            return None
        
        except Exception as e:
            return None
    
    def monitor_whale(self, whale):
        """Monitor a whale wallet for new transactions"""
        address = whale['address']
        
        # Get current block
        current_block = self.get_latest_block()
        
        # Initialize last block if first time
        if address not in self.last_blocks:
            self.last_blocks[address] = current_block
            return None
        
        last_block = self.last_blocks[address]
        
        if current_block == last_block:
            return None  # No new blocks
        
        # Check transactions in new blocks
        for block_num in range(last_block + 1, current_block + 1):
            try:
                block = w3.eth.get_block(block_num, full_transactions=True)
                
                for tx in block['transactions']:
                    if tx['from'].lower() == address.lower():
                        # Whale made a transaction!
                        trade = self.analyze_transaction(tx['hash'])
                        
                        if trade:
                            self.last_blocks[address] = current_block
                            return {
                                'whale': whale,
                                'trade': trade,
                                'block': block_num
                            }
            
            except Exception as e:
                continue
        
        self.last_blocks[address] = current_block
        return None
    
    def copy_whale_trade(self, whale_activity):
        """Copy a whale's trade immediately"""
        whale = whale_activity['whale']
        trade = whale_activity['trade']
        
        print(f"\n{'🐋'*40}")
        print(f"🐋 WHALE ACTIVITY DETECTED!")
        print(f"{'🐋'*40}")
        print(f"Whale: {whale['name']}")
        print(f"Win Rate: {whale['win_rate']}% | ROI: {whale['roi']}")
        print(f"Specialty: {whale['specialty']}")
        print(f"\nTrade:")
        print(f"  {trade['from_token']} → {trade['to_token']}")
        print(f"  TX: {trade['tx_hash']}")
        print(f"  Block: {whale_activity['block']}")
        print("\a" * 5)  # Alert
        
        # Determine direction
        if trade['from_token'] == 'USDC':
            direction = 'LONG'
            token = trade['to_token']
        elif trade['to_token'] == 'USDC':
            direction = 'SHORT'
            token = trade['from_token']
        else:
            print(f"⚠️  Not a USDC pair, skipping")
            return False
        
        # Calculate confidence based on whale's win rate
        confidence = whale['win_rate']  # Use whale's historical win rate
        
        print(f"\n🎯 COPYING TRADE:")
        print(f"  Token: {token}")
        print(f"  Direction: {direction}")
        print(f"  Confidence: {confidence}% (whale's win rate)")
        
        # Risk check
        allowed, reason, size_usd, size_pct = self.risk_manager.check_trade_allowed(confidence)
        
        if not allowed:
            print(f"\n❌ BLOCKED: {reason}")
            return False
        
        print(f"\n✅ Executing ${size_usd:.2f} ({size_pct*100:.1f}%)")
        
        # Execute
        result = self.execution_engine.execute_swap(
            token,
            direction,
            size_usd,
            confidence
        )
        
        if result['success']:
            self.trades_copied += 1
            print(f"\n✅ WHALE TRADE COPIED!")
            print(f"Our TX: {result['tx_hash']}")
            print(f"Trades copied: {self.trades_copied}")
            return True
        else:
            print(f"\n❌ COPY FAILED: {result.get('reason')}")
            return False
    
    def shadow_whales(self):
        """Main monitoring loop"""
        print("\n" + "="*80)
        print("🐋 WHALE SHADOW TRADER")
        print("="*80)
        print(f"Monitoring {len(WHALE_WALLETS)} profitable whale wallets")
        print("\nWhales:")
        for whale in WHALE_WALLETS:
            print(f"  • {whale['name']}: {whale['win_rate']}% win rate, {whale['roi']} ROI")
        print("\nWaiting for whale activity...")
        print("="*80 + "\n")
        
        check_count = 0
        
        while True:
            check_count += 1
            
            if check_count % 10 == 0:  # Status every 10 checks
                print(f"⏰ {datetime.now().strftime('%H:%M:%S')} - Monitoring... (Check #{check_count})")
            
            for whale in WHALE_WALLETS:
                try:
                    activity = self.monitor_whale(whale)
                    
                    if activity:
                        self.copy_whale_trade(activity)
                
                except Exception as e:
                    print(f"⚠️  Error monitoring {whale['name']}: {e}")
            
            time.sleep(12)  # Check every 12 seconds (new block on Arbitrum ~0.25s, batch checks)

if __name__ == "__main__":
    trader = WhaleShadowTrader()
    
    print("\n🐋 WHALE SHADOW TRADER")
    print("📊 Strategy: Copy profitable whale trades in real-time")
    print("🎯 Target: Follow 75-80% win rate whales")
    print("⚡ Speed: Monitor every 12 seconds for new blocks")
    print("\nPress Ctrl+C to stop\n")
    
    try:
        trader.shadow_whales()
    except KeyboardInterrupt:
        print(f"\n\n🛑 Whale shadow trader stopped")
        print(f"Trades copied: {trader.trades_copied}")
