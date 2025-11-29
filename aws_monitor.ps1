# AWS Monitor - Simple and Reliable Version
param([string]$View = "")

$PEM = "C:\Users\Kevan\donk x\donkx-prod.pem"
$IP = "54.158.163.67"
$SSH = "ssh -i `"$PEM`" ubuntu@$IP"

function Get-Stats {
    Write-Host "`n=== Fetching from AWS ===" -ForegroundColor Cyan
    
    Write-Host "Status: " -NoNewline
    $status = Invoke-Expression "$SSH `"sudo supervisorctl status | grep apex-trading-dragon | awk '{print `$2}'`""
    if ($status -eq "RUNNING") {
        Write-Host $status -ForegroundColor Green
    } else {
        Write-Host $status -ForegroundColor Red
    }
    
    Write-Host "Scans: " -NoNewline
    $scans = Invoke-Expression "$SSH `"grep -c SCAN ~/apex/logs/opportunity_ledger.log 2>/dev/null || echo 0`""
    Write-Host $scans -ForegroundColor Cyan
    
    Write-Host "Uptime: " -NoNewline
    $uptime = Invoke-Expression "$SSH `"ps -p ```$(pgrep -f start_trading | head -1) -o etime= 2>/dev/null || echo 'Not running'`""
    Write-Host $uptime.Trim() -ForegroundColor Yellow
    
    Write-Host ""
}

function Watch-Feed {
    Write-Host "`n=== Connecting to live feed ===" -ForegroundColor Cyan
    Write-Host "Press Ctrl+C to exit`n" -ForegroundColor Yellow
    Invoke-Expression "$SSH `"tail -f ~/apex/logs/opportunity_ledger.log`""
}

function Show-Status {
    Write-Host "`n=== Full Status ===" -ForegroundColor Cyan
    Invoke-Expression "$SSH `"sudo supervisorctl status`""
    Write-Host ""
    Invoke-Expression "$SSH `"ps aux | grep start_trading | grep -v grep`""
    Write-Host ""
}

function Show-Menu {
    Clear-Host
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "   AWS TRADING ENGINE MONITOR" -ForegroundColor White
    Write-Host "========================================`n" -ForegroundColor Cyan
    Write-Host "[1] Quick Stats" -ForegroundColor White
    Write-Host "[2] Live Opportunity Feed" -ForegroundColor White
    Write-Host "[3] Full Status" -ForegroundColor White
    Write-Host "[4] Restart Trading Engine" -ForegroundColor Yellow
    Write-Host "[5] Exit`n" -ForegroundColor Red
}

# Main
if ($View -eq "stats") {
    Get-Stats
    pause
}
elseif ($View -eq "ledger") {
    Watch-Feed
}
elseif ($View -eq "status") {
    Show-Status
    pause
}
else {
    while ($true) {
        Show-Menu
        $choice = Read-Host "Choice"
        
        switch ($choice) {
            "1" { Get-Stats; pause }
            "2" { Watch-Feed }
            "3" { Show-Status; pause }
            "4" {
                Write-Host "`nRestarting..." -ForegroundColor Yellow
                Invoke-Expression "$SSH `"sudo supervisorctl restart apex-full-stack:apex-trading-dragon`""
                Write-Host "Done!`n" -ForegroundColor Green
                Start-Sleep -Seconds 2
            }
            "5" { Write-Host ""; exit }
            default { Write-Host "Invalid" -ForegroundColor Red; Start-Sleep -Seconds 1 }
        }
    }
}
