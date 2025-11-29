"""
PROFESSIONAL RISK MANAGER V2 - Enhanced for Real Money
Battle-tested capital protection with dynamic position sizing
"""

import json
import os
from datetime import datetime, timedelta
from web3 import Web3

# Web3 setup
w3 = Web3(Web3.HTTPProvider('https://arb1.arbitrum.io/rpc'))

# Contract addresses (Arbitrum)
USDC_ADDRESS = '0xaf88d065e77c8cC2239327C5EDb3A432268e5831'
WALLET_ADDRESS = '0x63d48340AB2c1E0e244F2987962C69A1C06d1e68'

# AGGRESSIVE RISK PARAMETERS FOR SMALL ACCOUNTS
MAX_POSITION_SIZE_PCT = 0.40  # 40% per trade (go big when confidence is 90%+)
MAX_DAILY_TRADES = 10  # More opportunities = more chances to hit
MAX_DAILY_LOSS_PCT = 0.20  # Allow 20% drawdown (we're building from $29)
MAX_TOTAL_DRAWDOWN_PCT = 0.35  # Stop at -35% from peak
MIN_TRADE_SIZE_USD = 5  # Trade even with $29 balance

# DYNAMIC SIZING: Scale UP as we win
BALANCE_TIERS = {
    'micro': (0, 100),      # $0-100: 40% per trade (aggressive)
    'small': (100, 500),    # $100-500: 35% per trade
    'medium': (500, 2000),  # $500-2000: 30% per trade
    'large': (2000, 10000), # $2000+: 25% per trade (conservative)
}

