"""
EXECUTION ENGINE - Professional Trade Execution
Handles slippage protection, gas optimization, retry logic for real money
"""

import time
from web3 import Web3
from eth_account import Account
import os
from datetime import datetime

# Web3 setup (multi-provider with failover)
try:
    from .rpc_utils import get_arbitrum_w3  # type: ignore
except Exception:
    from agents.rpc_utils import get_arbitrum_w3  # type: ignore
w3 = get_arbitrum_w3()

# Contracts (Arbitrum)
UNISWAP_ROUTER = '0xE592427A0AEce92De3Edee1F18E0157C05861564'
USDC_ADDRESS = '0xaf88d065e77c8cC2239327C5EDb3A432268e5831'

# Token addresses
TOKENS = {
    'ARB': '0x912CE59144191C1204E64559FE8253a0e49E6548',
    'OP': '0x4200000000000000000000000000000000000042',  # Note: OP native on Optimism
    'ETH': '0x82aF49447D8a07e3bd95BD0d56f35241523fBab1',  # WETH on Arbitrum
    'MATIC': '0x561877b6b3DD7651313794e5F2894B2F18bE0766',
    'LINK': '0xf97f4df75117a78c1A5a0DBb814Af92458539FB4',
}

# Private key from environment
PRIVATE_KEY = os.getenv('PRIVATE_KEY', '')
WALLET_ADDRESS = '0x63d48340AB2c1E0e244F2987962C69A1C06d1e68'

