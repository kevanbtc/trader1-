# ALTERNATE METHOD: PowerShell Background Jobs
# Jobs run in background WITHOUT opening new windows
# Use Get-Job to monitor, Receive-Job to get output

Write-Host "`n🔧 LAUNCHING 3 AGENTS AS BACKGROUND JOBS" -ForegroundColor Cyan
Write-Host "=" -repeat 60 -ForegroundColor Cyan
Write-Host ""

# Kill any existing agents
Get-Process python -ErrorAction SilentlyContinue | ForEach-Object {
    $cmdLine = (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)" -ErrorAction SilentlyContinue).CommandLine
    if ($cmdLine -like "*agent*") {
        Stop-Process -Id $_.Id -Force
    }
}

Write-Host "Starting Agent 2 (Spread Compression) as background job..." -ForegroundColor Yellow
$job2 = Start-Job -Name "Agent2" -ScriptBlock {
    Set-Location $using:PWD
    & .\.venv\Scripts\python.exe .\agents\agent2_spread_compression.py 1800
}

Write-Host "Starting Agent 3 (Iceberg Sniper) as background job..." -ForegroundColor Yellow
$job3 = Start-Job -Name "Agent3" -ScriptBlock {
    Set-Location $using:PWD
    & .\.venv\Scripts\python.exe .\agents\agent3_iceberg_sniper.py 1800
}

Write-Host "Starting Agent 5 (Maker Rebate) as background job..." -ForegroundColor Yellow
$job5 = Start-Job -Name "Agent5" -ScriptBlock {
    Set-Location $using:PWD
    & .\.venv\Scripts\python.exe .\agents\agent5_maker_rebate.py 1800
}

Start-Sleep -Seconds 2

Write-Host ""
Write-Host "✅ All 3 agents running as background jobs" -ForegroundColor Green
Write-Host ""

# Show job status
Get-Job | Format-Table -Property Id, Name, State, HasMoreData

Write-Host ""
Write-Host "📊 MONITORING COMMANDS:" -ForegroundColor Cyan
Write-Host "   Get-Job                    # Show all job status" -ForegroundColor White
Write-Host "   Receive-Job -Name Agent2   # Get Agent 2 output" -ForegroundColor White
Write-Host "   Stop-Job -Name Agent3      # Stop Agent 3" -ForegroundColor White
Write-Host "   Get-Job | Stop-Job         # Stop all agents" -ForegroundColor White
Write-Host ""

# Keep checking status every 30 seconds
Write-Host "Monitoring agents (Ctrl+C to stop monitoring)..." -ForegroundColor Yellow
Write-Host ""

try {
    while ($true) {
        Start-Sleep -Seconds 30
        $timestamp = Get-Date -Format "HH:mm:ss"
        Write-Host "[$timestamp] Agent status:" -ForegroundColor Cyan
        Get-Job | Format-Table -Property Id, Name, State, HasMoreData -AutoSize
    }
}
catch {
    Write-Host "`n⚠️ Monitoring stopped. Agents still running in background." -ForegroundColor Yellow
    Write-Host "   Use 'Get-Job | Stop-Job' to stop all agents" -ForegroundColor White
}
