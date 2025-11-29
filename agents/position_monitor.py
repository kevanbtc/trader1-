"""
POSITION MONITOR - Tracks open trades and auto-exits
Monitors for profit targets (2x-5x) and stop losses (10%)
"""

import os
import sys
import time
import json
from datetime import datetime
from web3 import Web3
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

WALLET_ADDRESS = os.getenv("WALLET_ADDRESS")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")

try:
    from .rpc_utils import get_arbitrum_w3  # type: ignore
except Exception:
    from agents.rpc_utils import get_arbitrum_w3  # type: ignore
w3 = get_arbitrum_w3()

USDC = "0xaf88d065e77c8cC2239327C5EDb3A432268e5831"
WETH = "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1"

TOKENS = {
    'ARB': '0x912CE59144191C1204E64559FE8253a0e49E6548',
    'OP': '0x4200000000000000000000000000000000000042',
    'LINK': '0xf97f4df75117a78c1A5a0DBb814Af92458539FB4',
    'UNI': '0xFa7F8980b0f1E64A2062791cc3b0871572f1F7f0'
}

class PositionMonitor:
    def __init__(self):
        self.positions_file = os.path.join(os.path.dirname(__file__), '..', 'positions.json')
        self.positions = self.load_positions()
        
    def load_positions(self):
        """Load active positions from file"""
        if os.path.exists(self.positions_file):
            with open(self.positions_file, 'r') as f:
                return json.load(f)
        return []
    
    def save_positions(self):
        """Save positions to file"""
        with open(self.positions_file, 'w') as f:
            json.dump(self.positions, f, indent=2)
    
    def add_position(self, token_symbol, entry_price, amount, confidence):
        """Add new position to tracker"""
        position = {
            'id': len(self.positions) + 1,
            'token': token_symbol,
            'entry_price': entry_price,
            'amount': amount,
            'confidence': confidence,
            'entry_time': datetime.now().isoformat(),
            'status': 'OPEN',
            'profit_target_1': entry_price * 2.0,  # 2x
            'profit_target_2': entry_price * 5.0,  # 5x
            'stop_loss': entry_price * 0.90  # 10% stop
        }
        
        self.positions.append(position)
        self.save_positions()
        
        print(f"\n📊 Position #{position['id']} opened:")
        print(f"   Token: {token_symbol}")
        print(f"   Entry: ${entry_price:.4f}")
        print(f"   Target 1: ${position['profit_target_1']:.4f} (2x)")
        print(f"   Target 2: ${position['profit_target_2']:.4f} (5x)")
        print(f"   Stop: ${position['stop_loss']:.4f} (-10%)")
        
        return position
    
    def get_token_balance(self, token_address):
        """Get current token balance"""
        try:
            contract = w3.eth.contract(
                address=token_address,
                abi=[{
                    "constant": True,
                    "inputs": [{"name": "_owner", "type": "address"}],
                    "name": "balanceOf",
                    "outputs": [{"name": "balance", "type": "uint256"}],
                    "type": "function"
                }, {
                    "constant": True,
                    "inputs": [],
                    "name": "decimals",
                    "outputs": [{"name": "", "type": "uint8"}],
                    "type": "function"
                }]
            )
            
            balance = contract.functions.balanceOf(WALLET_ADDRESS).call()
            decimals = contract.functions.decimals().call()
            
            return balance / (10 ** decimals)
            
        except Exception as e:
            print(f"Error getting balance: {e}")
            return 0
    
    def get_current_price(self, token_symbol):
        """Get current token price from CryptoCompare"""
        try:
            import requests
            url = f"https://min-api.cryptocompare.com/data/price"
            params = {
                'fsym': token_symbol,
                'tsyms': 'USD'
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get('USD', 0)
            
        except Exception as e:
            print(f"Error getting price: {e}")
        
        return 0
    
    def check_position(self, position):
        """Check if position should be closed"""
        current_price = self.get_current_price(position['token'])
        
        if current_price == 0:
            return None
        
        entry_price = position['entry_price']
        profit_pct = ((current_price - entry_price) / entry_price) * 100
        
        print(f"\n📊 Position #{position['id']} - {position['token']}")
        print(f"   Entry: ${entry_price:.4f}")
        print(f"   Current: ${current_price:.4f}")
        print(f"   P&L: {profit_pct:+.2f}%")
        
        # Check stop loss
        if current_price <= position['stop_loss']:
            print(f"   🛑 STOP LOSS HIT! Exiting at ${current_price:.4f}")
            return 'STOP_LOSS'
        
        # Check profit target 2 (5x)
        if current_price >= position['profit_target_2']:
            print(f"   🎯 TARGET 2 HIT! (5x) Exiting at ${current_price:.4f}")
            return 'TARGET_2'
        
        # Check profit target 1 (2x)
        if current_price >= position['profit_target_1']:
            print(f"   🎯 TARGET 1 HIT! (2x) Taking 50% profit at ${current_price:.4f}")
            return 'TARGET_1'
        
        # Still in range
        target_1_distance = ((position['profit_target_1'] - current_price) / current_price) * 100
        print(f"   ⏳ Target 1 in {target_1_distance:.1f}%")
        
        return None
    
    def monitor_positions(self):
        """Monitor all open positions"""
        print("\n" + "="*100)
        print("📊 POSITION MONITOR")
        print("="*100)
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Active Positions: {len([p for p in self.positions if p['status'] == 'OPEN'])}")
        
        for position in self.positions:
            if position['status'] != 'OPEN':
                continue
            
            action = self.check_position(position)
            
            if action:
                # Close position
                position['status'] = 'CLOSED'
                position['close_time'] = datetime.now().isoformat()
                position['close_reason'] = action
                position['close_price'] = self.get_current_price(position['token'])
                
                profit_pct = ((position['close_price'] - position['entry_price']) / position['entry_price']) * 100
                position['profit_pct'] = profit_pct
                
                self.save_positions()
                
                print(f"\n✅ Position #{position['id']} CLOSED")
                print(f"   Reason: {action}")
                print(f"   Entry: ${position['entry_price']:.4f}")
                print(f"   Exit: ${position['close_price']:.4f}")
                print(f"   Profit: {profit_pct:+.2f}%")
        
        print("\n" + "="*100)
    
    def run_continuous(self):
        """Monitor positions continuously"""
        print("\n🔍 Position Monitor Started")
        print("Checking every 1 minute for profit targets and stop losses\n")
        
        try:
            while True:
                self.monitor_positions()
                time.sleep(60)  # Check every minute
                
        except KeyboardInterrupt:
            print("\n🛑 Position Monitor Stopped")

if __name__ == "__main__":
    monitor = PositionMonitor()
    monitor.run_continuous()
