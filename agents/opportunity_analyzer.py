"""
🧠 OPPORTUNITY ANALYZER - AI Post-Mortem Study System

Analyzes EVERY high-confidence signal (even ones we don't take) and tracks:
- What the confidence score was
- What happened to price after the signal
- How much profit we COULD have made with more capital
- Why we didn't take it (not enough funds, threshold not met, etc.)
- Patterns in missed opportunities

Generates detailed reports showing:
- Best missed opportunities of the day/week
- Total potential profits lost
- Success rate of signals we didn't take
- Recommendations for threshold adjustments
"""

import json
import time
from datetime import datetime
from pathlib import Path
import requests
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

class OpportunityAnalyzer:
    def __init__(self):
        self.api_key = None  # CryptoCompare API
        
        self.opportunities_file = 'data/opportunity_analysis.json'
        self.reports_dir = Path('reports')
        self.reports_dir.mkdir(exist_ok=True)
        
        # Thresholds for what we consider "high confidence"
        self.MIN_ANALYSIS_CONFIDENCE = 70  # Track anything 70%+
        self.PRICE_CHECK_INTERVALS = [5, 15, 30, 60, 120]  # Check price at 5min, 15min, 30min, 1hr, 2hr
        
        # Load existing opportunities
        self.opportunities = self.load_opportunities()
        
    def load_opportunities(self):
        """Load historical opportunity data"""
        if Path(self.opportunities_file).exists():
            with open(self.opportunities_file, 'r') as f:
                return json.load(f)
        return {'opportunities': [], 'summary': {}}
    
    def save_opportunities(self):
        """Save opportunity data"""
        Path('data').mkdir(exist_ok=True)
        with open(self.opportunities_file, 'w') as f:
            json.dump(self.opportunities, f, indent=2)
    
    def get_current_price(self, symbol):
        """Get current price for a token"""
        try:
            url = "https://min-api.cryptocompare.com/data/price"
            params = {
                'fsym': symbol,
                'tsyms': 'USD'
            }
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            return data.get('USD', 0)
        except:
            return 0
    
    def calculate_potential_profit(self, entry_price, exit_price, direction, amount_usd):
        """Calculate profit for a hypothetical trade"""
        if direction == 'LONG':
            price_change_pct = ((exit_price - entry_price) / entry_price) * 100
        else:  # SHORT
            price_change_pct = ((entry_price - exit_price) / entry_price) * 100
        
        profit_usd = (price_change_pct / 100) * amount_usd
        return {
            'price_change_pct': price_change_pct,
            'profit_usd': profit_usd,
            'roi': price_change_pct
        }
    
    def get_rsi(self, symbol, period=14):
        """Calculate RSI for a symbol"""
        try:
            url = "https://min-api.cryptocompare.com/data/v2/histohour"
            params = {'fsym': symbol, 'tsym': 'USD', 'limit': period + 1}
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if 'Data' not in data or 'Data' not in data['Data']:
                return 50
            
            prices = [candle['close'] for candle in data['Data']['Data']]
            
            gains = []
            losses = []
            for i in range(1, len(prices)):
                change = prices[i] - prices[i-1]
                if change > 0:
                    gains.append(change)
                    losses.append(0)
                else:
                    gains.append(0)
                    losses.append(abs(change))
            
            avg_gain = sum(gains) / len(gains) if gains else 0
            avg_loss = sum(losses) / len(losses) if losses else 0
            
            if avg_loss == 0:
                return 100
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            return rsi
        except:
            return 50
    
    def scan_and_record_opportunities(self):
        """Scan for opportunities and record them for analysis"""
        print("\n" + "="*80)
        print("🧠 AI OPPORTUNITY ANALYZER - Scanning Market")
        print("="*80)
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Tracking signals 70%+ confidence for post-mortem analysis\n")
        
        # Tokens to scan
        tokens = ['ARB', 'OP', 'AVAX', 'MATIC', 'ETH', 'BTC', 'SOL', 'LINK']
        
        # Get RSI signals
        rsi_signals = []
        print("📊 Scanning RSI Extremes...")
        for token in tokens:
            price = self.get_current_price(token)
            rsi = self.get_rsi(token)
            
            # RSI extreme signals
            if rsi > 75:  # Overbought
                confidence = min(95, 70 + ((rsi - 75) * 2))
                rsi_signals.append({
                    'pair': f'{token}/USDC',
                    'direction': 'SHORT',
                    'confidence': confidence,
                    'price': price,
                    'rsi': rsi
                })
                print(f"   🔴 {token}: RSI {rsi:.1f} - SHORT signal {confidence:.0f}%")
            elif rsi < 25:  # Oversold
                confidence = min(95, 70 + ((25 - rsi) * 2))
                rsi_signals.append({
                    'pair': f'{token}/USDC',
                    'direction': 'LONG',
                    'confidence': confidence,
                    'price': price,
                    'rsi': rsi
                })
                print(f"   🟢 {token}: RSI {rsi:.1f} - LONG signal {confidence:.0f}%")
        
        # Get volume signals - simplified version
        volume_signals = []
        print("\n📈 Scanning Volume Spikes...")
        print("   (Volume signals tracked by separate scanner)")
        
        # Record opportunities
        timestamp = datetime.now().isoformat()
        
        for signal in rsi_signals:
            opportunity = {
                'timestamp': timestamp,
                'signal_type': 'RSI_EXTREME',
                'token': signal['pair'].split('/')[0],
                'pair': signal['pair'],
                'direction': signal['direction'],
                'confidence': signal['confidence'],
                'entry_price': signal['price'],
                'rsi': signal['rsi'],
                'reason': f"RSI {signal['rsi']} - {'Extreme overbought' if signal['rsi'] > 75 else 'Extreme oversold'}",
                'taken': False,  # We'll update this if we actually traded it
                'price_checks': [],
                'final_result': None
            }
            self.opportunities['opportunities'].append(opportunity)
            print(f"\n📝 RECORDED: {opportunity['token']} {opportunity['direction']}")
            print(f"   Confidence: {opportunity['confidence']}%")
            print(f"   Entry: ${opportunity['entry_price']:.4f}")
            print(f"   RSI: {opportunity['rsi']}")
        
        for signal in volume_signals:
            opportunity = {
                'timestamp': timestamp,
                'signal_type': 'VOLUME_SPIKE',
                'token': signal['symbol'],
                'pair': f"{signal['symbol']}/USDC",
                'direction': 'LONG',  # Volume spikes typically precede pumps
                'confidence': signal['confidence'],
                'entry_price': signal['price'],
                'volume_spike': signal.get('spike_multiplier', 0),
                'reason': f"Volume spike {signal.get('spike_multiplier', 0):.1f}x - Major whale activity",
                'taken': False,
                'price_checks': [],
                'final_result': None
            }
            self.opportunities['opportunities'].append(opportunity)
            print(f"\n📝 RECORDED: {opportunity['token']} VOLUME SPIKE")
            print(f"   Confidence: {opportunity['confidence']}%")
            print(f"   Entry: ${opportunity['entry_price']:.4f}")
            print(f"   Volume: {opportunity['volume_spike']:.1f}x normal")
        
        self.save_opportunities()
        
        total_recorded = len(rsi_signals) + len(volume_signals)
        print(f"\n✅ Recorded {total_recorded} opportunities for post-mortem analysis")
        
        return total_recorded
    
    def update_opportunity_outcomes(self):
        """Check price movements on recorded opportunities"""
        print("\n" + "="*80)
        print("🔍 UPDATING OPPORTUNITY OUTCOMES")
        print("="*80)
        
        updated_count = 0
        
        for opp in self.opportunities['opportunities']:
            # Skip if already finalized
            if opp.get('final_result'):
                continue
            
            # Calculate time elapsed
            opp_time = datetime.fromisoformat(opp['timestamp'])
            elapsed_minutes = (datetime.now() - opp_time).total_seconds() / 60
            
            # Check if we should record a price check
            current_price = self.get_current_price(opp['token'])
            if current_price == 0:
                continue
            
            # Record price checks at intervals
            for interval in self.PRICE_CHECK_INTERVALS:
                # Check if we're past this interval but haven't recorded it yet
                existing_checks = [c['minutes'] for c in opp.get('price_checks', [])]
                if elapsed_minutes >= interval and interval not in existing_checks:
                    profit_calc = self.calculate_potential_profit(
                        opp['entry_price'],
                        current_price,
                        opp['direction'],
                        100  # Calculate for $100 position
                    )
                    
                    price_check = {
                        'minutes': interval,
                        'price': current_price,
                        'profit_usd': profit_calc['profit_usd'],
                        'roi': profit_calc['roi'],
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    if 'price_checks' not in opp:
                        opp['price_checks'] = []
                    opp['price_checks'].append(price_check)
                    updated_count += 1
                    
                    print(f"\n📊 {opp['token']} @ {interval}min:")
                    print(f"   Entry: ${opp['entry_price']:.4f}")
                    print(f"   Now: ${current_price:.4f}")
                    print(f"   ROI: {profit_calc['roi']:+.2f}%")
                    print(f"   Profit on $100: ${profit_calc['profit_usd']:+.2f}")
            
            # Finalize after 2 hours
            if elapsed_minutes >= 120 and not opp.get('final_result'):
                final_profit = self.calculate_potential_profit(
                    opp['entry_price'],
                    current_price,
                    opp['direction'],
                    100
                )
                
                opp['final_result'] = {
                    'final_price': current_price,
                    'total_roi': final_profit['roi'],
                    'profit_on_100': final_profit['profit_usd'],
                    'finalized_at': datetime.now().isoformat()
                }
                
                print(f"\n✅ FINALIZED: {opp['token']}")
                print(f"   Final ROI: {final_profit['roi']:+.2f}%")
                print(f"   Profit on $100: ${final_profit['profit_usd']:+.2f}")
        
        if updated_count > 0:
            self.save_opportunities()
            print(f"\n✅ Updated {updated_count} price checks")
        
        return updated_count
    
    def generate_report(self, lookback_hours=24):
        """Generate comprehensive analysis report"""
        print("\n" + "="*80)
        print("📊 OPPORTUNITY ANALYSIS REPORT")
        print("="*80)
        print(f"Analyzing last {lookback_hours} hours\n")
        
        cutoff_time = datetime.now().timestamp() - (lookback_hours * 3600)
        recent_opps = [
            opp for opp in self.opportunities['opportunities']
            if datetime.fromisoformat(opp['timestamp']).timestamp() > cutoff_time
        ]
        
        if not recent_opps:
            print("No opportunities recorded in this period.")
            return
        
        # Calculate statistics
        finalized = [opp for opp in recent_opps if opp.get('final_result')]
        winners = [opp for opp in finalized if opp['final_result']['total_roi'] > 0]
        losers = [opp for opp in finalized if opp['final_result']['total_roi'] <= 0]
        
        # Best opportunities
        if finalized:
            best = sorted(finalized, key=lambda x: x['final_result']['total_roi'], reverse=True)[:5]
            worst = sorted(finalized, key=lambda x: x['final_result']['total_roi'])[:5]
        else:
            best = []
            worst = []
        
        # Calculate total potential profit
        total_potential_100 = sum(opp['final_result']['profit_on_100'] for opp in finalized)
        total_potential_1000 = total_potential_100 * 10
        total_potential_10000 = total_potential_100 * 100
        
        # Win rate
        win_rate = (len(winners) / len(finalized) * 100) if finalized else 0
        
        # Generate report
        report = []
        report.append(f"Analysis Period: Last {lookback_hours} hours")
        report.append(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        report.append("="*80)
        report.append("SUMMARY STATISTICS")
        report.append("="*80)
        report.append(f"Total Opportunities Detected: {len(recent_opps)}")
        report.append(f"Finalized (2hr+ elapsed): {len(finalized)}")
        report.append(f"Still Tracking: {len(recent_opps) - len(finalized)}")
        report.append(f"Winners: {len(winners)} ({win_rate:.1f}%)")
        report.append(f"Losers: {len(losers)}")
        report.append("")
        report.append("POTENTIAL PROFITS (if we had taken ALL signals):")
        report.append(f"  With $100 positions: ${total_potential_100:+.2f}")
        report.append(f"  With $1,000 positions: ${total_potential_1000:+,.2f}")
        report.append(f"  With $10,000 positions: ${total_potential_10000:+,.2f}")
        report.append("")
        
        if best:
            report.append("="*80)
            report.append("🏆 TOP 5 BEST OPPORTUNITIES (We Didn't Take)")
            report.append("="*80)
            for i, opp in enumerate(best, 1):
                result = opp['final_result']
                report.append(f"\n#{i}. {opp['token']} {opp['direction']}")
                report.append(f"   Signal: {opp['signal_type']} @ {opp['confidence']}% confidence")
                report.append(f"   Time: {datetime.fromisoformat(opp['timestamp']).strftime('%H:%M:%S')}")
                report.append(f"   Entry: ${opp['entry_price']:.4f}")
                report.append(f"   Exit: ${result['final_price']:.4f}")
                report.append(f"   ROI: {result['total_roi']:+.2f}%")
                report.append(f"   Profit on $100: ${result['profit_on_100']:+.2f}")
                report.append(f"   Profit on $1000: ${result['profit_on_100']*10:+.2f}")
                report.append(f"   Reason: {opp['reason']}")
                
                # Show why we didn't take it
                if opp['confidence'] < 90:
                    report.append(f"   ❌ Why missed: Confidence {opp['confidence']}% below 90% threshold")
                else:
                    report.append(f"   ❌ Why missed: Insufficient funds or other filters")
        
        if worst:
            report.append("\n" + "="*80)
            report.append("⚠️  TOP 5 WORST SIGNALS (Good thing we didn't take)")
            report.append("="*80)
            for i, opp in enumerate(worst, 1):
                result = opp['final_result']
                report.append(f"\n#{i}. {opp['token']} {opp['direction']}")
                report.append(f"   Signal: {opp['signal_type']} @ {opp['confidence']}% confidence")
                report.append(f"   ROI: {result['total_roi']:+.2f}%")
                report.append(f"   Loss on $100: ${result['profit_on_100']:+.2f}")
        
        # Confidence analysis
        if finalized:
            report.append("\n" + "="*80)
            report.append("🎯 CONFIDENCE SCORE ANALYSIS")
            report.append("="*80)
            
            # Group by confidence ranges
            ranges = {
                '90-100%': [o for o in finalized if 90 <= o['confidence'] <= 100],
                '80-89%': [o for o in finalized if 80 <= o['confidence'] < 90],
                '70-79%': [o for o in finalized if 70 <= o['confidence'] < 80],
            }
            
            for range_name, opps in ranges.items():
                if opps:
                    range_winners = [o for o in opps if o['final_result']['total_roi'] > 0]
                    range_win_rate = (len(range_winners) / len(opps) * 100)
                    avg_roi = sum(o['final_result']['total_roi'] for o in opps) / len(opps)
                    
                    report.append(f"\n{range_name} Confidence Signals:")
                    report.append(f"   Count: {len(opps)}")
                    report.append(f"   Win Rate: {range_win_rate:.1f}%")
                    report.append(f"   Avg ROI: {avg_roi:+.2f}%")
                    
                    if range_name == '90-100%':
                        report.append(f"   💡 This is our current threshold - GOOD!")
                    elif range_name == '80-89%':
                        if range_win_rate > 75:
                            report.append(f"   💡 Consider lowering threshold to 85% - strong win rate!")
                    elif range_name == '70-79%':
                        if range_win_rate < 60:
                            report.append(f"   ⚠️  Keep threshold at 90% - these are too risky")
        
        # Save report
        report_text = "\n".join(report)
        print(report_text)
        
        # Save to file
        report_file = self.reports_dir / f"opportunity_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_file, 'w') as f:
            f.write(report_text)
        
        print(f"\n📄 Report saved to: {report_file}")
        
        return report_text
    
    def continuous_analysis_loop(self, scan_interval=300):
        """Run continuous analysis loop"""
        print("\n" + "="*80)
        print("🧠 OPPORTUNITY ANALYZER - CONTINUOUS MODE")
        print("="*80)
        print(f"Scanning every {scan_interval}s for opportunities")
        print("Tracking outcomes and generating reports")
        print("Press Ctrl+C to stop\n")
        
        try:
            while True:
                # Scan for new opportunities
                self.scan_and_record_opportunities()
                
                # Update outcomes of existing opportunities
                time.sleep(10)
                self.update_opportunity_outcomes()
                
                # Generate report every hour
                total_opps = len(self.opportunities['opportunities'])
                if total_opps > 0 and total_opps % 12 == 0:  # Every ~12 scans (1 hour)
                    self.generate_report(lookback_hours=24)
                
                # Wait for next scan
                print(f"\n⏳ Next scan in {scan_interval}s...")
                time.sleep(scan_interval)
                
        except KeyboardInterrupt:
            print("\n\n🛑 Analysis stopped by user")
            self.generate_report(lookback_hours=24)

if __name__ == "__main__":
    import sys
    
    analyzer = OpportunityAnalyzer()
    
    # Check if continuous mode requested
    if '--continuous' in sys.argv:
        analyzer.continuous_analysis_loop(scan_interval=300)  # 5 minutes
    else:
        # Run one-time analysis
        print("Running opportunity analysis...")
        analyzer.scan_and_record_opportunities()
        time.sleep(5)
        analyzer.update_opportunity_outcomes()
        analyzer.generate_report(lookback_hours=24)
        
        # Ask if they want continuous mode
        print("\n" + "="*80)
        print("💡 Want to run continuous analysis?")
        print("   Run: python launch_analyzer.py")
        print("   This will scan every 5 minutes and track ALL opportunities")
        print("   Generates reports showing what profits we COULD have made")
        print("="*80)
