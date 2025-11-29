#!/usr/bin/env python3
"""
🎯 AWS MISSION CONTROL - Unified Trading Dashboard
Real-time monitoring of your AWS trading engine from Windows
"""

import os
import sys
import json
import time
import subprocess
from datetime import datetime
from pathlib import Path

# ANSI Colors
class C:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'

# AWS Configuration
AWS_IP = "54.158.163.67"
PEM_PATH = r"C:\Users\Kevan\donk x\donkx-prod.pem"
SSH_BASE = f'ssh -i "{PEM_PATH}" ubuntu@{AWS_IP}'

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def ssh_cmd(cmd):
    """Execute SSH command and return output"""
    try:
        result = subprocess.run(
            f'{SSH_BASE} "{cmd}"',
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.stdout.strip()
    except Exception as e:
        return f"ERROR: {e}"

def draw_header():
    """Draw dashboard header"""
    print(f"{C.BOLD}{C.CYAN}{'='*80}{C.RESET}")
    print(f"{C.BOLD}{C.WHITE}🎯 AWS MISSION CONTROL - APEX TRADING ENGINE{C.RESET}")
    print(f"{C.CYAN}{'='*80}{C.RESET}")
    print(f"{C.DIM}AWS IP: {AWS_IP} | Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{C.RESET}")
    print()

def get_process_status():
    """Get trading process status"""
    cmd = "ps aux | grep 'start_trading' | grep -v grep | awk '{print $2,$3,$4}'"
    result = ssh_cmd(cmd)
    if result and not result.startswith("ERROR"):
        parts = result.split()
        if len(parts) >= 3:
            return {
                'pid': parts[0],
                'cpu': float(parts[1]),
                'ram': float(parts[2]),
                'status': 'RUNNING'
            }
    return {'status': 'STOPPED'}

def get_supervisor_status():
    """Get supervisor service status"""
    cmd = "sudo supervisorctl status 2>/dev/null"
    result = ssh_cmd(cmd)
    services = {}
    for line in result.split('\n'):
        if line.strip():
            parts = line.split()
            if len(parts) >= 2:
                name = parts[0].replace('apex-full-stack:', '')
                status = parts[1]
                services[name] = status
    return services

def get_scan_stats():
    """Get scanning statistics"""
    cmd = "grep -c 'SCAN' ~/apex/logs/opportunity_ledger.log 2>/dev/null || echo 0"
    total_scans = ssh_cmd(cmd)
    
    cmd = "tail -20 ~/apex/logs/opportunity_ledger.log 2>/dev/null | grep 'SCAN' | tail -1"
    latest_scan = ssh_cmd(cmd)
    
    cmd = "grep -i 'profit.*USD' ~/apex/logs/opportunity_ledger.log 2>/dev/null | wc -l"
    opportunities = ssh_cmd(cmd)
    
    return {
        'total_scans': int(total_scans) if total_scans.isdigit() else 0,
        'latest_scan': latest_scan,
        'opportunities': int(opportunities) if opportunities.isdigit() else 0
    }

def get_uptime():
    """Get process uptime"""
    cmd = "ps -p $(pgrep -f 'start_trading' | head -1) -o etime= 2>/dev/null"
    result = ssh_cmd(cmd)
    return result.strip() if result else "Unknown"

def get_recent_activity():
    """Get last 5 log entries"""
    cmd = "tail -15 ~/apex/logs/opportunity_ledger.log 2>/dev/null | grep -E 'SCAN|opportunity|No opportunities' | tail -5"
    result = ssh_cmd(cmd)
    return result.split('\n') if result else []

def draw_status_box(title, content, color=C.WHITE):
    """Draw a status box"""
    print(f"{C.BOLD}{color}┌{'─'*78}┐{C.RESET}")
    print(f"{C.BOLD}{color}│ {title:<76} │{C.RESET}")
    print(f"{C.BOLD}{color}├{'─'*78}┤{C.RESET}")
    for line in content:
        print(f"{color}│{C.RESET} {line:<77}{color}│{C.RESET}")
    print(f"{C.BOLD}{color}└{'─'*78}┘{C.RESET}")
    print()

def format_status_indicator(status):
    """Format status with color indicator"""
    if status == 'RUNNING':
        return f"{C.GREEN}● RUNNING{C.RESET}"
    elif status == 'STOPPED':
        return f"{C.RED}● STOPPED{C.RESET}"
    else:
        return f"{C.YELLOW}● {status}{C.RESET}"

def main():
    """Main dashboard loop"""
    print(f"{C.CYAN}Connecting to AWS trading engine...{C.RESET}")
    
    while True:
        try:
            clear()
            draw_header()
            
            # 1. Process Status
            process = get_process_status()
            if process['status'] == 'RUNNING':
                content = [
                    f"Process ID: {C.GREEN}{process['pid']}{C.RESET}",
                    f"CPU Usage: {C.YELLOW}{process['cpu']}%{C.RESET}",
                    f"RAM Usage: {C.YELLOW}{process['ram']}%{C.RESET}",
                    f"Uptime: {C.CYAN}{get_uptime()}{C.RESET}",
                    f"Status: {format_status_indicator('RUNNING')}"
                ]
            else:
                content = [
                    f"Status: {format_status_indicator('STOPPED')}",
                    f"{C.RED}Trading engine is not running!{C.RESET}"
                ]
            draw_status_box("🐉 TRADING ENGINE", content, C.CYAN)
            
            # 2. Services Status
            services = get_supervisor_status()
            content = []
            for name, status in services.items():
                indicator = format_status_indicator(status)
                content.append(f"{name:<30} {indicator}")
            if not content:
                content = [f"{C.YELLOW}No service status available{C.RESET}"]
            draw_status_box("⚙️  SERVICES", content, C.BLUE)
            
            # 3. Scanning Activity
            stats = get_scan_stats()
            content = [
                f"Total Scans: {C.WHITE}{stats['total_scans']:,}{C.RESET}",
                f"Opportunities Found: {C.GREEN}{stats['opportunities']}{C.RESET}",
                f"Scan Rate: {C.CYAN}~{stats['total_scans']/max(1, int(get_uptime().split(':')[0] or '1'))} scans/min{C.RESET}",
            ]
            draw_status_box("🔍 SCANNING STATS", content, C.MAGENTA)
            
            # 4. Recent Activity
            activity = get_recent_activity()
            content = []
            for line in activity[-5:]:
                if 'No opportunities' in line:
                    content.append(f"{C.DIM}{line[:75]}{C.RESET}")
                elif 'SCAN' in line:
                    content.append(f"{C.CYAN}{line[:75]}{C.RESET}")
                elif 'opportunity' in line.lower():
                    content.append(f"{C.GREEN}{line[:75]}{C.RESET}")
                else:
                    content.append(line[:75])
            if not content:
                content = [f"{C.DIM}No recent activity{C.RESET}"]
            draw_status_box("📊 RECENT ACTIVITY", content, C.YELLOW)
            
            # Footer
            print(f"{C.DIM}Press Ctrl+C to exit | Refreshes every 5 seconds{C.RESET}")
            
            time.sleep(5)
            
        except KeyboardInterrupt:
            print(f"\n{C.CYAN}Disconnecting from mission control...{C.RESET}")
            break
        except Exception as e:
            print(f"\n{C.RED}Error: {e}{C.RESET}")
            time.sleep(5)

if __name__ == '__main__':
    main()
