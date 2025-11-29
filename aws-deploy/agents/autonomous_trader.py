"""
AUTONOMOUS TRADER - FULL AUTO MODE
Scans + Executes trades automatically when 90%+ confidence hits
NO HUMAN NEEDED - Set it and forget it
"""

import os
import sys
import time
import json
from datetime import datetime
from web3 import Web3
from dotenv import load_dotenv

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

from multi_strategy_executor import MultiStrategyExecutor
from professional_risk_manager import ProfessionalRiskManager
from execution_engine import ExecutionEngine

# Trading config
ARBITRUM_RPC = os.getenv("ARBITRUM_RPC", "https://arb1.arbitrum.io/rpc")
WALLET_ADDRESS = os.getenv("WALLET_ADDRESS")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")

w3 = Web3(Web3.HTTPProvider(ARBITRUM_RPC))

# Uniswap V3 Router
UNISWAP_V3_ROUTER = "0xE592427A0AEce92De3Edee1F18E0157C05861564"
USDC = "0xaf88d065e77c8cC2239327C5EDb3A432268e5831"
WETH = "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1"

# Token addresses
TOKENS = {
    'ARB': '0x912CE59144191C1204E64559FE8253a0e49E6548',
    'OP': '0x4200000000000000000000000000000000000042',
    'LINK': '0xf97f4df75117a78c1A5a0DBb814Af92458539FB4',
    'UNI': '0xFa7F8980b0f1E64A2062791cc3b0871572f1F7f0'
}

