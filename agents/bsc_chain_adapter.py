"""
BSC Chain Adapter - Binance Smart Chain trading infrastructure
Loads DEXes, tokens, RPCs, and connects Hybrid Hunter to BSC
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from web3 import Web3
from datetime import datetime


class BSCChainAdapter:
    """Manages BSC chain infrastructure and price feeds"""
    
    def __init__(self, config_path: str = "config/bsc_config.json"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.web3 = None
        self.connected_rpc = None
        
        # DEX ABIs (simplified for getAmountsOut)
        self.router_abi = [
            {
                "constant": True,
                "inputs": [
                    {"name": "amountIn", "type": "uint256"},
                    {"name": "path", "type": "address[]"}
                ],
                "name": "getAmountsOut",
                "outputs": [{"name": "amounts", "type": "uint256[]"}],
                "payable": False,
                "stateMutability": "view",
                "type": "function"
            }
        ]
        
    def _load_config(self) -> Dict:
        """Load BSC configuration"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"BSC config not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            return json.load(f)
    
    def connect(self) -> bool:
        """Connect to BSC via public RPCs"""
        for rpc_url in self.config["rpc_endpoints"]:
            try:
                w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={'timeout': 10}))
                if w3.is_connected():
                    # Verify chain ID
                    chain_id = w3.eth.chain_id
                    if chain_id == self.config["chain_id"]:
                        self.web3 = w3
                        self.connected_rpc = rpc_url
                        latest_block = w3.eth.block_number
                        print(f"✅ Connected to BSC!")
                        print(f"   RPC: {rpc_url}")
                        print(f"   Chain ID: {chain_id}")
                        print(f"   Block: {latest_block:,}")
                        return True
                    else:
                        print(f"⚠️  Chain ID mismatch: expected {self.config['chain_id']}, got {chain_id}")
            except Exception as e:
                print(f"❌ RPC {rpc_url} failed: {e}")
                continue
        
        return False
    
    def get_token_price(self, token_address: str, dex_name: str, 
                        amount_in: float = 1.0) -> Optional[float]:
        """
        Get token price from specific DEX
        Returns price in USD (via USDC/USDT routing)
        """
        if not self.web3:
            return None
        
        dex_config = self.config["dexes"].get(dex_name)
        if not dex_config:
            return None
        
        router_address = dex_config["router"]
        
        try:
            router = self.web3.eth.contract(
                address=Web3.to_checksum_address(router_address),
                abi=self.router_abi
            )
            
            # Build path: token -> WBNB -> USDC
            token_addr = Web3.to_checksum_address(token_address)
            wbnb_addr = Web3.to_checksum_address(self.config["major_tokens"]["WBNB"])
            usdc_addr = Web3.to_checksum_address(self.config["stablecoins"]["USDC"])
            
            # Handle native token (WBNB)
            if token_address.lower() == self.config["major_tokens"]["WBNB"].lower():
                path = [token_addr, usdc_addr]
            else:
                path = [token_addr, wbnb_addr, usdc_addr]
            
            # Convert amount to wei (assuming 18 decimals)
            amount_in_wei = int(amount_in * 10**18)
            
            # Get amounts out
            amounts = router.functions.getAmountsOut(amount_in_wei, path).call()
            
            # Last amount is USDC output (18 decimals on BSC)
            usdc_out = amounts[-1] / 10**18
            
            # Price = USDC out / amount in
            price = usdc_out / amount_in
            
            return price
            
        except Exception as e:
            # Silent fail for individual price queries
            return None
    
    def get_all_prices(self, token_symbols: List[str] = None) -> Dict[str, Dict[str, float]]:
        """
        Get prices for all tokens across all DEXes
        Returns: {dex_name: {pair: price}}
        """
        if token_symbols is None:
            token_symbols = ["WBNB", "ETH", "BTCB", "CAKE", "XRP", "ADA"]
        
        # Skip MDEX - has stale price feeds
        skip_dexes = ["MDEX"]
        
        prices = {}
        
        for dex_name in self.config["dexes"].keys():
            if dex_name in skip_dexes:
                continue
            prices[dex_name] = {}
            
            for symbol in token_symbols:
                if symbol not in self.config["major_tokens"]:
                    continue
                
                token_address = self.config["major_tokens"][symbol]
                price = self.get_token_price(token_address, dex_name)
                
                if price is not None:
                    pair = f"{symbol}/USDC"
                    prices[dex_name][pair] = price
        
        return prices
    
    def get_stablecoin_prices(self) -> Dict[str, Dict[str, float]]:
        """
        Get stablecoin prices across all DEXes
        Returns: {stable_name: {dex_name: price}}
        """
        # Skip MDEX - has stale price feeds
        skip_dexes = ["MDEX"]
        
        stables = {}
        
        for stable, token_address in self.config["stablecoins"].items():
            stables[stable] = {}
            
            for dex_name in self.config["dexes"].keys():
                if dex_name in skip_dexes:
                    continue
                price = self.get_token_price(token_address, dex_name)
                if price is not None:
                    stables[stable][dex_name] = price
        
        return stables
    
    def build_market_data(self) -> Dict:
        """
        Build market data structure for Hybrid Hunter
        """
        prices = self.get_all_prices()
        stables = self.get_stablecoin_prices()
        
        # Extract unique pairs
        pairs = set()
        for dex_prices in prices.values():
            pairs.update(dex_prices.keys())
        
        return {
            "prices": prices,
            "stables": stables,
            "pairs": list(pairs),
            "timestamp": datetime.utcnow(),
            "chain": "BSC",
            "block": self.web3.eth.block_number if self.web3 else None
        }
    
    def get_gas_price(self) -> float:
        """Get current gas price in Gwei"""
        if not self.web3:
            return 5.0  # Default
        
        try:
            gas_wei = self.web3.eth.gas_price
            gas_gwei = gas_wei / 10**9
            return min(gas_gwei, self.config["gas_config"]["max_gas_gwei"])
        except:
            return 5.0
    
    def estimate_gas_cost_usd(self, num_txs: int = 2) -> float:
        """
        Estimate gas cost in USD
        num_txs: number of transactions (2 for buy+sell)
        """
        # Use config's average gas cost
        return self.config["gas_config"]["average_tx_cost_usd"] * num_txs
    
    def check_wallet_balance(self, wallet_address: str) -> Dict[str, float]:
        """Check wallet balances on BSC"""
        if not self.web3:
            return {}
        
        try:
            addr = Web3.to_checksum_address(wallet_address)
            
            # BNB balance
            bnb_wei = self.web3.eth.get_balance(addr)
            bnb_balance = bnb_wei / 10**18
            
            # Get BNB price
            bnb_price = self.get_token_price(
                self.config["wrapped_native"],
                "pancakeswap_v2"
            ) or 250.0
            
            return {
                "BNB": bnb_balance,
                "USD_value": bnb_balance * bnb_price,
                "sufficient_for_trading": bnb_balance > 0.01  # Need gas
            }
        except Exception as e:
            print(f"❌ Error checking balance: {e}")
            return {}


# Quick test
if __name__ == "__main__":
    print("🌐 BSC Chain Adapter - Initialization Test")
    print("=" * 60)
    
    adapter = BSCChainAdapter()
    
    # Connect to BSC
    if adapter.connect():
        print(f"\n📊 Gas Price: {adapter.get_gas_price():.2f} Gwei")
        print(f"💰 Estimated Gas Cost: ${adapter.estimate_gas_cost_usd():.4f}")
        
        # Check wallet (use environment variable)
        wallet = os.environ.get("WALLET_ADDRESS")
        if wallet:
            print(f"\n👛 Wallet Balance:")
            balance = adapter.check_wallet_balance(wallet)
            for key, value in balance.items():
                print(f"   {key}: {value}")
        
        # Sample price check
        print(f"\n💵 Sample Prices:")
        wbnb_price = adapter.get_token_price(adapter.config["major_tokens"]["WBNB"], "PancakeSwap_V2")
        if wbnb_price:
            print(f"   WBNB: ${wbnb_price:.2f}")
        else:
            print(f"   WBNB: Price fetch failed (may need liquidity or correct path)")
        
        print(f"\n✅ BSC adapter ready for trading!")
    else:
        print(f"\n❌ Failed to connect to BSC")
