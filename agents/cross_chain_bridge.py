"""
Cross-Chain Bridge Module
Integrated bridge for moving assets between chains (Polygon → Arbitrum, etc.)
Built-in to trading system for seamless multi-chain operations
"""

import asyncio
import time
import logging
from typing import Dict, List, Optional, Tuple
from web3 import Web3
from decimal import Decimal
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CrossChainBridge:
    """
    Multi-chain bridge integration
    
    Supports:
    - Polygon → Arbitrum (USDC, WETH, POL)
    - Ethereum → Arbitrum (USDC, WETH)
    - Optimism → Arbitrum (USDC, WETH)
    - Base → Arbitrum (USDC, WETH)
    
    Uses Hop Protocol for fast bridging (5-10 minutes)
    """
    
    # Supported chains
    CHAINS = {
        "ethereum": {
            "chain_id": 1,
            "name": "Ethereum",
            "rpc": "https://eth.llamarpc.com",
            "hop_bridge": "0x3666f603Cc164936C1b87e207F36BEBa4AC5f18a",  # USDC
        },
        "polygon": {
            "chain_id": 137,
            "name": "Polygon",
            "rpc": "https://polygon-rpc.com",
            "hop_bridge": "0x25D8039bB044dC227f741a9e381CA4cEAE2E6aE8",  # USDC
        },
        "arbitrum": {
            "chain_id": 42161,
            "name": "Arbitrum",
            "rpc": "https://arb1.arbitrum.io/rpc",
            "hop_bridge": "0x0e0E3d2C5c292161999474247956EF542caBF8dd",  # USDC
        },
        "optimism": {
            "chain_id": 10,
            "name": "Optimism",
            "rpc": "https://mainnet.optimism.io",
            "hop_bridge": "0x3c0FFAca566fCcfD9Cc95139FEF6CBA143795963",  # USDC
        },
        "base": {
            "chain_id": 8453,
            "name": "Base",
            "rpc": "https://mainnet.base.org",
            "hop_bridge": "0xe22D2beDb3Eca35E6397e0C6D62857094aA26F52",  # USDC
        }
    }
    
    # Token addresses per chain
    TOKENS = {
        "USDC": {
            "ethereum": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            "polygon": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",
            "arbitrum": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
            "optimism": "0x7F5c764cBc14f9669B88837ca1490cCa17c31607",
            "base": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            "decimals": 6,
        },
        "WETH": {
            "ethereum": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "polygon": "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619",
            "arbitrum": "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",
            "optimism": "0x4200000000000000000000000000000000000006",
            "base": "0x4200000000000000000000000000000000000006",
            "decimals": 18,
        },
        "POL": {  # Polygon native token
            "polygon": "0x0000000000000000000000000000000000001010",
            "decimals": 18,
        }
    }
    
    def __init__(self, wallet_address: str, wallet_private_key: str):
        self.wallet_address = wallet_address
        self.wallet_private_key = wallet_private_key
        
        # Initialize Web3 connections for each chain
        self.w3_connections = {}
        for chain, config in self.CHAINS.items():
            self.w3_connections[chain] = Web3(Web3.HTTPProvider(config["rpc"]))
        
        logger.info(
            f"✓ Cross-chain bridge initialized\n"
            f"  Wallet: {wallet_address}\n"
            f"  Chains: {len(self.CHAINS)} supported"
        )
    
    def get_balance(self, chain: str, token: str) -> Tuple[float, str]:
        """
        Get token balance on a specific chain
        
        Args:
            chain: Chain name (ethereum, polygon, arbitrum, etc.)
            token: Token symbol (USDC, WETH, POL)
            
        Returns:
            (balance, formatted_string)
        """
        try:
            if chain not in self.CHAINS:
                raise ValueError(f"Unsupported chain: {chain}")
            
            if token not in self.TOKENS:
                raise ValueError(f"Unsupported token: {token}")
            
            w3 = self.w3_connections[chain]
            token_config = self.TOKENS[token]
            
            if chain not in token_config:
                return (0.0, f"0.00 {token} (not available on {chain})")
            
            token_address = token_config[chain]
            decimals = token_config["decimals"]
            
            # Handle native tokens (POL)
            if token == "POL" and chain == "polygon":
                balance_wei = w3.eth.get_balance(self.wallet_address)
                balance = float(w3.from_wei(balance_wei, 'ether'))
                return (balance, f"{balance:.4f} POL")
            
            # ERC20 tokens
            erc20_abi = [
                {
                    "constant": True,
                    "inputs": [{"name": "_owner", "type": "address"}],
                    "name": "balanceOf",
                    "outputs": [{"name": "balance", "type": "uint256"}],
                    "type": "function"
                }
            ]
            
            contract = w3.eth.contract(
                address=Web3.to_checksum_address(token_address),
                abi=erc20_abi
            )
            
            balance_raw = contract.functions.balanceOf(
                Web3.to_checksum_address(self.wallet_address)
            ).call()
            
            balance = balance_raw / (10 ** decimals)
            
            return (balance, f"{balance:.4f} {token}")
        
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            return (0.0, f"0.00 {token} (error)")
    
    def get_all_balances(self) -> Dict[str, Dict[str, float]]:
        """
        Get all token balances across all chains
        
        Returns:
            {
                "ethereum": {"USDC": 100.5, "WETH": 0.05},
                "polygon": {"USDC": 32.0, "WETH": 0.01, "POL": 5.0},
                ...
            }
        """
        balances = {}
        
        print("\n" + "="*60)
        print("🌐 CROSS-CHAIN BALANCE CHECK")
        print("="*60)
        
        for chain in self.CHAINS.keys():
            balances[chain] = {}
            print(f"\n{self.CHAINS[chain]['name']}:")
            
            for token in self.TOKENS.keys():
                # Skip tokens not available on this chain
                if chain not in self.TOKENS[token]:
                    continue
                
                balance, formatted = self.get_balance(chain, token)
                balances[chain][token] = balance
                
                if balance > 0:
                    print(f"  ✓ {formatted}")
        
        print("\n" + "="*60 + "\n")
        
        return balances
    
    async def estimate_bridge_cost(
        self,
        from_chain: str,
        to_chain: str,
        token: str,
        amount: float
    ) -> Dict:
        """
        Estimate bridge cost and time using Hop Protocol API
        
        Returns:
            {
                "fee_usd": 1.25,
                "estimated_time_minutes": 10,
                "amount_received": 30.75,
                "fee_percentage": 4.0
            }
        """
        try:
            # Hop Protocol API endpoint
            hop_api = "https://api.hop.exchange/v1/quote"
            
            # Convert amount to token units
            decimals = self.TOKENS[token]["decimals"]
            amount_raw = int(amount * (10 ** decimals))
            
            params = {
                "amount": str(amount_raw),
                "token": token,
                "fromChainId": self.CHAINS[from_chain]["chain_id"],
                "toChainId": self.CHAINS[to_chain]["chain_id"],
                "slippage": "0.5",  # 0.5%
            }
            
            response = requests.get(hop_api, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Parse response
                total_fee = float(data.get("totalFee", 0)) / (10 ** decimals)
                amount_out = float(data.get("amountOut", 0)) / (10 ** decimals)
                estimated_time = data.get("estimatedTime", 600)  # seconds
                
                fee_percentage = (total_fee / amount) * 100 if amount > 0 else 0
                
                return {
                    "fee_usd": total_fee,
                    "estimated_time_minutes": estimated_time / 60,
                    "amount_received": amount_out,
                    "fee_percentage": fee_percentage,
                    "success": True
                }
            else:
                # Fallback estimates if API fails
                return {
                    "fee_usd": amount * 0.03,  # ~3% estimate
                    "estimated_time_minutes": 10,
                    "amount_received": amount * 0.97,
                    "fee_percentage": 3.0,
                    "success": False,
                    "note": "Estimated (API unavailable)"
                }
        
        except Exception as e:
            logger.warning(f"Could not get bridge quote: {e}")
            
            # Return conservative estimates
            return {
                "fee_usd": amount * 0.05,  # 5% conservative
                "estimated_time_minutes": 15,
                "amount_received": amount * 0.95,
                "fee_percentage": 5.0,
                "success": False,
                "note": "Conservative estimate"
            }
    
    def generate_bridge_instructions(
        self,
        from_chain: str,
        to_chain: str,
        token: str,
        amount: float
    ) -> str:
        """
        Generate step-by-step bridge instructions for user
        
        Returns formatted instructions string
        """
        instructions = f"""
╔══════════════════════════════════════════════════════════════╗
║  BRIDGE INSTRUCTIONS: {token} from {from_chain.upper()} → {to_chain.upper()}
╚══════════════════════════════════════════════════════════════╝

Amount to Bridge: {amount:.4f} {token}

STEP 1: Go to Hop Protocol
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
URL: https://app.hop.exchange

STEP 2: Connect Your Wallet
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Click "Connect Wallet"
- Select MetaMask
- Approve connection
- Make sure you're on {from_chain.upper()} network

STEP 3: Configure Bridge
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
From:   {self.CHAINS[from_chain]["name"]}
To:     {self.CHAINS[to_chain]["name"]}
Token:  {token}
Amount: {amount:.4f}

STEP 4: Review & Send
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Check estimated fee and time
- Click "Send"
- Confirm transaction in MetaMask

STEP 5: Wait for Bridge
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Estimated Time: 5-15 minutes
Track progress: https://app.hop.exchange/transactions

STEP 6: Switch Network in MetaMask
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Click network dropdown in MetaMask
- Select "{self.CHAINS[to_chain]["name"]}"
- Your {token} should appear after bridge completes

✓ DONE! Your {token} is now on {to_chain.upper()} and ready to trade.

"""
        return instructions
    
    async def interactive_bridge_setup(self):
        """
        Interactive CLI for setting up bridge transfers
        Guides user through the process
        """
        print("\n" + "="*60)
        print("🌉 CROSS-CHAIN BRIDGE SETUP")
        print("="*60)
        
        # Step 1: Show current balances
        print("\n📊 Current Balances:")
        balances = self.get_all_balances()
        
        # Step 2: Ask what they want to bridge
        print("\n" + "="*60)
        print("What do you want to bridge to Arbitrum?")
        print("="*60)
        
        bridge_options = []
        option_num = 1
        
        for chain, chain_balances in balances.items():
            if chain == "arbitrum":
                continue  # Skip Arbitrum (we're bridging TO it)
            
            for token, balance in chain_balances.items():
                if balance > 0:
                    bridge_options.append({
                        "number": option_num,
                        "chain": chain,
                        "token": token,
                        "balance": balance
                    })
                    print(
                        f"{option_num}. {balance:.4f} {token} "
                        f"from {self.CHAINS[chain]['name']}"
                    )
                    option_num += 1
        
        if not bridge_options:
            print("\n⚠️  No assets found to bridge. Fund a wallet first.")
            return
        
        print(f"{option_num}. Cancel")
        print("="*60)
        
        # For automation, just show the first viable option
        if bridge_options:
            selected = bridge_options[0]
            
            print(f"\n✓ Recommended: Bridge {selected['token']} from {selected['chain']}")
            
            # Estimate costs
            estimate = await self.estimate_bridge_cost(
                selected['chain'],
                'arbitrum',
                selected['token'],
                selected['balance']
            )
            
            print(f"\n💰 Bridge Estimate:")
            print(f"  Amount to bridge: {selected['balance']:.4f} {selected['token']}")
            print(f"  Bridge fee: ~{estimate['fee_usd']:.4f} {selected['token']} ({estimate['fee_percentage']:.2f}%)")
            print(f"  You'll receive: ~{estimate['amount_received']:.4f} {selected['token']}")
            print(f"  Estimated time: ~{estimate['estimated_time_minutes']:.0f} minutes")
            
            if not estimate['success']:
                print(f"  Note: {estimate.get('note', 'Estimated values')}")
            
            # Generate instructions
            instructions = self.generate_bridge_instructions(
                selected['chain'],
                'arbitrum',
                selected['token'],
                selected['balance']
            )
            
            print(instructions)
            
            # Save instructions to file
            instructions_file = "bridge_instructions.txt"
            with open(instructions_file, 'w') as f:
                f.write(instructions)
            
            print(f"✓ Instructions saved to: {instructions_file}")
            print("\nFollow these steps to bridge your assets to Arbitrum.")
            print("Once complete, run the bot with: python micro_capital_engine.py")


async def main():
    """Demo: Show cross-chain balances and bridge setup"""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    wallet_address = os.getenv('WALLET_ADDRESS')
    wallet_private_key = os.getenv('WALLET_PRIVATE_KEY')
    
    if not wallet_address or not wallet_private_key:
        print("⚠️  Set WALLET_ADDRESS and WALLET_PRIVATE_KEY in .env file")
        return
    
    bridge = CrossChainBridge(wallet_address, wallet_private_key)
    
    # Show balances across all chains
    balances = bridge.get_all_balances()
    
    # Interactive bridge setup
    await bridge.interactive_bridge_setup()


if __name__ == "__main__":
    asyncio.run(main())
