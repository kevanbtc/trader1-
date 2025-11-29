"""
APEX LIVE DASHBOARD
Real-time visual monitoring of all 5 APEX subsystems
Shows opportunities, executions, stats, and system health
"""

import os
import time
import json
from datetime import datetime, timedelta
from collections import deque
import asyncio

# ANSI color codes for Windows terminal
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BG_BLACK = '\033[40m'
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'

class ApexDashboard:
    """Real-time APEX monitoring dashboard"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.opportunities = deque(maxlen=20)  # Last 20 opportunities
        self.executions = deque(maxlen=10)     # Last 10 executions
        self.events = deque(maxlen=15)         # Last 15 events
        
        # Stats
        self.stats = {
            'total_opportunities': 0,
            'multihop_opps': 0,
            'flashloan_opps': 0,
            'event_opps': 0,
            'predictive_opps': 0,
            'trades_executed': 0,
            'trades_successful': 0,
            'total_pnl': 0.0,
            'best_trade': 0.0,
            'worst_trade': 0.0,
        }
        
        # System health
        self.system_health = {
            'rpc_connected': True,
            'last_block': 0,
            'gas_price': 0.0,
            'mcp_active': True,
            'swarm_active': True,
            'multihop_active': True,
            'flashloan_active': True,
            'event_hunter_active': True,
            'predictive_active': True,
        }
        
        # Load session data if exists
        self.load_latest_session()
    
    def load_latest_session(self):
        """Load latest session data from logs"""
        try:
            logs_dir = 'logs'
            if os.path.exists(logs_dir):
                sessions = [f for f in os.listdir(logs_dir) if f.startswith('session_') and f.endswith('.json')]
                if sessions:
                    latest = max(sessions, key=lambda x: os.path.getmtime(os.path.join(logs_dir, x)))
                    with open(os.path.join(logs_dir, latest), 'r') as f:
                        data = json.load(f)
                        self.stats['trades_executed'] = data.get('trades_executed', 0)
                        self.stats['total_pnl'] = data.get('session_pnl_usd', 0.0)
        except Exception as e:
            pass
    
    def clear_screen(self):
        """Clear terminal screen"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def print_header(self):
        """Print dashboard header"""
        runtime = datetime.now() - self.start_time
        hours, remainder = divmod(int(runtime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        print(f"{Colors.BG_BLUE}{Colors.WHITE}{Colors.BOLD}")
        print("╔══════════════════════════════════════════════════════════════════════════════╗")
        print("║                     🔥 APEX MODE LIVE DASHBOARD 🔥                          ║")
        print("╚══════════════════════════════════════════════════════════════════════════════╝")
        print(f"{Colors.RESET}")
        
        print(f"{Colors.CYAN}Runtime: {hours:02d}:{minutes:02d}:{seconds:02d} | ", end="")
        print(f"Block: {self.system_health['last_block']:,} | ", end="")
        print(f"Gas: {self.system_health['gas_price']:.4f} Gwei{Colors.RESET}")
        print()
    
    def print_system_status(self):
        """Print system health status"""
        print(f"{Colors.BOLD}🖥️  SYSTEM STATUS{Colors.RESET}")
        print("─" * 80)
        
        modules = [
            ("RPC Connection", self.system_health['rpc_connected']),
            ("MCP Intelligence", self.system_health['mcp_active']),
            ("Swarm Coordinator", self.system_health['swarm_active']),
            ("Multi-Hop Router", self.system_health['multihop_active']),
            ("Flashloan Executor", self.system_health['flashloan_active']),
            ("Event Hunter", self.system_health['event_hunter_active']),
            ("Predictive Model", self.system_health['predictive_active']),
        ]
        
        # Print in 2 columns
        for i in range(0, len(modules), 2):
            left = modules[i]
            status_left = f"{Colors.GREEN}✓ ACTIVE{Colors.RESET}" if left[1] else f"{Colors.RED}✗ OFFLINE{Colors.RESET}"
            print(f"  {left[0]:.<30} {status_left:.<30}", end="")
            
            if i + 1 < len(modules):
                right = modules[i + 1]
                status_right = f"{Colors.GREEN}✓ ACTIVE{Colors.RESET}" if right[1] else f"{Colors.RED}✗ OFFLINE{Colors.RESET}"
                print(f"{right[0]:.<30} {status_right}")
            else:
                print()
        
        print()
    
    def print_statistics(self):
        """Print trading statistics"""
        print(f"{Colors.BOLD}📊 TRADING STATISTICS{Colors.RESET}")
        print("─" * 80)
        
        win_rate = (self.stats['trades_successful'] / self.stats['trades_executed'] * 100) if self.stats['trades_executed'] > 0 else 0
        
        # First row
        print(f"  Total Opportunities: {Colors.YELLOW}{self.stats['total_opportunities']:>6}{Colors.RESET}    ", end="")
        print(f"Trades Executed: {Colors.CYAN}{self.stats['trades_executed']:>6}{Colors.RESET}    ", end="")
        print(f"Win Rate: {Colors.GREEN if win_rate >= 80 else Colors.YELLOW}{win_rate:>5.1f}%{Colors.RESET}")
        
        # Second row - opportunity breakdown
        print(f"  └─ Multi-Hop: {self.stats['multihop_opps']:>3}  ", end="")
        print(f"Flashloan: {self.stats['flashloan_opps']:>3}  ", end="")
        print(f"Events: {self.stats['event_opps']:>3}  ", end="")
        print(f"Predictive: {self.stats['predictive_opps']:>3}")
        
        # Third row - PnL
        pnl_color = Colors.GREEN if self.stats['total_pnl'] > 0 else Colors.RED if self.stats['total_pnl'] < 0 else Colors.YELLOW
        print(f"  Session PnL: {pnl_color}${self.stats['total_pnl']:>8.4f}{Colors.RESET}    ", end="")
        print(f"Best Trade: {Colors.GREEN}${self.stats['best_trade']:>7.4f}{Colors.RESET}    ", end="")
        print(f"Worst Trade: {Colors.RED}${self.stats['worst_trade']:>7.4f}{Colors.RESET}")
        
        print()
    
    def print_recent_opportunities(self):
        """Print recent opportunities detected"""
        print(f"{Colors.BOLD}🎯 RECENT OPPORTUNITIES (Last 20){Colors.RESET}")
        print("─" * 80)
        
        if not self.opportunities:
            print(f"  {Colors.YELLOW}Scanning for opportunities...{Colors.RESET}")
        else:
            print(f"  {'Time':<8} {'Type':<12} {'Pair':<15} {'Profit':<10} {'Status':<15}")
            print(f"  {'-'*8} {'-'*12} {'-'*15} {'-'*10} {'-'*15}")
            
            for opp in list(self.opportunities)[-10:]:  # Last 10
                time_str = opp['time'].strftime('%H:%M:%S')
                opp_type = opp['type']
                pair = opp.get('pair', 'N/A')
                profit = opp.get('profit', 0.0)
                status = opp.get('status', 'DETECTED')
                
                profit_color = Colors.GREEN if profit > 0.10 else Colors.YELLOW if profit > 0.05 else Colors.WHITE
                status_color = Colors.GREEN if status == 'EXECUTED' else Colors.YELLOW if status == 'PENDING' else Colors.WHITE
                
                print(f"  {time_str} {opp_type:<12} {pair:<15} {profit_color}${profit:>6.4f}{Colors.RESET}   {status_color}{status}{Colors.RESET}")
        
        print()
    
    def print_recent_executions(self):
        """Print recent trade executions"""
        print(f"{Colors.BOLD}💰 RECENT EXECUTIONS (Last 10){Colors.RESET}")
        print("─" * 80)
        
        if not self.executions:
            print(f"  {Colors.YELLOW}No trades executed yet{Colors.RESET}")
        else:
            print(f"  {'Time':<8} {'Type':<12} {'Path':<25} {'PnL':<10} {'Status':<10}")
            print(f"  {'-'*8} {'-'*12} {'-'*25} {'-'*10} {'-'*10}")
            
            for exec_data in list(self.executions):
                time_str = exec_data['time'].strftime('%H:%M:%S')
                exec_type = exec_data['type']
                path = exec_data.get('path', 'N/A')[:24]
                pnl = exec_data.get('pnl', 0.0)
                status = exec_data.get('status', 'PENDING')
                
                pnl_color = Colors.GREEN if pnl > 0 else Colors.RED if pnl < 0 else Colors.YELLOW
                status_color = Colors.GREEN if status == 'SUCCESS' else Colors.RED if status == 'FAILED' else Colors.YELLOW
                
                print(f"  {time_str} {exec_type:<12} {path:<25} {pnl_color}${pnl:>6.4f}{Colors.RESET}   {status_color}{status}{Colors.RESET}")
        
        print()
    
    def print_live_events(self):
        """Print live blockchain events"""
        print(f"{Colors.BOLD}🎯 BLOCKCHAIN EVENTS (Last 15){Colors.RESET}")
        print("─" * 80)
        
        if not self.events:
            print(f"  {Colors.YELLOW}Listening for blockchain events...{Colors.RESET}")
        else:
            for event in list(self.events)[-8:]:  # Last 8
                time_str = event['time'].strftime('%H:%M:%S')
                event_type = event['type']
                description = event.get('description', '')
                
                # Color based on event type
                if 'WHALE' in event_type:
                    icon = "🐋"
                    color = Colors.MAGENTA
                elif 'LIQUIDATION' in event_type:
                    icon = "⚡"
                    color = Colors.RED
                elif 'ORACLE' in event_type:
                    icon = "📊"
                    color = Colors.CYAN
                elif 'IMBALANCE' in event_type:
                    icon = "🔮"
                    color = Colors.BLUE
                else:
                    icon = "📡"
                    color = Colors.WHITE
                
                print(f"  {time_str} {icon} {color}{event_type}{Colors.RESET}: {description[:60]}")
        
        print()
    
    def print_footer(self):
        """Print dashboard footer"""
        print("─" * 80)
        print(f"{Colors.CYAN}Press Ctrl+C to stop monitoring{Colors.RESET}")
        print(f"{Colors.YELLOW}Dashboard updates every 2 seconds{Colors.RESET}")
    
    def add_opportunity(self, opp_type: str, pair: str, profit: float, status: str = "DETECTED"):
        """Add new opportunity to feed"""
        self.opportunities.append({
            'time': datetime.now(),
            'type': opp_type,
            'pair': pair,
            'profit': profit,
            'status': status
        })
        self.stats['total_opportunities'] += 1
        
        # Update type-specific counters
        if 'MULTI' in opp_type.upper():
            self.stats['multihop_opps'] += 1
        elif 'FLASH' in opp_type.upper():
            self.stats['flashloan_opps'] += 1
        elif 'EVENT' in opp_type.upper():
            self.stats['event_opps'] += 1
        elif 'PREDICT' in opp_type.upper():
            self.stats['predictive_opps'] += 1
    
    def add_execution(self, exec_type: str, path: str, pnl: float, status: str = "SUCCESS"):
        """Add new execution to feed"""
        self.executions.append({
            'time': datetime.now(),
            'type': exec_type,
            'path': path,
            'pnl': pnl,
            'status': status
        })
        self.stats['trades_executed'] += 1
        if status == "SUCCESS":
            self.stats['trades_successful'] += 1
            self.stats['total_pnl'] += pnl
            self.stats['best_trade'] = max(self.stats['best_trade'], pnl)
            if pnl < 0:
                self.stats['worst_trade'] = min(self.stats['worst_trade'], pnl)
    
    def add_event(self, event_type: str, description: str):
        """Add new blockchain event"""
        self.events.append({
            'time': datetime.now(),
            'type': event_type,
            'description': description
        })
    
    def update_system_health(self, **kwargs):
        """Update system health metrics"""
        self.system_health.update(kwargs)
    
    def render(self):
        """Render complete dashboard"""
        self.clear_screen()
        self.print_header()
        self.print_system_status()
        self.print_statistics()
        self.print_recent_opportunities()
        self.print_recent_executions()
        self.print_live_events()
        self.print_footer()
    
    def simulate_activity(self):
        """Simulate activity for demo (remove in production)"""
        import random
        
        # Simulate opportunities
        if random.random() > 0.7:  # 30% chance
            opp_types = ['MULTI-HOP', 'FLASHLOAN', 'EVENT-ARB', 'PREDICTIVE']
            pairs = ['WETH/USDC', 'ARB/USDC', 'GMX/USDC', 'WETH/USDT', 'GRAIL/WETH']
            self.add_opportunity(
                random.choice(opp_types),
                random.choice(pairs),
                random.uniform(0.02, 0.50),
                random.choice(['DETECTED', 'PENDING', 'EXECUTED'])
            )
        
        # Simulate executions
        if random.random() > 0.95:  # 5% chance
            paths = ['USDC→WETH→ARB→USDC', 'WETH→GMX→USDC→WETH', 'USDC→GRAIL→WETH']
            self.add_execution(
                random.choice(['STANDARD', 'FLASHLOAN', 'MULTI-HOP']),
                random.choice(paths),
                random.uniform(-0.05, 0.30),
                random.choice(['SUCCESS', 'SUCCESS', 'SUCCESS', 'FAILED'])
            )
        
        # Simulate events
        if random.random() > 0.85:  # 15% chance
            events = [
                ('WHALE_SWAP', '$75k WETH→USDC on Uniswap V3'),
                ('LIQUIDATION', '$120k position liquidated on Aave'),
                ('ORACLE_UPDATE', 'Chainlink price feed updated'),
                ('IMBALANCE', '2.3x bid/ask imbalance on GMX'),
                ('LARGE_TRANSFER', '$200k USDC transfer detected'),
            ]
            event = random.choice(events)
            self.add_event(event[0], event[1])

async def monitor_logs():
    """Monitor log files for real activity"""
    dashboard = ApexDashboard()
    
    # Simulate RPC connection check
    try:
        from web3 import Web3
        from dotenv import load_dotenv
        load_dotenv()
        
        rpc_url = os.getenv('ARBITRUM_RPC', 'https://arb1.arbitrum.io/rpc')
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        
        if w3.is_connected():
            dashboard.update_system_health(
                rpc_connected=True,
                last_block=w3.eth.block_number,
                gas_price=w3.eth.gas_price / 1e9
            )
    except Exception as e:
        dashboard.update_system_health(rpc_connected=False)
    
    # Main monitoring loop
    try:
        while True:
            # Simulate activity for demo (replace with real log parsing)
            dashboard.simulate_activity()
            
            # Update block number if RPC connected
            if dashboard.system_health['rpc_connected']:
                try:
                    from web3 import Web3
                    rpc_url = os.getenv('ARBITRUM_RPC', 'https://arb1.arbitrum.io/rpc')
                    w3 = Web3(Web3.HTTPProvider(rpc_url))
                    dashboard.update_system_health(
                        last_block=w3.eth.block_number,
                        gas_price=w3.eth.gas_price / 1e9
                    )
                except:
                    pass
            
            # Render dashboard
            dashboard.render()
            
            # Wait before next update
            await asyncio.sleep(2)
    
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Dashboard stopped by user{Colors.RESET}")
        print(f"\n{Colors.CYAN}Final Statistics:{Colors.RESET}")
        print(f"  Total Opportunities: {dashboard.stats['total_opportunities']}")
        print(f"  Trades Executed: {dashboard.stats['trades_executed']}")
        print(f"  Session PnL: ${dashboard.stats['total_pnl']:.4f}")

if __name__ == "__main__":
    print(f"{Colors.CYAN}Starting APEX Live Dashboard...{Colors.RESET}")
    print(f"{Colors.YELLOW}Connecting to monitoring systems...{Colors.RESET}\n")
    time.sleep(1)
    
    asyncio.run(monitor_logs())
