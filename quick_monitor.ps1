# AWS Trading Engine - Quick Monitor Launcher
# PowerShell version with better Windows support

param(
    [string]$View = ""
)

$PEM = "C:\Users\Kevan\donk x\donkx-prod.pem"
$IP = "54.158.163.67"

function Show-Menu {
    Clear-Host
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "   AWS TRADING ENGINE - MONITORING" -ForegroundColor White
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Choose your view:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "[1] Mission Control (Unified Dashboard)" -ForegroundColor White
    Write-Host "[2] Live Opportunity Ledger" -ForegroundColor White
    Write-Host "[3] Process & Service Status" -ForegroundColor White
    Write-Host "[4] Recent Activity Stream" -ForegroundColor White
    Write-Host "[5] Quick Stats Summary" -ForegroundColor White
    Write-Host "[6] Service Control (Restart/Stop)" -ForegroundColor White
    Write-Host "[7] Exit" -ForegroundColor Red
    Write-Host ""
}

function Launch-MissionControl {
    Write-Host ""
    Write-Host "🚀 Launching Mission Control Dashboard..." -ForegroundColor Cyan
    Write-Host ""
    python aws_mission_control.py
}

function Watch-OpportunityLedger {
    Write-Host ""
    Write-Host "📊 Connecting to opportunity ledger..." -ForegroundColor Cyan
    Write-Host "Press Ctrl+C to exit" -ForegroundColor Yellow
    Write-Host ""
    ssh -i "$PEM" ubuntu@$IP "tail -f ~/apex/logs/opportunity_ledger.log"
}

function Show-ProcessStatus {
    Write-Host ""
    Write-Host "⚙️  Checking process status..." -ForegroundColor Cyan
    Write-Host ""
    ssh -i "$PEM" ubuntu@$IP @"
echo '🐉 TRADING ENGINE PROCESS:'
ps aux | grep 'start_trading' | grep -v grep | awk '{print \"  PID: \" `$2 \" | CPU: \" `$3\"% | RAM: \" `$4\"%\"}'
echo ''
echo '⏱️  UPTIME:'
ps -p `$(pgrep -f 'start_trading' | head -1) -o etime= 2>/dev/null
echo ''
echo '📊 SERVICES:'
sudo supervisorctl status
echo ''
echo '🔍 SCAN STATS:'
echo \"  Total scans: `$(grep -c SCAN ~/apex/logs/opportunity_ledger.log 2>/dev/null)\"
echo \"  Opportunities found: `$(grep -i 'profit.*USD' ~/apex/logs/opportunity_ledger.log 2>/dev/null | wc -l)\"
"@
    Write-Host ""
    pause
}

function Show-RecentActivity {
    Write-Host ""
    Write-Host "Recent activity (last 50 entries)..." -ForegroundColor Cyan
    Write-Host ""
    ssh -i "$PEM" ubuntu@$IP "tail -50 ~/apex/logs/opportunity_ledger.log; echo ''; echo '--- LIVE STREAM (Ctrl+C to exit) ---'; tail -f ~/apex/logs/opportunity_ledger.log"
}

function Show-QuickStats {
    Write-Host ""
    Write-Host "💰 Fetching quick stats..." -ForegroundColor Cyan
    Write-Host ""
    
    $stats = ssh -i "$PEM" ubuntu@$IP @"
echo 'SCANS:'
grep -c SCAN ~/apex/logs/opportunity_ledger.log 2>/dev/null || echo 0
echo 'OPPORTUNITIES:'
grep -i 'profit.*USD' ~/apex/logs/opportunity_ledger.log 2>/dev/null | wc -l
echo 'UPTIME:'
ps -p `$(pgrep -f 'start_trading' | head -1) -o etime= 2>/dev/null || echo 'Not running'
echo 'CPU:'
ps aux | grep 'start_trading' | grep -v grep | awk '{print `$3}' || echo '0'
echo 'RAM:'
ps aux | grep 'start_trading' | grep -v grep | awk '{print `$4}' || echo '0'
echo 'STATUS:'
sudo supervisorctl status | grep 'apex-trading-dragon' | awk '{print `$2}'
"@
    
    $lines = $stats -split "`n"
    $scans = 0
    $opps = 0
    $uptime = "Unknown"
    $cpu = "0"
    $ram = "0"
    $status = "Unknown"
    
    for ($i = 0; $i -lt $lines.Length; $i++) {
        if ($lines[$i] -eq "SCANS:" -and $i+1 -lt $lines.Length) { $scans = $lines[$i+1] }
        if ($lines[$i] -eq "OPPORTUNITIES:" -and $i+1 -lt $lines.Length) { $opps = $lines[$i+1] }
        if ($lines[$i] -eq "UPTIME:" -and $i+1 -lt $lines.Length) { $uptime = $lines[$i+1].Trim() }
        if ($lines[$i] -eq "CPU:" -and $i+1 -lt $lines.Length) { $cpu = $lines[$i+1] }
        if ($lines[$i] -eq "RAM:" -and $i+1 -lt $lines.Length) { $ram = $lines[$i+1] }
        if ($lines[$i] -eq "STATUS:" -and $i+1 -lt $lines.Length) { $status = $lines[$i+1] }
    }
    
    Write-Host "╔════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║    AWS TRADING ENGINE QUICK STATS      ║" -ForegroundColor White
    Write-Host "╠════════════════════════════════════════╣" -ForegroundColor Cyan
    Write-Host "║                                        ║"
    Write-Host "║  Status:         " -NoNewline
    if ($status -eq "RUNNING") {
        Write-Host "$status          " -ForegroundColor Green -NoNewline
    } else {
        Write-Host "$status          " -ForegroundColor Red -NoNewline
    }
    Write-Host "║"
    Write-Host "║  Uptime:         $uptime" -NoNewline
    Write-Host (" " * (23 - $uptime.Length)) -NoNewline
    Write-Host "║"
    Write-Host "║  CPU Usage:      $cpu%" -NoNewline
    Write-Host (" " * (22 - $cpu.Length)) -NoNewline
    Write-Host "║"
    Write-Host "║  RAM Usage:      $ram%" -NoNewline
    Write-Host (" " * (22 - $ram.Length)) -NoNewline
    Write-Host "║"
    Write-Host "║                                        ║"
    Write-Host "║  Total Scans:    $scans" -NoNewline
    Write-Host (" " * (23 - $scans.ToString().Length)) -NoNewline
    Write-Host "║"
    Write-Host "║  Opportunities:  $opps" -NoNewline
    Write-Host (" " * (23 - $opps.ToString().Length)) -NoNewline
    Write-Host "║"
    Write-Host "║                                        ║"
    Write-Host "╚════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""
    pause
}

