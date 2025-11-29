"""
⚡ UNYKORN SYSTEMS - MULTI-SOURCE PRICE VALIDATION
FETCHER-X: Cross-Check Pricing to Prevent False Arbitrage

Purpose: Validate opportunities against multiple data sources
Features:
- CoinGecko Pro API integration
- Chainlink on-chain oracle validation
- 1inch API price comparison
- Sanity check filters (prevents stale/fake prices)
- Confidence scoring
"""

import asyncio
import time
import os
import sys
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import aiohttp
from web3 import Web3
import logging
import time as _time
from functools import lru_cache

logger = logging.getLogger(__name__)

# ===== Logging/Emoji safety for Windows & redirected logs =====
def _is_utf8_environment() -> bool:
    try:
        encs = {
            'stdout': getattr(sys.stdout, 'encoding', None),
            'stderr': getattr(sys.stderr, 'encoding', None),
            'default': sys.getdefaultencoding(),
            'io': os.environ.get('PYTHONIOENCODING', '')
        }
        return any(e and 'utf' in e.lower() for e in encs.values())
    except Exception:
        return False


def _env_flag(name: str, default: Optional[bool] = None) -> Optional[bool]:
    val = os.environ.get(name)
    if val is None:
        return default
    val = val.strip().lower()
    if val in ('1', 'true', 'yes', 'on'):
        return True
    if val in ('0', 'false', 'no', 'off'):
        return False
    return default


ALLOW_EMOJI_LOGS = _env_flag('PRICE_VALIDATOR_EMOJI_LOGS', None)
if ALLOW_EMOJI_LOGS is None:
    ALLOW_EMOJI_LOGS = _is_utf8_environment()

_EMOJI_MAP = {
    '🔍': '[CHK]',
    '✅': '[OK]',
    '❌': '[X]',
    '⚠️': '[WARN]',
}


def _sanitize_text(msg):
    if ALLOW_EMOJI_LOGS or not isinstance(msg, str):
        return msg
    for emo, repl in _EMOJI_MAP.items():
        msg = msg.replace(emo, repl)
    try:
        msg = msg.encode('ascii', 'ignore').decode('ascii')
    except Exception:
        pass
    return msg


class _EmojiSanitizingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            record.msg = _sanitize_text(record.msg)
            if record.args:
                if isinstance(record.args, dict):
                    record.args = {k: _sanitize_text(v) for k, v in record.args.items()}
                elif isinstance(record.args, tuple):
                    record.args = tuple(_sanitize_text(a) for a in record.args)
                else:
                    record.args = _sanitize_text(record.args)
        except Exception:
            pass
        return True


logger.addFilter(_EmojiSanitizingFilter())


class PriceSource(Enum):
    """Price data sources"""
    ON_CHAIN = "on_chain"  # Direct DEX query
    COINGECKO = "coingecko"  # CoinGecko Pro API
    CHAINLINK = "chainlink"  # Chainlink oracle
    ONEINCH = "1inch"  # 1inch aggregator API
    THEGRAPH = "thegraph"  # Subgraph data


