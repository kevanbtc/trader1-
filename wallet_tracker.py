#!/usr/bin/env python3
"""
💰 WALLET BALANCE TRACKER - Prove It's Real Money
Shows ACTUAL on-chain wallet balances in real-time
Compares with trading session P&L to verify execution
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime
from web3 import Web3

# ANSI Colors
class C:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'

class WalletTracker:
    def __init__(self):
        # Load environment
        self.load_env()
        
        # Web3 connection
        from agents.rpc_config import RPCConfig
        self.rpc_url = RPCConfig.get_rpc('ARBITRUM')
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        
        # Wallet address
        self.wallet = self.env.get('WALLET_ADDRESS', '0x5fc05DA8cB29f08754ac120Ab6F4F6176774b53E')
        
        # Token contracts
        self.tokens = {
            'USDC': {
                'address': '0xaf88d065e77c8cC2239327C5EDb3A432268e5831',
                'decimals': 6,
                'price': 1.0
            },
            'USDT': {
                'address': '0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9',
                'decimals': 6,
                'price': 1.0
            },
            'WETH': {
                'address': '0x82aF49447D8a07e3bd95BD0d56f35241523fBab1',
                'decimals': 18,
                'price': 3500.0  # Approximate
            },
            'ARB': {
                'address': '0x912CE59144191C1204E64559FE8253a0e49E6548',
                'decimals': 18,
                'price': 0.80  # Approximate
            }
        }
        
        # Tracking
        self.start_balances = {}
        self.start_time = datetime.now()
        
    def load_env(self):
        """Load .env file"""
        self.env = {}
        env_file = Path(__file__).parent / '.env'
        if env_file.exists():
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        self.env[key.strip()] = value.strip()
    
    def get_eth_balance(self):
        """Get ETH balance for gas"""
        try:
            time.sleep(0.3)  # Rate limit: 300ms between calls
            balance_wei = self.w3.eth.get_balance(Web3.to_checksum_address(self.wallet))
            return balance_wei / 1e18
        except Exception as e:
            if '429' in str(e):
                print(f"{C.YELLOW}⏳ Rate limited - waiting...{C.RESET}")
                time.sleep(2)
                return self.start_balances.get('ETH', 0.0)
            print(f"{C.RED}Error reading ETH: {e}{C.RESET}")
            return 0.0
    
    def get_token_balance(self, token_symbol):
        """Get token balance from blockchain"""
        try:
            time.sleep(0.3)  # Rate limit: 300ms between calls
            token_info = self.tokens[token_symbol]
            
            # ERC20 ABI for balanceOf
            abi = [{
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "balance", "type": "uint256"}],
                "type": "function"
            }]
            
            contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(token_info['address']),
                abi=abi
            )
            
            balance_wei = contract.functions.balanceOf(
                Web3.to_checksum_address(self.wallet)
            ).call()
            
            # Convert from wei to human-readable
            return balance_wei / (10 ** token_info['decimals'])
            
        except Exception as e:
            if '429' in str(e):
                print(f"{C.YELLOW}⏳ Rate limited on {token_symbol} - using cached...{C.RESET}")
                time.sleep(2)
                return self.start_balances.get(token_symbol, 0.0)
            print(f"{C.RED}Error reading {token_symbol}: {e}{C.RESET}")
            return 0.0
    
    def get_latest_session(self):
        """Get most recent trading session"""
        try:
            logs_dir = Path('logs')
            if not logs_dir.exists():
                return None
            
            session_files = sorted(
                logs_dir.glob('session_*.json'),
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )
            
            if not session_files:
                return None
            
            with open(session_files[0], 'r') as f:
                return json.load(f)
        except Exception:
            return None
    
    def capture_starting_balances(self):
        """Capture wallet state at monitor start"""
        print(f"{C.YELLOW}📸 Capturing starting wallet state...{C.RESET}")
        
        self.start_balances['ETH'] = self.get_eth_balance()
        for token in self.tokens.keys():
            self.start_balances[token] = self.get_token_balance(token)
        
        print(f"{C.GREEN}✅ Starting balances captured!{C.RESET}")
        time.sleep(1)
    
    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def print_header(self):
        """Print header with connection info"""
        runtime = (datetime.now() - self.start_time).total_seconds()
        runtime_str = f"{int(runtime // 60):02d}:{int(runtime % 60):02d}"
        
        try:
            block = self.w3.eth.block_number
            gas = self.w3.eth.gas_price / 1e9
        except:
            block = 0
            gas = 0.0
        
        print(f"{C.BOLD}{'='*80}{C.RESET}")
        print(f"{C.BOLD}{C.RED}        💰 WALLET TRACKER - REAL ON-CHAIN BALANCES 💰{C.RESET}".center(90))
        print(f"{C.BOLD}{'='*80}{C.RESET}\n")
        print(f"{C.CYAN}Wallet: {self.wallet}{C.RESET}")
        print(f"{C.CYAN}Runtime: {runtime_str} | Block: {block:,} | Gas: {gas:.4f} Gwei{C.RESET}\n")
    
    def print_balances(self):
        """Print current wallet balances with changes"""
        print(f"{C.BOLD}📊 CURRENT WALLET STATE (Real Blockchain Data){C.RESET}")
        print("─" * 80)
        
        total_value_usd = 0.0
        total_change_usd = 0.0
        
        # ETH
        eth_now = self.get_eth_balance()
        eth_start = self.start_balances.get('ETH', eth_now)
        eth_change = eth_now - eth_start
        eth_value = eth_now * 3500
        eth_change_usd = eth_change * 3500
        
        color = C.GREEN if eth_change > 0 else C.RED if eth_change < 0 else C.RESET
        sign = '+' if eth_change >= 0 else ''
        
        print(f"  {C.YELLOW}ETH (Gas):{C.RESET}")
        print(f"    Current: {eth_now:.6f} ETH (${eth_value:.2f})")
        print(f"    Change:  {color}{sign}{eth_change:.6f} ETH ({sign}${eth_change_usd:.2f}){C.RESET}")
        print()
        
        total_value_usd += eth_value
        total_change_usd += eth_change_usd
        
        # Tokens
        for token, info in self.tokens.items():
            bal_now = self.get_token_balance(token)
            bal_start = self.start_balances.get(token, bal_now)
            change = bal_now - bal_start
            
            value_usd = bal_now * info['price']
            change_usd = change * info['price']
            
            # Only show if we have balance or there's been a change
            if bal_now > 0.001 or abs(change) > 0.001:
                color = C.GREEN if change > 0 else C.RED if change < 0 else C.RESET
                sign = '+' if change >= 0 else ''
                
                print(f"  {C.CYAN}{token}:{C.RESET}")
                print(f"    Current: {bal_now:.6f} {token} (${value_usd:.2f})")
                print(f"    Change:  {color}{sign}{change:.6f} {token} ({sign}${change_usd:.2f}){C.RESET}")
                print()
                
                total_value_usd += value_usd
                total_change_usd += change_usd
        
        print("─" * 80)
        print(f"{C.BOLD}  Total Wallet Value: ${total_value_usd:.2f}{C.RESET}")
        
        pnl_color = C.GREEN if total_change_usd > 0 else C.RED if total_change_usd < 0 else C.YELLOW
        sign = '+' if total_change_usd >= 0 else ''
        print(f"{C.BOLD}  Net Change (P&L):  {pnl_color}{sign}${total_change_usd:.4f}{C.RESET}")
        print("─" * 80)
        
        return total_change_usd
    
    def print_session_comparison(self, wallet_pnl):
        """Compare wallet changes with session P&L"""
        print(f"\n{C.BOLD}🔍 VERIFICATION - Session vs Wallet{C.RESET}")
        print("─" * 80)
        
        session = self.get_latest_session()
        
        if not session:
            print(f"  {C.YELLOW}No trading session found{C.RESET}")
            return
        
        mode = session.get('mode', 'UNKNOWN')
        session_pnl = session.get('risk', {}).get('session_pnl_usd', 0.0)
        trades = session.get('trades_executed', 0)
        opps = session.get('opportunities_detected', 0)
        
        mode_color = C.GREEN if mode == 'LIVE' else C.YELLOW
        
        print(f"  Trading Mode:        {mode_color}{mode}{C.RESET}")
        print(f"  Opportunities:       {opps}")
        print(f"  Trades Executed:     {trades}")
        print(f"  Session Reported P&L: ${session_pnl:.4f}")
        print(f"  Wallet Actual Change: ${wallet_pnl:.4f}")
        
        # Verify match
        diff = abs(wallet_pnl - session_pnl)
        
        if trades == 0:
            print(f"\n  {C.YELLOW}⏳ No trades yet - wallet should be unchanged{C.RESET}")
            if abs(wallet_pnl) < 0.01:
                print(f"  {C.GREEN}✓ Verified: Wallet unchanged{C.RESET}")
            else:
                print(f"  {C.RED}⚠ Warning: Wallet changed but no trades logged{C.RESET}")
        else:
            print(f"\n  Difference: ${diff:.4f}")
            
            if diff < 0.10:  # Within 10 cents
                print(f"  {C.GREEN}✓ Verified: Session P&L matches wallet changes{C.RESET}")
            else:
                print(f"  {C.RED}⚠ Warning: Large discrepancy detected!{C.RESET}")
        
        # Show recent trades
        if trades > 0:
            trade_log = session.get('trade_log', [])
            if trade_log:
                print(f"\n  {C.BOLD}Recent Trades:{C.RESET}")
                for trade in trade_log[-3:]:  # Last 3
                    success = '✓' if trade.get('success') else '✗'
                    pair = trade.get('pair', 'N/A')
                    pnl = trade.get('net_profit_usd', 0.0)
                    gas = trade.get('gas_cost_usd', 0.0)
                    
                    pnl_color = C.GREEN if pnl > 0 else C.RED
                    print(f"    {success} {pair:15} | {pnl_color}${pnl:.4f}{C.RESET} | Gas: ${gas:.4f}")
        
        print("─" * 80)
    
    def run(self):
        """Main monitoring loop"""
        # Capture starting state
        self.capture_starting_balances()
        
        print(f"\n{C.GREEN}🚀 Starting real-time monitoring...{C.RESET}\n")
        time.sleep(2)
        
        while True:
            try:
                self.clear_screen()
                
                # Display
                self.print_header()
                wallet_pnl = self.print_balances()
                self.print_session_comparison(wallet_pnl)
                
                print(f"\n{C.CYAN}Updates every 15 seconds (reduced to avoid rate limits) | Press Ctrl+C to stop{C.RESET}")
                print("─" * 80)
                
                # Wait
                time.sleep(15)
                
            except KeyboardInterrupt:
                print(f"\n\n{C.GREEN}✅ Wallet tracker stopped{C.RESET}")
                break
            except Exception as e:
                print(f"\n{C.RED}Error: {e}{C.RESET}")
                time.sleep(15)

def main():
    # Enable ANSI colors on Windows
    if os.name == 'nt':
        os.system('color')
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    
    tracker = WalletTracker()
    tracker.run()

if __name__ == '__main__':
    main()
