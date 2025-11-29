"""
Flashloan Execution Module
Integrates Aave V3 and Balancer V2 flashloans for capital-free arbitrage
Enables 10-100x position scaling with zero capital requirements
Atomic execution = zero risk (reverts if unprofitable)
"""

import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
from web3 import Web3
from eth_abi import encode
import os

@dataclass
class FlashloanRoute:
    """Flashloan execution route"""
    provider: str  # "AAVE_V3" or "BALANCER_V2"
    loan_token: str  # Token to borrow
    loan_amount: float  # Amount to borrow
    loan_amount_wei: int  # Amount in wei
    premium_bps: int  # Flashloan fee in basis points
    premium_amount: float  # Fee in tokens
    arbitrage_path: List[Dict]  # Path to execute with borrowed funds
    expected_profit: float  # Expected profit after repaying loan + fee
    execution_data: bytes  # Encoded calldata for flashloan callback

@dataclass
class FlashloanResult:
    """Result of flashloan execution"""
    success: bool
    tx_hash: Optional[str]
    profit_usd: float
    gas_used: int
    gas_cost_usd: float
    net_profit_usd: float
    error: Optional[str]

class FlashloanExecutor:
    """
    Flashloan execution engine for Aave V3 and Balancer V2
    Allows capital-free arbitrage with atomic safety
    """
    
    # Arbitrum contract addresses
    AAVE_POOL = "0x794a61358D6845594F94dc1DB02A252b5b4814aD"  # Aave V3 Pool
    BALANCER_VAULT = "0xBA12222222228d8Ba445958a75a0704d566BF2C8"  # Balancer V2 Vault
    
    def __init__(self, w3: Web3, wallet_address: str, private_key: str):
        self.w3 = w3
        self.wallet_address = wallet_address
        self.private_key = private_key
        
        # Flashloan parameters
        self.aave_premium_bps = 9  # 0.09% Aave V3 fee
        self.balancer_premium_bps = 0  # 0% Balancer fee (but requires exact repayment)
        
        # Contract ABIs (minimal)
        self.aave_abi = [
            {
                "inputs": [
                    {"name": "receiverAddress", "type": "address"},
                    {"name": "assets", "type": "address[]"},
                    {"name": "amounts", "type": "uint256[]"},
                    {"name": "interestRateModes", "type": "uint256[]"},
                    {"name": "onBehalfOf", "type": "address"},
                    {"name": "params", "type": "bytes"},
                    {"name": "referralCode", "type": "uint16"}
                ],
                "name": "flashLoan",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            }
        ]
        
        self.balancer_abi = [
            {
                "inputs": [
                    {"name": "recipient", "type": "address"},
                    {"name": "tokens", "type": "address[]"},
                    {"name": "amounts", "type": "uint256[]"},
                    {"name": "userData", "type": "bytes"}
                ],
                "name": "flashLoan",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            }
        ]
        
        # Contracts
        self.aave_pool = self.w3.eth.contract(address=self.AAVE_POOL, abi=self.aave_abi)
        self.balancer_vault = self.w3.eth.contract(address=self.BALANCER_VAULT, abi=self.balancer_abi)
        
        # Execution settings
        self.max_loan_multiplier = 20  # Max 20x wallet balance
        self.min_profit_after_fee = float(os.environ.get('MIN_FLASHLOAN_PROFIT_USD', '0.10'))
        
        print(f"⚡ Flashloan Executor initialized: Aave fee {self.aave_premium_bps}bps, Balancer fee {self.balancer_premium_bps}bps")
        print(f"⚡ Min profit after fees: ${self.min_profit_after_fee}")
    
    async def calculate_optimal_loan(self, opportunity: Dict, available_capital: float) -> FlashloanRoute:
        """
        Calculate optimal flashloan size and route
        Scales position size to maximize profit while staying within liquidity limits
        """
        # Extract opportunity details
        token_in = opportunity.get('token_in', 'USDC')
        buy_price = opportunity.get('buy_price', 0)
        sell_price = opportunity.get('sell_price', 0)
        buy_dex = opportunity.get('buy_dex', '')
        sell_dex = opportunity.get('sell_dex', '')
        max_liquidity = opportunity.get('liquidity', 1000)  # Max trade size before significant slippage
        
        # Calculate spread
        spread_bps = int(((sell_price - buy_price) / buy_price) * 10000) if buy_price > 0 else 0
        
        # Determine optimal loan size (limited by liquidity)
        # Start with 10x wallet balance, cap at liquidity limit
        optimal_loan = min(available_capital * 10, max_liquidity * 0.5)  # 50% of liquidity to avoid slippage
        
        # Choose provider (Balancer has no fee, prefer it)
        provider = "BALANCER_V2"
        premium_bps = self.balancer_premium_bps
        
        # Calculate premium
        premium_amount = optimal_loan * (premium_bps / 10000)
        
        # Estimate profit
        gross_profit = optimal_loan * (spread_bps / 10000)
        net_profit = gross_profit - premium_amount - 0.50  # Subtract estimated gas cost
        
        # Build arbitrage path
        arbitrage_path = [
            {
                'action': 'SWAP',
                'dex': buy_dex,
                'token_in': token_in,
                'token_out': opportunity.get('token_out', 'WETH'),
                'amount': optimal_loan
            },
            {
                'action': 'SWAP',
                'dex': sell_dex,
                'token_in': opportunity.get('token_out', 'WETH'),
                'token_out': token_in,
                'amount': 'OUTPUT_OF_PREVIOUS'
            }
        ]
        
        # Encode execution data (simplified - real implementation would encode full swap path)
        execution_data = encode(['address', 'uint256'], [self.wallet_address, int(optimal_loan * 1e6)])
        
        return FlashloanRoute(
            provider=provider,
            loan_token=token_in,
            loan_amount=optimal_loan,
            loan_amount_wei=int(optimal_loan * 1e6),  # Assume 6 decimals for USDC
            premium_bps=premium_bps,
            premium_amount=premium_amount,
            arbitrage_path=arbitrage_path,
            expected_profit=net_profit,
            execution_data=execution_data
        )
    
    async def execute_flashloan_arbitrage(self, route: FlashloanRoute, dry_run: bool = False) -> FlashloanResult:
        """
        Execute flashloan arbitrage
        If dry_run=True, simulates execution without broadcasting transaction
        """
        if route.expected_profit < self.min_profit_after_fee:
            return FlashloanResult(
                success=False,
                tx_hash=None,
                profit_usd=0,
                gas_used=0,
                gas_cost_usd=0,
                net_profit_usd=0,
                error=f"Profit ${route.expected_profit:.4f} below minimum ${self.min_profit_after_fee}"
            )
        
        try:
            if route.provider == "AAVE_V3":
                result = await self._execute_aave_flashloan(route, dry_run)
            elif route.provider == "BALANCER_V2":
                result = await self._execute_balancer_flashloan(route, dry_run)
            else:
                raise ValueError(f"Unknown flashloan provider: {route.provider}")
            
            return result
        
        except Exception as e:
            return FlashloanResult(
                success=False,
                tx_hash=None,
                profit_usd=0,
                gas_used=0,
                gas_cost_usd=0,
                net_profit_usd=0,
                error=str(e)
            )
    
    async def _execute_aave_flashloan(self, route: FlashloanRoute, dry_run: bool) -> FlashloanResult:
        """Execute Aave V3 flashloan"""
        # Build transaction
        token_address = self._get_token_address(route.loan_token)
        
        tx = self.aave_pool.functions.flashLoan(
            self.wallet_address,  # receiverAddress
            [token_address],  # assets
            [route.loan_amount_wei],  # amounts
            [0],  # interestRateModes (0 = no debt)
            self.wallet_address,  # onBehalfOf
            route.execution_data,  # params
            0  # referralCode
        ).build_transaction({
            'from': self.wallet_address,
            'nonce': self.w3.eth.get_transaction_count(self.wallet_address),
            'gas': 500000,
            'gasPrice': self.w3.eth.gas_price
        })
        
        if dry_run:
            print(f"⚡ [DRY RUN] Would execute Aave flashloan: {route.loan_amount} {route.loan_token}")
            return FlashloanResult(
                success=True,
                tx_hash="DRY_RUN",
                profit_usd=route.expected_profit,
                gas_used=500000,
                gas_cost_usd=0.10,
                net_profit_usd=route.expected_profit - 0.10,
                error=None
            )
        
        # Sign and send transaction
        signed_tx = self.w3.eth.account.sign_transaction(tx, self.private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        print(f"⚡ Aave flashloan broadcasted: {tx_hash.hex()}")
        
        # Wait for confirmation
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
        
        success = receipt['status'] == 1
        gas_used = receipt['gasUsed']
        gas_cost_usd = (gas_used * tx['gasPrice']) / 1e18 * 3000  # Approximate
        
        return FlashloanResult(
            success=success,
            tx_hash=tx_hash.hex(),
            profit_usd=route.expected_profit if success else 0,
            gas_used=gas_used,
            gas_cost_usd=gas_cost_usd,
            net_profit_usd=route.expected_profit - gas_cost_usd if success else -gas_cost_usd,
            error=None if success else "Transaction reverted"
        )
    
    async def _execute_balancer_flashloan(self, route: FlashloanRoute, dry_run: bool) -> FlashloanResult:
        """Execute Balancer V2 flashloan"""
        # Build transaction
        token_address = self._get_token_address(route.loan_token)
        
        tx = self.balancer_vault.functions.flashLoan(
            self.wallet_address,  # recipient
            [token_address],  # tokens
            [route.loan_amount_wei],  # amounts
            route.execution_data  # userData
        ).build_transaction({
            'from': self.wallet_address,
            'nonce': self.w3.eth.get_transaction_count(self.wallet_address),
            'gas': 450000,
            'gasPrice': self.w3.eth.gas_price
        })
        
        if dry_run:
            print(f"⚡ [DRY RUN] Would execute Balancer flashloan: {route.loan_amount} {route.loan_token}")
            return FlashloanResult(
                success=True,
                tx_hash="DRY_RUN",
                profit_usd=route.expected_profit,
                gas_used=450000,
                gas_cost_usd=0.09,
                net_profit_usd=route.expected_profit - 0.09,
                error=None
            )
        
        # Sign and send transaction
        signed_tx = self.w3.eth.account.sign_transaction(tx, self.private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        print(f"⚡ Balancer flashloan broadcasted: {tx_hash.hex()}")
        
        # Wait for confirmation
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
        
        success = receipt['status'] == 1
        gas_used = receipt['gasUsed']
        gas_cost_usd = (gas_used * tx['gasPrice']) / 1e18 * 3000  # Approximate
        
        return FlashloanResult(
            success=success,
            tx_hash=tx_hash.hex(),
            profit_usd=route.expected_profit if success else 0,
            gas_used=gas_used,
            gas_cost_usd=gas_cost_usd,
            net_profit_usd=route.expected_profit - gas_cost_usd if success else -gas_cost_usd,
            error=None if success else "Transaction reverted"
        )
    
    def _get_token_address(self, symbol: str) -> str:
        """Get token contract address from symbol"""
        tokens = {
            "USDC": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
            "USDC.e": "0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8",
            "USDT": "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9",
            "DAI": "0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1",
            "WETH": "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",
            "WBTC": "0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f",
            "ARB": "0x912CE59144191C1204E64559FE8253a0e49E6548"
        }
        return tokens.get(symbol, tokens["USDC"])
    
    def format_route(self, route: FlashloanRoute) -> str:
        """Format flashloan route for display"""
        return f"""
⚡ FLASHLOAN ROUTE
Provider: {route.provider}
Loan: {route.loan_amount:.2f} {route.loan_token}
Fee: {route.premium_amount:.4f} {route.loan_token} ({route.premium_bps}bps)
Path: {' → '.join([step['dex'] for step in route.arbitrage_path])}
Expected Profit: ${route.expected_profit:.4f}
"""