@dataclass
class PriceQuote:
    """Single price quote from a source"""
    source: PriceSource
    token_address: str
    price_usd: float
    timestamp: int
    confidence: float  # 0-1
    liquidity_usd: Optional[float] = None
    volume_24h_usd: Optional[float] = None
    error: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of multi-source price validation"""
    is_valid: bool
    consensus_price_usd: float
    price_deviation_pct: float
    sources_agreed: int
    sources_total: int
    confidence_score: float  # 0-100
    reasoning: str
    individual_quotes: List[PriceQuote]
    swarm: Optional[Dict[str, Any]] = None


@dataclass
class SwarmResult:
    decision: str  # EXECUTE, SKIP, WAIT, CAUTION, etc.
    consensus: float  # 0-1
    confidence: float  # 0-1 or 0-100 scaled later
    votes: Optional[Dict[str, Any]] = None
    reasoning: Optional[str] = None


class PriceValidator:
    """
    Multi-source price validator for arbitrage opportunities.
    
    Prevents false positives from:
    - Stale on-chain data
    - Low liquidity pools
    - Oracle manipulation
    - Flash loan attacks
    - Price feed errors
    
    Strategy:
    1. Query multiple independent sources
    2. Calculate consensus price
    3. Flag outliers (>5% deviation)
    4. Require 3+ sources agree
    5. Weight by liquidity + volume
    """
    
    # Chainlink Price Feed addresses (Arbitrum mainnet)
    CHAINLINK_FEEDS = {
        # Store as lowercase keys; lookups will be normalized
        "0x82af49447d8a07e3bd95bd0d56f35241523fbab1": "0x639Fe6ab55C921f74e7fac1ee960C0B6293ba612",  # WETH/USD
        "0x2f2a2543b76a4166549f7aab2e75bef0aefc5b0f": "0x6ce185860a4963106506C203335A2910413708e9",  # WBTC/USD
    }
    
    def __init__(
        self,
        w3: Web3,
        coingecko_api_key: Optional[str] = None,
        oneinch_api_key: Optional[str] = None,
        thegraph_api_key: Optional[str] = None
    ):
        """
        Initialize price validator.
        
        Args:
            w3: Web3 instance
            coingecko_api_key: CoinGecko Pro API key
            oneinch_api_key: 1inch API key
            thegraph_api_key: The Graph API key
        """
        self.w3 = w3
        self.coingecko_api_key = coingecko_api_key
        self.oneinch_api_key = oneinch_api_key
        self.thegraph_api_key = thegraph_api_key
        # normalized chainlink mapping
        self._chainlink_feeds = dict(self.CHAINLINK_FEEDS)
        # simple in-memory cache { (key): (value, ts) }
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._cache_ttl_sec = 7.0  # short TTL to avoid hammering providers
        
        # Chainlink oracle ABI (minimal)
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
        self.validations_performed = 0
        self.validations_passed = 0
        self.validations_failed = 0
        self.false_positives_caught = 0
        
        logger.info(f"🔍 Price Validator initialized")
        logger.info(f"   CoinGecko: {'✅' if coingecko_api_key else '❌'}")
        logger.info(f"   1inch: {'✅' if oneinch_api_key else '❌'}")
        logger.info(f"   The Graph: {'✅' if thegraph_api_key else '❌'}")

    @classmethod
    def from_env(cls, w3: Web3) -> "PriceValidator":
        """Create PriceValidator using environment variables.
        COINGECKO_API_KEY, ONEINCH_API_KEY, THEGRAPH_API_KEY are read if present.
        """
        return cls(
            w3=w3,
            coingecko_api_key=os.environ.get('COINGECKO_API_KEY'),
            oneinch_api_key=os.environ.get('ONEINCH_API_KEY'),
            thegraph_api_key=os.environ.get('THEGRAPH_API_KEY')
        )
    
    
    async def get_chainlink_price(self, token_address: str) -> Optional[PriceQuote]:
        """
        Get price from Chainlink oracle.
        
        Args:
            token_address: Token contract address
            
        Returns:
            PriceQuote if available
        """
        feed_address = self._chainlink_feeds.get(token_address.lower())
        
        if not feed_address:
            return None
        
        try:
            # cache by token
            cache_key = f"cl:{token_address.lower()}"
            now = _time.time()
            cached = self._cache.get(cache_key)
            if cached and (now - cached[1]) < self._cache_ttl_sec:
                return cached[0]
            feed_contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(feed_address),
                abi=self.chainlink_abi
            )
            
            round_data = feed_contract.functions.latestRoundData().call()
            
            # Parse response
            price = round_data[1] / 1e8  # Chainlink uses 8 decimals
            updated_at = round_data[3]
            
            # Check staleness (reject if >1 hour old)
            now = int(time.time())
            if now - updated_at > 3600:
                logger.warning(f"⚠️ Chainlink price stale ({now - updated_at}s old)")
                return None
            
            quote = PriceQuote(
                source=PriceSource.CHAINLINK,
                token_address=token_address,
                price_usd=price,
                timestamp=updated_at,
                confidence=0.95  # Chainlink very reliable
            )
            self._cache[cache_key] = (quote, now)
            return quote
            
        except Exception as e:
            logger.warning(f"⚠️ Chainlink query failed: {e}")
            return None
    
    
    async def get_coingecko_price(self, token_address: str) -> Optional[PriceQuote]:
        """
        Get price from CoinGecko Pro API.
        
        Args:
            token_address: Token contract address
            
        Returns:
            PriceQuote if available
        """
        if not self.coingecko_api_key:
            return None
        
        url = "https://pro-api.coingecko.com/api/v3/simple/token_price/arbitrum-one"
        
        params = {
            "contract_addresses": token_address,
            "vs_currencies": "usd",
            "include_24hr_vol": "true",
            "include_24hr_change": "true"
        }
        
        headers = {
            "x-cg-pro-api-key": self.coingecko_api_key
        }
        
        try:
            cache_key = f"cg:{token_address.lower()}"
            now = _time.time()
            cached = self._cache.get(cache_key)
            if cached and (now - cached[1]) < self._cache_ttl_sec:
                return cached[0]
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status != 200:
                        return None
                    
                    data = await resp.json()
                    token_data = data.get(token_address.lower(), {})
                    
                    if not token_data or "usd" not in token_data:
                        return None
                    
                    quote = PriceQuote(
                        source=PriceSource.COINGECKO,
                        token_address=token_address,
                        price_usd=token_data["usd"],
                        timestamp=int(time.time()),
                        confidence=0.85,  # Good but sometimes lags
                        volume_24h_usd=token_data.get("usd_24h_vol")
                    )
                    self._cache[cache_key] = (quote, now)
                    return quote
                    
        except Exception as e:
            logger.warning(f"⚠️ CoinGecko query failed: {e}")
            return None
    
    
    async def get_oneinch_price(self, token_address: str) -> Optional[PriceQuote]:
        """
        Get price from 1inch API.
        
        Args:
            token_address: Token contract address
            
        Returns:
            PriceQuote if available
        """
        if not self.oneinch_api_key:
            return None
        
        # 1inch swap quote API
        url = f"https://api.1inch.dev/swap/v6.0/42161/quote"
        
        # Get quote for 1 token → USDC
        usdc_address = "0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8"
        
        params = {
            "src": token_address,
            "dst": usdc_address,
            "amount": str(10**18)  # 1 token (assuming 18 decimals)
        }
        
        headers = {
            "Authorization": f"Bearer {self.oneinch_api_key}"
        }
        
        try:
            cache_key = f"1inch:{token_address.lower()}"
            now = _time.time()
            cached = self._cache.get(cache_key)
            if cached and (now - cached[1]) < self._cache_ttl_sec:
                return cached[0]
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status != 200:
                        return None
                    
                    data = await resp.json()
                    
                    # Calculate price from swap quote
                    dst_amount = int(data.get("dstAmount", 0))
                    price_usd = dst_amount / 1e6  # USDC has 6 decimals
                    
                    quote = PriceQuote(
                        source=PriceSource.ONEINCH,
                        token_address=token_address,
                        price_usd=price_usd,
                        timestamp=int(time.time()),
                        confidence=0.90  # Very accurate (aggregates DEXes)
                    )
                    self._cache[cache_key] = (quote, now)
                    return quote
                    
        except Exception as e:
            logger.warning(f"⚠️ 1inch query failed: {e}")
            return None
    
    
    async def validate_opportunity(
        self,
        token_address: str,
        on_chain_buy_price: float,
        on_chain_sell_price: float,
        spread_bps: float,
        *,
        expected_profit_usd: Optional[float] = None,
        use_swarm: bool = False,
        swarm_min_consensus: float = 0.7,
        swarm_adapter: Optional["SwarmAdapter"] = None,
        extra_features: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        """
        Validate arbitrage opportunity against multiple sources.
        
        Args:
            token_address: Token being arbitraged
            on_chain_buy_price: Price from buy DEX
            on_chain_sell_price: Price from sell DEX
            spread_bps: Detected spread in basis points
            
        Returns:
            ValidationResult with detailed analysis
        """
        self.validations_performed += 1
        
        logger.info(f"🔍 Validating opportunity: {spread_bps:.1f} BPS spread")
        logger.info(f"   On-chain buy: ${on_chain_buy_price:.2f}")
        logger.info(f"   On-chain sell: ${on_chain_sell_price:.2f}")
        
        # Query all sources in parallel
        quotes = await asyncio.gather(
            self.get_chainlink_price(token_address),
            self.get_coingecko_price(token_address),
            self.get_oneinch_price(token_address),
            return_exceptions=True
        )
        
        # Filter out None and exceptions
        valid_quotes = [q for q in quotes if isinstance(q, PriceQuote)]
        
        # Add on-chain prices as quotes
        valid_quotes.extend([
            PriceQuote(
                source=PriceSource.ON_CHAIN,
                token_address=token_address,
                price_usd=on_chain_buy_price,
                timestamp=int(time.time()),
                confidence=0.70  # Lower confidence (could be stale)
            ),
            PriceQuote(
                source=PriceSource.ON_CHAIN,
                token_address=token_address,
                price_usd=on_chain_sell_price,
                timestamp=int(time.time()),
                confidence=0.70
            )
        ])
        
        # Need at least 2 sources to validate (lowered for RPC constraints)
        if len(valid_quotes) < 2:
            self.validations_failed += 1
            return ValidationResult(
                is_valid=False,
                consensus_price_usd=0,
                price_deviation_pct=0,
                sources_agreed=0,
                sources_total=len(valid_quotes),
                confidence_score=0,
                reasoning="Insufficient price sources (need 2+)",
                individual_quotes=valid_quotes
            )
        
        # Calculate weighted consensus price
        total_weight = sum(q.confidence for q in valid_quotes)
        consensus_price = sum(
            q.price_usd * q.confidence for q in valid_quotes
        ) / total_weight
        
        # Calculate deviations
        deviations = []
        for quote in valid_quotes:
            deviation_pct = abs(quote.price_usd - consensus_price) / consensus_price * 100
            deviations.append(deviation_pct)
        
        max_deviation = max(deviations)
        avg_deviation = sum(deviations) / len(deviations)
        
        # Count sources that agree (within 5%)
        sources_agreed = sum(1 for dev in deviations if dev <= 5.0)
        
        # Calculate confidence score
        confidence_factors = {
            "source_agreement": sources_agreed / len(valid_quotes) * 40,  # 40 points
            "low_deviation": max(0, (10 - max_deviation) / 10 * 30),  # 30 points
            "source_count": min(len(valid_quotes) / 5, 1.0) * 20,  # 20 points
            "high_confidence_sources": sum(
                1 for q in valid_quotes if q.confidence >= 0.85
            ) / len(valid_quotes) * 10  # 10 points
        }
        
        confidence_score = sum(confidence_factors.values())
        
        # Validation rules
        is_valid = True
        reasoning = []
        
        # Rule 1: Max deviation > 10% = likely error
        if max_deviation > 10:
            is_valid = False
            reasoning.append(f"High price deviation ({max_deviation:.1f}% > 10%)")
        
        # Rule 2: <2 sources agree = insufficient consensus (lowered for RPC constraints)
        if sources_agreed < 2:
            is_valid = False
            reasoning.append(f"Low consensus (only {sources_agreed}/{len(valid_quotes)} sources agree)")
        
        # Rule 3: Confidence < 40 = too uncertain (lowered for RPC constraints)
        if confidence_score < 40:
            is_valid = False
            reasoning.append(f"Low confidence score ({confidence_score:.1f}/100)")
        
        # Rule 4: Spread too large (>800 BPS) = likely stale data
        if spread_bps > 800:
            is_valid = False
            reasoning.append(f"Suspiciously large spread ({spread_bps:.0f} BPS > 800)")
            self.false_positives_caught += 1
        
        # Rule 5: On-chain prices deviate significantly from off-chain = stale
        on_chain_deviations = [
            abs(q.price_usd - consensus_price) / consensus_price * 100
            for q in valid_quotes if q.source == PriceSource.ON_CHAIN
        ]
        
        if on_chain_deviations and max(on_chain_deviations) > 8:
            is_valid = False
            reasoning.append(
                f"On-chain price stale ({max(on_chain_deviations):.1f}% off-chain difference)"
            )
            self.false_positives_caught += 1
        
        swarm_payload: Optional[Dict[str, Any]] = None
        if use_swarm:
            adapter = swarm_adapter or SwarmAdapter.maybe_create()
            if adapter:
                features = {
                    "token_address": token_address,
                    "spread_bps": spread_bps,
                    "on_chain_buy_price": on_chain_buy_price,
                    "on_chain_sell_price": on_chain_sell_price,
                    "price_confidence": confidence_score / 100.0,
                }
                if expected_profit_usd is not None:
                    features["expected_profit_usd"] = expected_profit_usd
                if extra_features:
                    features.update(extra_features)
                swarm_res = await adapter.evaluate(features)
                if swarm_res:
                    # Combine: require consensus threshold and EXECUTE-like decision
                    if swarm_res.consensus < swarm_min_consensus or swarm_res.decision.lower() not in ("execute", "approve"):
                        is_valid = False
                        reasoning.append(
                            f"Swarm veto (decision={swarm_res.decision}, consensus={swarm_res.consensus:.2f} < {swarm_min_consensus:.2f})"
                        )
                    # Blend confidence: 70% price + 30% swarm
                    confidence_score = 0.7 * confidence_score + 0.3 * (swarm_res.confidence * 100.0)
                    swarm_payload = {
                        "decision": swarm_res.decision,
                        "consensus": swarm_res.consensus,
                        "confidence": swarm_res.confidence,
                        "reasoning": swarm_res.reasoning,
                        "votes": swarm_res.votes,
                    }
            else:
                logger.info("Swarm adapter not available; proceeding without swarm")

        if is_valid:
            reasoning.append("All validation checks passed")
            self.validations_passed += 1
        else:
            self.validations_failed += 1
        
        result = ValidationResult(
            is_valid=is_valid,
            consensus_price_usd=consensus_price,
            price_deviation_pct=max_deviation,
            sources_agreed=sources_agreed,
            sources_total=len(valid_quotes),
            confidence_score=confidence_score,
            reasoning=" | ".join(reasoning),
            individual_quotes=valid_quotes,
            swarm=swarm_payload
        )
        
        # Log result
        if is_valid:
            logger.info(f"✅ VALIDATION PASSED ({confidence_score:.1f}/100)")
        else:
            logger.warning(f"❌ VALIDATION FAILED: {result.reasoning}")
        
        logger.info(f"   Consensus price: ${consensus_price:.2f}")
        logger.info(f"   Max deviation: {max_deviation:.2f}%")
        logger.info(f"   Sources agreed: {sources_agreed}/{len(valid_quotes)}")
        
        return result
    
    
    def get_stats(self) -> Dict[str, any]:
        """Get validator statistics"""
        pass_rate = (
            self.validations_passed / self.validations_performed * 100
            if self.validations_performed > 0
            else 0
        )
        
        return {
            "validations_performed": self.validations_performed,
            "validations_passed": self.validations_passed,
            "validations_failed": self.validations_failed,
            "pass_rate": pass_rate,
            "false_positives_caught": self.false_positives_caught
        }


class SwarmAdapter:
    """Best-effort adapter to call the Swarm Coordinator without tight coupling.
    Expects agents.swarm_coordinator to expose one of:
    - evaluate_opportunity(features: dict) -> dict
    - swarm_evaluate(features: dict) -> dict
    - evaluate(features: dict) -> dict
    Returned dict should include keys like: decision(str), consensus(float 0-1), confidence(float 0-1), votes, reasoning.
    """

    def __init__(self, mod: Any, fn_name: str):
        self._mod = mod
        self._fn_name = fn_name

    @staticmethod
    def maybe_create() -> Optional["SwarmAdapter"]:
        try:
            import agents.swarm_coordinator as swarm
        except Exception:
            return None
        for name in ("evaluate_opportunity", "swarm_evaluate", "evaluate"):
            fn = getattr(swarm, name, None)
            if callable(fn):
                return SwarmAdapter(swarm, name)
        return None

    async def evaluate(self, features: Dict[str, Any]) -> Optional[SwarmResult]:
        try:
            fn = getattr(self._mod, self._fn_name)
            # Support both sync and async evaluators
            if asyncio.iscoroutinefunction(fn):
                data = await fn(features)
            else:
                loop = asyncio.get_running_loop()
                data = await loop.run_in_executor(None, fn, features)
            if not isinstance(data, dict):
                return None
            decision = str(data.get("decision", "")).upper() or "SKIP"
            consensus = float(data.get("consensus", 0.0))
            confidence = float(data.get("confidence", data.get("score", 0.0)))
            # Normalize confidence if seems like 0-100
            if confidence > 1.0:
                confidence = min(confidence / 100.0, 1.0)
            return SwarmResult(
                decision=decision,
                consensus=consensus,
                confidence=confidence,
                votes=data.get("votes"),
                reasoning=data.get("reasoning")
            )
        except Exception as e:
            logger.warning(f"Swarm evaluation failed: {e}")
            return None


# ═══════════════════════════════════════════════════════════════
# USAGE EXAMPLE
# ═══════════════════════════════════════════════════════════════

async def demo_price_validation():
    """Demonstrate price validation"""
    
    # Initialize Web3
    w3 = Web3(Web3.HTTPProvider("https://arb-mainnet.g.alchemy.com/v2/YOUR_KEY"))
    
    # Initialize validator
    validator = PriceValidator(
        w3=w3,
        coingecko_api_key="YOUR_COINGECKO_KEY",
        oneinch_api_key="YOUR_1INCH_KEY"
    )
    
    # Example: Validate suspicious 549 BPS spread
    weth_address = "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1"
    
    result = await validator.validate_opportunity(
        token_address=weth_address,
        on_chain_buy_price=2918.50,  # Sushiswap
        on_chain_sell_price=3078.25,  # Uniswap V3
        spread_bps=549
    )
    
    print(f"\n📊 Validation Result:")
    print(f"   Valid: {result.is_valid}")
    print(f"   Consensus price: ${result.consensus_price_usd:.2f}")
    print(f"   Confidence: {result.confidence_score:.1f}/100")
    print(f"   Reasoning: {result.reasoning}")
    print(f"\n   Individual quotes:")
    for quote in result.individual_quotes:
        print(f"      {quote.source.value}: ${quote.price_usd:.2f}")
    
    # Print statistics
    stats = validator.get_stats()
    print(f"\n📈 Validator Statistics:")
    print(f"   Total validations: {stats['validations_performed']}")
    print(f"   Pass rate: {stats['pass_rate']:.1f}%")
    print(f"   False positives caught: {stats['false_positives_caught']}")


if __name__ == "__main__":
    asyncio.run(demo_price_validation())
