#!/usr/bin/env python3
"""Real on-chain DEX scanner - reads actual prices from Arbitrum DEXes."""

import os
from web3 import Web3
from decimal import Decimal
from dataclasses import dataclass
from typing import List, Optional
import asyncio

@dataclass
class RealArbitrageOpportunity:
    """Real arbitrage opportunity from on-chain data."""
    token_pair: str
    buy_dex: str
    sell_dex: str
    buy_price: Decimal
    sell_price: Decimal
    spread_bps: int
    buy_pool_address: str
    sell_pool_address: str
    estimated_profit_usd: Decimal
    token0_address: str
    token1_address: str
    buy_liquidity: Decimal
    sell_liquidity: Decimal

class RealDEXScanner:
    """Scans actual Arbitrum DEXes for real arbitrage opportunities."""
    
    # Uniswap V3 Factory on Arbitrum
    UNISWAP_V3_FACTORY = "0x1F98431c8aD98523631AE4a59f267346ea31F984"
    
    # Sushiswap V2 Factory on Arbitrum  
    SUSHISWAP_FACTORY = "0xc35DADB65012eC5796536bD9864eD8773aBc74C4"
    
    # Token addresses on Arbitrum
    TOKENS = {
        "USDC": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",  # Native USDC
        "WETH": "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",
        "ARB": "0x912CE59144191C1204E64559FE8253a0e49E6548",
        "WBTC": "0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f",
    }
    
    # Uniswap V3 Pool ABI (minimal - just what we need)
    POOL_ABI = [
        {"inputs": [], "name": "token0", "outputs": [{"type": "address"}], "stateMutability": "view", "type": "function"},
        {"inputs": [], "name": "token1", "outputs": [{"type": "address"}], "stateMutability": "view", "type": "function"},
        {"inputs": [], "name": "slot0", "outputs": [
            {"type": "uint160", "name": "sqrtPriceX96"},
            {"type": "int24", "name": "tick"},
            {"type": "uint16", "name": "observationIndex"},
            {"type": "uint16", "name": "observationCardinality"},
            {"type": "uint16", "name": "observationCardinalityNext"},
            {"type": "uint8", "name": "feeProtocol"},
            {"type": "bool", "name": "unlocked"}
        ], "stateMutability": "view", "type": "function"},
        {"inputs": [], "name": "liquidity", "outputs": [{"type": "uint128"}], "stateMutability": "view", "type": "function"}
    ]
    
    # Uniswap V3 Factory ABI
    FACTORY_ABI = [
        {"inputs": [
            {"type": "address", "name": "tokenA"},
            {"type": "address", "name": "tokenB"},
            {"type": "uint24", "name": "fee"}
        ], "name": "getPool", "outputs": [{"type": "address", "name": "pool"}], "stateMutability": "view", "type": "function"}
    ]
    
    def __init__(self, w3: Web3):
        self.w3 = w3
        self.uniswap_factory = w3.eth.contract(
            address=self.UNISWAP_V3_FACTORY,
            abi=self.FACTORY_ABI
        )
        
    async def get_uniswap_v3_price(self, token0: str, token1: str, fee: int = 3000) -> Optional[tuple]:
        """Get real price from Uniswap V3 pool.
        
        Args:
            token0: First token address
            token1: Second token address  
            fee: Pool fee tier (3000 = 0.3%, 500 = 0.05%, 10000 = 1%)
            
        Returns:
            (price, liquidity, pool_address) or None
        """
        try:
            pool_address = self.uniswap_factory.functions.getPool(
                token0, token1, fee
            ).call()
            
            if pool_address == "0x0000000000000000000000000000000000000000":
                return None
                
            pool = self.w3.eth.contract(address=pool_address, abi=self.POOL_ABI)
            
            # Get sqrt price from slot0
            slot0 = pool.functions.slot0().call()
            sqrt_price_x96 = slot0[0]
            
            # Convert sqrtPriceX96 to actual price
            # price = (sqrtPriceX96 / 2^96)^2
            price = (sqrt_price_x96 / (2**96)) ** 2
            
            # Get liquidity
            liquidity = pool.functions.liquidity().call()
            
            return (Decimal(str(price)), Decimal(str(liquidity)), pool_address)
            
        except Exception as e:
            print(f"Error getting Uniswap price for {token0[:6]}/{token1[:6]}: {e}")
            return None
    
    async def scan_pair(self, token0_name: str, token1_name: str, capital_usd: Decimal) -> List[RealArbitrageOpportunity]:
        """Scan a token pair across multiple DEXes for arbitrage.
        
        Args:
            token0_name: First token symbol (e.g. "WETH")
            token1_name: Second token symbol (e.g. "USDC")
            capital_usd: Trading capital in USD
            
        Returns:
            List of profitable arbitrage opportunities
        """
        token0 = self.TOKENS[token0_name]
        token1 = self.TOKENS[token1_name]
        
        opportunities = []
        
        # Get prices from different fee tiers on Uniswap V3
        uni_005 = await self.get_uniswap_v3_price(token0, token1, 500)  # 0.05%
        uni_030 = await self.get_uniswap_v3_price(token0, token1, 3000)  # 0.3%
        uni_100 = await self.get_uniswap_v3_price(token0, token1, 10000)  # 1%
        
        pools = []
        if uni_005:
            pools.append(("Uniswap_V3_0.05%", uni_005[0], uni_005[1], uni_005[2]))
        if uni_030:
            pools.append(("Uniswap_V3_0.3%", uni_030[0], uni_030[1], uni_030[2]))
        if uni_100:
            pools.append(("Uniswap_V3_1%", uni_100[0], uni_100[1], uni_100[2]))
            
        # Compare all pool pairs for arbitrage
        for i, (dex1, price1, liq1, addr1) in enumerate(pools):
            for dex2, price2, liq2, addr2 in pools[i+1:]:
                if price1 == 0 or price2 == 0:
                    continue
                    
                # Calculate spread
                if price1 < price2:
                    buy_dex, buy_price, buy_liq, buy_addr = dex1, price1, liq1, addr1
                    sell_dex, sell_price, sell_liq, sell_addr = dex2, price2, liq2, addr2
                else:
                    buy_dex, buy_price, buy_liq, buy_addr = dex2, price2, liq2, addr2
                    sell_dex, sell_price, sell_liq, sell_addr = dex1, price1, liq1, addr1
                
                spread = ((sell_price - buy_price) / buy_price) * 10000  # in BPS
                
                # Minimum 5 BPS spread to be profitable after fees
                if spread >= 5:
                    # Estimate profit (simplified)
                    estimated_profit = capital_usd * (spread / 10000) * Decimal("0.85")  # 15% slippage buffer
                    
                    opportunities.append(RealArbitrageOpportunity(
                        token_pair=f"{token0_name}/{token1_name}",
                        buy_dex=buy_dex,
                        sell_dex=sell_dex,
                        buy_price=buy_price,
                        sell_price=sell_price,
                        spread_bps=int(spread),
                        buy_pool_address=buy_addr,
                        sell_pool_address=sell_addr,
                        estimated_profit_usd=estimated_profit,
                        token0_address=token0,
                        token1_address=token1,
                        buy_liquidity=buy_liq,
                        sell_liquidity=sell_liq
                    ))
        
        return opportunities
    
    async def scan_all_pairs(self, capital_usd: Decimal) -> List[RealArbitrageOpportunity]:
        """Scan all token pairs for arbitrage opportunities.
        
        Args:
            capital_usd: Trading capital in USD
            
        Returns:
            List of all profitable opportunities sorted by profit
        """
        all_opportunities = []
        
        # Scan major pairs
        pairs = [
            ("WETH", "USDC"),
            ("ARB", "USDC"),
            ("WBTC", "USDC"),
            ("WETH", "ARB"),
        ]
        
        for token0, token1 in pairs:
            try:
                opps = await self.scan_pair(token0, token1, capital_usd)
                all_opportunities.extend(opps)
            except Exception as e:
                print(f"Error scanning {token0}/{token1}: {e}")
        
        # Sort by estimated profit
        all_opportunities.sort(key=lambda x: x.estimated_profit_usd, reverse=True)
        
        return all_opportunities