class AutonomousTrader:
    def __init__(self):
        self.executor = MultiStrategyExecutor()
        self.risk_manager = ProfessionalRiskManager()
        self.execution_engine = ExecutionEngine()
        self.scan_count = 0
        self.trades_executed = 0
        self.total_profit = 0
        
        # Trade log
        self.log_file = os.path.join(os.path.dirname(__file__), '..', 'logs', 'autonomous_trades.log')
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        
    def log(self, message):
        """Log to file and console"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_line = f"[{timestamp}] {message}"
        print(log_line)
        
        with open(self.log_file, 'a') as f:
            f.write(log_line + '\n')
    
    def get_token_address(self, symbol):
        """Get token address from symbol"""
        if symbol in TOKENS:
            return TOKENS[symbol]
        return None
    
    def execute_swap(self, token_in, token_out, amount_in, min_amount_out):
        """Execute swap on Uniswap V3"""
        try:
            self.log(f"🔄 Executing swap: {amount_in} {token_in} → {token_out}")
            
            router = w3.eth.contract(
                address=UNISWAP_V3_ROUTER,
                abi=[{
                    "inputs": [{
                        "components": [
                            {"internalType": "address", "name": "tokenIn", "type": "address"},
                            {"internalType": "address", "name": "tokenOut", "type": "address"},
                            {"internalType": "uint24", "name": "fee", "type": "uint24"},
                            {"internalType": "address", "name": "recipient", "type": "address"},
                            {"internalType": "uint256", "name": "deadline", "type": "uint256"},
                            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                            {"internalType": "uint256", "name": "amountOutMinimum", "type": "uint256"},
                            {"internalType": "uint160", "name": "sqrtPriceLimitX96", "type": "uint160"}
                        ],
                        "internalType": "struct ISwapRouter.ExactInputSingleParams",
                        "name": "params",
                        "type": "tuple"
                    }],
                    "name": "exactInputSingle",
                    "outputs": [{"internalType": "uint256", "name": "amountOut", "type": "uint256"}],
                    "stateMutability": "payable",
                    "type": "function"
                }]
            )
            
            deadline = int(time.time()) + 300  # 5 minutes
            
            params = {
                'tokenIn': token_in,
                'tokenOut': token_out,
                'fee': 3000,  # 0.3% fee tier
                'recipient': WALLET_ADDRESS,
                'deadline': deadline,
                'amountIn': amount_in,
                'amountOutMinimum': min_amount_out,
                'sqrtPriceLimitX96': 0
            }
            
            # Build transaction
            gas_price = w3.eth.gas_price
            
            txn = router.functions.exactInputSingle(params).build_transaction({
                'from': WALLET_ADDRESS,
                'gas': 300000,
                'gasPrice': int(gas_price * 1.2),  # 20% higher for speed
                'nonce': w3.eth.get_transaction_count(WALLET_ADDRESS),
                'value': 0
            })
            
            # Sign and send
            signed_txn = w3.eth.account.sign_transaction(txn, PRIVATE_KEY)
            tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            self.log(f"✅ Transaction sent: {tx_hash.hex()}")
            
            # Wait for confirmation
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if receipt['status'] == 1:
                self.log(f"✅ SWAP SUCCESS! Gas used: {receipt['gasUsed']}")
                return True
            else:
                self.log(f"❌ SWAP FAILED - Transaction reverted")
                return False
                
        except Exception as e:
            self.log(f"❌ Error executing swap: {e}")
            return False
    
    def execute_opportunity(self, opportunity):
        """Execute a trading opportunity using PRO risk management"""
        self.log("\n" + "="*100)
        self.log(f"🎯 OPPORTUNITY DETECTED #{self.trades_executed + 1}")
        self.log("="*100)
        self.log(f"Pair: {opportunity['pair']}")
        self.log(f"Direction: {opportunity.get('direction', 'LONG')}")
        self.log(f"Confidence: {opportunity['confidence']}%")
        self.log(f"Signals: {opportunity['signal_count']} aligned")
        
        # PRO RISK CHECK
        confidence = opportunity['confidence']
        allowed, reason, position_size_usd, position_size_pct = self.risk_manager.check_trade_allowed(confidence)
        
        if not allowed:
            self.log(f"\n❌ TRADE BLOCKED BY RISK MANAGER")
            self.log(f"   Reason: {reason}")
            return False
        
        self.log(f"\n✅ RISK MANAGER APPROVED")
        self.log(f"   Position Size: ${position_size_usd:.2f} ({position_size_pct*100:.1f}%)")
        
        # Parse pair (e.g., "ARB/USDC")
        base_symbol = opportunity['pair'].split('/')[0]
        direction = opportunity.get('direction', 'LONG')
        
        # Get token address
        token_address = self.get_token_address(base_symbol)
        if not token_address:
            self.log(f"❌ Unknown token: {base_symbol}")
            return False
        
        # Execute via PRO execution engine
        self.log(f"\n🚀 EXECUTING VIA PRO ENGINE...")
        
        result = self.execution_engine.execute_swap(
            base_symbol,
            direction,
            position_size_usd,
            confidence
        )
        
        if result['success']:
            self.trades_executed += 1
            
            # Record trade with risk manager
            entry_price = result.get('entry_price', 0)  # Get from result
            self.risk_manager.record_trade_open(
                base_symbol,
                direction,
                entry_price,
                position_size_usd,
                confidence
            )
            
            self.log(f"\n✅ TRADE EXECUTED SUCCESSFULLY!")
            self.log(f"   TX: {result['tx_hash']}")
            self.log(f"   Link: https://arbiscan.io/tx/{result['tx_hash']}")
            
            # Save to opportunities log
            opportunity['executed'] = True
            opportunity['tx_hash'] = result['tx_hash']
            opportunity['timestamp'] = datetime.now().isoformat()
            
            with open('data/executed_trades.json', 'a') as f:
                json.dump(opportunity, f)
                f.write('\n')
            
            return True
        else:
            self.log(f"\n❌ EXECUTION FAILED: {result.get('reason', 'Unknown')}")
            return False
            self.log(f"✅ TRADE #{self.trades_executed} EXECUTED!")
            self.log(f"📊 Next: Wait for profit target or stop loss")
            
            # TODO: Monitor position and exit at target
            
        return success
    
    def run_autonomous(self):
        """Run autonomous trading loop"""
        self.log("\n" + "="*100)
        self.log("🤖 AUTONOMOUS TRADER - FULL AUTO MODE")
        self.log("="*100)
        self.log(f"Wallet: {WALLET_ADDRESS}")
        self.log(f"Strategy: 90%+ confidence trades only")
        self.log(f"Auto-execute: YES")
        self.log(f"Scan interval: 10 minutes")
        self.log("="*100)
        self.log("\n💤 You can sleep - I'll handle everything!\n")
        
        try:
            while True:
                self.scan_count += 1
                self.log(f"\n🔍 Scan #{self.scan_count} - {datetime.now().strftime('%H:%M:%S')}")
                
                # Run multi-strategy scan
                opportunities = self.executor.run_full_scan()
                
                if opportunities:
                    self.log(f"\n🚨 {len(opportunities)} OPPORTUNITIES FOUND!")
                    
                    # Execute each opportunity
                    for opp in opportunities:
                        self.execute_opportunity(opp)
                        
                    # Alert user
                    self.log("\n" + "🔔"*30)
                    self.log("🔔 TRADE EXECUTED - CHECK WALLET!")
                    self.log("🔔"*30)
                    
                else:
                    self.log("⏳ No 90%+ setups - continuing patrol...")
                
                # Stats
                self.log(f"\n📊 Session Stats:")
                self.log(f"   Scans: {self.scan_count}")
                self.log(f"   Trades: {self.trades_executed}")
                self.log(f"   Log: {self.log_file}")
                
                # Wait 10 minutes
                next_scan = datetime.now().replace(second=0, microsecond=0)
                next_scan = next_scan.replace(minute=(next_scan.minute + 10) % 60)
                self.log(f"\n⏰ Next scan: {next_scan.strftime('%H:%M')}")
                
                time.sleep(600)
                
        except KeyboardInterrupt:
            self.log("\n\n🛑 AUTONOMOUS TRADER STOPPED")
            self.log(f"Total Scans: {self.scan_count}")
            self.log(f"Total Trades: {self.trades_executed}")
        except Exception as e:
            self.log(f"\n❌ CRITICAL ERROR: {e}")
            import traceback
            self.log(traceback.format_exc())

if __name__ == "__main__":
    trader = AutonomousTrader()
    trader.run_autonomous()
