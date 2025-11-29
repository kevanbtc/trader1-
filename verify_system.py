#!/usr/bin/env python3
"""
✅ SYSTEM VERIFICATION SCRIPT
Validates all subsystems are present and functional
"""

import os
import sys
from pathlib import Path

# Color codes
C_GREEN = '\033[92m'
C_RED = '\033[91m'
C_YELLOW = '\033[93m'
C_CYAN = '\033[96m'
C_BOLD = '\033[1m'
C_RESET = '\033[0m'

def check_module(module_name, description):
    """Check if a module exists and can be imported"""
    try:
        __import__(module_name)
        print(f"  {C_GREEN}✓{C_RESET} {description}")
        return True
    except ImportError as e:
        print(f"  {C_RED}✗{C_RESET} {description} - {e}")
        return False

def check_file(file_path, description):
    """Check if a file exists"""
    if Path(file_path).exists():
        print(f"  {C_GREEN}✓{C_RESET} {description}")
        return True
    else:
        print(f"  {C_RED}✗{C_RESET} {description} - File not found")
        return False

def check_env_var(var_name, description, required=True):
    """Check if environment variable is set"""
    value = os.getenv(var_name)
    if value:
        # Mask sensitive values
        if 'KEY' in var_name or 'SECRET' in var_name:
            display_value = f"{value[:8]}...{value[-4:]}" if len(value) > 12 else "***"
        else:
            display_value = value
        print(f"  {C_GREEN}✓{C_RESET} {description}: {display_value}")
        return True
    else:
        if required:
            print(f"  {C_RED}✗{C_RESET} {description} - NOT SET")
        else:
            print(f"  {C_YELLOW}⚠{C_RESET} {description} - Optional, not set")
        return not required