class ProfessionalRiskManager:
    """Enhanced risk management for real capital growth"""
    
    def __init__(self):
        self.state_file = 'data/risk_state_v2.json'
        self.load_state()
    
    def load_state(self):
        """Load risk tracking state"""
        if os.path.exists(self.state_file):
            with open(self.state_file, 'r') as f:
                self.state = json.load(f)
        else:
            self.state = {
                'starting_balance': 0,
                'peak_balance': 0,
                'daily_trades': 0,
                'daily_pnl': 0,
                'last_reset_date': datetime.now().strftime('%Y-%m-%d'),
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'total_pnl': 0,
                'best_trade': 0,
                'worst_trade': 0,
                'consecutive_wins': 0,
                'consecutive_losses': 0,
                'max_consecutive_wins': 0,
                'max_consecutive_losses': 0
            }
            self.save_state()
    
    def save_state(self):
        """Save risk state"""
        os.makedirs('data', exist_ok=True)
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    def reset_daily_limits(self):
        """Reset daily counters at midnight"""
        today = datetime.now().strftime('%Y-%m-%d')
        if self.state['last_reset_date'] != today:
            print(f"\n📅 NEW TRADING DAY: {today}")
            print(f"   Yesterday: {self.state['daily_trades']} trades, ${self.state['daily_pnl']:.2f} P&L")
            self.state['daily_trades'] = 0
            self.state['daily_pnl'] = 0
            self.state['last_reset_date'] = today
            self.save_state()
    
    def get_current_balance(self):
        """Get USDC balance from blockchain"""
        try:
            usdc = w3.eth.contract(
                address=Web3.to_checksum_address(USDC_ADDRESS),
                abi=[{
                    "constant": True,
                    "inputs": [{"name": "_owner", "type": "address"}],
                    "name": "balanceOf",
                    "outputs": [{"name": "balance", "type": "uint256"}],
                    "type": "function"
                }]
            )
            balance_wei = usdc.functions.balanceOf(
                Web3.to_checksum_address(WALLET_ADDRESS)
            ).call()
            return balance_wei / 10**6  # USDC has 6 decimals
        except Exception as e:
            print(f"⚠️  Balance fetch error: {e}")
            return 0
    
    def get_balance_tier(self, balance):
        """Determine which tier balance falls into"""
        for tier_name, (min_bal, max_bal) in BALANCE_TIERS.items():
            if min_bal <= balance < max_bal:
                return tier_name
        return 'large'  # Over $10k
    
    def get_position_size_pct(self, balance, confidence_score):
        """
        Dynamic position sizing based on balance tier and confidence
        
        Tier-based base sizes:
        - Micro ($0-100): 40% base
        - Small ($100-500): 35% base  
        - Medium ($500-2000): 30% base
        - Large ($2000+): 25% base
        
        Confidence bonus:
        - 90% = base size
        - 95% = base + 5%
        - 100% = base + 10%
        """
        tier = self.get_balance_tier(balance)
        
        # Base size by tier
        tier_sizes = {
            'micro': 0.40,
            'small': 0.35,
            'medium': 0.30,
            'large': 0.25
        }
        
        base_size = tier_sizes[tier]
        
        # Confidence bonus (0-10% extra)
        confidence_bonus = (confidence_score - 90) / 100 * 0.10
        
        # Winning streak bonus (max +5%)
        streak_bonus = 0
        if self.state['consecutive_wins'] >= 3:
            streak_bonus = min(self.state['consecutive_wins'] * 0.01, 0.05)
        
        # Losing streak penalty (reduce size)
        streak_penalty = 0
        if self.state['consecutive_losses'] >= 2:
            streak_penalty = self.state['consecutive_losses'] * 0.05
        
        total_size = base_size + confidence_bonus + streak_bonus - streak_penalty
        
        # Cap at 50% max (never go all-in)
        total_size = min(max(total_size, 0.15), 0.50)
        
        return total_size
    
    def update_peak_balance(self, current_balance):
        """Track highest balance for drawdown calculation"""
        if current_balance > self.state['peak_balance']:
            self.state['peak_balance'] = current_balance
            self.save_state()
            print(f"🎯 NEW PEAK BALANCE: ${current_balance:.2f}")
            
            # Set starting balance on first peak
            if self.state['starting_balance'] == 0:
                self.state['starting_balance'] = current_balance
                self.save_state()
    
    def calculate_drawdown(self, current_balance):
        """Calculate drawdown from peak"""
        if self.state['peak_balance'] == 0:
            return 0
        dd = (self.state['peak_balance'] - current_balance) / self.state['peak_balance']
        return dd
    
    def check_trade_allowed(self, confidence_score):
        """
        Comprehensive pre-trade risk check
        Returns: (allowed: bool, reason: str, position_size_usd: float, position_size_pct: float)
        """
        self.reset_daily_limits()
        
        current_balance = self.get_current_balance()
        self.update_peak_balance(current_balance)
        
        # Check 1: Minimum balance
        if current_balance < MIN_TRADE_SIZE_USD:
            return False, f"Balance too low: ${current_balance:.2f}", 0, 0
        
        # Check 2: Daily trade limit
        if self.state['daily_trades'] >= MAX_DAILY_TRADES:
            return False, f"Daily limit reached ({MAX_DAILY_TRADES} trades)", 0, 0
        
        # Check 3: Daily loss limit
        if self.state['daily_pnl'] < 0:
            daily_loss_pct = abs(self.state['daily_pnl']) / current_balance
            if daily_loss_pct >= MAX_DAILY_LOSS_PCT:
                return False, f"Daily loss limit: {daily_loss_pct*100:.1f}% (max {MAX_DAILY_LOSS_PCT*100:.0f}%)", 0, 0
        
        # Check 4: Total drawdown limit
        drawdown = self.calculate_drawdown(current_balance)
        if drawdown >= MAX_TOTAL_DRAWDOWN_PCT:
            return False, f"Max drawdown: {drawdown*100:.1f}% (limit {MAX_TOTAL_DRAWDOWN_PCT*100:.0f}%)", 0, 0
        
        # Check 5: Confidence threshold
        if confidence_score < 90:
            return False, f"Confidence too low: {confidence_score:.1f}% (need 90%+)", 0, 0
        
        # Check 6: Consecutive losses (pause after 5 straight losses)
        if self.state['consecutive_losses'] >= 5:
            return False, f"5 consecutive losses - taking a break", 0, 0
        
        # Calculate dynamic position size
        position_size_pct = self.get_position_size_pct(current_balance, confidence_score)
        position_size_usd = current_balance * position_size_pct
        
        # Ensure minimum trade size
        if position_size_usd < MIN_TRADE_SIZE_USD:
            position_size_usd = MIN_TRADE_SIZE_USD
            position_size_pct = MIN_TRADE_SIZE_USD / current_balance
        
        tier = self.get_balance_tier(current_balance)
        
        print(f"\n✅ TRADE APPROVED")
        print(f"   Balance: ${current_balance:.2f} (Tier: {tier.upper()})")
        print(f"   Confidence: {confidence_score:.1f}%")
        print(f"   Position: ${position_size_usd:.2f} ({position_size_pct*100:.1f}%)")
        print(f"   Streak: {self.state['consecutive_wins']} wins / {self.state['consecutive_losses']} losses")
        
        return True, "All risk checks passed ✅", position_size_usd, position_size_pct
    
    def record_trade_open(self, token, direction, entry_price, size_usd, confidence):
        """Record trade execution"""
        self.state['daily_trades'] += 1
        self.state['total_trades'] += 1
        self.save_state()
        
        print(f"\n📊 TRADE #{self.state['total_trades']} OPENED")
        print(f"   Token: {token}")
        print(f"   Direction: {direction}")
        print(f"   Entry: ${entry_price:.4f}")
        print(f"   Size: ${size_usd:.2f}")
        print(f"   Confidence: {confidence:.1f}%")
        print(f"   Daily trades: {self.state['daily_trades']}/{MAX_DAILY_TRADES}")
    
    def record_trade_close(self, token, direction, entry_price, exit_price, size_usd, exit_reason):
        """Record trade closure with P&L"""
        # Calculate P&L
        if direction == 'LONG':
            pnl_pct = ((exit_price - entry_price) / entry_price) * 100
        else:  # SHORT
            pnl_pct = ((entry_price - exit_price) / entry_price) * 100
        
        pnl_usd = size_usd * (pnl_pct / 100)
        
        # Update daily/total P&L
        self.state['daily_pnl'] += pnl_usd
        self.state['total_pnl'] += pnl_usd
        
        # Update win/loss streaks
        if pnl_usd > 0:
            self.state['winning_trades'] += 1
            self.state['consecutive_wins'] += 1
            self.state['consecutive_losses'] = 0
            
            if self.state['consecutive_wins'] > self.state['max_consecutive_wins']:
                self.state['max_consecutive_wins'] = self.state['consecutive_wins']
            
            if pnl_usd > self.state['best_trade']:
                self.state['best_trade'] = pnl_usd
            
            print(f"\n✅ WIN: +${pnl_usd:.2f} (+{pnl_pct:.1f}%)")
            print(f"   {self.state['consecutive_wins']} win streak! 🔥")
        else:
            self.state['losing_trades'] += 1
            self.state['consecutive_losses'] += 1
            self.state['consecutive_wins'] = 0
            
            if self.state['consecutive_losses'] > self.state['max_consecutive_losses']:
                self.state['max_consecutive_losses'] = self.state['consecutive_losses']
            
            if pnl_usd < self.state['worst_trade']:
                self.state['worst_trade'] = pnl_usd
            
            print(f"\n❌ LOSS: ${pnl_usd:.2f} ({pnl_pct:.1f}%)")
            print(f"   {self.state['consecutive_losses']} loss streak")
        
        # Calculate statistics
        total_closed = self.state['winning_trades'] + self.state['losing_trades']
        win_rate = (self.state['winning_trades'] / total_closed * 100) if total_closed > 0 else 0
        
        print(f"\n📈 STATS")
        print(f"   Exit: ${exit_price:.4f} ({exit_reason})")
        print(f"   Total P&L: ${self.state['total_pnl']:.2f}")
        print(f"   Win Rate: {win_rate:.1f}% ({self.state['winning_trades']}/{total_closed})")
        print(f"   Daily P&L: ${self.state['daily_pnl']:.2f}")
        
        self.save_state()
    
    def get_status_report(self):
        """Generate comprehensive risk status report"""
        current_balance = self.get_current_balance()
        drawdown = self.calculate_drawdown(current_balance)
        tier = self.get_balance_tier(current_balance)
        
        daily_loss_pct = 0
        if current_balance > 0 and self.state['daily_pnl'] < 0:
            daily_loss_pct = abs(self.state['daily_pnl']) / current_balance * 100
        
        total_closed = self.state['winning_trades'] + self.state['losing_trades']
        win_rate = (self.state['winning_trades'] / total_closed * 100) if total_closed > 0 else 0
        
        # Calculate ROI if we have starting balance
        roi = 0
        if self.state['starting_balance'] > 0:
            roi = ((current_balance - self.state['starting_balance']) / self.state['starting_balance']) * 100
        
        report = f"""
{'='*80}
🛡️  PROFESSIONAL RISK MANAGER V2
{'='*80}

💰 CAPITAL STATUS:
   Current Balance:  ${current_balance:.2f}
   Starting Balance: ${self.state['starting_balance']:.2f}
   Peak Balance:     ${self.state['peak_balance']:.2f}
   Total P&L:        ${self.state['total_pnl']:.2f}
   ROI:              {roi:+.1f}%
   Tier:             {tier.upper()}
   
📉 RISK METRICS:
   Current Drawdown: {drawdown*100:.1f}% (limit: {MAX_TOTAL_DRAWDOWN_PCT*100:.0f}%)
   Daily Loss:       {daily_loss_pct:.1f}% (limit: {MAX_DAILY_LOSS_PCT*100:.0f}%)
   Status:           {'🟢 SAFE' if drawdown < MAX_TOTAL_DRAWDOWN_PCT * 0.5 else '🟡 CAUTION' if drawdown < MAX_TOTAL_DRAWDOWN_PCT else '🔴 DANGER'}

📊 TODAY:
   Trades:           {self.state['daily_trades']}/{MAX_DAILY_TRADES}
   P&L:              ${self.state['daily_pnl']:+.2f}
   Status:           {'🟢 Green' if self.state['daily_pnl'] > 0 else '🔴 Red' if self.state['daily_pnl'] < -5 else '⚪ Flat'}

📈 ALL-TIME:
   Total Trades:     {self.state['total_trades']}
   Wins:             {self.state['winning_trades']} ✅
   Losses:           {self.state['losing_trades']} ❌
   Win Rate:         {win_rate:.1f}%
   Best Trade:       ${self.state['best_trade']:.2f}
   Worst Trade:      ${self.state['worst_trade']:.2f}

🔥 STREAKS:
   Current:          {self.state['consecutive_wins']} wins / {self.state['consecutive_losses']} losses
   Max Win Streak:   {self.state['max_consecutive_wins']} 🔥
   Max Loss Streak:  {self.state['max_consecutive_losses']} 💀

⚙️  POSITION SIZING:
   Base Size:        {self.get_position_size_pct(current_balance, 90)*100:.0f}% (90% confidence)
   With Bonus:       {self.get_position_size_pct(current_balance, 100)*100:.0f}% (100% confidence)
   Next Trade:       ~${current_balance * self.get_position_size_pct(current_balance, 95):.2f}
{'='*80}
"""
        return report

def main():
    """Test professional risk manager"""
    rm = ProfessionalRiskManager()
    print(rm.get_status_report())
    
    print("\n🧪 TESTING TRADE APPROVAL (95% confidence)...")
    allowed, reason, size_usd, size_pct = rm.check_trade_allowed(95)
    
    if allowed:
        print(f"\n✅ TRADE ALLOWED")
        print(f"   Position: ${size_usd:.2f} ({size_pct*100:.1f}%)")
    else:
        print(f"\n❌ TRADE BLOCKED: {reason}")

if __name__ == "__main__":
    main()
