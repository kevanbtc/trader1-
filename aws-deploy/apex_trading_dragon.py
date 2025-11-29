#!/usr/bin/env python3
"""
🐉 APEX TRADING DRAGON
24/7 Autonomous Trading Engine for AWS Deployment
Integrates with private RPC, mempool sniffer, and full strategy execution.
"""

import os
import sys
import time
import asyncio
from pathlib import Path

# Add parent directory to path to import trading engine
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.defi_price_feed import DeFiPriceFeed
from agents.execution_engine import ExecutionEngine
from agents.professional_risk_manager import ProfessionalRiskManager
from agents.swarm_coordinator import SwarmCoordinator
from agents.mcp_intelligence import MCPIntelligence
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('/home/ubuntu/apex/logs/trading_dragon.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ApexTradingDragon:
    """24/7 Autonomous Trading Dragon for AWS deployment."""
    
    def __init__(self):
        self.rpc_url = os.getenv("ARBITRUM_RPC", "http://127.0.0.1:8547")
        self.ws_url = os.getenv("ARBITRUM_WS", "ws://127.0.0.1:8548")
        self.private_key = os.getenv("PRIVATE_KEY")
        self.wallet_address = os.getenv("PUBLIC_ADDRESS")
        
        # Performance settings
        self.scan_interval = float(os.getenv("SCAN_INTERVAL_MS", "250")) / 1000
        self.min_profit_usd = float(os.getenv("MIN_PROFIT_USD", "0.02"))
        self.max_position_usd = float(os.getenv("MAX_POSITION_USD", "15.00"))
        
        # AI/Swarm settings
        self.swarm_mode = os.getenv("SWARM_MODE", "1") == "1"
        self.ai_mode = os.getenv("AI_MODE", "1") == "1"
        self.auto_compound = os.getenv("AUTO_COMPOUND", "1") == "1"
        
        # Initialize components
        self.price_feed = None
        self.execution_engine = None
        self.risk_manager = None
        self.swarm = None
        self.mcp = None
        
        # Session tracking
        self.start_time = time.time()
        self.total_scans = 0
        self.total_opportunities = 0
        self.total_trades = 0
        self.session_pnl = 0.0
    
    def initialize_components(self):
        """Initialize all trading components."""
        logger.info("🐉 Initializing Apex Trading Dragon...")
        logger.info(f"   RPC: {self.rpc_url}")
        logger.info(f"   Wallet: {self.wallet_address}")
        logger.info(f"   Min Profit: ${self.min_profit_usd}")
        logger.info(f"   Max Position: ${self.max_position_usd}")
        logger.info(f"   Swarm Mode: {self.swarm_mode}")
        logger.info(f"   AI Mode: {self.ai_mode}")
        logger.info("")
        
        try:
            # Initialize risk manager
            self.risk_manager = ProfessionalRiskManager(
                max_position_size_usd=self.max_position_usd,
                max_gas_gwei=float(os.getenv("MAX_GAS_GWEI", "0.02"))
            )
            logger.info("✅ Risk Manager initialized")
            
            # Initialize execution engine
            self.execution_engine = ExecutionEngine(
                private_key=self.private_key,
                rpc_url=self.rpc_url
            )
            logger.info("✅ Execution Engine initialized")
            
            # Initialize price feed
            self.price_feed = DeFiPriceFeed(
                rpc_url=self.rpc_url,
                min_profit_usd=self.min_profit_usd
            )
            logger.info("✅ Price Feed initialized")
            
            # Initialize swarm if enabled
            if self.swarm_mode:
                self.swarm = SwarmCoordinator()
                logger.info("✅ Swarm Coordinator initialized")
            
            # Initialize MCP if enabled
            if self.ai_mode:
                self.mcp = MCPIntelligence()
                logger.info("✅ MCP Intelligence initialized")
            
            logger.info("\n🚀 All systems operational - beginning autonomous trading\n")
            return True
        
        except Exception as e:
            logger.error(f"❌ Initialization failed: {e}")
            return False
    
    async def scan_markets(self):
        """Execute single market scan."""
        try:
            self.total_scans += 1
            
            # Scan for opportunities
            opportunities = await self.price_feed.scan_all_pairs()
            
            if opportunities:
                self.total_opportunities += len(opportunities)
                logger.info(f"🎯 SCAN #{self.total_scans}: Found {len(opportunities)} opportunities")
                
                # Execute best opportunity
                best_opp = opportunities[0]
                
                # Risk check
                if self.risk_manager.should_execute_trade(best_opp):
                    logger.info(f"   Executing: {best_opp.buy_dex} → {best_opp.sell_dex}")
                    logger.info(f"   Profit: ${best_opp.net_profit_usd:.4f}")
                    
                    result = await self.execution_engine.execute_arbitrage(best_opp)
                    
                    if result["success"]:
                        self.total_trades += 1
                        self.session_pnl += result["net_profit_usd"]
                        logger.info(f"✅ Trade successful | PnL: ${result['net_profit_usd']:.4f}")
                        logger.info(f"   Session PnL: ${self.session_pnl:.4f}")
                    else:
                        logger.warning(f"⚠️ Trade failed: {result.get('error', 'Unknown')}")
                else:
                    logger.info(f"   ⛔ Trade blocked by risk manager")
            
            else:
                # Only log every 20th scan when quiet
                if self.total_scans % 20 == 0:
                    logger.info(f"📊 Scan #{self.total_scans} | Market quiet | Trades: {self.total_trades} | PnL: ${self.session_pnl:.4f}")
        
        except Exception as e:
            logger.error(f"❌ Scan error: {e}")
    
    async def run_forever(self):
        """Main trading loop - runs 24/7."""
        if not self.initialize_components():
            logger.error("Failed to initialize - exiting")
            return
        
        logger.info("♾️  Entering infinite trading loop (24/7 mode)")
        logger.info(f"   Scan interval: {self.scan_interval}s")
        logger.info("")
        
        while True:
            try:
                await self.scan_markets()
                await asyncio.sleep(self.scan_interval)
            
            except KeyboardInterrupt:
                logger.info("\n🛑 Shutdown signal received")
                break
            except Exception as e:
                logger.error(f"❌ Critical error: {e}")
                logger.info("   Restarting in 10 seconds...")
                await asyncio.sleep(10)
        
        # Shutdown
        runtime = (time.time() - self.start_time) / 3600
        logger.info("\n" + "="*60)
        logger.info("🐉 APEX TRADING DRAGON SESSION COMPLETE")
        logger.info("="*60)
        logger.info(f"Runtime: {runtime:.2f} hours")
        logger.info(f"Total Scans: {self.total_scans}")
        logger.info(f"Opportunities: {self.total_opportunities}")
        logger.info(f"Trades Executed: {self.total_trades}")
        logger.info(f"Session PnL: ${self.session_pnl:.4f}")
        logger.info("="*60)

if __name__ == "__main__":
    dragon = ApexTradingDragon()
    asyncio.run(dragon.run_forever())
