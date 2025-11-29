# AWS Trading Engine Monitor - Simple Version
# No emoji, pure ASCII

param([string]$View = "")

$PEM = "C:\Users\Kevan\donk x\donkx-prod.pem"
$IP = "54.158.163.67"

function Show-Menu {
    Clear-Host
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "   AWS TRADING ENGINE - MONITORING" -ForegroundColor White
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "[1] Mission Control Dashboard" -ForegroundColor White
    Write-Host "[2] Live Opportunity Feed" -ForegroundColor White
    Write-Host "[3] Process Status" -ForegroundColor White
    Write-Host "[4] Quick Stats" -ForegroundColor White
    Write-Host "[5] Restart Services" -ForegroundColor White
    Write-Host "[6] Exit" -ForegroundColor Red
    Write-Host ""
}

function Get-QuickStats {
    Write-Host ""
    Write-Host "Fetching stats from AWS..." -ForegroundColor Cyan
    
    $output = ssh -i "$PEM" ubuntu@$IP @'
echo "STATUS:`sudo supervisorctl status | grep 'apex-trading-dragon' | awk '{print $2}' 2>/dev/null || echo 'UNKNOWN'"
echo "SCANS:`grep -c SCAN ~/apex/logs/opportunity_ledger.log 2>/dev/null || echo '0'"
echo "OPPS:`grep -i 'profit.*USD' ~/apex/logs/opportunity_ledger.log 2>/dev/null | wc -l`"
echo "UPTIME:`ps -p $(pgrep -f 'start_trading' | head -1) -o etime= 2>/dev/null | tr -d ' ' || echo 'Not running'"
echo "CPU:`ps aux | grep 'start_trading' | grep -v grep | awk '{print $3}' 2>/dev/null || echo '0'"
echo "RAM:`ps aux | grep 'start_trading' | grep -v grep | awk '{print $4}' 2>/dev/null || echo '0'"
'@
    
    $data = @{}
    foreach ($line in $output -split "`n") {
        if ($line -match "^(\w+):(.+)$") {
            $data[$matches[1]] = $matches[2].Trim()
        }
    }
    
    Write-Host ""
    Write-Host "============================================" -ForegroundColor Cyan
    Write-Host "      AWS TRADING ENGINE - QUICK STATS" -ForegroundColor White
    Write-Host "============================================" -ForegroundColor Cyan
    Write-Host ""
    
    $status = $data['STATUS']
    if ($status -eq 'RUNNING') {
        Write-Host "  Status:        " -NoNewline
        Write-Host "RUNNING" -ForegroundColor Green
    } else {
        Write-Host "  Status:        " -NoNewline
        Write-Host $status -ForegroundColor Red
    }
    
    Write-Host "  Uptime:        $($data['UPTIME'])" -ForegroundColor White
    Write-Host "  CPU:           $($data['CPU'])%" -ForegroundColor Yellow
    Write-Host "  RAM:           $($data['RAM'])%" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  Total Scans:   $($data['SCANS'])" -ForegroundColor Cyan
    Write-Host "  Opportunities: $($data['OPPS'])" -ForegroundColor Green
    Write-Host ""
    Write-Host "============================================" -ForegroundColor Cyan
    Write-Host ""
}

function Watch-Ledger {
    Write-Host ""
    Write-Host "Connecting to opportunity ledger..." -ForegroundColor Cyan
    Write-Host "Press Ctrl+C to exit" -ForegroundColor Yellow
    Write-Host ""
    ssh -i "$PEM" ubuntu@$IP "tail -f ~/apex/logs/opportunity_ledger.log"
}

function Show-ProcessStatus {
    Write-Host ""
    Write-Host "Checking process status..." -ForegroundColor Cyan
    Write-Host ""
    
    ssh -i "$PEM" ubuntu@$IP @'
echo "=== TRADING ENGINE PROCESS ==="
ps aux | grep 'start_trading' | grep -v grep | awk '{print "  PID: " $2 " | CPU: " $3"% | RAM: " $4"%"}'
echo ""
echo "=== UPTIME ==="
ps -p $(pgrep -f 'start_trading' | head -1) -o etime= 2>/dev/null || echo "  Not running"
echo ""
echo "=== SERVICES ==="
sudo supervisorctl status
echo ""
echo "=== SCAN STATS ==="
echo "  Total scans: $(grep -c SCAN ~/apex/logs/opportunity_ledger.log 2>/dev/null || echo 0)"
'@
    
    Write-Host ""
}

function Restart-Services {
    Write-Host ""
    Write-Host "=== SERVICE CONTROL ===" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "[1] Restart Trading Engine Only" -ForegroundColor White
    Write-Host "[2] Restart All Services" -ForegroundColor White
    Write-Host "[3] Back" -ForegroundColor Yellow
    Write-Host ""
    
    $choice = Read-Host "Enter choice"
    
    if ($choice -eq "1") {
        Write-Host ""
        Write-Host "Restarting trading engine..." -ForegroundColor Yellow
        ssh -i "$PEM" ubuntu@$IP "sudo supervisorctl restart apex-full-stack:apex-trading-dragon"
        Write-Host "Done!" -ForegroundColor Green
        Start-Sleep -Seconds 2
    }
    elseif ($choice -eq "2") {
        Write-Host ""
        Write-Host "Restarting all services..." -ForegroundColor Yellow
        ssh -i "$PEM" ubuntu@$IP "sudo supervisorctl restart apex-full-stack:"
        Write-Host "Done!" -ForegroundColor Green
        Start-Sleep -Seconds 2
    }
}

function Launch-Dashboard {
    Write-Host ""
    Write-Host "Launching Mission Control..." -ForegroundColor Cyan
    python aws_mission_control.py
}

# Main
if ($View -eq "stats") {
    Get-QuickStats
    pause
}
elseif ($View -eq "ledger") {
    Watch-Ledger
}
elseif ($View -eq "status") {
    Show-ProcessStatus
    pause
}
elseif ($View -eq "dashboard") {
    Launch-Dashboard
}
else {
    while ($true) {
        Show-Menu
        $choice = Read-Host "Enter choice (1-6)"
        
        switch ($choice) {
            "1" { Launch-Dashboard }
            "2" { Watch-Ledger }
            "3" { Show-ProcessStatus; pause }
            "4" { Get-QuickStats; pause }
            "5" { Restart-Services }
            "6" { Write-Host ""; Write-Host "Goodbye!" -ForegroundColor Cyan; exit }
            default { Write-Host "Invalid choice" -ForegroundColor Red; Start-Sleep -Seconds 1 }
        }
    }
}
