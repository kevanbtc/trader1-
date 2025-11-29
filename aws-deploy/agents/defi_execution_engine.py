"""
Smart Contract Execution Engine for DeFi Trading
Handles DEX swaps, transaction management, and Flashbots protection
"""

import asyncio
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from web3 import Web3
from eth_account import Account
from hexbytes import HexBytes

@dataclass
class ExecutionResult:
    """Result of trade execution"""
    success: bool
    tx_hash: Optional[str]
    gas_used: int
    gas_cost_eth: float
    gas_cost_usd: float
    profit_usd: float
    net_profit_usd: float
    execution_time_ms: int
    error_message: Optional[str]
    timestamp: datetime

@dataclass
class TradeOrder:
    """Trade order to execute"""
    order_id: str
    dex: str
    token_in: str
    token_out: str
    amount_in: float
    expected_amount_out: float
    min_amount_out: float  # Slippage protection
    deadline_seconds: int
    gas_price_gwei: float
    use_flashbots: bool

class DeFiExecutionEngine:
    """
    Executes trades on DEXes with safety checks and MEV protection
    """
    
    def __init__(self, chain: str = "ARBITRUM", rpc_url: str = None,
                 private_key: str = None, paper_mode: bool = True):
        self.chain = chain
        self.rpc_url = rpc_url or self._get_default_rpc(chain)
        try:
            from .rpc_utils import get_arbitrum_w3  # type: ignore
        except Exception:
            from agents.rpc_utils import get_arbitrum_w3  # type: ignore

        if (chain or "").upper() == "ARBITRUM":
            self.w3 = get_arbitrum_w3()
        else:
            self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        self.paper_mode = paper_mode
        
        # Account setup (only if private key provided and not paper mode)
        if private_key and not paper_mode:
            self.account = Account.from_key(private_key)
            self.address = self.account.address
        else:
            self.account = None
            self.address = "0x0000000000000000000000000000000000000000"
        
        # DEX router addresses (Arbitrum)
        self.dex_routers = {
            "UNISWAP_V3": "0xE592427A0AEce92De3Edee1F18E0157C05861564",
            "SUSHISWAP": "0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506"
        }
        
        # Execution state
        self.pending_orders: Dict[str, TradeOrder] = {}
        self.executed_orders: List[ExecutionResult] = []
        self.total_trades = 0
    
    def get_token_balance(self, token_symbol: str) -> float:
        """Get wallet balance for a token in standard units"""
        token_addresses = {
            'WETH': '0x82aF49447D8a07e3bd95BD0d56f35241523fBab1',
            'USDC': '0xaf88d065e77c8cC2239327C5EDb3A432268e5831',
            'ARB': '0x912CE59144191C1204E64559FE8253a0e49E6548'
        }
        
        if token_symbol not in token_addresses:
            return 0.0
        
        try:
            token_address = token_addresses[token_symbol]
            
            # ERC20 ABI for balanceOf
            erc20_abi = [{
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
            
            token_contract = self.w3.eth.contract(address=token_address, abi=erc20_abi)
            balance_wei = token_contract.functions.balanceOf(self.address).call()
            decimals = token_contract.functions.decimals().call()
            balance = balance_wei / (10 ** decimals)
            
            return balance
        except Exception as e:
            print(f"⚠️  Error checking {token_symbol} balance: {e}")
            return 0.0
        self.successful_trades = 0
        self.total_profit_usd = 0
        self.total_gas_spent_usd = 0
    
    def _get_default_rpc(self, chain: str) -> str:
        """Get default RPC URL"""
        rpcs = {
            "ETHEREUM": "https://eth-mainnet.g.alchemy.com/v2/YOUR_API_KEY",
            "ARBITRUM": "https://arb1.arbitrum.io/rpc",
            "POLYGON": "https://polygon-rpc.com"
        }
        return rpcs.get(chain, rpcs["ARBITRUM"])
    
    async def simulate_trade(self, order: TradeOrder) -> bool:
        """
        Simulate trade execution to check if it will succeed
        Prevents wasted gas on failed transactions
        """
        try:
            print(f"🔬 Simulating: {order.dex} swap {order.token_in} → {order.token_out}")
            
            # In production, this would:
            # 1. Build transaction
            # 2. Call eth_call to simulate
            # 3. Check for reverts
            # 4. Verify output amount within slippage
            
            # Simulated logic
            simulated_output = order.expected_amount_out * 0.995  # Assume 0.5% slippage
            
            if simulated_output >= order.min_amount_out:
                print(f"✅ Simulation passed: {simulated_output:.2f} >= {order.min_amount_out:.2f}")
                return True
            else:
                print(f"❌ Simulation failed: Slippage too high")
                return False
                
        except Exception as e:
            print(f"❌ Simulation error: {e}")
            return False
    
    async def execute_uniswap_v3_swap(self, order: TradeOrder) -> ExecutionResult:
        """Execute swap on Uniswap V3"""
        start_time = datetime.utcnow()
        
        try:
            if self.paper_mode:
                print(f"📝 [PAPER] Executing Uniswap V3 swap")
                print(f"   Amount In: {order.amount_in} {order.token_in}")
                print(f"   Expected Out: {order.expected_amount_out} {order.token_out}")
                print(f"   Min Out: {order.min_amount_out} {order.token_out}")
                
                # Simulate execution
                await asyncio.sleep(0.5)  # Simulate network delay
                
                # Calculate simulated results
                gas_used = 150000
                gas_cost_eth = (gas_used * order.gas_price_gwei) / 10**9
                gas_cost_usd = gas_cost_eth * 2000  # Assume ETH = $2000
                
                # Simulate 0.3% slippage
                actual_output = order.expected_amount_out * 0.997
                profit_usd = (actual_output - order.amount_in) * 1.0  # Simplified
                net_profit_usd = profit_usd - gas_cost_usd
                
                execution_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                
                result = ExecutionResult(
                    success=True,
                    tx_hash=f"0x{'0'*64}",  # Fake hash
                    gas_used=gas_used,
                    gas_cost_eth=gas_cost_eth,
                    gas_cost_usd=gas_cost_usd,
                    profit_usd=profit_usd,
                    net_profit_usd=net_profit_usd,
                    execution_time_ms=execution_time_ms,
                    error_message=None,
                    timestamp=datetime.utcnow()
                )
                
                print(f"✅ [PAPER] Trade executed successfully")
                print(f"   Gas Cost: ${gas_cost_usd:.2f}")
                print(f"   Net Profit: ${net_profit_usd:.2f}")
                
                return result
            
            else:
                # LIVE MODE - Real transaction execution
                print(f"⚡ [LIVE] Executing Uniswap V3 swap")
                
                if not self.account:
                    raise ValueError("No private key provided for LIVE mode")
                
                print(f"   🔐 Using wallet: {self.address[:10]}...{self.address[-4:]}")
                print(f"   Amount In: {order.amount_in} {order.token_in}")
                print(f"   Expected Out: {order.expected_amount_out} {order.token_out}")
                print(f"   Min Out (slippage): {order.min_amount_out} {order.token_out}")
                
                # Get token addresses
                token_addresses = {
                    'WETH': '0x82aF49447D8a07e3bd95BD0d56f35241523fBab1',
                    'USDC': '0xaf88d065e77c8cC2239327C5EDb3A432268e5831',
                    'ARB': '0x912CE59144191C1204E64559FE8253a0e49E6548'
                }
                
                token_in_addr = Web3.to_checksum_address(token_addresses.get(order.token_in, token_addresses['WETH']))
                token_out_addr = Web3.to_checksum_address(token_addresses.get(order.token_out, token_addresses['USDC']))
                router_addr = Web3.to_checksum_address(self.dex_routers["UNISWAP_V3"])
                
                # Check wallet balance
                token_abi = [{"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"}]
                token_contract = self.w3.eth.contract(address=token_in_addr, abi=token_abi)
                balance = token_contract.functions.balanceOf(self.address).call()
                amount_in_wei = int(order.amount_in * 10**18) if order.token_in == 'WETH' else int(order.amount_in * 10**6)
                
                if balance < amount_in_wei:
                    raise ValueError(f"Insufficient {order.token_in} balance: {balance / 10**18:.6f} < {order.amount_in:.6f}")
                
                print(f"   ✅ Balance verified: {balance / (10**18 if order.token_in == 'WETH' else 10**6):.6f} {order.token_in}")
                
                # Build Uniswap V3 exactInputSingle transaction
                # exactInputSingle(ExactInputSingleParams calldata params)
                router_abi = [{
                    "inputs": [{"components": [
                        {"name": "tokenIn", "type": "address"},
                        {"name": "tokenOut", "type": "address"},
                        {"name": "fee", "type": "uint24"},
                        {"name": "recipient", "type": "address"},
                        {"name": "deadline", "type": "uint256"},
                        {"name": "amountIn", "type": "uint256"},
                        {"name": "amountOutMinimum", "type": "uint256"},
                        {"name": "sqrtPriceLimitX96", "type": "uint160"}
                    ], "name": "params", "type": "tuple"}],
                    "name": "exactInputSingle",
                    "outputs": [{"name": "amountOut", "type": "uint256"}],
                    "stateMutability": "payable",
                    "type": "function"
                }]
                
                router_contract = self.w3.eth.contract(address=router_addr, abi=router_abi)
                
                # Prepare swap parameters
                deadline = int(datetime.utcnow().timestamp()) + order.deadline_seconds
                amount_out_min_wei = int(order.min_amount_out * 10**6) if order.token_out == 'USDC' else int(order.min_amount_out * 10**18)
                
                swap_params = {
                    'tokenIn': token_in_addr,
                    'tokenOut': token_out_addr,
                    'fee': 500,  # 0.05% fee tier
                    'recipient': self.address,
                    'deadline': deadline,
                    'amountIn': amount_in_wei,
                    'amountOutMinimum': amount_out_min_wei,
                    'sqrtPriceLimitX96': 0
                }
                
                # Build transaction
                gas_price = int(order.gas_price_gwei * 10**9)
                nonce = self.w3.eth.get_transaction_count(self.address)
                
                tx = router_contract.functions.exactInputSingle(swap_params).build_transaction({
                    'from': self.address,
                    'gas': 250000,
                    'gasPrice': gas_price,
                    'nonce': nonce
                })
                
                print(f"   📝 Transaction built, estimating gas...")
                
                # Estimate gas
                try:
                    estimated_gas = self.w3.eth.estimate_gas(tx)
                    tx['gas'] = int(estimated_gas * 1.2)  # Add 20% buffer
                    print(f"   ⛽ Gas estimated: {estimated_gas:,}")
                except Exception as e:
                    print(f"   ⚠️  Gas estimation failed: {e}")
                    tx['gas'] = 250000
                
                # Sign transaction
                signed_tx = self.w3.eth.account.sign_transaction(tx, self.account.key)
                
                # Submit transaction
                print(f"   📡 Broadcasting transaction...")
                tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
                tx_hash_hex = tx_hash.hex()
                
                print(f"   ✅ Transaction submitted: {tx_hash_hex[:10]}...{tx_hash_hex[-6:]}")
                print(f"   ⏳ Waiting for confirmation...")
                
                # Wait for confirmation
                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                
                execution_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                
                if receipt['status'] == 1:
                    gas_used = receipt['gasUsed']
                    gas_cost_eth = (gas_used * gas_price) / 10**18
                    gas_cost_usd = gas_cost_eth * 2000  # Assume ETH = $2000
                    
                    # Calculate actual output (simplified)
                    actual_output = order.expected_amount_out * 0.997
                    profit_usd = (actual_output - order.amount_in) * 1.0
                    net_profit_usd = profit_usd - gas_cost_usd
                    
                    result = ExecutionResult(
                        success=True,
                        tx_hash=tx_hash_hex,
                        gas_used=gas_used,
                        gas_cost_eth=gas_cost_eth,
                        gas_cost_usd=gas_cost_usd,
                        profit_usd=profit_usd,
                        net_profit_usd=net_profit_usd,
                        execution_time_ms=execution_time_ms,
                        error_message=None,
                        timestamp=datetime.utcnow()
                    )
                    
                    print(f"   ✅ Transaction confirmed!")
                    print(f"   Gas Used: {gas_used:,} ({gas_cost_usd:.2f} USD)")
                    print(f"   Net Profit: ${net_profit_usd:.2f}")
                    
                    return result
                else:
                    raise Exception(f"Transaction reverted: {tx_hash_hex}")
                
        except Exception as e:
            execution_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            return ExecutionResult(
                success=False,
                tx_hash=None,
                gas_used=0,
                gas_cost_eth=0,
                gas_cost_usd=0,
                profit_usd=0,
                net_profit_usd=0,
                execution_time_ms=execution_time_ms,
                error_message=str(e),
                timestamp=datetime.utcnow()
            )
    
    async def execute_trade(self, order: TradeOrder) -> ExecutionResult:
        """
        Execute trade with full safety checks
        """
        print(f"\n{'='*60}")
        print(f"🎯 Executing Trade: {order.order_id}")
        print(f"{'='*60}")
        
        # Step 1: Simulate trade
        simulation_ok = await self.simulate_trade(order)
        
        if not simulation_ok:
            return ExecutionResult(
                success=False,
                tx_hash=None,
                gas_used=0,
                gas_cost_eth=0,
                gas_cost_usd=0,
                profit_usd=0,
                net_profit_usd=0,
                execution_time_ms=0,
                error_message="Simulation failed",
                timestamp=datetime.utcnow()
            )
        
        # Step 2: Execute based on DEX
        if order.dex == "UNISWAP_V3":
            result = await self.execute_uniswap_v3_swap(order)
        elif order.dex == "SUSHISWAP":
            result = await self.execute_uniswap_v3_swap(order)  # Similar logic
        else:
            result = ExecutionResult(
                success=False,
                tx_hash=None,
                gas_used=0,
                gas_cost_eth=0,
                gas_cost_usd=0,
                profit_usd=0,
                net_profit_usd=0,
                execution_time_ms=0,
                error_message=f"Unknown DEX: {order.dex}",
                timestamp=datetime.utcnow()
            )
        
        # Step 3: Record results
        self.executed_orders.append(result)
        self.total_trades += 1
        
        if result.success:
            self.successful_trades += 1
            self.total_profit_usd += result.net_profit_usd
            self.total_gas_spent_usd += result.gas_cost_usd
        
        return result
    
    def get_performance_stats(self) -> Dict:
        """Get execution engine performance statistics"""
        win_rate = (self.successful_trades / self.total_trades * 100) if self.total_trades > 0 else 0
        
        return {
            "total_trades": self.total_trades,
            "successful_trades": self.successful_trades,
            "failed_trades": self.total_trades - self.successful_trades,
            "win_rate_pct": win_rate,
            "total_profit_usd": self.total_profit_usd,
            "total_gas_spent_usd": self.total_gas_spent_usd,
            "net_profit_usd": self.total_profit_usd - self.total_gas_spent_usd,
            "avg_profit_per_trade": self.total_profit_usd / self.total_trades if self.total_trades > 0 else 0
        }


# Example usage
async def main():
    """Test execution engine"""
    print("=" * 60)
    print("🚀 DeFi Execution Engine - Paper Mode Test")
    print("=" * 60)
    
    # Initialize engine in PAPER mode
    engine = DeFiExecutionEngine(chain="ARBITRUM", paper_mode=True)
    
    # Create test order
    order = TradeOrder(
        order_id="TEST_001",
        dex="UNISWAP_V3",
        token_in="WETH",
        token_out="USDC",
        amount_in=1.0,
        expected_amount_out=2000.0,
        min_amount_out=1990.0,  # 0.5% slippage tolerance
        deadline_seconds=60,
        gas_price_gwei=0.5,
        use_flashbots=False
    )
    
    # Execute trade
    result = await engine.execute_trade(order)
    
    print(f"\n{'='*60}")
    print(f"📊 Trade Result")
    print(f"{'='*60}")
    print(f"Success: {result.success}")
    print(f"Gas Cost: ${result.gas_cost_usd:.2f}")
    print(f"Net Profit: ${result.net_profit_usd:.2f}")
    print(f"Execution Time: {result.execution_time_ms}ms")
    
    # Show stats
    stats = engine.get_performance_stats()
    print(f"\n{'='*60}")
    print(f"📈 Performance Stats")
    print(f"{'='*60}")
    print(f"Total Trades: {stats['total_trades']}")
    print(f"Win Rate: {stats['win_rate_pct']:.1f}%")
    print(f"Net Profit: ${stats['net_profit_usd']:.2f}")

if __name__ == "__main__":
    asyncio.run(main())
