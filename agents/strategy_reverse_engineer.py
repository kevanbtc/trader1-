"""
🔄 STRATEGY REVERSE ENGINEER
Analyzes past signals to determine what strategy SHOULD have been used.

Reverse engineers:
- Long-term holds (1d, 3d, 7d, 30d)
- Swing trades (4hr, 8hr, 24hr)
- Different entries (DCA, laddered, better timing)
- Optimal strategy recommendation

Shows what we SHOULD have done vs what we DID.
"""

import time
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path

class StrategyReverseEngineer:
    def __init__(self):
        self.api_key = "f168377cf78600f6aa2fe2bde6bb57a6ebeb87c2f74f27e1e1e9fbfbe9e7c3aa"
        self.base_url = "https://min-api.cryptocompare.com/data"
        
        # Data storage
        self.data_dir = Path("data")
        self.report_dir = Path("reports/strategy_analysis")
        self.data_dir.mkdir(exist_ok=True)
        self.report_dir.mkdir(parents=True, exist_ok=True)
        
        self.analysis_file = self.data_dir / "strategy_analysis.json"
        
        # Time horizons for analysis (12hr max)
        self.timeframes = {
            'scalp': [5, 15, 30, 60],     # minutes
            'intraday': [2, 4, 6, 8, 10, 12]  # hours (max 12hr)
        }
        
        # Position sizes for comparison
        self.position_scenarios = {
            'conservative': 0.25,  # 25% of capital
            'moderate': 0.40,      # 40% of capital
            'aggressive': 0.60,    # 60% of capital
            'full': 1.0            # 100% of capital
        }
        
        # Capital scenarios
        self.capital_levels = [100, 500, 1000, 5000, 10000]
        
        # Load existing data
        self.analysis_data = self._load_data()
        
    def _load_data(self):
        """Load existing analysis data"""
        if self.analysis_file.exists():
            with open(self.analysis_file, 'r') as f:
                return json.load(f)
        return {'signals': [], 'summary': {}}
    
    def _save_data(self):
        """Save analysis data"""
        with open(self.analysis_file, 'w') as f:
            json.dump(self.analysis_data, f, indent=2)
    
    def get_historical_price(self, symbol, timestamp):
        """Get price at specific timestamp"""
        try:
            url = f"{self.base_url}/pricehistorical"
            params = {
                'fsym': symbol,
                'tsyms': 'USD',
                'ts': int(timestamp),
                'api_key': self.api_key
            }
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if symbol in data:
                return data[symbol]['USD']
            return None
        except Exception as e:
            print(f"Error fetching historical price: {e}")
            return None
    
    def get_price_range(self, symbol, hours_back):
        """Get price range over time period"""
        try:
            url = f"{self.base_url}/v2/histohour"
            params = {
                'fsym': symbol,
                'tsym': 'USD',
                'limit': hours_back,
                'api_key': self.api_key
            }
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if 'Data' in data and 'Data' in data['Data']:
                prices = [candle['close'] for candle in data['Data']['Data']]
                return {
                    'current': prices[-1],
                    'high': max(prices),
                    'low': min(prices),
                    'avg': sum(prices) / len(prices),
                    'prices': prices
                }
            return None
        except Exception as e:
            print(f"Error fetching price range: {e}")
            return None
    
    def analyze_strategy_outcomes(self, signal_entry):
        """Analyze what would've happened with different strategies"""
        token = signal_entry['token']
        entry_price = signal_entry['entry_price']
        direction = signal_entry['direction']
        entry_time = datetime.fromisoformat(signal_entry['timestamp'])
        
        results = {
            'token': token,
            'entry_price': entry_price,
            'entry_time': signal_entry['timestamp'],
            'direction': direction,
            'strategies': {}
        }
        
        # 1. SCALP TRADING (minutes)
        print(f"   📊 Analyzing scalp trades (5-60 min)...")
        scalp_results = {}
        for minutes in self.timeframes['scalp']:
            future_time = entry_time + timedelta(minutes=minutes)
            if future_time > datetime.now():
                continue
                
            exit_price = self.get_historical_price(token, future_time.timestamp())
            if exit_price:
                if direction == 'LONG':
                    pnl_pct = ((exit_price - entry_price) / entry_price) * 100
                else:  # SHORT
                    pnl_pct = ((entry_price - exit_price) / entry_price) * 100
                
                scalp_results[f'{minutes}min'] = {
                    'exit_price': exit_price,
                    'pnl_pct': round(pnl_pct, 2),
                    'outcome': 'WIN' if pnl_pct > 0 else 'LOSS'
                }
        
        results['strategies']['scalp'] = scalp_results
        
        # 2. INTRADAY TRADING (2-12 hours)
        print(f"   📊 Analyzing intraday trades (2-12 hr)...")
        intraday_results = {}
        for hours in self.timeframes['intraday']:
            future_time = entry_time + timedelta(hours=hours)
            if future_time > datetime.now():
                continue
                
            exit_price = self.get_historical_price(token, future_time.timestamp())
            if exit_price:
                if direction == 'LONG':
                    pnl_pct = ((exit_price - entry_price) / entry_price) * 100
                else:
                    pnl_pct = ((entry_price - exit_price) / entry_price) * 100
                
                intraday_results[f'{hours}hr'] = {
                    'exit_price': exit_price,
                    'pnl_pct': round(pnl_pct, 2),
                    'outcome': 'WIN' if pnl_pct > 0 else 'LOSS'
                }
        
        results['strategies']['intraday'] = intraday_results
        
        # 4. FIND OPTIMAL STRATEGY
        all_outcomes = []
        for strategy_type, outcomes in results['strategies'].items():
            for timeframe, data in outcomes.items():
                all_outcomes.append({
                    'strategy': strategy_type,
                    'timeframe': timeframe,
                    'pnl_pct': data['pnl_pct'],
                    'exit_price': data['exit_price']
                })
        
        if all_outcomes:
            best = max(all_outcomes, key=lambda x: x['pnl_pct'])
            worst = min(all_outcomes, key=lambda x: x['pnl_pct'])
            
            results['optimal_strategy'] = {
                'best': best,
                'worst': worst,
                'recommendation': self._get_strategy_recommendation(best, worst)
            }
        
        return results
    
    def _get_strategy_recommendation(self, best, worst):
        """Determine what strategy should've been used"""
        best_pnl = best['pnl_pct']
        
        if best_pnl > 15:
            return f"🟢 INTRADAY HOLD would've been OPTIMAL! {best['strategy']} for {best['timeframe']} = +{best_pnl}%"
        elif best_pnl > 8:
            return f"🟡 EXTENDED HOLD (4-12hr) better! {best['strategy']} for {best['timeframe']} = +{best_pnl}%"
        elif best_pnl > 3:
            return f"🔵 SCALP worked! {best['strategy']} for {best['timeframe']} = +{best_pnl}%"
        elif best_pnl > 0:
            return f"⚪ Marginal profit. {best['strategy']} for {best['timeframe']} = +{best_pnl}%"
        else:
            return f"🔴 ALL strategies lost! Best was {best['strategy']} for {best['timeframe']} = {best_pnl}%"
    
    def analyze_entry_improvements(self, signal_entry):
        """Analyze if different entry timing would've been better"""
        token = signal_entry['token']
        entry_price = signal_entry['entry_price']
        entry_time = datetime.fromisoformat(signal_entry['timestamp'])
        
        print(f"   📊 Analyzing alternative entry points...")
        
        # Check prices 1hr before and after signal
        price_window = self.get_price_range(token, hours_back=2)
        
        if not price_window:
            return None
        
        better_entries = []
        
        # For LONG: lower prices = better entry
        # For SHORT: higher prices = better entry
        direction = signal_entry['direction']
        
        if direction == 'LONG':
            # Find lower prices within window
            for i, price in enumerate(price_window['prices']):
                if price < entry_price:
                    improvement_pct = ((entry_price - price) / entry_price) * 100
                    better_entries.append({
                        'price': price,
                        'improvement': round(improvement_pct, 2),
                        'timing': f'{i} hours from signal'
                    })
        else:  # SHORT
            # Find higher prices within window
            for i, price in enumerate(price_window['prices']):
                if price > entry_price:
                    improvement_pct = ((price - entry_price) / entry_price) * 100
                    better_entries.append({
                        'price': price,
                        'improvement': round(improvement_pct, 2),
                        'timing': f'{i} hours from signal'
                    })
        
        if better_entries:
            best_entry = max(better_entries, key=lambda x: x['improvement'])
            return {
                'could_improve': True,
                'best_entry': best_entry,
                'all_options': sorted(better_entries, key=lambda x: x['improvement'], reverse=True)[:3]
            }
        
        return {
            'could_improve': False,
            'message': 'Signal timing was optimal! No better entry within 2hr window.'
        }
    
    def calculate_capital_scenarios(self, pnl_pct):
        """Calculate profit for different capital levels"""
        scenarios = {}
        for capital in self.capital_levels:
            profit_usd = capital * (pnl_pct / 100)
            final_capital = capital + profit_usd
            scenarios[f'${capital}'] = {
                'initial': capital,
                'profit': round(profit_usd, 2),
                'final': round(final_capital, 2),
                'roi': round(pnl_pct, 2)
            }
        return scenarios
    
    def scan_historical_signals(self):
        """Scan for signals from the past and analyze them"""
        print("🔍 Scanning for historical signals to reverse engineer...\n")
        
        # Define tokens to analyze
        tokens = ['ETH', 'BTC', 'ARB', 'SOL', 'AVAX', 'OP', 'LINK', 'MATIC']
        
        # Look back 7 days
        lookback_hours = 24 * 7
        
        signals_found = []
        
        for token in tokens:
            print(f"📊 Scanning {token}...")
            
            # Get RSI data
            try:
                url = f"{self.base_url}/v2/histohour"
                params = {
                    'fsym': token,
                    'tsym': 'USD',
                    'limit': lookback_hours,
                    'api_key': self.api_key
                }
                response = requests.get(url, params=params, timeout=10)
                data = response.json()
                
                if 'Data' not in data or 'Data' not in data['Data']:
                    continue
                
                candles = data['Data']['Data']
                
                # Calculate RSI for each point
                for i in range(14, len(candles)):
                    window = candles[i-14:i+1]
                    closes = [c['close'] for c in window]
                    
                    # Simple RSI calculation
                    gains = []
                    losses = []
                    for j in range(1, len(closes)):
                        change = closes[j] - closes[j-1]
                        if change > 0:
                            gains.append(change)
                            losses.append(0)
                        else:
                            gains.append(0)
                            losses.append(abs(change))
                    
                    avg_gain = sum(gains) / len(gains) if gains else 0
                    avg_loss = sum(losses) / len(losses) if losses else 0.00001
                    
                    rs = avg_gain / avg_loss
                    rsi = 100 - (100 / (1 + rs))
                    
                    # Check for extreme RSI (signal trigger)
                    if rsi > 75 or rsi < 25:
                        signal = {
                            'timestamp': datetime.fromtimestamp(candles[i]['time']).isoformat(),
                            'token': token,
                            'entry_price': candles[i]['close'],
                            'rsi': round(rsi, 2),
                            'direction': 'SHORT' if rsi > 75 else 'LONG',
                            'confidence': 70 + (abs(rsi - 50) / 50 * 30)  # Higher confidence at extremes
                        }
                        signals_found.append(signal)
                        print(f"   🎯 Found signal: {token} RSI {rsi:.1f} @ ${candles[i]['close']:.4f}")
                
            except Exception as e:
                print(f"   ❌ Error scanning {token}: {e}")
                continue
        
        return signals_found
    
    def generate_comprehensive_report(self, analyzed_signals):
        """Generate detailed strategy comparison report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.report_dir / f"strategy_analysis_{timestamp}.txt"
        
        report = []
        report.append("=" * 80)
        report.append("🔄 STRATEGY REVERSE ENGINEERING REPORT")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Total Signals Analyzed: {len(analyzed_signals)}\n")
        
        # Summary statistics
        all_strategies = {'scalp': [], 'intraday': []}
        best_overall = []
        
        for signal in analyzed_signals:
            if 'strategies' not in signal:
                continue
                
            for strategy_type, outcomes in signal['strategies'].items():
                for timeframe, data in outcomes.items():
                    all_strategies[strategy_type].append(data['pnl_pct'])
                    best_overall.append({
                        'token': signal['token'],
                        'strategy': strategy_type,
                        'timeframe': timeframe,
                        'pnl': data['pnl_pct']
                    })
        
        # Strategy performance comparison
        report.append("📊 STRATEGY PERFORMANCE COMPARISON")
        report.append("-" * 80)
        
        for strategy_type, pnls in all_strategies.items():
            if pnls:
                avg_pnl = sum(pnls) / len(pnls)
                win_rate = len([p for p in pnls if p > 0]) / len(pnls) * 100
                best_pnl = max(pnls)
                worst_pnl = min(pnls)
                
                report.append(f"\n{strategy_type.upper()} TRADING:")
                report.append(f"  Average PnL: {avg_pnl:.2f}%")
                report.append(f"  Win Rate: {win_rate:.1f}%")
                report.append(f"  Best Trade: +{best_pnl:.2f}%")
                report.append(f"  Worst Trade: {worst_pnl:.2f}%")
        
        # Top 10 best trades
        report.append("\n\n🏆 TOP 10 BEST TRADES (What We SHOULD Have Done)")
        report.append("-" * 80)
        
        top_trades = sorted(best_overall, key=lambda x: x['pnl'], reverse=True)[:10]
        for i, trade in enumerate(top_trades, 1):
            report.append(f"{i}. {trade['token']} - {trade['strategy']} for {trade['timeframe']}: +{trade['pnl']:.2f}%")
        
        # Detailed signal analysis
        report.append("\n\n📋 DETAILED SIGNAL ANALYSIS")
        report.append("=" * 80)
        
        for signal in analyzed_signals[:10]:  # First 10 signals
            report.append(f"\n{signal['token']} - {signal['direction']}")
            report.append(f"Entry: ${signal['entry_price']:.4f} at {signal['entry_time']}")
            
            if 'optimal_strategy' in signal:
                report.append(f"\n{signal['optimal_strategy']['recommendation']}")
                
                best = signal['optimal_strategy']['best']
                report.append(f"  Best: {best['strategy']} {best['timeframe']} = +{best['pnl_pct']}% (${best['exit_price']:.4f})")
                
                worst = signal['optimal_strategy']['worst']
                report.append(f"  Worst: {worst['strategy']} {worst['timeframe']} = {worst['pnl_pct']}% (${worst['exit_price']:.4f})")
            
            if 'entry_analysis' in signal and signal['entry_analysis']:
                if signal['entry_analysis'].get('could_improve'):
                    best_entry = signal['entry_analysis']['best_entry']
                    report.append(f"\n  ⚠️  Better entry available: ${best_entry['price']:.4f} ({best_entry['timing']})")
                    report.append(f"      Improvement: +{best_entry['improvement']:.2f}%")
                else:
                    report.append(f"\n  ✅ Entry timing was optimal!")
            
            report.append("-" * 80)
        
        # Save report
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report))
        
        print(f"\n📄 Report saved: {report_file}")
        return '\n'.join(report)
    
    def run_analysis(self):
        """Main analysis loop"""
        print("🔄 STRATEGY REVERSE ENGINEER")
        print("=" * 60)
        print("Analyzing what strategies SHOULD have been used...\n")
        
        # 1. Find historical signals
        signals = self.scan_historical_signals()
        
        if not signals:
            print("❌ No signals found in lookback period")
            return
        
        print(f"\n✅ Found {len(signals)} signals to analyze\n")
        print("=" * 60)
        
        # 2. Analyze each signal
        analyzed_signals = []
        
        for i, signal in enumerate(signals[:20], 1):  # Analyze first 20 to avoid API limits
            print(f"\n[{i}/{min(20, len(signals))}] Analyzing {signal['token']} {signal['direction']} signal...")
            print(f"   Entry: ${signal['entry_price']:.4f} | RSI: {signal['rsi']:.1f}")
            
            # Analyze strategies
            strategy_results = self.analyze_strategy_outcomes(signal)
            
            # Analyze entry improvements
            entry_analysis = self.analyze_entry_improvements(signal)
            
            strategy_results['entry_analysis'] = entry_analysis
            
            analyzed_signals.append(strategy_results)
            
            # Rate limiting
            time.sleep(2)
        
        # 3. Generate report
        print("\n" + "=" * 60)
        print("📊 Generating comprehensive report...\n")
        
        report = self.generate_comprehensive_report(analyzed_signals)
        
        # 4. Save analysis data
        self.analysis_data['signals'].extend(analyzed_signals)
        self.analysis_data['last_run'] = datetime.now().isoformat()
        self._save_data()
        
        print("\n✅ Analysis complete!")
        print(f"📁 Data saved: {self.analysis_file}")
        
        return analyzed_signals

if __name__ == "__main__":
    import sys
    
    # Check for demo mode
    if len(sys.argv) > 1 and sys.argv[1] == '--demo':
        print("🎭 DEMO MODE - Using sample signals\n")
        
        # Create sample signals for demonstration
        demo_signals = [
            {
                'timestamp': '2025-11-20T10:00:00',
                'token': 'AVAX',
                'entry_price': 14.20,
                'rsi': 78.5,
                'direction': 'SHORT',
                'confidence': 85
            },
            {
                'timestamp': '2025-11-21T14:30:00',
                'token': 'OP',
                'entry_price': 0.30,
                'rsi': 23.2,
                'direction': 'LONG',
                'confidence': 82
            },
            {
                'timestamp': '2025-11-22T08:15:00',
                'token': 'ARB',
                'entry_price': 0.21,
                'rsi': 21.8,
                'direction': 'LONG',
                'confidence': 88
            }
        ]
        
        print(f"✅ Created {len(demo_signals)} demo signals\n")
        print("=" * 60)
        
        engineer = StrategyReverseEngineer()
        
        # Analyze demo signals
        analyzed = []
        for i, signal in enumerate(demo_signals, 1):
            print(f"\n[{i}/{len(demo_signals)}] Analyzing {signal['token']} {signal['direction']} signal...")
            print(f"   Entry: ${signal['entry_price']:.4f} | RSI: {signal['rsi']:.1f}")
            print("   (Demo mode - showing structure)")
            
            # Create demo results
            demo_result = {
                'token': signal['token'],
                'entry_price': signal['entry_price'],
                'entry_time': signal['timestamp'],
                'direction': signal['direction'],
                'strategies': {
                    'scalp': {
                        '5min': {'exit_price': signal['entry_price'] * 1.01, 'pnl_pct': 1.0, 'outcome': 'WIN'},
                        '15min': {'exit_price': signal['entry_price'] * 1.03, 'pnl_pct': 3.0, 'outcome': 'WIN'},
                        '30min': {'exit_price': signal['entry_price'] * 1.02, 'pnl_pct': 2.0, 'outcome': 'WIN'},
                        '60min': {'exit_price': signal['entry_price'] * 0.98, 'pnl_pct': -2.0, 'outcome': 'LOSS'}
                    },
                    'intraday': {
                        '2hr': {'exit_price': signal['entry_price'] * 1.05, 'pnl_pct': 5.0, 'outcome': 'WIN'},
                        '4hr': {'exit_price': signal['entry_price'] * 1.08, 'pnl_pct': 8.0, 'outcome': 'WIN'},
                        '6hr': {'exit_price': signal['entry_price'] * 1.12, 'pnl_pct': 12.0, 'outcome': 'WIN'},
                        '8hr': {'exit_price': signal['entry_price'] * 1.15, 'pnl_pct': 15.0, 'outcome': 'WIN'},
                        '10hr': {'exit_price': signal['entry_price'] * 1.18, 'pnl_pct': 18.0, 'outcome': 'WIN'},
                        '12hr': {'exit_price': signal['entry_price'] * 1.20, 'pnl_pct': 20.0, 'outcome': 'WIN'}
                    }
                },
                'optimal_strategy': {
                    'best': {'strategy': 'intraday', 'timeframe': '12hr', 'pnl_pct': 20.0, 'exit_price': signal['entry_price'] * 1.20},
                    'worst': {'strategy': 'scalp', 'timeframe': '60min', 'pnl_pct': -2.0, 'exit_price': signal['entry_price'] * 0.98},
                    'recommendation': f"🟢 INTRADAY HOLD would've been OPTIMAL! intraday for 12hr = +20.0%"
                },
                'entry_analysis': {
                    'could_improve': True,
                    'best_entry': {
                        'price': signal['entry_price'] * 0.97,
                        'improvement': 3.0,
                        'timing': '1 hours from signal'
                    }
                }
            }
            
            analyzed.append(demo_result)
            print(f"   {demo_result['optimal_strategy']['recommendation']}")
        
        # Generate report
        print("\n" + "=" * 60)
        print("📊 Generating demo report...\n")
        engineer.generate_comprehensive_report(analyzed)
        
        print("\n✅ Demo complete!")
        print("Run without --demo flag to analyze real historical data")
        
    else:
        engineer = StrategyReverseEngineer()
        engineer.run_analysis()