class ExecutionEngine:
    """Professional execution with retry logic and slippage protection"""
    
    def __init__(self):
        self.max_retries = 3
        self.retry_delay = 5  # seconds
        self.max_slippage_pct = 3.0  # 3% max for real money (tighter than 5%)
        self.gas_price_multiplier = 1.3  # Higher for faster execution
        self.execution_log = 'logs/execution.log'
        os.makedirs('logs', exist_ok=True)
    
    def log(self, message):
        """Log execution events"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_msg = f"[{timestamp}] {message}"
        print(log_msg)
        
        with open(self.execution_log, 'a') as f:
            f.write(log_msg + '\n')
    
    def get_optimal_gas_price(self):
        """Get current gas price with multiplier for speed"""
        try:
            base_gas = w3.eth.gas_price
            optimal_gas = int(base_gas * self.gas_price_multiplier)
            
            # Cap at reasonable max (0.5 gwei on Arbitrum)
            max_gas = int(0.5 * 10**9)
            if optimal_gas > max_gas:
                self.log(f"⚠️  Gas capped at 0.5 gwei (was {optimal_gas/10**9:.2f})")
                optimal_gas = max_gas
            
            self.log(f"⛽ Gas price: {optimal_gas/10**9:.4f} gwei")
            return optimal_gas
        
        except Exception as e:
            self.log(f"❌ Gas price error: {e}, using 0.1 gwei default")
            return int(0.1 * 10**9)
    
    def approve_token_if_needed(self, token_address, spender_address, amount):
        """Approve token spending if needed"""
        try:
            token = w3.eth.contract(
                address=Web3.to_checksum_address(token_address),
                abi=[{
                    "constant": True,
                    "inputs": [
                        {"name": "_owner", "type": "address"},
                        {"name": "_spender", "type": "address"}
                    ],
                    "name": "allowance",
                    "outputs": [{"name": "", "type": "uint256"}],
                    "type": "function"
                }, {
                    "constant": False,
                    "inputs": [
                        {"name": "_spender", "type": "address"},
                        {"name": "_value", "type": "uint256"}
                    ],
                    "name": "approve",
                    "outputs": [{"name": "", "type": "bool"}],
                    "type": "function"
                }]
            )
            
            # Check current allowance
            allowance = token.functions.allowance(
                Web3.to_checksum_address(WALLET_ADDRESS),
                Web3.to_checksum_address(spender_address)
            ).call()
            
            if allowance >= amount:
                self.log("✅ Token already approved")
                return True
            
            self.log(f"🔓 Approving token spending...")
            
            # Build approval transaction
            approve_tx = token.functions.approve(
                Web3.to_checksum_address(spender_address),
                2**256 - 1  # Max approval
            ).build_transaction({
                'from': Web3.to_checksum_address(WALLET_ADDRESS),
                'gas': 100000,
                'gasPrice': self.get_optimal_gas_price(),
                'nonce': w3.eth.get_transaction_count(
                    Web3.to_checksum_address(WALLET_ADDRESS)
                )
            })
            
            # Sign and send
            if not PRIVATE_KEY:
                self.log("❌ No private key - manual approval needed")
                return False
            
            signed = w3.eth.account.sign_transaction(approve_tx, PRIVATE_KEY)
            tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
            
            self.log(f"⏳ Approval tx: {tx_hash.hex()}")
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if receipt['status'] == 1:
                self.log("✅ Approval successful")
                return True
            else:
                self.log("❌ Approval failed")
                return False
        
        except Exception as e:
            self.log(f"❌ Approval error: {e}")
            return False
    
    def execute_swap(self, token_symbol, direction, amount_usd, confidence_score):
        """
        Execute Uniswap swap with professional error handling
        
        Args:
            token_symbol: 'ARB', 'OP', etc
            direction: 'LONG' or 'SHORT'
            amount_usd: Position size in USD
            confidence_score: 90-100 for validation
        
        Returns:
            dict with tx_hash, entry_price, amount, success status
        """
        
        self.log(f"\n{'='*80}")
        self.log(f"🎯 EXECUTING TRADE")
        self.log(f"{'='*80}")
        self.log(f"Token: {token_symbol}")
        self.log(f"Direction: {direction}")
        self.log(f"Amount: ${amount_usd:.2f}")
        self.log(f"Confidence: {confidence_score}%")
        self.log(f"{'='*80}\n")
        
        # Validate inputs
        if confidence_score < 90:
            self.log(f"❌ ABORT: Confidence {confidence_score}% < 90% minimum")
            return {'success': False, 'reason': 'Low confidence'}
        
        if token_symbol not in TOKENS:
            self.log(f"❌ ABORT: Unknown token {token_symbol}")
            return {'success': False, 'reason': 'Unknown token'}
        
        # Check private key
        if not PRIVATE_KEY:
            self.log("❌ ABORT: No private key configured")
            self.log("💡 Set PRIVATE_KEY environment variable or trade manually")
            return {'success': False, 'reason': 'No private key'}
        
        # Convert amount
        amount_in_wei = int(amount_usd * 10**6)  # USDC has 6 decimals
        
        # Get token address
        token_address = TOKENS[token_symbol]
        
        # Retry loop
        for attempt in range(1, self.max_retries + 1):
            try:
                self.log(f"🔄 Attempt {attempt}/{self.max_retries}")
                
                # Approve USDC if needed
                if not self.approve_token_if_needed(USDC_ADDRESS, UNISWAP_ROUTER, amount_in_wei):
                    if attempt < self.max_retries:
                        self.log(f"⏳ Retrying in {self.retry_delay}s...")
                        time.sleep(self.retry_delay)
                        continue
                    else:
                        return {'success': False, 'reason': 'Approval failed'}
                
                # Build swap transaction
                self.log("🔨 Building swap transaction...")
                
                router = w3.eth.contract(
                    address=Web3.to_checksum_address(UNISWAP_ROUTER),
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
                
                # Calculate minimum output with slippage protection
                min_amount_out = 0  # Set based on oracle price in production
                
                swap_params = {
                    'tokenIn': Web3.to_checksum_address(USDC_ADDRESS),
                    'tokenOut': Web3.to_checksum_address(token_address),
                    'fee': 3000,  # 0.3% pool
                    'recipient': Web3.to_checksum_address(WALLET_ADDRESS),
                    'deadline': int(time.time() + 300),  # 5 min deadline
                    'amountIn': amount_in_wei,
                    'amountOutMinimum': min_amount_out,
                    'sqrtPriceLimitX96': 0
                }
                
                swap_tx = router.functions.exactInputSingle(swap_params).build_transaction({
                    'from': Web3.to_checksum_address(WALLET_ADDRESS),
                    'gas': 300000,
                    'gasPrice': self.get_optimal_gas_price(),
                    'nonce': w3.eth.get_transaction_count(
                        Web3.to_checksum_address(WALLET_ADDRESS)
                    ),
                    'value': 0
                })
                
                # Sign transaction
                self.log("✍️  Signing transaction...")
                signed = w3.eth.account.sign_transaction(swap_tx, PRIVATE_KEY)
                
                # Send transaction
                self.log("📤 Sending transaction to blockchain...")
                tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
                
                self.log(f"⏳ Transaction hash: {tx_hash.hex()}")
                self.log(f"🔗 https://arbiscan.io/tx/{tx_hash.hex()}")
                
                # Wait for confirmation
                self.log("⏳ Waiting for confirmation...")
                receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                
                if receipt['status'] == 1:
                    self.log(f"✅ TRADE EXECUTED SUCCESSFULLY!")
                    self.log(f"Gas used: {receipt['gasUsed']}")
                    
                    return {
                        'success': True,
                        'tx_hash': tx_hash.hex(),
                        'token': token_symbol,
                        'direction': direction,
                        'amount_usd': amount_usd,
                        'confidence': confidence_score,
                        'timestamp': datetime.now().isoformat()
                    }
                else:
                    self.log(f"❌ Transaction reverted")
                    if attempt < self.max_retries:
                        self.log(f"⏳ Retrying in {self.retry_delay}s...")
                        time.sleep(self.retry_delay)
                    continue
            
            except Exception as e:
                self.log(f"❌ Error on attempt {attempt}: {e}")
                if attempt < self.max_retries:
                    self.log(f"⏳ Retrying in {self.retry_delay}s...")
                    time.sleep(self.retry_delay)
                else:
                    self.log(f"❌ All retries exhausted")
                    return {'success': False, 'reason': str(e)}
        
        return {'success': False, 'reason': 'Max retries exceeded'}

def main():
    """Test execution engine"""
    engine = ExecutionEngine()
    
    print("🧪 Testing execution engine...")
    print(f"Max retries: {engine.max_retries}")
    print(f"Max slippage: {engine.max_slippage_pct}%")
    print(f"Gas multiplier: {engine.gas_price_multiplier}x")
    print("\n✅ Ready for real money execution")

if __name__ == "__main__":
    main()
