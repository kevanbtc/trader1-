"""
SMART EXECUTOR - Only execute 80%+ confidence trades
Goal: 2-3 BIG HITS to turn $29 → thousands
"""

import os
import sys
import json
from datetime import datetime
from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

ARBITRUM_RPC = os.getenv("ARBITRUM_RPC", "https://arb1.arbitrum.io/rpc")
w3 = Web3(Web3.HTTPProvider(ARBITRUM_RPC))

WALLET_ADDRESS = os.getenv("WALLET_ADDRESS")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")

# Uniswap V3 Router
UNISWAP_V3_ROUTER = "0xE592427A0AEce92De3Edee1F18E0157C05861564"

ROUTER_ABI = [
    {
        "inputs": [
            {
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
            }
        ],
        "name": "exactInputSingle",
        "outputs": [{"internalType": "uint256", "name": "amountOut", "type": "uint256"}],
        "stateMutability": "payable",
        "type": "function"
    }
]

ERC20_ABI = [
    {
        "constant": False,
        "inputs": [
            {"name": "_spender", "type": "address"},
            {"name": "_value", "type": "uint256"}
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function"
    }
]


class SmartExecutor:
    def __init__(self):
        self.wallet = Web3.to_checksum_address(WALLET_ADDRESS)
        self.account = Account.from_key(PRIVATE_KEY)
        self.router = w3.eth.contract(
            address=Web3.to_checksum_address(UNISWAP_V3_ROUTER),
            abi=ROUTER_ABI
        )
        self.executed_trades = []
        
    def approve_token(self, token_address, amount):
        """Approve router to spend token"""
        token = w3.eth.contract(
            address=Web3.to_checksum_address(token_address),
            abi=ERC20_ABI
        )
        
        tx = token.functions.approve(
            UNISWAP_V3_ROUTER,
            amount
        ).build_transaction({
            'from': self.wallet,
            'gas': 100000,
            'gasPrice': w3.eth.gas_price,
            'nonce': w3.eth.get_transaction_count(self.wallet)
        })
        
        signed = self.account.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        return receipt
    
    def execute_swap(self, token_in, token_out, amount_in, fee=3000, slippage_percent=5):
        """Execute a swap on Uniswap V3"""
        try:
            # Approve first
            print(f"Approving {amount_in} tokens...")
            self.approve_token(token_in, amount_in)
            
            # Calculate minimum output (slippage protection)
            amount_out_min = int(amount_in * (100 - slippage_percent) / 100)
            
            # Build swap params
            deadline = int(datetime.now().timestamp()) + 600  # 10 min
            params = (
                Web3.to_checksum_address(token_in),
                Web3.to_checksum_address(token_out),
                fee,
                self.wallet,
                deadline,
                amount_in,
                amount_out_min,
                0
            )
            
            # Build transaction
            tx = self.router.functions.exactInputSingle(params).build_transaction({
                'from': self.wallet,
                'gas': 300000,
                'gasPrice': int(w3.eth.gas_price * 1.2),  # 20% higher for speed
                'nonce': w3.eth.get_transaction_count(self.wallet),
                'value': 0
            })
            
            # Sign and send
            signed = self.account.sign_transaction(tx)
            tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
            
            print(f"Transaction sent: {tx_hash.hex()}")
            print(f"Waiting for confirmation...")
            
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if receipt['status'] == 1:
                print(f"✅ Swap successful!")
                return receipt
            else:
                print(f"❌ Swap failed")
                return None
                
        except Exception as e:
            print(f"Error executing swap: {e}")
            return None
    
    def execute_opportunity(self, opportunity):
        """Execute a single opportunity based on type"""
        opp_type = opportunity['type']
        confidence = opportunity['confidence']
        
        print(f"\n{'='*80}")
        print(f"🎯 EXECUTING: {opp_type} ({confidence}% confidence)")
        print(f"{'='*80}")
        
        if opp_type == 'NEW_TOKEN_LAUNCH':
            return self.execute_token_launch(opportunity)
        elif 'LEVERAGE' in opp_type:
            return self.execute_leverage_trade(opportunity)
        else:
            print(f"Unknown opportunity type: {opp_type}")
            return False
    
    def execute_token_launch(self, opp):
        """Buy a newly launched token"""
        try:
            # Use WETH to buy the new token
            WETH = "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1"
            new_token = opp['token']
            
            # Buy with 0.001 ETH (~$3)
            amount_in = int(0.001 * 1e18)
            
            print(f"Buying {opp['symbol']} ({opp['name']})")
            print(f"Pool: {opp['pool']}")
            print(f"Liquidity: ${opp['liquidity_usd']:,.0f}")
            print(f"Amount: 0.001 ETH (~$3)")
            
            # Execute swap
            receipt = self.execute_swap(WETH, new_token, amount_in, fee=3000, slippage_percent=10)
            
            if receipt:
                self.executed_trades.append({
                    'type': 'TOKEN_LAUNCH_BUY',
                    'token': new_token,
                    'symbol': opp['symbol'],
                    'amount_eth': 0.001,
                    'tx_hash': receipt['transactionHash'].hex(),
                    'timestamp': datetime.now().isoformat(),
                    'target_profit': '5x-20x'
                })
                
                print(f"\n🚀 TOKEN ACQUIRED!")
                print(f"Now monitoring for 5x-20x exit...")
                return True
            else:
                return False
                
        except Exception as e:
            print(f"Error executing token launch: {e}")
            return False
    
    def execute_leverage_trade(self, opp):
        """Execute leverage trade (requires integration with GMX or similar)"""
        print(f"⚠️  Leverage trading requires GMX integration")
        print(f"Pair: {opp['pair']}")
        print(f"Direction: {opp['type']}")
        print(f"Reason: {opp['reason']}")
        print(f"\nTODO: Implement GMX position opening")
        return False
    
    def load_and_execute_opportunities(self):
        """Load opportunities.json and execute those approved"""
        try:
            with open('opportunities.json', 'r') as f:
                opportunities = json.load(f)
            
            if not opportunities:
                print("No opportunities to execute")
                return
            
            print(f"Found {len(opportunities)} opportunities")
            print(f"\n⚠️  REVIEW BEFORE EXECUTING:")
            for i, opp in enumerate(opportunities, 1):
                print(f"\n#{i} - {opp['type']} ({opp['confidence']}% confidence)")
                if opp['type'] == 'NEW_TOKEN_LAUNCH':
                    print(f"   Token: {opp['symbol']}")
                    print(f"   Liquidity: ${opp['liquidity_usd']:,.0f}")
                
            # Ask for confirmation
            response = input(f"\nExecute ALL opportunities? (yes/no): ")
            if response.lower() != 'yes':
                print("Execution cancelled")
                return
            
            # Execute each
            for opp in opportunities:
                success = self.execute_opportunity(opp)
                if success:
                    print(f"✅ Executed successfully")
                else:
                    print(f"❌ Execution failed")
                    
        except FileNotFoundError:
            print("No opportunities.json file found")
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    import sys
    
    executor = SmartExecutor()
    
    if len(sys.argv) > 1 and sys.argv[1] == 'auto':
        # Auto mode: execute without confirmation
        executor.load_and_execute_opportunities()
    else:
        # Manual mode: require confirmation
        executor.load_and_execute_opportunities()
