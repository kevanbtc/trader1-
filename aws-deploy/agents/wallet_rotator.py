"""
Wallet Rotation System for MEV Protection
Rotates across EOA1-4 every 7-15 minutes to avoid MEV sniper pattern detection
Each wallet has independent gas funding and nonce sequencing

Used by: live_engine.py, flashbots_executor.py
Prevents: MEV snipers from tracking profitable wallet patterns
"""

import time
import random
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from web3 import Web3
from eth_account import Account
from eth_account.signers.local import LocalAccount
import logging

logger = logging.getLogger(__name__)


@dataclass
class WalletStats:
    """Statistics for individual wallet"""
    address: str
    balance_eth: float = 0.0
    nonce: int = 0
    trades_executed: int = 0
    total_profit_usd: float = 0.0
    last_used: float = 0.0
    gas_spent_eth: float = 0.0
    is_available: bool = True
    consecutive_failures: int = 0
    
    @property
    def net_profit_eth(self) -> float:
        """Net profit after gas costs"""
        return self.total_profit_usd - self.gas_spent_eth
    
    @property
    def avg_profit_per_trade(self) -> float:
        """Average profit per trade"""
        if self.trades_executed == 0:
            return 0.0
        return self.total_profit_usd / self.trades_executed


class WalletRotator:
    """
    Wallet rotation system for MEV protection
    
    Features:
    - Rotates across 4 EOA wallets
    - Random rotation interval (7-15 minutes)
    - Independent nonce management per wallet
    - Balance monitoring and gas funding alerts
    - Pattern obfuscation to avoid MEV detection
    
    Security Benefits:
    - Prevents MEV bots from tracking profitable addresses
    - Reduces correlation between trades
    - Makes front-running harder
    - Distributes risk across multiple wallets
    """
    
    def __init__(
        self,
        private_keys: List[str],
        w3: Web3,
        min_rotation_seconds: int = 420,  # 7 minutes
        max_rotation_seconds: int = 900,  # 15 minutes
        min_balance_eth: float = 0.01,
        max_consecutive_failures: int = 3
    ):
        """
        Initialize wallet rotator
        
        Args:
            private_keys: List of private keys for EOA1-4
            w3: Web3 instance
            min_rotation_seconds: Minimum time before rotation (default 7 min)
            max_rotation_seconds: Maximum time before rotation (default 15 min)
            min_balance_eth: Alert if wallet balance below this (default 0.01 ETH)
            max_consecutive_failures: Disable wallet after this many failures
        """
        self.w3 = w3
        self.min_rotation_seconds = min_rotation_seconds
        self.max_rotation_seconds = max_rotation_seconds
        self.min_balance_eth = min_balance_eth
        self.max_consecutive_failures = max_consecutive_failures
        
        # Initialize wallets
        self.wallets: List[LocalAccount] = []
        self.wallet_stats: Dict[str, WalletStats] = {}
        
        for i, private_key in enumerate(private_keys, 1):
            try:
                # Remove 0x prefix if present
                if private_key.startswith('0x'):
                    private_key = private_key[2:]
                
                account = Account.from_key(private_key)
                self.wallets.append(account)
                
                stats = WalletStats(address=account.address)
                self.wallet_stats[account.address] = stats
                
                logger.info(f"Initialized EOA{i}: {account.address}")
                
            except Exception as e:
                logger.error(f"Failed to initialize wallet {i}: {e}")
        
        if not self.wallets:
            raise ValueError("No valid wallets provided!")
        
        # Rotation state
        self.current_wallet_index = 0
        self.last_rotation_time = time.time()
        self.next_rotation_time = self._calculate_next_rotation()
        
        # Statistics
        self.total_rotations = 0
        self.rotation_history: List[Tuple[float, str]] = []
        
        # Update initial balances
        self._update_all_balances()
        
        logger.info(
            f"Wallet rotator initialized with {len(self.wallets)} wallets, "
            f"rotation interval: {min_rotation_seconds//60}-{max_rotation_seconds//60} minutes"
        )
    
    def _calculate_next_rotation(self) -> float:
        """Calculate next rotation time with randomization"""
        interval = random.uniform(
            self.min_rotation_seconds,
            self.max_rotation_seconds
        )
        return time.time() + interval
    
    def _update_all_balances(self):
        """Update balance for all wallets"""
        for wallet in self.wallets:
            try:
                balance_wei = self.w3.eth.get_balance(wallet.address)
                balance_eth = self.w3.from_wei(balance_wei, 'ether')
                
                stats = self.wallet_stats[wallet.address]
                stats.balance_eth = float(balance_eth)
                stats.nonce = self.w3.eth.get_transaction_count(wallet.address)
                
                # Check for low balance
                if balance_eth < self.min_balance_eth:
                    logger.warning(
                        f"LOW BALANCE: {wallet.address} has {balance_eth:.4f} ETH "
                        f"(below {self.min_balance_eth} ETH)"
                    )
                
            except Exception as e:
                logger.error(f"Failed to update balance for {wallet.address}: {e}")
    
    def get_current_wallet(self) -> Tuple[LocalAccount, WalletStats]:
        """
        Get current active wallet
        Automatically rotates if rotation interval elapsed
        
        Returns:
            Tuple of (wallet_account, wallet_stats)
        """
        # Check if rotation needed
        current_time = time.time()
        if current_time >= self.next_rotation_time:
            self._rotate_wallet()
        
        wallet = self.wallets[self.current_wallet_index]
        stats = self.wallet_stats[wallet.address]
        
        # Update last used time
        stats.last_used = current_time
        
        return wallet, stats
    
    def _rotate_wallet(self):
        """Rotate to next available wallet"""
        old_index = self.current_wallet_index
        old_wallet = self.wallets[old_index]
        
        # Find next available wallet
        attempts = 0
        max_attempts = len(self.wallets) * 2
        
        while attempts < max_attempts:
            # Move to next wallet (circular)
            self.current_wallet_index = (self.current_wallet_index + 1) % len(self.wallets)
            new_wallet = self.wallets[self.current_wallet_index]
            new_stats = self.wallet_stats[new_wallet.address]
            
            # Check if wallet is available
            if new_stats.is_available:
                if new_stats.consecutive_failures < self.max_consecutive_failures:
                    # Wallet is good, use it
                    break
            
            attempts += 1
        
        if attempts >= max_attempts:
            logger.error("CRITICAL: All wallets unavailable! Using current wallet.")
            return
        
        # Update rotation tracking
        self.total_rotations += 1
        self.last_rotation_time = time.time()
        self.next_rotation_time = self._calculate_next_rotation()
        
        # Record rotation
        rotation_record = (self.last_rotation_time, new_wallet.address)
        self.rotation_history.append(rotation_record)
        if len(self.rotation_history) > 1000:
            self.rotation_history = self.rotation_history[-1000:]
        
        # Update balances
        self._update_all_balances()
        
        logger.info(
            f"WALLET ROTATION: {old_wallet.address[:10]}... → {new_wallet.address[:10]}... "
            f"(rotation #{self.total_rotations}, next in "
            f"{(self.next_rotation_time - time.time())/60:.1f} min)"
        )
    
    def force_rotation(self):
        """Force immediate rotation to next wallet"""
        logger.info("Forcing immediate wallet rotation")
        self.next_rotation_time = time.time()
        self._rotate_wallet()
    
    def record_trade(
        self,
        wallet_address: str,
        profit_usd: float,
        gas_cost_eth: float,
        success: bool = True
    ):
        """
        Record trade execution for wallet
        
        Args:
            wallet_address: Address that executed trade
            profit_usd: Profit in USD
            gas_cost_eth: Gas cost in ETH
            success: Whether trade succeeded
        """
        stats = self.wallet_stats.get(wallet_address)
        if not stats:
            logger.error(f"Unknown wallet address: {wallet_address}")
            return
        
        stats.trades_executed += 1
        stats.total_profit_usd += profit_usd
        stats.gas_spent_eth += gas_cost_eth
        
        if not success:
            stats.consecutive_failures += 1
            if stats.consecutive_failures >= self.max_consecutive_failures:
                stats.is_available = False
                logger.warning(
                    f"Wallet {wallet_address[:10]}... disabled after "
                    f"{stats.consecutive_failures} consecutive failures"
                )
        else:
            stats.consecutive_failures = 0
        
        # Update nonce
        try:
            stats.nonce = self.w3.eth.get_transaction_count(wallet_address)
        except Exception as e:
            logger.error(f"Failed to update nonce for {wallet_address}: {e}")
    
    def get_wallet_by_address(self, address: str) -> Optional[LocalAccount]:
        """Get wallet account by address"""
        for wallet in self.wallets:
            if wallet.address.lower() == address.lower():
                return wallet
        return None
    
    def get_all_addresses(self) -> List[str]:
        """Get list of all wallet addresses"""
        return [w.address for w in self.wallets]
    
    def get_statistics(self) -> Dict:
        """Get comprehensive statistics for all wallets"""
        self._update_all_balances()
        
        total_balance = sum(s.balance_eth for s in self.wallet_stats.values())
        total_trades = sum(s.trades_executed for s in self.wallet_stats.values())
        total_profit = sum(s.total_profit_usd for s in self.wallet_stats.values())
        total_gas = sum(s.gas_spent_eth for s in self.wallet_stats.values())
        
        return {
            "total_rotations": self.total_rotations,
            "current_wallet": self.wallets[self.current_wallet_index].address,
            "next_rotation_in_seconds": max(0, self.next_rotation_time - time.time()),
            "total_balance_eth": total_balance,
            "total_trades": total_trades,
            "total_profit_usd": total_profit,
            "total_gas_eth": total_gas,
            "net_profit_usd": total_profit - total_gas,
            "wallets": {
                address: {
                    "balance_eth": stats.balance_eth,
                    "nonce": stats.nonce,
                    "trades_executed": stats.trades_executed,
                    "total_profit_usd": stats.total_profit_usd,
                    "gas_spent_eth": stats.gas_spent_eth,
                    "net_profit_eth": stats.net_profit_eth,
                    "avg_profit_per_trade": stats.avg_profit_per_trade,
                    "is_available": stats.is_available,
                    "consecutive_failures": stats.consecutive_failures,
                    "minutes_since_last_use": (time.time() - stats.last_used) / 60 if stats.last_used > 0 else 999,
                }
                for address, stats in self.wallet_stats.items()
            }
        }
    
    def print_status(self):
        """Print current status of all wallets"""
        stats = self.get_statistics()
        
        print("\n" + "="*100)
        print("WALLET ROTATION STATUS")
        print("="*100)
        
        current_addr = stats['current_wallet']
        print(f"Current Wallet: {current_addr}")
        print(f"Next Rotation:  {stats['next_rotation_in_seconds']/60:.1f} minutes")
        print(f"Total Rotations: {stats['total_rotations']}")
        print(f"\nAggregate Stats:")
        print(f"  Total Balance:   {stats['total_balance_eth']:.4f} ETH")
        print(f"  Total Trades:    {stats['total_trades']}")
        print(f"  Total Profit:    ${stats['total_profit_usd']:.2f}")
        print(f"  Total Gas:       {stats['total_gas_eth']:.4f} ETH")
        print(f"  Net Profit:      ${stats['net_profit_usd']:.2f}")
        
        print("\n" + "-"*100)
        print(f"{'Wallet':<44} {'Balance':>12} {'Trades':>8} {'Profit':>12} {'Gas':>10} {'Status':<10}")
        print("-"*100)
        
        for address, wallet_stats in stats['wallets'].items():
            is_current = "→ ACTIVE" if address == current_addr else ""
            status = "✓ Ready" if wallet_stats['is_available'] else "✗ Disabled"
            
            print(
                f"{address:<44} "
                f"{wallet_stats['balance_eth']:>12.4f} "
                f"{wallet_stats['trades_executed']:>8} "
                f"${wallet_stats['total_profit_usd']:>11.2f} "
                f"{wallet_stats['gas_spent_eth']:>10.4f} "
                f"{status:<10} {is_current}"
            )
        
        print("="*100 + "\n")


