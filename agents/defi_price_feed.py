"""
Real-time DeFi Price Feed Infrastructure
Monitors Uniswap V3, Sushiswap, Curve for arbitrage opportunities
WebSocket connections + RPC polling for tick-level precision
Integrated with MCP Intelligence for smart filtering
"""

import asyncio
import websockets
import json
import time
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from web3 import Web3
from eth_abi import decode
import os

# Import RPC Error Handling
try:
    from agents.rpc_errors import (
        RpcRateLimitError, RpcConnectionError, RpcBackoffManager,
        safe_rpc_call, is_rate_limit_error
    )
    RPC_ERROR_HANDLING = True
except ImportError:
    print("⚠️  RPC error handling not available")
    RPC_ERROR_HANDLING = False
    class RpcRateLimitError(Exception): pass
    class RpcConnectionError(Exception): pass

# Import MCP Intelligence
try:
    from agents.mcp_intelligence import MCPIntelligence, MarketSignal
    MCP_AVAILABLE = True
except ImportError:
    print("⚠️  MCP Intelligence not available - running without smart filters")
    MCP_AVAILABLE = False

# Import Swarm Coordinator
try:
    from agents.swarm_coordinator import SwarmCoordinator, SwarmDecision
    SWARM_AVAILABLE = True
except ImportError:
    print("⚠️  Swarm Coordinator not available - running without multi-agent consensus")
    SWARM_AVAILABLE = False

# Intel Ingestor (optional)
try:
    from agents.intel_ingestor import process_intelligence  # type: ignore
    INTEL_AVAILABLE = True
except Exception:
    print("⚠️  Intel Ingestor not available - running without intel synthesis")
    INTEL_AVAILABLE = False

@dataclass
class PriceQuote:
    """Price quote from a specific DEX"""
    dex: str
    pool_address: str
    token_in: str
    token_out: str
    amount_in: float
    amount_out: float
    price: float
    timestamp: datetime
    gas_estimate: int
    liquidity: float

@dataclass
class ArbitrageOpportunity:
    """Detected arbitrage opportunity"""
    buy_dex: str
    sell_dex: str
    token_path: List[str]
    buy_price: float
    sell_price: float
    profit_bps: int
    profit_usd: float
    gas_cost_usd: float
    net_profit_usd: float
    confidence: float
    timestamp: datetime
    execution_priority: str  # LOW, MEDIUM, HIGH, CRITICAL