async def main():
    """Test the real DEX scanner."""
    from dotenv import load_dotenv
    load_dotenv()
    
    # Connect to Arbitrum
    w3 = Web3(Web3.HTTPProvider("https://arb1.arbitrum.io/rpc"))
    print(f"Connected to Arbitrum: {w3.is_connected()}")
    print(f"Block: {w3.eth.block_number}\n")
    
    scanner = RealDEXScanner(w3)
    
    print("🔍 Scanning real Arbitrum DEXes for arbitrage...\n")
    opportunities = await scanner.scan_all_pairs(Decimal("29"))
    
    if opportunities:
        print(f"✅ Found {len(opportunities)} opportunities:\n")
        for opp in opportunities[:5]:  # Show top 5
            print(f"  {opp.token_pair} | {opp.buy_dex} → {opp.sell_dex}")
            print(f"  Spread: {opp.spread_bps} BPS | Profit: ${opp.estimated_profit_usd:.2f}")
            print(f"  Buy: {opp.buy_pool_address[:10]}... @ {opp.buy_price:.6f}")
            print(f"  Sell: {opp.sell_pool_address[:10]}... @ {opp.sell_price:.6f}\n")
    else:
        print("❌ No profitable opportunities found")


if __name__ == "__main__":
    asyncio.run(main())
