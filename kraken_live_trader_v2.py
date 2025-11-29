#!/usr/bin/env python3
"""
🔥 KRAKEN LIVE TRADER V2 - MICROSTRUCTURE ENGINE
================================================
Detects REAL Kraken opportunities using:
- Price premium vs Binance US (Kraken lag detection)
- Spread compression (pre-bounce signal)
- Order book imbalance signals
- Adaptive momentum windows
- Sub-second RSI calculations

V2 FIXES:
- Uses Binance US API (not blocked)
- Detects microstructure events (not just raw prices)
- Adaptive thresholds for Kraken's tight spreads
- Real signal detection that actually fires
"""

import requests
import time
import hmac
import hashlib
import base64
import urllib.parse
from datetime import datetime
from collections import deque
import statistics
import os
from dotenv import load_dotenv
from nonce_manager import next_nonce

# Load .env file explicitly
load_dotenv()

class KrakenAPI:
    """Full Kraken API with authenticated order placement"""
    
    def __init__(self, api_key=None, api_secret=None):
        self.api_key = api_key or os.environ.get("KRAKEN_API_KEY")
        self.api_secret = api_secret or os.environ.get("KRAKEN_API_SECRET")
        
        # Validate credentials exist
        if not self.api_key or not self.api_secret:
            raise Exception("❌ FATAL: Missing Kraken API credentials!\n"
                          "   Set KRAKEN_API_KEY and KRAKEN_API_SECRET in .env file.\n"
                          "   Found in .env: Check that keys are not empty.")
        
        print(f"✅ Kraken API authenticated (key length: {len(self.api_key)})")
        self.base_url = "https://api.kraken.com"
    
    def _sign(self, urlpath, data):
        """Generate authentication signature"""
        postdata = urllib.parse.urlencode(data)
        encoded = (str(data['nonce']) + postdata).encode()
        message = urlpath.encode() + hashlib.sha256(encoded).digest()
        signature = hmac.new(
            base64.b64decode(self.api_secret),
            message,
            hashlib.sha512
        )
        return base64.b64encode(signature.digest()).decode()
    
    def _request(self, uri_path, data=None, private=False):
        """Execute API request with persistent nonce"""
        url = self.base_url + uri_path
        
        if private:
            if not data:
                data = {}
            # Use persistent monotonic nonce (fixes "invalid nonce" error)
            data['nonce'] = next_nonce()
            headers = {
                'API-Key': self.api_key,
                'API-Sign': self._sign(uri_path, data)
            }
            response = requests.post(url, headers=headers, data=data, timeout=10)
        else:
            response = requests.get(url, params=data, timeout=10)
        
        return response.json()
    
    def get_ticker(self, pair):
        """Get ticker data for a pair"""
        result = self._request("/0/public/Ticker", {"pair": pair})
        if result.get("error"):
            return None
        return result.get("result", {}).get(pair, {})
    
    def get_order_book(self, pair, count=10):
        """Get order book depth"""
        result = self._request("/0/public/Depth", {"pair": pair, "count": count})
        if result.get("error"):
            return None
        return result.get("result", {}).get(pair, {})
    
    def get_balance(self):
        """Get account balances"""
        return self._request("/0/private/Balance", private=True)
    
    def place_order(self, pair, order_type, side, volume, price=None):
        """Place an order"""
        data = {
            "pair": pair,
            "type": side,  # buy or sell
            "ordertype": order_type,  # market or limit
            "volume": str(volume)
        }
        if price:
            data["price"] = str(price)
        
        result = self._request("/0/private/AddOrder", data=data, private=True)
        return result