class DeFiPriceFeed:
    """
    Real-time price feed aggregator for multiple DEXes
    Supports: Uniswap V3, Sushiswap, Curve
    Integrated with MCP Intelligence for opportunity validation
    """
    
    def __init__(self, chain: str = "ARBITRUM", rpc_url: str = None, enable_mcp: bool = True):
        self.chain = chain
        # Always prefer resilient multi-provider Web3 for Arbitrum
        self.rpc_url = rpc_url or self._get_default_rpc(chain)
        try:
            from .rpc_utils import get_arbitrum_w3  # type: ignore
        except Exception:
            from agents.rpc_utils import get_arbitrum_w3  # type: ignore

        if (chain or "").upper() == "ARBITRUM":
            # If explicit RPC URL provided, use it directly (bypasses multi-provider rotation)
            if rpc_url:
                self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
            else:
                self.w3 = get_arbitrum_w3()
        else:
            # Fallback to direct provider for non-Arbitrum chains
            self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        
        # Price cache
        self.price_cache: Dict[str, PriceQuote] = {}
        self.opportunity_callbacks: List[Callable] = []
        
        # RPC backoff manager
        max_consecutive_errors = int(os.getenv('MAX_CONSECUTIVE_RPC_ERRORS', '5'))
        backoff_seconds = float(os.getenv('RPC_BACKOFF_SECONDS', '15'))
        self.rpc_backoff = RpcBackoffManager(
            max_consecutive_errors=max_consecutive_errors,
            backoff_seconds=backoff_seconds
        ) if RPC_ERROR_HANDLING else None
        
        # MCP Intelligence integration
        self.enable_mcp = enable_mcp and MCP_AVAILABLE
        self.mcp = None
        if self.enable_mcp:
            try:
                # Let MCP use the same resilient provider by omitting rpc_url
                # so it falls back to rpc_utils.get_arbitrum_w3()
                self.mcp = MCPIntelligence(chain=chain, rpc_url=None)
                print("🧠 MCP Intelligence ENABLED - Smart filtering active")
            except Exception as e:
                print(f"⚠️  MCP initialization failed: {e}")
                self.enable_mcp = False
        else:
            print("📊 MCP Intelligence DISABLED - Basic filtering only")
        
        # Swarm Coordinator integration
        self.enable_swarm = enable_mcp and SWARM_AVAILABLE  # Swarm requires MCP
        self.swarm = None
        if self.enable_swarm:
            try:
                self.swarm = SwarmCoordinator()
                print("🐝 Swarm Intelligence ENABLED - Multi-agent consensus active")
            except Exception as e:
                print(f"⚠️  Swarm initialization failed: {e}")
                self.enable_swarm = False
        else:
            print("📊 Swarm Intelligence DISABLED - Single-agent decisions")

        # Intel Ingestor integration
        self.enable_intel = os.environ.get('INTEL_INGESTOR_ENABLED', '1').strip().lower() in ('1','true','yes','on') and INTEL_AVAILABLE
        if self.enable_intel:
            print("🧩 Intel Ingestor ENABLED - Structured insight synthesis active")
        else:
            print("📊 Intel Ingestor DISABLED - Skipping intel synthesis")
        
        # MCP configuration
        self.mcp_min_confidence = 55  # Minimum MCP score to execute (0-100)
        self.mcp_required_for_large_trades = True  # Require MCP approval for trades >$5k
        
        # Price history tracking for MCP
        self.last_price_update: Dict[str, datetime] = {}
        
        # Trading state for swarm context
        self.total_exposure_usd = 0
        self.consecutive_losses = 0
        self.recent_spreads = []  # Track recent spread sizes
        
        # Multi-DEX Adapter for expanded scanning
        try:
            from agents.multi_dex_adapter import MultiDexAdapter
            self.multi_dex = MultiDexAdapter(self.w3)
            venue_count = self.multi_dex.get_total_venues()
            print(f"🌐 Multi-DEX Adapter ENABLED - Scanning {venue_count} venues")
            self.multi_dex.print_status()
        except Exception as e:
            print(f"⚠️  Multi-DEX adapter initialization failed: {e}")
            self.multi_dex = None
        
        # DEX router addresses (Arbitrum) - Legacy support
        self.dex_routers = {
            "UNISWAP_V3": "0xE592427A0AEce92De3Edee1F18E0157C05861564",
            "SUSHISWAP": "0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506",
            "CURVE": "0x7544Fe3d184b6B55D6B36c3FCA1157eE0Ba30287"
        }
        # Uniswap V3 Quoter V2 (widely deployed address incl. Arbitrum)
        self.uniswap_quoter_v2 = "0x61fFE014bA17989E743c5F6cB21bF9697530B21e"
        
        # Token addresses (Arbitrum) - EXPANDED UNIVERSE
        self.tokens = self._load_token_universe()
        
        # Uniswap V3 pools (Arbitrum)
        self.univ3_pools = {
            "WETH/USDC-0.05": "0xC6962004f452bE9203591991D15f6b388e09E8D0",
            "WETH/USDC-0.3": "0xC31E54c7a869B9FcBEcc14363CF510d1c41fa443",
            "WETH/USDT-0.05": "0x641C00A822e8b671738d32a431a4Fb6074E5c79d"
        }
        
        # Monitoring state
        self.running = False
        self.last_block = 0
        
    def _load_token_universe(self) -> Dict[str, str]:
        """Load expanded token universe from config"""
        try:
            # Try Smart Predator config first (50 curated, high-liquidity tokens)
            predator_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'smart_predator_tokens.json')
            if os.path.exists(predator_path):
                with open(predator_path, 'r') as f:
                    data = json.load(f)
                tokens = {}
                for symbol, info in data.get('tokens', {}).items():
                    addr = info.get('address', '')
                    # Skip placeholder addresses (all zeros)
                    if addr and addr != '0x0000000000000000000000000000000000000000':
                        tokens[symbol] = addr
                print(f"📚 Loaded {len(tokens)} tokens from Smart Predator universe")
                return tokens
            
            # Fallback to original token_universe.json
            universe_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'token_universe.json')
            with open(universe_path, 'r') as f:
                data = json.load(f)
            
            tokens = {}
            for category, details in data['arbitrum_token_universe'].items():
                for token_info in details.get('tokens', []):
                    tokens[token_info['symbol']] = token_info['address']
            
            print(f"📚 Loaded {len(tokens)} tokens from expanded universe")
            return tokens
        except Exception as e:
            print(f"⚠️  Failed to load token universe, using fallback: {e}")
            # Fallback to core tokens
            return {
                "WETH": "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",
                "USDC": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
                "USDC.e": "0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8",
                "USDT": "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9",
                "DAI": "0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1",
                "WBTC": "0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f",
                "ARB": "0x912CE59144191C1204E64559FE8253a0e49E6548"
            }
    
    def _get_default_rpc(self, chain: str) -> str:
        """Get default RPC URL for chain - uses centralized config"""
        try:
            from .rpc_config import RPCConfig
            return RPCConfig.get_rpc(chain)
        except:
            # Final fallback
            rpcs = {
                "ETHEREUM": "https://eth.llamarpc.com",
                "ARBITRUM": "https://arb1.arbitrum.io/rpc",
                "POLYGON": "https://polygon.llamarpc.com"
            }
            return rpcs.get(chain, rpcs["ARBITRUM"])
    
    def register_opportunity_callback(self, callback: Callable):
        """Register callback to be called when arbitrage opportunity detected"""
        self.opportunity_callbacks.append(callback)
    
    async def get_uniswap_v3_quote(self, pool_address: str, token_in: str, 
                                    token_out: str, amount_in: float) -> Optional[PriceQuote]:
        """
        Get price quote from Uniswap V3 pool
        Reads slot0 for current price and liquidity
        """
        try:
            # Uniswap V3 Pool ABI for slot0()
            pool_abi = [
                {
                    "inputs": [],
                    "name": "slot0",
                    "outputs": [
                        {"name": "sqrtPriceX96", "type": "uint160"},
                        {"name": "tick", "type": "int24"},
                        {"name": "observationIndex", "type": "uint16"},
                        {"name": "observationCardinality", "type": "uint16"},
                        {"name": "observationCardinalityNext", "type": "uint16"},
                        {"name": "feeProtocol", "type": "uint8"},
                        {"name": "unlocked", "type": "bool"}
                    ],
                    "stateMutability": "view",
                    "type": "function"
                },
                {
                    "inputs": [],
                    "name": "liquidity",
                    "outputs": [{"name": "", "type": "uint128"}],
                    "stateMutability": "view",
                    "type": "function"
                },
                {
                    "inputs": [],
                    "name": "token0",
                    "outputs": [{"name": "", "type": "address"}],
                    "stateMutability": "view",
                    "type": "function"
                },
                {
                    "inputs": [],
                    "name": "token1",
                    "outputs": [{"name": "", "type": "address"}],
                    "stateMutability": "view",
                    "type": "function"
                },
                {
                    "inputs": [],
                    "name": "fee",
                    "outputs": [{"name": "", "type": "uint24"}],
                    "stateMutability": "view",
                    "type": "function"
                }
            ]
            
            # Create contract instance
            pool_contract = self.w3.eth.contract(address=pool_address, abi=pool_abi)
            
            # Get current price from slot0
            slot0 = pool_contract.functions.slot0().call()
            sqrt_price_x96 = slot0[0]
            tick = slot0[1]
            
            # Get liquidity
            liquidity = pool_contract.functions.liquidity().call()
            
            # Read token ordering and decimals
            pool_token0 = pool_contract.functions.token0().call()
            pool_token1 = pool_contract.functions.token1().call()
            pool_fee = 0
            try:
                pool_fee = int(pool_contract.functions.fee().call())
            except Exception:
                pool_fee = 0  # not critical for mid-price
            
            erc20_dec_abi = [
                {
                    "constant": True,
                    "inputs": [],
                    "name": "decimals",
                    "outputs": [{"name": "", "type": "uint8"}],
                    "payable": False,
                    "stateMutability": "view",
                    "type": "function",
                }
            ]
            token0_contract = self.w3.eth.contract(address=pool_token0, abi=erc20_dec_abi)
            token1_contract = self.w3.eth.contract(address=pool_token1, abi=erc20_dec_abi)
            decimals0 = int(token0_contract.functions.decimals().call())
            decimals1 = int(token1_contract.functions.decimals().call())
            
            # Convert sqrtPriceX96 to human-readable price
            # Uniswap V3 mid-price expresses token1 per token0 when using slot0
            # price_1_per_0 = (sqrtPriceX96 / 2^96)^2 * 10^(decimals0 - decimals1)
            Q96 = 2 ** 96
            price_ratio = (sqrt_price_x96 / Q96) ** 2
            price_1_per_0 = price_ratio * (10 ** (decimals0 - decimals1))

            # Determine direction relative to requested token_in/out
            price_out_per_in: float
            if token_in.lower() == pool_token0.lower() and token_out.lower() == pool_token1.lower():
                price_out_per_in = float(price_1_per_0)
            elif token_in.lower() == pool_token1.lower() and token_out.lower() == pool_token0.lower():
                # inverse path
                if price_1_per_0 == 0:
                    return None
                price_out_per_in = float(1.0 / price_1_per_0)
            else:
                # The provided token pair doesn't match this pool
                return None

            # Calculate amount out using mid-price (no fee/slippage accounted)
            amount_out = amount_in * price_out_per_in

            # Try Uniswap V3 Quoter V2 for executable quote (accounts for fee); fallback to mid-price
            try:
                quoter_abi = [
                    {
                        "inputs": [
                            {
                                "components": [
                                    {"name": "tokenIn", "type": "address"},
                                    {"name": "tokenOut", "type": "address"},
                                    {"name": "fee", "type": "uint24"},
                                    {"name": "recipient", "type": "address"},
                                    {"name": "amountIn", "type": "uint256"},
                                    {"name": "sqrtPriceLimitX96", "type": "uint160"}
                                ],
                                "name": "params",
                                "type": "tuple"
                            }
                        ],
                        "name": "quoteExactInputSingle",
                        "outputs": [
                            {"name": "amountOut", "type": "uint256"},
                            {"name": "sqrtPriceX96After", "type": "uint160"},
                            {"name": "initializedTicksCrossed", "type": "uint32"},
                            {"name": "gasEstimate", "type": "uint256"}
                        ],
                        "stateMutability": "nonpayable",
                        "type": "function"
                    }
                ]

                quoter = self.w3.eth.contract(address=self.uniswap_quoter_v2, abi=quoter_abi)

                # Determine decimals for token_in and token_out
                if token_in.lower() == pool_token0.lower():
                    dec_in = decimals0
                else:
                    dec_in = decimals1
                if token_out.lower() == pool_token0.lower():
                    dec_out = decimals0
                else:
                    dec_out = decimals1

                amount_in_wei = int(amount_in * (10 ** dec_in))
                params = (
                    token_in,
                    token_out,
                    pool_fee,
                    "0x0000000000000000000000000000000000000000",
                    amount_in_wei,
                    0
                )

                result = quoter.functions.quoteExactInputSingle(params).call()
                amount_out_wei = result[0]
                amount_out_quoter = amount_out_wei / (10 ** dec_out)
                price_out_per_in_quoter = amount_out_quoter / amount_in if amount_in > 0 else price_out_per_in

                # If quoter returns a sane value, prefer it
                if amount_out_quoter > 0:
                    amount_out = amount_out_quoter
                    price_out_per_in = price_out_per_in_quoter
            except Exception:
                # Quoter may be unavailable or revert; continue with mid-price
                pass
            
            return PriceQuote(
                dex="UNISWAP_V3",
                pool_address=pool_address,
                token_in=token_in,
                token_out=token_out,
                amount_in=amount_in,
                amount_out=amount_out,
                price=price_out_per_in,
                timestamp=datetime.utcnow(),
                gas_estimate=150000,
                liquidity=float(liquidity / 10**18)
            )
        except Exception as e:
            err_msg = str(e)
            if is_rate_limit_error(e):
                print(f"⚠️  Uniswap V3 quote rate limited: 429")
                raise RpcRateLimitError(err_msg)
            print(f"Error getting Uniswap V3 quote: {e}")
            return None
    
    async def get_sushiswap_quote(self, token_in: str, token_out: str, 
                                   amount_in: float) -> Optional[PriceQuote]:
        """Get price quote from Sushiswap using Router V2"""
        try:
            # Sushiswap Router V2 ABI for getAmountsOut
            router_abi = [
                {
                    "inputs": [
                        {"name": "amountIn", "type": "uint256"},
                        {"name": "path", "type": "address[]"}
                    ],
                    "name": "getAmountsOut",
                    "outputs": [{"name": "amounts", "type": "uint256[]"}],
                    "stateMutability": "view",
                    "type": "function"
                }
            ]
            
            router_address = self.w3.to_checksum_address(self.dex_routers["SUSHISWAP"])
            router_contract = self.w3.eth.contract(address=router_address, abi=router_abi)
            
            # ERC20 decimals ABI
            erc20_dec_abi = [
                {
                    "constant": True,
                    "inputs": [],
                    "name": "decimals",
                    "outputs": [{"name": "", "type": "uint8"}],
                    "payable": False,
                    "stateMutability": "view",
                    "type": "function",
                }
            ]

            # Fetch decimals dynamically
            token_in_dec = int(self.w3.eth.contract(address=token_in, abi=erc20_dec_abi).functions.decimals().call())
            token_out_dec = int(self.w3.eth.contract(address=token_out, abi=erc20_dec_abi).functions.decimals().call())

            # Convert amount to smallest units of token_in
            amount_in_wei = int(amount_in * (10 ** token_in_dec))
            
            # Path for swap - prefer deeper liquidity routes on Arbitrum
            path = [token_in, token_out]
            try:
                # Common case: WETH -> USDC has deeper liquidity via USDC.e on Sushi
                if token_in.lower() == self.tokens["WETH"].lower() and token_out.lower() == self.tokens["USDC"].lower():
                    usdc_e = self.tokens.get("USDC_E")
                    if usdc_e:
                        path = [token_in, usdc_e, token_out]
                # Reverse case (not used currently): USDC -> WETH via USDC.e
                elif token_in.lower() == self.tokens["USDC"].lower() and token_out.lower() == self.tokens["WETH"].lower():
                    usdc_e = self.tokens.get("USDC_E")
                    if usdc_e:
                        path = [token_in, usdc_e, token_out]
            except Exception:
                # If token symbols not in map, keep default direct path
                pass
            
            # Ensure checksummed path addresses
            path = [self.w3.to_checksum_address(a) for a in path]

            # Get amounts out
            amounts = router_contract.functions.getAmountsOut(amount_in_wei, path).call()
            
            # amounts[0] is input, amounts[1] is output
            amount_out_wei = amounts[1]
            
            # Convert output to human units using token_out decimals
            amount_out = amount_out_wei / (10 ** token_out_dec)
            
            # Calculate price
            price = amount_out / amount_in
            
            return PriceQuote(
                dex="SUSHISWAP",
                pool_address=router_address,
                token_in=token_in,
                token_out=token_out,
                amount_in=amount_in,
                amount_out=amount_out,
                price=price,
                timestamp=datetime.utcnow(),
                gas_estimate=180000,
                liquidity=500000  # Can't easily get from router
            )
        except Exception as e:
            err_msg = str(e)
            if is_rate_limit_error(e):
                print(f"⚠️  Sushiswap quote rate limited: 429")
                raise RpcRateLimitError(err_msg)
            print(f"Error getting Sushiswap quote: {e}")
            return None
    
    async def scan_arbitrage_opportunities(self, amount_usd: float = 1000) -> List[ArbitrageOpportunity]:
        """
        Scan all DEX pairs for arbitrage opportunities
        Returns list of profitable opportunities sorted by net profit
        """
        opportunities = []
        
        # Check WETH/USDC across DEXes (most liquid pair on Arbitrum)
        # Use dynamic amount based on MAX_POSITION_USD (default to smaller amount)
        eth_price_estimate = 3000  # Rough estimate for amount calculation
        amount_eth = min(amount_usd / eth_price_estimate, 0.5)
        
        token_pairs = [
            ("WETH", "USDC", amount_eth),  # Dynamic amount based on position size
        ]
        
        for token_in_symbol, token_out_symbol, amount_in in token_pairs:
            token_in = self.tokens.get(token_in_symbol)
            token_out = self.tokens.get(token_out_symbol)
            
            if not token_in or not token_out:
                continue
            
            # Get quotes from all DEXes
            quotes = {}
            
            # Uniswap V3 - try multiple fee tiers
            for fee_tier in ["0.05", "0.3"]:
                pool_key = f"{token_in_symbol}/{token_out_symbol}-{fee_tier}"
                univ3_pool = self.univ3_pools.get(pool_key)
                if univ3_pool:
                    try:
                        quote = await self.get_uniswap_v3_quote(
                            univ3_pool, token_in, token_out, amount_in
                        )
                        if quote:
                            quotes[f"UNISWAP_V3_{fee_tier}"] = quote
                    except Exception as e:
                        print(f"Failed to get Uniswap V3 quote ({fee_tier}%): {e}")
            
            # Sushiswap
            try:
                sushi_quote = await self.get_sushiswap_quote(token_in, token_out, amount_in)
                if sushi_quote:
                    quotes["SUSHISWAP"] = sushi_quote
            except Exception as e:
                print(f"Failed to get Sushiswap quote: {e}")
            
            # Compare all quote combinations
            quote_names = list(quotes.keys())
            for i in range(len(quote_names)):
                for j in range(i + 1, len(quote_names)):
                    dex1, dex2 = quote_names[i], quote_names[j]
                    quote1, quote2 = quotes[dex1], quotes[dex2]
                    
                    # Determine buy/sell direction
                    if quote1.price < quote2.price:
                        buy_dex, buy_quote = dex1, quote1
                        sell_dex, sell_quote = dex2, quote2
                    else:
                        buy_dex, buy_quote = dex2, quote2
                        sell_dex, sell_quote = dex1, quote1
                    
                    # Calculate spread
                    price_diff = sell_quote.price - buy_quote.price
                    profit_bps = int((price_diff / buy_quote.price) * 10000)
                    
                    # Skip if spread too small
                    if profit_bps < 3:  # Min 3 BPS (0.03%)
                        continue
                    
                    # Estimate gas cost
                    try:
                        gas_price_gwei = self.w3.eth.gas_price / 10**9
                    except:
                        gas_price_gwei = 0.01  # Fallback for Arbitrum
                    
                    gas_estimate = buy_quote.gas_estimate + sell_quote.gas_estimate
                    gas_cost_eth = (gas_estimate * gas_price_gwei) / 10**9
                    
                    # Get ETH price from buy_quote (WETH/USDC price)
                    eth_price_usd = buy_quote.price
                    gas_cost_usd = gas_cost_eth * eth_price_usd
                    
                    # Calculate profit
                    gross_profit_usd = amount_in * eth_price_usd * (profit_bps / 10000)
                    net_profit_usd = gross_profit_usd - gas_cost_usd
                    
                    # Only report if profitable after gas
                    # Use environment-configurable threshold (default low for discovery)
                    try:
                        min_net_profit = float(os.environ.get('FEED_MIN_NET_PROFIT_USD', os.environ.get('MIN_PROFIT_USD', '0.02')))
                    except Exception:
                        min_net_profit = 0.02
                    if net_profit_usd > min_net_profit:
                        # Determine execution priority
                        if profit_bps > 50:
                            priority = "CRITICAL"
                        elif profit_bps > 25:
                            priority = "HIGH"
                        elif profit_bps > 10:
                            priority = "MEDIUM"
                        else:
                            priority = "LOW"
                        
                        # Confidence based on liquidity
                        min_liquidity = min(buy_quote.liquidity, sell_quote.liquidity)
                        if min_liquidity > 100000:
                            confidence = 0.95
                        elif min_liquidity > 50000:
                            confidence = 0.85
                        elif min_liquidity > 10000:
                            confidence = 0.70
                        else:
                            confidence = 0.50
                        
                        opportunity = ArbitrageOpportunity(
                            buy_dex=buy_dex,
                            sell_dex=sell_dex,
                            token_path=[token_in_symbol, token_out_symbol],
                            buy_price=buy_quote.price,
                            sell_price=sell_quote.price,
                            profit_bps=profit_bps,
                            profit_usd=gross_profit_usd,
                            gas_cost_usd=gas_cost_usd,
                            net_profit_usd=net_profit_usd,
                            confidence=confidence,
                            timestamp=datetime.utcnow(),
                            execution_priority=priority
                        )
                        
                        opportunities.append(opportunity)
        
        # Sort by net profit descending
        opportunities.sort(key=lambda x: x.net_profit_usd, reverse=True)
        
        return opportunities
    
    async def monitor_loop(self, scan_interval_ms: int = 1000, max_position_usd: float = 25.0):
        """
        Main monitoring loop
        Scans for opportunities at specified interval
        With RPC rate limiting and backoff
        """
        self.running = True
        print(f"🔍 Starting price feed monitor on {self.chain}")
        print(f"Scan interval: {scan_interval_ms}ms")
        print(f"💰 Max position size: ${max_position_usd:.2f}")
        if self.rpc_backoff:
            print(f"🛡️  RPC protection: {self.rpc_backoff.max_consecutive_errors} error limit, {self.rpc_backoff.backoff_seconds}s backoff")
        
        scan_count = 0
        last_opportunity_count = 0
        
        # Create opportunity ledger file
        ledger_path = Path("logs") / "opportunity_ledger.log"
        ledger_path.parent.mkdir(exist_ok=True)
        
        while self.running:
            try:
                # Check if we need to back off due to RPC errors
                if self.rpc_backoff:
                    await self.rpc_backoff.maybe_backoff()
                
                # Scan for opportunities with dynamic position sizing
                opportunities = await self.scan_arbitrage_opportunities(amount_usd=max_position_usd)
                
                # Record success
                if self.rpc_backoff:
                    self.rpc_backoff.record_success()
                
                scan_count += 1
                
                # Log every scan to ledger
                timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                with open(ledger_path, "a", encoding="utf-8") as f:
                    f.write(f"\n{'='*80}\n")
                    f.write(f"🔍 SCAN #{scan_count} | {timestamp}\n")
                    f.write(f"{'='*80}\n")
                    if len(opportunities) > 0:
                        f.write(f"✅ Found {len(opportunities)} opportunities:\n\n")
                        for i, opp in enumerate(opportunities, 1):
                            f.write(f"  [{i}] {opp.buy_dex} → {opp.sell_dex}\n")
                            f.write(f"      Pair: {'/'.join(opp.token_path)}\n")
                            f.write(f"      Profit: ${opp.net_profit_usd:.4f} ({opp.profit_bps:.1f} bps)\n")
                            f.write(f"      Buy: ${opp.buy_price:.6f} | Sell: ${opp.sell_price:.6f}\n")
                            f.write(f"      Gas: ${opp.gas_cost_usd:.4f}\n\n")
                    else:
                        f.write("❌ No opportunities found (market quiet)\n")
                
                # Print every scan to console
                if len(opportunities) > 0:
                    last_opportunity_count = len(opportunities)
                    print(f"✅ Scan #{scan_count}: {len(opportunities)} opportunities | Ledger: {ledger_path}")
                elif scan_count % 10 == 0:
                    print(f"🔍 Scan #{scan_count}: 0 opportunities (market quiet)")
                
                # Notify callbacks (with MCP filtering)
                for opp in opportunities:
                    min_profit_filter = float(os.environ.get('MIN_PROFIT_USD', '0.02'))
                    if opp.net_profit_usd > min_profit_filter:
                        
                        # MCP Intelligence Analysis
                        mcp_approved = True
                        mcp_score = 50.0  # Neutral default
                        mcp_reasoning = "MCP disabled"
                        
                        if self.enable_mcp and self.mcp:
                            try:
                                # Update MCP price history
                                token_pair = f"{opp.token_path[0]}/{opp.token_path[1]}"
                                current_time = datetime.utcnow()
                                
                                # Track price as candlestick data
                                self.mcp.update_price_history(
                                    token_pair=token_pair,
                                    timestamp=current_time,
                                    open_price=opp.buy_price,
                                    high=max(opp.buy_price, opp.sell_price),
                                    low=min(opp.buy_price, opp.sell_price),
                                    close=opp.sell_price,
                                    volume=1000  # Placeholder
                                )
                                
                                # Analyze opportunity with MCP
                                signal: MarketSignal = await self.mcp.analyze_opportunity(
                                    token_pair=token_pair,
                                    buy_price=opp.buy_price,
                                    sell_price=opp.sell_price,
                                    spread_bps=opp.profit_bps
                                )
                                
                                mcp_score = signal.strength
                                mcp_reasoning = signal.reasoning[:80]  # Truncate
                                
                                # Get trade recommendation
                                mcp_approved = self.mcp.get_trade_recommendation(
                                    signal=signal,
                                    net_profit_usd=opp.net_profit_usd
                                )
                                
                                # SWARM INTELLIGENCE (if enabled)
                                swarm_decision = None
                                if self.enable_swarm and self.swarm and mcp_approved:
                                    try:
                                        # Build market context for swarm
                                        self.recent_spreads.append(opp.profit_bps)
                                        if len(self.recent_spreads) > 50:
                                            self.recent_spreads = self.recent_spreads[-50:]
                                        
                                        market_context = {
                                            'liquidity_score': min(opp.confidence, 1.0),
                                            'recent_spreads': self.recent_spreads,
                                            'gas_price_gwei': self.w3.eth.gas_price / 1e9,
                                            'network_congestion': 0.3,  # TODO: calculate from mempool
                                            'total_exposure_usd': self.total_exposure_usd,
                                            'max_position_usd': 3000,
                                            'current_drawdown_pct': -2.5,  # TODO: track actual
                                            'consecutive_losses': self.consecutive_losses,
                                            'volatility_score': 0.5,  # TODO: calculate
                                            'max_gas_gwei': 1.0,
                                            'expected_slippage_bps': 15
                                        }
                                        
                                        # Convert opp to dict for swarm
                                        opp_dict = {
                                            'profit_bps': opp.profit_bps,
                                            'net_profit_usd': opp.net_profit_usd,
                                            'buy_price': opp.buy_price,
                                            'sell_price': opp.sell_price,
                                            'gas_cost_usd': opp.gas_cost_usd,
                                            'priority': opp.execution_priority
                                        }
                                        
                                        swarm_decision = await self.swarm.evaluate_opportunity(opp_dict, market_context)
                                        
                                        # Override MCP with swarm consensus
                                        if swarm_decision.action == "EXECUTE":
                                            mcp_approved = True
                                            mcp_score = swarm_decision.confidence
                                            mcp_reasoning = f"SWARM: {swarm_decision.consensus_level:.0%} consensus"
                                        elif swarm_decision.action == "SKIP":
                                            mcp_approved = False
                                            mcp_reasoning = f"SWARM REJECT: {swarm_decision.dissenting_opinions[0] if swarm_decision.dissenting_opinions else 'Consensus'}'"
                                        elif swarm_decision.action == "WAIT":
                                            mcp_approved = False
                                            mcp_reasoning = f"SWARM CAUTION: {swarm_decision.consensus_level:.0%} consensus - mixed signals"
                                    
                                    except Exception as e:
                                        print(f"⚠️  Swarm analysis failed: {e}")
                                
                                # Log MCP/Swarm analysis
                                swarm_badge = "🐝" if swarm_decision else "🧠"

                                # Intel synthesis (log-only)
                                intel_badge = ""
                                if self.enable_intel:
                                    try:
                                        intel_text = (
                                            f"{opp.buy_dex}->{opp.sell_dex} {opp.profit_bps}bps, "
                                            f"net ${opp.net_profit_usd:.2f}, gas {self.w3.eth.gas_price/1e9:.3f} gwei, "
                                            f"liq_score {opp.confidence:.2f}"
                                        )
                                        intel_pkg = process_intelligence(intel_text)
                                        ai_weight = intel_pkg['integrations'][0]['trading_ai']['signal_weight'] if intel_pkg.get('integrations') else 0.5
                                        intel_id = intel_pkg['structural'].get('intel_id', '')
                                        intel_badge = f" | 🧩 {ai_weight:.2f} ID:{intel_id[-6:]}"
                                    except Exception as e:
                                        intel_badge = ""
                                        print(f"⚠️  Intel synthesis failed: {e}")
                                if mcp_approved:
                                    print(f"💰 OPPORTUNITY: {opp.buy_dex} → {opp.sell_dex} | "
                                          f"{opp.token_path[0]}/{opp.token_path[1]} | "
                                          f"Profit: {opp.profit_bps} BPS (${opp.net_profit_usd:.2f} net) | "
                                          f"Priority: {opp.execution_priority} | "
                                          f"{swarm_badge} {mcp_score:.1f}/100 ✅{intel_badge}")
                                else:
                                    print(f"⏭️  FILTERED: {opp.buy_dex} → {opp.sell_dex} | "
                                          f"{opp.profit_bps} BPS | "
                                          f"{swarm_badge} {mcp_score:.1f}/100 ❌ ({mcp_reasoning}){intel_badge}")
                            
                            except Exception as e:
                                print(f"⚠️  MCP analysis failed: {e} - Defaulting to APPROVE")
                                mcp_approved = True  # Fail open (allow trade if MCP breaks)
                        
                        else:
                            # No MCP - show basic opportunity
                            print(f"💰 OPPORTUNITY: {opp.buy_dex} → {opp.sell_dex} | "
                                  f"{opp.token_path[0]}/{opp.token_path[1]} | "
                                  f"Profit: {opp.profit_bps} BPS (${opp.net_profit_usd:.2f} net) | "
                                  f"Priority: {opp.execution_priority}")
                        
                        # Execute callbacks only if MCP approved
                        if mcp_approved:
                            for callback in self.opportunity_callbacks:
                                await callback(opp)
                
                # Wait before next scan
                await asyncio.sleep(scan_interval_ms / 1000)
            
            except RpcRateLimitError as e:
                if self.rpc_backoff:
                    should_backoff = self.rpc_backoff.record_error()
                    if should_backoff:
                        print(f"⚠️  RPC rate limit hit ({self.rpc_backoff.consecutive_errors} consecutive): {e}")
                        await self.rpc_backoff.maybe_backoff()
                    else:
                        print(f"⚠️  RPC rate limit ({self.rpc_backoff.consecutive_errors}/{self.rpc_backoff.max_consecutive_errors}): {e}")
                        await asyncio.sleep(scan_interval_ms / 1000)
                else:
                    print(f"⚠️  RPC rate limit: {e}")
                    await asyncio.sleep(scan_interval_ms / 1000)
            
            except RpcConnectionError as e:
                if self.rpc_backoff:
                    self.rpc_backoff.record_error()
                print(f"⚠️  RPC connection error: {e}")
                await asyncio.sleep(scan_interval_ms / 1000)
                
            except Exception as e:
                print(f"❌ Error in monitor loop: {e}")
                import traceback
                traceback.print_exc()
                await asyncio.sleep(5)
    
    def stop(self):
        """Stop monitoring loop"""
        self.running = False
        print("🛑 Stopping price feed monitor")


# Example usage and testing
async def example_opportunity_handler(opportunity: ArbitrageOpportunity):
    """Example callback when opportunity detected"""
    if opportunity.execution_priority in ["HIGH", "CRITICAL"]:
        print(f"⚡ EXECUTING: {opportunity.buy_dex} → {opportunity.sell_dex}")
        # Here you would call the execution engine
        # await execute_arbitrage(opportunity)

async def main():
    """Test the price feed"""
    # Initialize feed
    feed = DeFiPriceFeed(chain="ARBITRUM")
    
    # Register opportunity handler
    feed.register_opportunity_callback(example_opportunity_handler)
    
    # Start monitoring
    print("=" * 60)
    print("🚀 DeFi Price Feed - Aggressive Overnight Mode")
    print("=" * 60)
    
    try:
        await feed.monitor_loop(scan_interval_ms=2000)  # Scan every 2 seconds
    except KeyboardInterrupt:
        feed.stop()
        print("\n✅ Price feed stopped")

if __name__ == "__main__":
    asyncio.run(main())