# Example usage and testing
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Example configuration
    # NOTE: These are example private keys - DO NOT USE IN PRODUCTION
    # Generate your own secure keys and store them in .env file
    example_keys = [
        os.getenv("EOA1_PRIVATE_KEY", "0x" + "1" * 64),
        os.getenv("EOA2_PRIVATE_KEY", "0x" + "2" * 64),
        os.getenv("EOA3_PRIVATE_KEY", "0x" + "3" * 64),
        os.getenv("EOA4_PRIVATE_KEY", "0x" + "4" * 64),
    ]
    
    # Initialize Web3 (Arbitrum mainnet)
    rpc_url = os.getenv("ARBITRUM_RPC", "https://arb1.arbitrum.io/rpc")
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    
    print("Initializing wallet rotator...")
    rotator = WalletRotator(
        private_keys=example_keys,
        w3=w3,
        min_rotation_seconds=30,  # 30 seconds for testing
        max_rotation_seconds=60,  # 60 seconds for testing
        min_balance_eth=0.001
    )
    
    # Show initial status
    rotator.print_status()
    
    # Simulate some trades
    print("\nSimulating trades...")
    for i in range(5):
        wallet, stats = rotator.get_current_wallet()
        print(f"\nTrade {i+1}: Using wallet {wallet.address[:10]}...")
        
        # Record simulated trade
        rotator.record_trade(
            wallet_address=wallet.address,
            profit_usd=random.uniform(5, 50),
            gas_cost_eth=random.uniform(0.0001, 0.001),
            success=True
        )
        
        time.sleep(2)
        
        # Force rotation every 2 trades for demo
        if i % 2 == 1:
            rotator.force_rotation()
    
    # Show final status
    rotator.print_status()
    
    # Show statistics
    stats = rotator.get_statistics()
    print(f"\n✓ Wallet rotation test complete")
    print(f"  Total rotations: {stats['total_rotations']}")
    print(f"  All wallets: {len(rotator.get_all_addresses())}")