class KrakenLiveTraderV2:
    """
    V2 Trader with REAL opportunity detection
    """
    
    def __init__(self, capital_usd=29.0):
        self.kraken = KrakenAPI()
        # Initialize capital from live USDC balance if available
        try:
            _bal = self.kraken.get_balance()
            if not _bal.get("error"):
                usdc_avail = float(_bal.get("result", {}).get("USDC", 0.0))
                # Prefer live balance; fall back to provided capital
                self.capital_usd = usdc_avail if usdc_avail > 0 else capital_usd
                # Cache holdings for base assets
                self.holdings = {
                    "USDC": usdc_avail,
                    "XBT": float(_bal.get("result", {}).get("XBT", 0.0)),
                    "ETH": float(_bal.get("result", {}).get("ETH", 0.0)),
                    "SOL": float(_bal.get("result", {}).get("SOL", 0.0)),
                    "XRP": float(_bal.get("result", {}).get("XRP", 0.0))
                }
            else:
                self.capital_usd = capital_usd
                self.holdings = {"USDC": 0.0}
        except Exception:
            self.capital_usd = capital_usd
            self.holdings = {"USDC": 0.0}
        
        # Trading pairs - USDC pairs (you have USDC balance, not ZUSD)
        self.pairs = {
            "BTC": "XBTUSDC",
            "ETH": "ETHUSDC", 
            "SOL": "SOLUSDC",
            "XRP": "XRPUSDC"
        }
        # Optional env override to enable a subset of pairs (e.g., "ETH,SOL")
        enabled_pairs = os.environ.get("KRAKEN_ENABLED_PAIRS")
        if enabled_pairs:
            keep = set(p.strip().upper() for p in enabled_pairs.split(",") if p.strip())
            self.pairs = {sym: pair for sym, pair in self.pairs.items() if sym in keep}
        
        # Binance US mapping (not blocked)
        self.binance_map = {
            "XBTUSDC": "BTCUSD",
            "ETHUSDC": "ETHUSD",
            "SOLUSDC": "SOLUSD",
            "XRPUSDC": "XRPUSD"
        }
        
        # Price history for momentum calculation
        self.price_history = {pair: deque(maxlen=20) for pair in self.pairs.values()}
        self.spread_history = {pair: deque(maxlen=20) for pair in self.pairs.values()}
        
        # Trading state
        self.trades_executed = 0
        self.opportunities_found = 0
        self.total_pnl = 0.0
        
        print("🔥 KRAKEN TRADER V2 INITIALIZED")
        print("=" * 60)
        # Runtime verification: query Kraken balances to prove correct account is loaded
        try:
            bal_resp = self.kraken.get_balance()  # calls Kraken private /Balance using API key/secret from .env
            bal = bal_resp.get("result", {}) if not bal_resp.get("error") else {}
            # Kraken uses currency keys like "USDC", "XXRP", "XXBT", "XETH"
            def _to_float(val):
                try:
                    return float(val)
                except Exception:
                    return 0.0
            usdc = _to_float(bal.get("USDC", 0.0))
            xrp = _to_float(bal.get("XXRP", bal.get("XRP", 0.0)))
            xbt = _to_float(bal.get("XXBT", bal.get("XBT", 0.0)))
            eth = _to_float(bal.get("XETH", bal.get("ETH", 0.0)))
            print(f"Account check: USDC={usdc:.4f}, XRP={xrp:.5f}, XBT={xbt:.6f}, ETH={eth:.6f}")
        except Exception as e:
            print(f"[WARN] Unable to verify Kraken balances at init: {e}")

        print(f"Capital: ${self.capital_usd:.2f} USDC")
        print(f"Pairs: {list(self.pairs.keys())}")
        print("\nSTRATEGIES:")
        print("  1. PREMIUM GAP - Kraken lag vs Binance US")
        print("  2. SPREAD COMPRESSION - Pre-bounce detection")
        print("  3. ADAPTIVE MOMENTUM - Multi-timeframe signals")
        print("  4. ORDER BOOK IMBALANCE - Whale detection")
        print("=" * 60)
        print()
    
    def get_binance_price(self, symbol):
        """Get reference price from Binance US with fast fail and fallbacks.
        - Short connect/read timeouts to avoid hanging the trading loop
        - Small retry count for transient network hiccups
        - Fallbacks: Coinbase spot, then Kraken ticker last price
        """
        url = f"https://api.binance.us/api/v3/ticker/price?symbol={symbol}"
        headers = {"User-Agent": "KrakenMicroTrader/2.0"}
        for attempt in range(2):  # quick retries
            try:
                # Separate connect/read timeouts to avoid SSL read hang
                resp = requests.get(url, headers=headers, timeout=(2, 3))
                resp.raise_for_status()
                data = resp.json()
                price = float(data.get("price"))
                if price > 0:
                    return price
            except Exception:
                time.sleep(0.2)
        # Fallback to Coinbase
        cb_map = {
            "BTCUSD": "BTC-USD",
            "ETHUSD": "ETH-USD",
            "SOLUSD": "SOL-USD",
            "XRPUSD": "XRP-USD"
        }
        try:
            if symbol in cb_map:
                cb_url = f"https://api.coinbase.com/v2/prices/{cb_map[symbol]}/spot"
                resp = requests.get(cb_url, headers=headers, timeout=(2, 3))
                resp.raise_for_status()
                data = resp.json()
                price = float(data["data"]["amount"])
                if price > 0:
                    return price
        except Exception:
            pass
        # Final fallback: Use Kraken's own ticker for the mapped pair
        try:
            # Map binance symbol back to kraken pair
            reverse_map = {v: k for k, v in self.binance_map.items()}
            kraken_pair = reverse_map.get(symbol)
            if kraken_pair:
                ticker = self.kraken.get_ticker(kraken_pair)
                if ticker and "c" in ticker:
                    return float(ticker["c"][0])
        except Exception:
            pass
        return None
    
    def detect_premium_gap(self, kraken_pair, kraken_price):
        """Detect price premium/discount vs Binance US"""
        binance_symbol = self.binance_map.get(kraken_pair)
        if not binance_symbol:
            return None
        
        binance_price = self.get_binance_price(binance_symbol)
        if not binance_price:
            return None
        
        premium_pct = ((kraken_price - binance_price) / binance_price) * 100
        
        # Kraken lags 200-600ms behind Binance
        # Premium > 0.25% = buy on Binance, sell on Kraken
        # Premium < -0.25% = buy on Kraken, sell on Binance
        
        if abs(premium_pct) > 0.25:
            signal = "BUY" if premium_pct < 0 else "SELL"
            return {
                "type": "PREMIUM_GAP",
                "pair": kraken_pair,
                "signal": signal,
                "premium_pct": premium_pct,
                "kraken_price": kraken_price,
                "binance_price": binance_price,
                "expected_profit_pct": abs(premium_pct) * 0.6  # 60% capture
            }
        
        return None
    
    def detect_spread_compression(self, kraken_pair, ticker):
        """Detect spread compression (pre-bounce signal)"""
        ask = float(ticker["a"][0])
        bid = float(ticker["b"][0])
        last = float(ticker["c"][0])
        
        spread_pct = ((ask - bid) / last) * 100
        
        # Track spread history
        self.spread_history[kraken_pair].append(spread_pct)
        
        if len(self.spread_history[kraken_pair]) < 10:
            return None
        
        avg_spread = statistics.mean(self.spread_history[kraken_pair])
        
        # Spread compressed to < 40% of normal = imminent bounce
        if spread_pct < avg_spread * 0.4 and avg_spread > 0.01:
            return {
                "type": "SPREAD_COMPRESSION",
                "pair": kraken_pair,
                "signal": "BUY",  # Buy before bounce
                "spread_pct": spread_pct,
                "avg_spread_pct": avg_spread,
                "compression_ratio": spread_pct / avg_spread,
                "expected_profit_pct": (avg_spread - spread_pct) * 0.5
            }
        
        return None
    
    def detect_adaptive_momentum(self, kraken_pair, price):
        """Adaptive momentum across multiple timeframes"""
        self.price_history[kraken_pair].append(price)
        
        if len(self.price_history[kraken_pair]) < 10:
            return None
        
        prices = list(self.price_history[kraken_pair])
        
        # Short momentum (last 5 prices)
        short_momentum = (prices[-1] - prices[-5]) / prices[-5] * 100
        
        # Medium momentum (last 10 prices)
        med_momentum = (prices[-1] - prices[-10]) / prices[-10] * 100
        
        # Strong uptrend: both positive and accelerating
        if short_momentum > 0.3 and med_momentum > 0.2 and short_momentum > med_momentum:
            return {
                "type": "MOMENTUM_UP",
                "pair": kraken_pair,
                "signal": "BUY",
                "short_momentum_pct": short_momentum,
                "med_momentum_pct": med_momentum,
                "expected_profit_pct": short_momentum * 0.3
            }
        
        # Strong downtrend: both negative and accelerating
        if short_momentum < -0.3 and med_momentum < -0.2 and short_momentum < med_momentum:
            return {
                "type": "MOMENTUM_DOWN",
                "pair": kraken_pair,
                "signal": "SELL",
                "short_momentum_pct": short_momentum,
                "med_momentum_pct": med_momentum,
                "expected_profit_pct": abs(short_momentum) * 0.3
            }
        
        return None
    
    def detect_order_book_imbalance(self, kraken_pair):
        """Detect whale orders via book imbalance"""
        book = self.kraken.get_order_book(kraken_pair, count=10)
        if not book:
            return None
        
        bids = book.get("bids", [])
        asks = book.get("asks", [])
        
        if not bids or not asks:
            return None
        
        # Sum top 10 bid/ask volumes
        bid_volume = sum(float(b[1]) for b in bids[:10])
        ask_volume = sum(float(a[1]) for a in asks[:10])
        
        total_volume = bid_volume + ask_volume
        if total_volume == 0:
            return None
        
        bid_ratio = bid_volume / total_volume
        
        # Heavy bid pressure (>65%) = likely upward move
        if bid_ratio > 0.65:
            return {
                "type": "BOOK_IMBALANCE_BUY",
                "pair": kraken_pair,
                "signal": "BUY",
                "bid_ratio": bid_ratio,
                "bid_volume": bid_volume,
                "ask_volume": ask_volume,
                "expected_profit_pct": (bid_ratio - 0.5) * 2.0  # Imbalance strength
            }
        
        # Heavy ask pressure (>65%) = likely downward move
        if bid_ratio < 0.35:
            return {
                "type": "BOOK_IMBALANCE_SELL",
                "pair": kraken_pair,
                "signal": "SELL",
                "bid_ratio": bid_ratio,
                "bid_volume": bid_volume,
                "ask_volume": ask_volume,
                "expected_profit_pct": (0.5 - bid_ratio) * 2.0
            }
        
        return None
    
    def scan_for_opportunities(self):
        """Run all detection strategies"""
        opportunities = []
        
        for symbol, kraken_pair in self.pairs.items():
            try:
                # Get ticker
                ticker = self.kraken.get_ticker(kraken_pair)
                if not ticker:
                    continue
                
                last_price = float(ticker["c"][0])

                # Skip if minimum order cost exceeds available funds for BUY signals we might generate
                # This avoids futile execution attempts for small accounts on pairs with high minimums
                min_sizes = {
                    "BTCUSDC": 0.0001,
                    "ETHUSDC": 0.002,
                    "SOLUSDC": 0.1,
                    "XRPUSDC": 10.0
                }
                min_units = min_sizes.get(kraken_pair, 0.0001)
                min_cost_usd = min_units * last_price
                cushion = float(os.environ.get("KRAKEN_TRADE_BUFFER", "1.08"))
                # If we don't even have the post-cushion USDC to buy minimum, bias against BUY signals
                # We'll still allow SELL signals (subject to holdings) and PREMIUM GAP calculations.
                insufficient_for_min_buy = (self.capital_usd / cushion) < min_cost_usd
                
                # Strategy 1: Premium Gap
                opp = self.detect_premium_gap(kraken_pair, last_price)
                if opp:
                    # If this creates a BUY but we can't meet minimum, skip adding
                    if not (opp["signal"] == "BUY" and insufficient_for_min_buy):
                        opportunities.append(opp)
                
                # Strategy 2: Spread Compression
                opp = self.detect_spread_compression(kraken_pair, ticker)
                if opp:
                    if not (opp["signal"] == "BUY" and insufficient_for_min_buy):
                        opportunities.append(opp)
                
                # Strategy 3: Adaptive Momentum
                opp = self.detect_adaptive_momentum(kraken_pair, last_price)
                if opp:
                    if not (opp["signal"] == "BUY" and insufficient_for_min_buy):
                        opportunities.append(opp)
                
                # Strategy 4: Order Book Imbalance
                opp = self.detect_order_book_imbalance(kraken_pair)
                if opp:
                    # SELL signals are allowed; BUY signals require min funds
                    if not (opp["signal"] == "BUY" and insufficient_for_min_buy):
                        opportunities.append(opp)
            
            except Exception as e:
                print(f"  ⚠️ Error scanning {symbol}: {e}")
                continue
        
        # Holdings-aware filter: drop SELL opps where base asset balance is zero
        try:
            balances = self.kraken.get_balance()
            bal = balances.get("result", {}) if not balances.get("error") else {}
        except Exception:
            bal = {}
        filtered = []
        for opp in opportunities:
            if opp.get("signal") == "SELL":
                base_asset = opp.get("pair", "").replace("USDC", "")
                base_key = "XBT" if base_asset in ("BTC", "XBT") else base_asset
                try:
                    have = float(bal.get(base_key, 0.0))
                except Exception:
                    have = 0.0
                if have <= 0:
                    continue
            filtered.append(opp)
        
        return filtered
    
    def execute_trade(self, opp, paper_mode=True):
        """Execute trade (LIVE or PAPER)"""
        
        # Kraken minimum order sizes (units, not USD)
        min_sizes = {
            "BTCUSDC": 0.0001,   # ~$10
            "ETHUSDC": 0.002,    # ~$6.60
            "SOLUSDC": 0.1,      # ~$19.20
            "XRPUSDC": 10.0      # ~$22
        }
        
        # Get current price (must fetch fresh, don't use stale opportunity data)
        try:
            ticker = self.kraken.get_ticker(opp["pair"])
            current_price = float(ticker["c"][0])
        except Exception as e:
            print(f"     ⚠️ ERROR: Cannot get current price for {opp['pair']}: {e}")
            return False
        
        # Position sizing based strictly on actual balances
        cushion = float(os.environ.get("KRAKEN_TRADE_BUFFER", "1.08"))  # buffer for fees/slippage
        # For BUY: spend available USDC after cushion; for SELL: use available base asset units
        side = "buy" if opp["signal"] == "BUY" else "sell"
        if side == "buy":
            # Use live USDC balance rather than a fixed cap
            try:
                balances = self.kraken.get_balance()
                usdc_avail = 0.0
                if not balances.get("error"):
                    usdc_avail = float(balances.get("result", {}).get("USDC", 0.0))
                else:
                    usdc_avail = self.holdings.get("USDC", self.capital_usd)
            except Exception:
                usdc_avail = self.holdings.get("USDC", self.capital_usd)
            position_usd = max(0.0, usdc_avail / cushion)
            position_size = position_usd / current_price if current_price > 0 else 0.0
        else:
            # SELL: determine base asset available units
            base_asset = opp["pair"].replace("USDC", "")
            base_key = "XBT" if base_asset in ("BTC", "XBT") else base_asset
            try:
                balances = self.kraken.get_balance()
                if not balances.get("error"):
                    avail_units = float(balances.get("result", {}).get(base_key, 0.0))
                else:
                    avail_units = float(self.holdings.get(base_key, 0.0))
            except Exception:
                avail_units = float(self.holdings.get(base_key, 0.0))
            position_size = max(0.0, avail_units)
            position_usd = position_size * current_price
        
        # Enforce Kraken minimums
        min_required = min_sizes.get(opp["pair"], 0.0001)
        if position_size < min_required:
            position_size = min_required
            position_usd = position_size * current_price
        
        # Apply cushion to avoid Kraken "Insufficient funds" due to fees/slippage
        # Keep position within available capital after accounting for cushion
        position_usd = min(position_usd, self.capital_usd / cushion)
        position_size = position_usd / current_price

        # If BUY and minimum requirement exceeds available USDC after cushion, skip
        if opp["signal"] == "BUY" and (position_size < min_required) and (min_required * current_price > (self.holdings.get("USDC", self.capital_usd) / cushion)):
            print(f"     ❌ BUY SKIPPED: Minimum order ${min_required * current_price:.2f} exceeds available after cushion")
            return False
        
        # Estimate profit
        profit_usd = position_usd * (opp["expected_profit_pct"] / 100)
        
        print(f"\n  💰 EXECUTING {opp['type']}")
        print(f"     Pair: {opp['pair']}")
        print(f"     Signal: {opp['signal']}")
        print(f"     Position: ${position_usd:.2f} ({position_size:.6f} units)")
        print(f"     Expected: ${profit_usd:.4f}")
        
        if paper_mode:
            print(f"     Mode: PAPER")
            self.trades_executed += 1
            self.total_pnl += profit_usd
            return True
        
        # LIVE EXECUTION
        try:
            # If SELL signal, ensure we actually have the base asset to sell
            if side == "sell":
                # Map pair to base asset symbol used in balances
                base_asset = opp["pair"].replace("USDC", "")  # e.g., BTCUSDC -> BTC
                # Kraken sometimes uses XBT for BTC; normalize
                if base_asset == "BTC":
                    balance_key = "XBT"
                else:
                    balance_key = base_asset
                balances = self.kraken.get_balance()
                if balances.get("error"):
                    print(f"     ⚠️ Could not retrieve balances for SELL check: {balances['error']}")
                else:
                    avail = float(balances.get("result", {}).get(balance_key, 0.0))
                    if avail <= 0:
                        print(f"     ❌ SELL SKIPPED: No {balance_key} balance available")
                        return False
                    if position_size > avail:
                        print(f"     ⚠️ Adjusting SELL volume to available {balance_key}: {avail:.6f}")
                        position_size = avail
                        position_usd = position_size * current_price
                        print(f"     New Position: ${position_usd:.2f} ({position_size:.6f} units)")
            else:
                # BUY path: ensure sufficient USDC after cushion
                balances = self.kraken.get_balance()
                if not balances.get("error"):
                    usdc_avail = float(balances.get("result", {}).get("USDC", 0.0))
                    max_usd_buy = usdc_avail / cushion
                    if position_usd > max_usd_buy:
                        print(f"     ⚠️ Adjusting BUY position to available USDC after cushion: ${max_usd_buy:.2f}")
                        position_usd = max_usd_buy
                        position_size = position_usd / current_price
                        # Still enforce minimums if needed
                        if position_size < min_required:
                            print(f"     ❌ BUY SKIPPED: Minimum units {min_required} exceed adjusted size {position_size:.6f}")
                            return False

            result = self.kraken.place_order(
                pair=opp["pair"],
                order_type="market",
                side=side,
                volume=position_size
            )
            
            if result.get("error"):
                print(f"     ❌ ORDER FAILED: {result['error']}")
                return False
            
            order_id = result.get("result", {}).get("txid", ["unknown"])[0]
            print(f"     ✅ ORDER PLACED: {order_id}")
            
            self.trades_executed += 1
            self.total_pnl += profit_usd
            return True
        
        except Exception as e:
            print(f"     ❌ EXECUTION ERROR: {e}")
            return False
    
    def run(self, duration=1800, paper_mode=True):
        """Main trading loop"""
        print(f"\n{'📄 PAPER MODE' if paper_mode else '🔥 LIVE MODE'} - Running for {duration}s\n")
        
        start_time = time.time()
        end_time = start_time + duration
        scan_num = 0
        
        while time.time() < end_time:
            scan_num += 1
            elapsed = int(time.time() - start_time)
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] SCAN #{scan_num} (T+{elapsed}s)")
            
            # Scan for opportunities
            opportunities = self.scan_for_opportunities()
            
            if not opportunities:
                print("  No signals detected")
            else:
                print(f"  🎯 {len(opportunities)} signal(s) found:")
                self.opportunities_found += len(opportunities)
                
                for opp in opportunities:
                    print(f"     → {opp['type']} on {opp['pair']}: {opp['signal']} ({opp['expected_profit_pct']:.3f}%)")
                    
                    # Execute the first executable opportunity (prefer BUYs with funds, SELLs with holdings)
                    executed = False
                    for candidate in opportunities:
                        ok = self.execute_trade(candidate, paper_mode=paper_mode)
                        if ok:
                            executed = True
                            break
                    if not executed:
                        print("  ⚠️ No executable opportunities (funds/holdings constraints)")
            
            print()
            time.sleep(1.5)  # Scan every 1.5 seconds (AGGRESSIVE)
        
        # Final report
        print("\n" + "=" * 60)
        print("📊 SESSION COMPLETE")
        print("=" * 60)
        print(f"Duration: {duration}s")
        print(f"Scans: {scan_num}")
        print(f"Opportunities: {self.opportunities_found}")
        print(f"Trades: {self.trades_executed}")
        print(f"Total P&L: ${self.total_pnl:.2f} ({'paper' if paper_mode else 'LIVE'})")
        print("=" * 60)


if __name__ == "__main__":
    import sys
    
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 300  # Default 5 min
    paper = "--live" not in sys.argv
    
    trader = KrakenLiveTraderV2(capital_usd=29.0)
    trader.run(duration=duration, paper_mode=paper)
