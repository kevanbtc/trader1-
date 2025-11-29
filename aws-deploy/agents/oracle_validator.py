"""
Oracle Triangulation - Multi-Source Price Validation
Combines Chainlink + Pyth + Coinbase for maximum reliability
Disables trading if price deviation >1% (volatility trap detection)

Used by: price_validator.py, live_engine.py
Prevents: Trading on stale/manipulated oracle data, volatility traps
"""

import time
import requests
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from web3 import Web3
import logging

logger = logging.getLogger(__name__)


class OracleSource(Enum):
    """Supported oracle sources"""
    CHAINLINK = "chainlink"
    PYTH = "pyth"
    COINBASE = "coinbase"


@dataclass
class PriceReading:
    """Single price reading from an oracle"""
    source: OracleSource
    price_usd: float
    timestamp: float
    confidence: float = 1.0  # 0-1, higher = more reliable
    
    def __str__(self):
        return f"{self.source.value}: ${self.price_usd:.2f} (confidence: {self.confidence:.2%})"


@dataclass
class TriangulatedPrice:
    """Result of oracle triangulation"""
    consensus_price: float
    deviation_pct: float
    readings: List[PriceReading]
    is_valid: bool
    warning_message: Optional[str] = None
    
    def __str__(self):
        status = "✓ VALID" if self.is_valid else "✗ INVALID"
        return (
            f"{status} - Consensus: ${self.consensus_price:.2f}, "
            f"Deviation: {self.deviation_pct:.2f}%"
        )