def main():
    print(f"\n{C_BOLD}{C_CYAN}{'='*80}{C_RESET}")
    print(f"{C_BOLD}{C_CYAN}🔍 TRADING ENGINE SYSTEM VERIFICATION{C_RESET}")
    print(f"{C_BOLD}{C_CYAN}{'='*80}{C_RESET}\n")
    
    # Load .env
    env_file = Path('.env')
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
    
    all_checks = []
    
    # 1. Core Trading Components
    print(f"{C_BOLD}1. Core Trading Components{C_RESET}")
    all_checks.append(check_file('agents/defi_price_feed.py', 'Price Feed Scanner'))
    all_checks.append(check_file('agents/defi_execution_engine.py', 'Execution Engine'))
    all_checks.append(check_file('agents/trading_supervisor.py', 'Trading Supervisor'))
    all_checks.append(check_file('start_trading.py', 'Main Trading Script'))
    all_checks.append(check_file('autonomous_master.py', 'Autonomous Master Controller'))
    print()
    
    # 2. Intelligence Layer
    print(f"{C_BOLD}2. Intelligence & Decision Layer{C_RESET}")
    all_checks.append(check_file('agents/mcp_intelligence.py', 'MCP Intelligence'))
    all_checks.append(check_file('agents/swarm_coordinator.py', 'Swarm Coordinator'))
    all_checks.append(check_file('agents/intel_ingestor.py', 'Intel Ingestor'))
    all_checks.append(check_file('agents/intelligence_loop.py', 'Intelligence Loop'))
    print()
    
    # 3. Risk & Safety Layer
    print(f"{C_BOLD}3. Risk Management & Safety Systems{C_RESET}")
    all_checks.append(check_file('agents/risk_guardian.py', 'Risk Guardian'))
    all_checks.append(check_file('agents/professional_risk_manager.py', 'Professional Risk Manager'))
    all_checks.append(check_file('agents/gas_sentinel.py', 'Gas Sentinel'))
    all_checks.append(check_file('agents/liquidity_monitor.py', 'Liquidity Monitor'))
    all_checks.append(check_file('agents/flash_crash_detector.py', 'Flash Crash Detector'))
    all_checks.append(check_file('agents/position_monitor.py', 'Position Monitor'))
    print()
    
    # 4. APEX Mode Subsystems
    print(f"{C_BOLD}4. APEX Mode Advanced Subsystems{C_RESET}")
    all_checks.append(check_file('agents/apex_coordinator.py', 'APEX Coordinator'))
    all_checks.append(check_file('agents/multi_hop_router.py', 'Multi-Hop Router'))
    all_checks.append(check_file('agents/flashloan_executor.py', 'Flashloan Executor'))
    all_checks.append(check_file('agents/block_event_hunter.py', 'Block Event Hunter'))
    all_checks.append(check_file('agents/predictive_liquidity.py', 'Predictive Liquidity'))
    print()
    
    # 5. Execution & Smart Routing
    print(f"{C_BOLD}5. Smart Execution Layer{C_RESET}")
    all_checks.append(check_file('agents/smart_executor.py', 'Smart Executor'))
    all_checks.append(check_file('agents/flashbots_executor.py', 'Flashbots Executor'))
    all_checks.append(check_file('agents/execution_engine.py', 'Base Execution Engine'))
    print()
    
    # 6. Market Intelligence & Tracking
    print(f"{C_BOLD}6. Market Intelligence & Tracking{C_RESET}")
    all_checks.append(check_file('agents/oracle_validator.py', 'Oracle Validator'))
    all_checks.append(check_file('agents/price_validator.py', 'Price Validator'))
    all_checks.append(check_file('agents/smart_money_tracker.py', 'Smart Money Tracker'))
    all_checks.append(check_file('agents/whale_shadow_trader.py', 'Whale Shadow Trader'))
    all_checks.append(check_file('agents/volume_spike_scanner.py', 'Volume Spike Scanner'))
    all_checks.append(check_file('agents/strategy_reverse_engineer.py', 'Strategy Reverse Engineer'))
    all_checks.append(check_file('agents/master_scanner.py', 'Master Scanner'))
    print()
    
    # 7. Specialized Trading Strategies
    print(f"{C_BOLD}7. Specialized Trading Strategies{C_RESET}")
    all_checks.append(check_file('agents/aggressive_hunter.py', 'Aggressive Hunter'))
    all_checks.append(check_file('agents/continuous_hunter.py', 'Continuous Hunter'))
    all_checks.append(check_file('agents/rapid_scanner.py', 'Rapid Scanner'))
    all_checks.append(check_file('agents/real_dex_scanner.py', 'Real DEX Scanner'))
    all_checks.append(check_file('agents/token_sniper.py', 'Token Sniper'))
    all_checks.append(check_file('agents/opportunity_analyzer.py', 'Opportunity Analyzer'))
    print()
    
    # 8. Multi-Strategy & Coordination
    print(f"{C_BOLD}8. Multi-Strategy Coordination{C_RESET}")
    all_checks.append(check_file('agents/multi_strategy_executor.py', 'Multi-Strategy Executor'))
    all_checks.append(check_file('agents/autonomous_trader.py', 'Autonomous Trader'))
    all_checks.append(check_file('agents/wallet_rotator.py', 'Wallet Rotator'))
    print()
    
    # 9. Cross-Chain & DeFi
    print(f"{C_BOLD}9. Cross-Chain & Advanced DeFi{C_RESET}")
    all_checks.append(check_file('agents/cross_chain_bridge.py', 'Cross-Chain Bridge'))
    all_checks.append(check_file('agents/leverage_trader.py', 'Leverage Trader'))
    print()
    
    # 10. Utilities & Infrastructure
    print(f"{C_BOLD}10. Infrastructure & Utilities{C_RESET}")
    all_checks.append(check_file('agents/rpc_utils.py', 'RPC Utilities'))
    all_checks.append(check_file('agents/multi_provider_rpc.py', 'Multi-Provider RPC'))
    all_checks.append(check_file('agents/rpc_errors.py', 'RPC Error Handling'))
    print()
    
    # 11. Monitoring & Visualization
    print(f"{C_BOLD}11. Monitoring & Visualization{C_RESET}")
    all_checks.append(check_file('wallet_tracker.py', 'Wallet Balance Tracker'))
    all_checks.append(check_file('live_monitor.py', 'Live Monitor Dashboard'))
    all_checks.append(check_file('check_wallet.py', 'Wallet Checker'))
    print()
    
    # 12. Configuration
    print(f"{C_BOLD}12. Configuration Files{C_RESET}")
    all_checks.append(check_file('.env', 'Environment Configuration'))
    all_checks.append(check_file('config/aggressive_overnight_bots.json', 'Bot Configuration'))
    all_checks.append(check_file('config/smart_predator_tokens.json', 'Token Universe'))
    all_checks.append(check_file('config/trading_config.json', 'Trading Config'))
    all_checks.append(check_file('requirements.txt', 'Python Dependencies'))
    print()
    
    # 13. Environment Variables
    print(f"{C_BOLD}13. Critical Environment Variables{C_RESET}")
    all_checks.append(check_env_var('TRADING_MODE', 'Trading Mode', required=True))
    all_checks.append(check_env_var('ENABLE_PAPER_MODE', 'Paper Mode Flag', required=True))
    all_checks.append(check_env_var('WALLET_ADDRESS', 'Wallet Address', required=True))
    all_checks.append(check_env_var('WALLET_PRIVATE_KEY', 'Private Key', required=True))
    all_checks.append(check_env_var('MAX_POSITION_USD', 'Max Position Size', required=True))
    all_checks.append(check_env_var('MIN_PROFIT_USD', 'Min Profit Threshold', required=True))
    all_checks.append(check_env_var('SCAN_INTERVAL_MS', 'Scan Interval', required=True))
    all_checks.append(check_env_var('MAX_GAS_GWEI', 'Max Gas Price', required=True))
    print()
    
    # 14. Intelligence Configuration
    print(f"{C_BOLD}14. Intelligence System Configuration{C_RESET}")
    all_checks.append(check_env_var('ENABLE_MCP', 'MCP Intelligence', required=True))
    all_checks.append(check_env_var('ENABLE_SWARM', 'Swarm Intelligence', required=True))
    all_checks.append(check_env_var('ENABLE_INTEL_INGESTOR', 'Intel Ingestor', required=True))
    all_checks.append(check_env_var('MCP_CONFIDENCE_THRESHOLD', 'MCP Threshold', required=False))
    all_checks.append(check_env_var('SWARM_REQUIRED_AGREEMENT', 'Swarm Agreement', required=False))
    print()
    
    # 15. APEX Mode Configuration
    print(f"{C_BOLD}15. APEX Mode Configuration{C_RESET}")
    all_checks.append(check_env_var('ENABLE_APEX_MODE', 'APEX Mode', required=False))
    all_checks.append(check_env_var('ENABLE_MULTIHOP', 'Multi-Hop', required=False))
    all_checks.append(check_env_var('ENABLE_FLASHLOAN', 'Flashloan', required=False))
    all_checks.append(check_env_var('ENABLE_EVENT_HUNTER', 'Event Hunter', required=False))
    all_checks.append(check_env_var('ENABLE_PREDICTIVE', 'Predictive Model', required=False))
    print()
    
    # 16. RPC Configuration
    print(f"{C_BOLD}16. RPC Configuration{C_RESET}")
    all_checks.append(check_env_var('ARB_RPC_1', 'Primary RPC', required=True))
    all_checks.append(check_env_var('ARB_RPC_2', 'Secondary RPC', required=False))
    all_checks.append(check_env_var('ARB_RPC_3', 'Tertiary RPC', required=False))
    print()
    
    # 17. DEX Configuration
    print(f"{C_BOLD}17. DEX Universe Configuration{C_RESET}")
    dexes = [
        ('ENABLE_UNISWAP', 'Uniswap'),
        ('ENABLE_SUSHISWAP', 'Sushiswap'),
        ('ENABLE_CURVE', 'Curve'),
        ('ENABLE_CAMELOT', 'Camelot'),
        ('ENABLE_BALANCER', 'Balancer'),
        ('ENABLE_TRADERJOE', 'TraderJoe'),
        ('ENABLE_RAMSES', 'Ramses'),
        ('ENABLE_KYBERSWAP', 'KyberSwap'),
        ('ENABLE_FRAXSWAP', 'Fraxswap'),
    ]
    for var, name in dexes:
        all_checks.append(check_env_var(var, f'{name} DEX', required=False))
    print()
    
    # Summary
    passed = sum(all_checks)
    total = len(all_checks)
    percentage = (passed / total * 100) if total > 0 else 0
    
    print(f"{C_BOLD}{C_CYAN}{'='*80}{C_RESET}")
    print(f"{C_BOLD}VERIFICATION SUMMARY{C_RESET}")
    print(f"{C_BOLD}{C_CYAN}{'='*80}{C_RESET}")
    
    if percentage == 100:
        print(f"\n{C_GREEN}{C_BOLD}✅ ALL SYSTEMS OPERATIONAL{C_RESET}")
        print(f"{C_GREEN}Passed: {passed}/{total} checks (100%){C_RESET}")
        print(f"\n{C_GREEN}🚀 System is READY for autonomous trading!{C_RESET}")
    elif percentage >= 90:
        print(f"\n{C_YELLOW}{C_BOLD}⚠️  MOSTLY OPERATIONAL{C_RESET}")
        print(f"{C_YELLOW}Passed: {passed}/{total} checks ({percentage:.1f}%){C_RESET}")
        print(f"\n{C_YELLOW}Some optional components missing but core systems ready{C_RESET}")
    else:
        print(f"\n{C_RED}{C_BOLD}❌ CRITICAL ISSUES DETECTED{C_RESET}")
        print(f"{C_RED}Passed: {passed}/{total} checks ({percentage:.1f}%){C_RESET}")
        print(f"\n{C_RED}System NOT ready for trading - fix critical issues first{C_RESET}")
    
    print(f"\n{C_CYAN}{'='*80}{C_RESET}\n")
    
    return percentage == 100

if __name__ == '__main__':
    # Enable ANSI on Windows
    if os.name == 'nt':
        os.system('color')
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    
    success = main()
    sys.exit(0 if success else 1)
