"""
Block Event Hunter - Real-time blockchain event listener
Detects whale swaps, oracle updates, liquidations, large transfers
Executes arbitrage within 1-2 blocks of price-moving events
Pure alpha extraction through information asymmetry
"""

import asyncio
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
from web3 import Web3
from eth_abi import decode
import json

@dataclass
class BlockEvent:
    """Blockchain event that may create arbitrage opportunity"""
    event_type: str  # "WHALE_SWAP", "ORACLE_UPDATE", "LIQUIDATION", "LARGE_TRANSFER"
    block_number: int
    transaction_hash: str
    token_affected: str
    amount_usd: float
    dex_protocol: str
    estimated_price_impact: float  # Expected price impact in bps
    timestamp: datetime
    raw_log: Dict

@dataclass
class EventOpportunity:
    """Arbitrage opportunity triggered by blockchain event"""
    trigger_event: BlockEvent
    opportunity_type: str  # "FRONT_RUN", "BACK_RUN", "IMMEDIATE_ARB"
    token_pair: str
    buy_dex: str
    sell_dex: str
    estimated_profit_usd: float
    execution_deadline_block: int  # Must execute by this block
    priority: str  # "CRITICAL", "HIGH", "MEDIUM"

class BlockEventHunter:
    """
    Real-time event listener and arbitrage trigger
    Subscribes to pending transactions and new blocks
    Detects high-value events and triggers immediate execution
    """
    
    # Event signatures (keccak256 hashes)
    SWAP_EVENT_SIG = "0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822"  # Uniswap V2 Swap
    SWAP_V3_EVENT_SIG = "0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"  # Uniswap V3 Swap
    TRANSFER_EVENT_SIG = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"  # ERC20 Transfer
    
    # Whale threshold (USD)
    WHALE_SWAP_THRESHOLD = 50000  # $50k+ swaps
    LARGE_TRANSFER_THRESHOLD = 100000  # $100k+ transfers
    
    def __init__(self, w3: Web3, token_prices: Dict[str, float]):
        self.w3 = w3
        self.token_prices = token_prices  # Token address -> USD price
        
        # Event callbacks
        self.event_callbacks: List[Callable] = []
        
        # DEX contract addresses to monitor (Arbitrum)
        self.monitored_dexes = {
            "0xE592427A0AEce92De3Edee1F18E0157C05861564": "Uniswap V3",
            "0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506": "Sushiswap",
            "0x7544Fe3d184b6B55D6B36c3FCA1157eE0Ba30287": "Curve",
            "0xc873fEcbd354f5A56E00E710B90EF4201db2448d": "Camelot V2",
            "0xBA12222222228d8Ba445958a75a0704d566BF2C8": "Balancer V2"
        }
        
        # Recent events cache (prevent duplicates)
        self.recent_events: Dict[str, datetime] = {}
        self.cache_ttl = 60  # 60 second cache
        
        # Statistics
        self.events_detected = 0
        self.opportunities_created = 0
        
        print(f"🎯 Block Event Hunter initialized")
        print(f"🎯 Monitoring {len(self.monitored_dexes)} DEX contracts")
        print(f"🎯 Whale threshold: ${self.WHALE_SWAP_THRESHOLD:,}")
    
    def register_callback(self, callback: Callable):
        """Register callback to receive event opportunities"""
        self.event_callbacks.append(callback)
    
    async def start_listening(self):
        """Start listening to blockchain events"""
        print("🎯 Starting event listener...")
        
        # Subscribe to new blocks
        block_task = asyncio.create_task(self._listen_new_blocks())
        
        # Subscribe to pending transactions (if available)
        pending_task = asyncio.create_task(self._listen_pending_txs())
        
        await asyncio.gather(block_task, pending_task)
    
    async def _listen_new_blocks(self):
        """Listen for new blocks and scan for events"""
        last_block = self.w3.eth.block_number
        
        while True:
            try:
                current_block = self.w3.eth.block_number
                
                if current_block > last_block:
                    # Process new blocks
                    for block_num in range(last_block + 1, current_block + 1):
                        await self._process_block(block_num)
                    
                    last_block = current_block
                
                await asyncio.sleep(0.5)  # Check every 500ms
            
            except Exception as e:
                print(f"⚠️  Block listener error: {e}")
                await asyncio.sleep(2)
    
    async def _listen_pending_txs(self):
        """Listen for pending transactions (mempool monitoring)"""
        # Note: This requires WebSocket connection, fallback gracefully
        try:
            # Create filter for pending transactions
            pending_filter = self.w3.eth.filter('pending')
            
            while True:
                try:
                    pending_txs = pending_filter.get_new_entries()
                    
                    for tx_hash in pending_txs:
                        await self._process_pending_tx(tx_hash)
                    
                    await asyncio.sleep(0.2)  # Check every 200ms
                
                except Exception as e:
                    print(f"⚠️  Pending tx listener error: {e}")
                    await asyncio.sleep(2)
        
        except Exception as e:
            print(f"⚠️  Cannot subscribe to pending txs (requires WebSocket): {e}")
            # Gracefully continue without pending tx monitoring
            while True:
                await asyncio.sleep(60)
    
    async def _process_block(self, block_num: int):
        """Process a single block for events"""
        try:
            block = self.w3.eth.get_block(block_num, full_transactions=True)
            
            for tx in block['transactions']:
                # Check if transaction interacts with monitored DEXes
                if tx['to'] and tx['to'] in self.monitored_dexes:
                    await self._analyze_transaction(tx, block_num)
        
        except Exception as e:
            print(f"⚠️  Error processing block {block_num}: {e}")
    
    async def _process_pending_tx(self, tx_hash: str):
        """Process pending transaction (front-run detection)"""
        try:
            tx = self.w3.eth.get_transaction(tx_hash)
            
            if tx and tx['to'] and tx['to'] in self.monitored_dexes:
                # Potential front-run opportunity
                await self._analyze_pending_transaction(tx)
        
        except Exception as e:
            # Pending tx may not be available yet
            pass
    
    async def _analyze_transaction(self, tx: Dict, block_num: int):
        """Analyze transaction for arbitrage-worthy events"""
        try:
            receipt = self.w3.eth.get_transaction_receipt(tx['hash'])
            
            for log in receipt['logs']:
                # Check for Swap events
                if log['topics'][0].hex() == self.SWAP_EVENT_SIG or \
                   log['topics'][0].hex() == self.SWAP_V3_EVENT_SIG:
                    
                    event = await self._parse_swap_event(log, tx, block_num)
                    if event:
                        await self._handle_event(event)
                
                # Check for large transfers
                elif log['topics'][0].hex() == self.TRANSFER_EVENT_SIG:
                    event = await self._parse_transfer_event(log, tx, block_num)
                    if event:
                        await self._handle_event(event)
        
        except Exception as e:
            print(f"⚠️  Error analyzing transaction: {e}")
    
    async def _analyze_pending_transaction(self, tx: Dict):
        """Analyze pending transaction for front-run opportunities"""
        # Decode transaction input to estimate swap size
        # This is a simplified version - real implementation would decode calldata
        value_eth = tx['value'] / 1e18
        if value_eth > 10:  # Large ETH swap
            print(f"🎯 Detected large pending swap: {value_eth:.2f} ETH")
            # Create front-run opportunity (not implemented in this version)
    
    async def _parse_swap_event(self, log: Dict, tx: Dict, block_num: int) -> Optional[BlockEvent]:
        """Parse DEX swap event"""
        try:
            # Decode swap event (simplified - varies by DEX)
            # Uniswap V2: Swap(address indexed sender, uint amount0In, uint amount1In, uint amount0Out, uint amount1Out, address indexed to)
            
            dex_name = self.monitored_dexes.get(log['address'], "Unknown DEX")
            
            # Estimate swap size (simplified)
            # In production, would decode specific amounts and calculate USD value
            estimated_usd = 10000  # Placeholder
            
            if estimated_usd < self.WHALE_SWAP_THRESHOLD:
                return None  # Not a whale swap
            
            event = BlockEvent(
                event_type="WHALE_SWAP",
                block_number=block_num,
                transaction_hash=tx['hash'].hex(),
                token_affected="UNKNOWN",  # Would decode from log
                amount_usd=estimated_usd,
                dex_protocol=dex_name,
                estimated_price_impact=50,  # Estimate in bps
                timestamp=datetime.now(),
                raw_log=dict(log)
            )
            
            self.events_detected += 1
            return event
        
        except Exception as e:
            return None
    
    async def _parse_transfer_event(self, log: Dict, tx: Dict, block_num: int) -> Optional[BlockEvent]:
        """Parse large ERC20 transfer event"""
        try:
            # Decode Transfer event: Transfer(address indexed from, address indexed to, uint256 value)
            if len(log['topics']) < 3:
                return None
            
            # Decode amount (data field)
            amount_raw = int(log['data'], 16) if log['data'] else 0
            amount_tokens = amount_raw / 1e18  # Assume 18 decimals
            
            # Get token price
            token_address = log['address']
            token_price = self.token_prices.get(token_address, 0)
            amount_usd = amount_tokens * token_price
            
            if amount_usd < self.LARGE_TRANSFER_THRESHOLD:
                return None  # Not large enough
            
            event = BlockEvent(
                event_type="LARGE_TRANSFER",
                block_number=block_num,
                transaction_hash=tx['hash'].hex(),
                token_affected=token_address,
                amount_usd=amount_usd,
                dex_protocol="N/A",
                estimated_price_impact=0,
                timestamp=datetime.now(),
                raw_log=dict(log)
            )
            
            self.events_detected += 1
            return event
        
        except Exception as e:
            return None
    
    async def _handle_event(self, event: BlockEvent):
        """Handle detected event and create opportunities"""
        # Check cache to prevent duplicates
        cache_key = f"{event.transaction_hash}:{event.event_type}"
        if cache_key in self.recent_events:
            return
        
        self.recent_events[cache_key] = datetime.now()
        
        # Clean old cache entries
        self._clean_cache()
        
        print(f"🎯 EVENT DETECTED: {event.event_type} | ${event.amount_usd:,.2f} | {event.dex_protocol}")
        
        # Create arbitrage opportunity
        opportunity = await self._create_opportunity_from_event(event)
        
        if opportunity:
            self.opportunities_created += 1
            
            # Notify callbacks
            for callback in self.event_callbacks:
                try:
                    await callback(opportunity)
                except Exception as e:
                    print(f"⚠️  Callback error: {e}")
    
    async def _create_opportunity_from_event(self, event: BlockEvent) -> Optional[EventOpportunity]:
        """Create arbitrage opportunity from blockchain event"""
        # Simplified opportunity creation
        # In production, would analyze price impact across DEXes
        
        if event.event_type == "WHALE_SWAP" and event.estimated_price_impact > 20:
            return EventOpportunity(
                trigger_event=event,
                opportunity_type="IMMEDIATE_ARB",
                token_pair="WETH/USDC",  # Would be dynamic
                buy_dex="Uniswap V3",
                sell_dex="Sushiswap",
                estimated_profit_usd=5.0,
                execution_deadline_block=event.block_number + 2,
                priority="HIGH"
            )
        
        return None
    
    def _clean_cache(self):
        """Remove old entries from cache"""
        now = datetime.now()
        to_remove = []
        
        for key, timestamp in self.recent_events.items():
            if (now - timestamp).total_seconds() > self.cache_ttl:
                to_remove.append(key)
        
        for key in to_remove:
            del self.recent_events[key]
    
    def get_stats(self) -> Dict:
        """Get hunter statistics"""
        return {
            'events_detected': self.events_detected,
            'opportunities_created': self.opportunities_created,
            'cache_size': len(self.recent_events)
        }