function Show-ServiceControl {
    Write-Host ""
    Write-Host "SERVICE CONTROL" -ForegroundColor Cyan
    Write-Host "==================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "[1] Restart Trading Engine" -ForegroundColor White
    Write-Host "[2] Restart All Services" -ForegroundColor White
    Write-Host "[3] Stop Trading Engine" -ForegroundColor White
    Write-Host "[4] View Current Status" -ForegroundColor White
    Write-Host "[5] Back to Main Menu" -ForegroundColor Yellow
    Write-Host ""
    
    $choice = Read-Host "Enter choice (1-5)"
    
    switch ($choice) {
        "1" {
            Write-Host ""
            Write-Host "⚠️  Restarting trading engine..." -ForegroundColor Yellow
            ssh -i "$PEM" ubuntu@$IP "sudo supervisorctl restart apex-full-stack:apex-trading-dragon"
            Write-Host "✅ Trading engine restarted!" -ForegroundColor Green
            Start-Sleep -Seconds 2
        }
        "2" {
            Write-Host ""
            Write-Host "⚠️  Restarting all services..." -ForegroundColor Yellow
            ssh -i "$PEM" ubuntu@$IP "sudo supervisorctl restart apex-full-stack:"
            Write-Host "✅ All services restarted!" -ForegroundColor Green
            Start-Sleep -Seconds 2
        }
        "3" {
            Write-Host ""
            Write-Host "⚠️  WARNING: This will stop trading!" -ForegroundColor Red
            $confirm = Read-Host "Type YES to confirm"
            if ($confirm -eq "YES") {
                ssh -i "$PEM" ubuntu@$IP "sudo supervisorctl stop apex-full-stack:apex-trading-dragon"
                Write-Host "⛔ Trading engine stopped!" -ForegroundColor Red
            } else {
                Write-Host "❌ Cancelled" -ForegroundColor Yellow
            }
            Start-Sleep -Seconds 2
        }
        "4" {
            ssh -i "$PEM" ubuntu@$IP "sudo supervisorctl status"
            pause
        }
    }
}

# Main loop
if ($View -ne "") {
    # Direct launch if view specified
    switch ($View) {
        "mission" { Launch-MissionControl }
        "ledger" { Watch-OpportunityLedger }
        "status" { Show-ProcessStatus }
        "activity" { Show-RecentActivity }
        "stats" { Show-QuickStats }
        default { Write-Host "Unknown view: $View" -ForegroundColor Red }
    }
} else {
    # Interactive menu
    while ($true) {
        Show-Menu
        $choice = Read-Host "Enter choice (1-7)"
        
        switch ($choice) {
            "1" { Launch-MissionControl }
            "2" { Watch-OpportunityLedger }
            "3" { Show-ProcessStatus }
            "4" { Show-RecentActivity }
            "5" { Show-QuickStats }
            "6" { Show-ServiceControl }
            "7" { 
                Write-Host ""
                Write-Host "Goodbye!" -ForegroundColor Cyan
                exit 
            }
            default { 
                Write-Host ""
                Write-Host "Invalid choice. Please enter 1-7." -ForegroundColor Red
                Start-Sleep -Seconds 2
            }
        }
    }
}
