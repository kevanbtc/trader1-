"""
Multi-DEX Adapter for Arbitrum
Expands scanning to 9 DEXes simultaneously
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional
from web3 import Web3

class MultiDexAdapter:
    """Adapter to scan multiple DEX protocols on Arbitrum"""
    
    def __init__(self, w3: Web3):
        self.w3 = w3
        self.config = self._load_config()
        self.enabled_dexes = self._get_enabled_dexes()
        
    def _load_config(self) -> dict:
        """Load DEX ecosystem configuration"""
        config_path = Path(__file__).parent.parent / 'config' / 'dex_ecosystem.json'
        if config_path.exists():
            with open(config_path, 'r') as f:
                return json.load(f)
        return {}
    
    def _get_enabled_dexes(self) -> List[str]:
        """Get list of enabled DEXes from environment and config"""
        enabled = []
        ecosystem = self.config.get('arbitrum_dex_ecosystem', {})
        
        for dex_name, dex_config in ecosystem.items():
            # Check if explicitly enabled in config
            if dex_config.get('enabled', False):
                # Check environment override
                env_key = f"ENABLE_{dex_name.upper().replace('_', '')}"
                if os.getenv(env_key, 'true').lower() == 'true':
                    enabled.append(dex_name)
        
        return enabled
    
    def get_dex_config(self, dex_name: str) -> Optional[dict]:
        """Get configuration for specific DEX"""
        ecosystem = self.config.get('arbitrum_dex_ecosystem', {})
        return ecosystem.get(dex_name)
    
    def get_all_pool_addresses(self) -> Dict[str, List[str]]:
        """Get all pool addresses across enabled DEXes"""
        pools = {}
        
        for dex in self.enabled_dexes:
            config = self.get_dex_config(dex)
            if not config:
                continue
            
            dex_pools = self._fetch_pools_for_dex(dex, config)
            if dex_pools:
                pools[dex] = dex_pools
        
        return pools
    
    def _fetch_pools_for_dex(self, dex_name: str, config: dict) -> List[str]:
        """Fetch pool addresses for specific DEX"""
        # For now, return known pools from config
        # TODO: Query factory contracts to discover new pools
        
        if dex_name == 'curve':
            return list(config.get('pools', {}).values())
        
        # Return empty for now - will be populated by factory queries
        return []
    
    def get_quote_from_dex(self, dex_name: str, pool_address: str, 
                          token_in: str, token_out: str, amount_in: int) -> Optional[dict]:
        """Get quote from specific DEX pool"""
        config = self.get_dex_config(dex_name)
        if not config:
            return None
        
        # Route to appropriate quoter based on DEX type
        if 'uniswap' in dex_name or 'camelot_v3' in dex_name:
            return self._get_v3_quote(pool_address, token_in, amount_in, config)
        elif dex_name == 'balancer_v2':
            return self._get_balancer_quote(pool_address, token_in, token_out, amount_in, config)
        elif dex_name == 'kyberswap_elastic':
            return self._get_kyber_quote(pool_address, token_in, amount_in, config)
        else:
            return self._get_v2_quote(pool_address, token_in, token_out, amount_in, config)
    
    def _get_v3_quote(self, pool: str, token_in: str, amount_in: int, config: dict) -> Optional[dict]:
        """Get quote from Uniswap V3 style pool"""
        try:
            quoter_address = config.get('quoter')
            if not quoter_address:
                return None
            
            # Simplified - in production would call quoter contract
            return {
                'dex': 'v3_style',
                'pool': pool,
                'amount_out': 0,  # TODO: actual quote
                'gas_estimate': 150000
            }
        except Exception:
            return None
    
    def _get_v2_quote(self, pool: str, token_in: str, token_out: str, 
                     amount_in: int, config: dict) -> Optional[dict]:
        """Get quote from Uniswap V2 style pool"""
        try:
            # Get reserves from pool
            pool_contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(pool),
                abi=[{
                    "constant": True,
                    "inputs": [],
                    "name": "getReserves",
                    "outputs": [
                        {"name": "reserve0", "type": "uint112"},
                        {"name": "reserve1", "type": "uint112"},
                        {"name": "blockTimestampLast", "type": "uint32"}
                    ],
                    "type": "function"
                }]
            )
            
            reserves = pool_contract.functions.getReserves().call()
            reserve_in = reserves[0]
            reserve_out = reserves[1]
            
            # Calculate output using constant product formula
            fee = config.get('fee', 3000)
            amount_in_with_fee = amount_in * (10000 - fee // 10)
            numerator = amount_in_with_fee * reserve_out
            denominator = (reserve_in * 10000) + amount_in_with_fee
            amount_out = numerator // denominator
            
            return {
                'dex': 'v2_style',
                'pool': pool,
                'amount_out': amount_out,
                'gas_estimate': 120000
            }
        except Exception:
            return None
    
    def _get_balancer_quote(self, pool: str, token_in: str, token_out: str,
                           amount_in: int, config: dict) -> Optional[dict]:
        """Get quote from Balancer V2 pool"""
        # Balancer uses vault-based swaps - would query vault for swap preview
        return None
    
    def _get_kyber_quote(self, pool: str, token_in: str, amount_in: int, 
                        config: dict) -> Optional[dict]:
        """Get quote from KyberSwap Elastic pool"""
        # Similar to Uni V3 but with different tick math
        return None
    
    def get_scanning_priority(self) -> List[str]:
        """Get DEXes sorted by scanning priority"""
        priorities = []
        for dex in self.enabled_dexes:
            config = self.get_dex_config(dex)
            if config:
                priority = config.get('priority', 999)
                priorities.append((dex, priority))
        
        priorities.sort(key=lambda x: x[1])
        return [dex for dex, _ in priorities]
    
    def get_total_venues(self) -> int:
        """Get total number of enabled trading venues"""
        return len(self.enabled_dexes)
    
    def print_status(self):
        """Print enabled DEX status"""
        print(f"\n🔍 Multi-DEX Scanner Active")
        print(f"📊 Scanning {len(self.enabled_dexes)} venues:")
        
        for dex in self.get_scanning_priority():
            config = self.get_dex_config(dex)
            priority = config.get('priority', '?')
            print(f"   [{priority}] {dex.replace('_', ' ').title()}")