class OracleValidator:
    """
    Multi-source oracle triangulation for price validation
    
    Features:
    - Queries Chainlink, Pyth, and Coinbase simultaneously
    - Calculates consensus price with confidence weighting
    - Detects price manipulation and volatility traps
    - Disables trading on >1% deviation between sources
    
    Why This Matters:
    - Single oracle can be manipulated or stale
    - Cross-validation prevents false arbitrage signals
    - Protects against flash crashes and exploits
    - Used by professional trading desks for risk management
    """
    
    def __init__(
        self,
        w3: Web3,
        max_deviation_pct: float = 1.0,
        min_sources: int = 2,
        pyth_api_key: Optional[str] = None,
        coinbase_api_key: Optional[str] = None
    ):
        """
        Initialize oracle validator
        
        Args:
            w3: Web3 instance for Chainlink queries
            max_deviation_pct: Max allowed deviation between sources (default 1.0%)
            min_sources: Minimum sources required for validation (default 2)
            pyth_api_key: Pyth Network API key (optional)
            coinbase_api_key: Coinbase API key (optional)
        """
        self.w3 = w3
        self.max_deviation = max_deviation_pct
        self.min_sources = min_sources
        self.pyth_api_key = pyth_api_key
        self.coinbase_api_key = coinbase_api_key
        
        # Chainlink price feed addresses (Ethereum mainnet)
        self.chainlink_feeds = {
            "ETH/USD": "0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419",
            "BTC/USD": "0xF4030086522a5bEEa4988F8cA5B36dbC97BeE88c",
            "USDC/USD": "0x8fFfFfd4AfB6115b954Bd326cbe7B4BA576818f6",
            "USDT/USD": "0x3E7d1eAB13ad0104d2750B8863b489D65364e32D",
        }
        
        # Chainlink ABI (minimal - just latestRoundData)
        self.chainlink_abi = [
            {
                "inputs": [],
                "name": "latestRoundData",
                "outputs": [
                    {"name": "roundId", "type": "uint80"},
                    {"name": "answer", "type": "int256"},
                    {"name": "startedAt", "type": "uint256"},
                    {"name": "updatedAt", "type": "uint256"},
                    {"name": "answeredInRound", "type": "uint80"}
                ],
                "stateMutability": "view",
                "type": "function"
            }
        ]
        
        # Statistics
        self.total_validations = 0
        self.valid_count = 0
        self.invalid_count = 0
        self.max_deviation_seen = 0.0
        
        logger.info(
            f"Oracle validator initialized: "
            f"max_deviation={max_deviation_pct}%, "
            f"min_sources={min_sources}"
        )
    
    def validate_price(self, symbol: str) -> TriangulatedPrice:
        """
        Validate price across multiple oracle sources
        
        Args:
            symbol: Token pair (e.g., "ETH/USD", "BTC/USD")
        
        Returns:
            TriangulatedPrice with consensus and validation status
        """
        readings: List[PriceReading] = []
        
        # Query all sources
        chainlink_price = self._get_chainlink_price(symbol)
        if chainlink_price:
            readings.append(chainlink_price)
        
        pyth_price = self._get_pyth_price(symbol)
        if pyth_price:
            readings.append(pyth_price)
        
        coinbase_price = self._get_coinbase_price(symbol)
        if coinbase_price:
            readings.append(coinbase_price)
        
        # Calculate consensus
        result = self._calculate_consensus(readings)
        
        # Update statistics
        self.total_validations += 1
        if result.is_valid:
            self.valid_count += 1
        else:
            self.invalid_count += 1
        
        if result.deviation_pct > self.max_deviation_seen:
            self.max_deviation_seen = result.deviation_pct
        
        # Log result
        if result.is_valid:
            logger.debug(f"Oracle validation PASSED: {result}")
        else:
            logger.warning(f"Oracle validation FAILED: {result}")
            for reading in readings:
                logger.warning(f"  {reading}")
        
        return result
    
    def _get_chainlink_price(self, symbol: str) -> Optional[PriceReading]:
        """Query Chainlink oracle"""
        try:
            feed_address = self.chainlink_feeds.get(symbol)
            if not feed_address:
                logger.debug(f"No Chainlink feed for {symbol}")
                return None
            
            contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(feed_address),
                abi=self.chainlink_abi
            )
            
            # Get latest round data
            round_data = contract.functions.latestRoundData().call()
            answer = round_data[1]
            updated_at = round_data[3]
            
            # Chainlink prices have 8 decimals
            price = answer / 10**8
            
            # Check if price is stale (>1 hour old)
            age_seconds = time.time() - updated_at
            if age_seconds > 3600:
                logger.warning(
                    f"Chainlink {symbol} price is stale: {age_seconds/60:.1f} minutes old"
                )
                confidence = max(0.5, 1.0 - (age_seconds / 7200))  # Degrade confidence
            else:
                confidence = 1.0
            
            return PriceReading(
                source=OracleSource.CHAINLINK,
                price_usd=price,
                timestamp=time.time(),
                confidence=confidence
            )
            
        except Exception as e:
            logger.error(f"Chainlink query failed for {symbol}: {e}")
            return None
    
    def _get_pyth_price(self, symbol: str) -> Optional[PriceReading]:
        """Query Pyth Network oracle"""
        try:
            # Map symbols to Pyth price IDs
            pyth_ids = {
                "ETH/USD": "0xff61491a931112ddf1bd8147cd1b641375f79f5825126d665480874634fd0ace",
                "BTC/USD": "0xe62df6c8b4a85fe1a67db44dc12de5db330f7ac66b72dc658afedf0f4a415b43",
            }
            
            price_id = pyth_ids.get(symbol)
            if not price_id:
                logger.debug(f"No Pyth feed for {symbol}")
                return None
            
            # Query Pyth API
            url = f"https://hermes.pyth.network/v2/updates/price/latest"
            params = {"ids[]": price_id}
            
            if self.pyth_api_key:
                headers = {"Authorization": f"Bearer {self.pyth_api_key}"}
            else:
                headers = {}
            
            response = requests.get(url, params=params, headers=headers, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            if not data.get("parsed"):
                return None
            
            price_data = data["parsed"][0]["price"]
            price = float(price_data["price"]) * (10 ** price_data["expo"])
            confidence_interval = float(price_data["conf"]) * (10 ** price_data["expo"])
            
            # Calculate confidence based on interval width
            confidence = max(0.5, 1.0 - (confidence_interval / price))
            
            return PriceReading(
                source=OracleSource.PYTH,
                price_usd=price,
                timestamp=time.time(),
                confidence=confidence
            )
            
        except Exception as e:
            logger.error(f"Pyth query failed for {symbol}: {e}")
            return None
    
    def _get_coinbase_price(self, symbol: str) -> Optional[PriceReading]:
        """Query Coinbase exchange API"""
        try:
            # Convert symbol format (ETH/USD -> ETH-USD)
            pair = symbol.replace("/", "-")
            
            url = f"https://api.exchange.coinbase.com/products/{pair}/ticker"
            
            if self.coinbase_api_key:
                headers = {"Authorization": f"Bearer {self.coinbase_api_key}"}
            else:
                headers = {}
            
            response = requests.get(url, headers=headers, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            price = float(data["price"])
            volume = float(data.get("volume", 0))
            
            # Higher volume = higher confidence
            confidence = min(1.0, 0.7 + (volume / 10000000))
            
            return PriceReading(
                source=OracleSource.COINBASE,
                price_usd=price,
                timestamp=time.time(),
                confidence=confidence
            )
            
        except Exception as e:
            logger.error(f"Coinbase query failed for {symbol}: {e}")
            return None
    
    def _calculate_consensus(self, readings: List[PriceReading]) -> TriangulatedPrice:
        """
        Calculate consensus price from multiple readings
        Uses confidence-weighted average
        """
        if len(readings) < self.min_sources:
            return TriangulatedPrice(
                consensus_price=0.0,
                deviation_pct=999.0,
                readings=readings,
                is_valid=False,
                warning_message=f"Insufficient sources: {len(readings)} < {self.min_sources}"
            )
        
        # Calculate weighted average
        total_weight = sum(r.confidence for r in readings)
        if total_weight == 0:
            return TriangulatedPrice(
                consensus_price=0.0,
                deviation_pct=999.0,
                readings=readings,
                is_valid=False,
                warning_message="Total confidence weight is zero"
            )
        
        consensus_price = sum(
            r.price_usd * r.confidence for r in readings
        ) / total_weight
        
        # Calculate max deviation from consensus
        deviations = [
            abs(r.price_usd - consensus_price) / consensus_price * 100
            for r in readings
        ]
        max_deviation = max(deviations) if deviations else 0.0
        
        # Validate deviation
        is_valid = max_deviation <= self.max_deviation
        warning = None if is_valid else (
            f"Price deviation {max_deviation:.2f}% exceeds threshold {self.max_deviation}%"
        )
        
        return TriangulatedPrice(
            consensus_price=consensus_price,
            deviation_pct=max_deviation,
            readings=readings,
            is_valid=is_valid,
            warning_message=warning
        )
    
    def get_statistics(self) -> Dict:
        """Get oracle validation statistics"""
        if self.total_validations == 0:
            return {
                "total_validations": 0,
                "valid_rate": 0.0,
                "max_deviation_seen": 0.0,
            }
        
        return {
            "total_validations": self.total_validations,
            "valid_count": self.valid_count,
            "invalid_count": self.invalid_count,
            "valid_rate": (self.valid_count / self.total_validations) * 100,
            "max_deviation_seen": self.max_deviation_seen,
            "max_allowed_deviation": self.max_deviation,
        }
    
    def print_status(self):
        """Print oracle validator status"""
        stats = self.get_statistics()
        
        print("\n" + "="*80)
        print("ORACLE VALIDATOR STATUS")
        print("="*80)
        
        print(f"\nConfiguration:")
        print(f"  Max Deviation:  {self.max_deviation}%")
        print(f"  Min Sources:    {self.min_sources}")
        print(f"  Pyth API:       {'✓ Configured' if self.pyth_api_key else '✗ Not configured'}")
        print(f"  Coinbase API:   {'✓ Configured' if self.coinbase_api_key else '✗ Not configured'}")
        
        if stats['total_validations'] > 0:
            print(f"\nStatistics:")
            print(f"  Total Validations: {stats['total_validations']}")
            print(f"  Valid:             {stats['valid_count']} ({stats['valid_rate']:.1f}%)")
            print(f"  Invalid:           {stats['invalid_count']}")
            print(f"  Max Deviation:     {stats['max_deviation_seen']:.2f}%")
        
        print("="*80 + "\n")


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
    
    # Initialize Web3 (Ethereum mainnet for Chainlink)
    rpc_url = os.getenv("ETHEREUM_RPC", "https://eth.llamarpc.com")
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    
    print("Initializing oracle validator...")
    validator = OracleValidator(
        w3=w3,
        max_deviation_pct=1.0,
        min_sources=2,
        pyth_api_key=os.getenv("PYTH_API_KEY"),
        coinbase_api_key=os.getenv("COINBASE_API_KEY")
    )
    
    # Test ETH/USD validation
    print("\nValidating ETH/USD across multiple oracles...")
    result = validator.validate_price("ETH/USD")
    
    print(f"\nResult: {result}")
    print("\nIndividual Readings:")
    for reading in result.readings:
        print(f"  {reading}")
    
    if result.is_valid:
        print(f"\n✓ VALIDATION PASSED - Consensus: ${result.consensus_price:.2f}")
    else:
        print(f"\n✗ VALIDATION FAILED - {result.warning_message}")
    
    # Test BTC/USD
    print("\n" + "-"*80)
    print("\nValidating BTC/USD across multiple oracles...")
    result_btc = validator.validate_price("BTC/USD")
    
    print(f"\nResult: {result_btc}")
    print("\nIndividual Readings:")
    for reading in result_btc.readings:
        print(f"  {reading}")
    
    # Show statistics
    validator.print_status()
    
    print("\n✓ Oracle validator test complete")
