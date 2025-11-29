# WINDOWS PARALLEL EXECUTION FIX
# PowerShell doesn't support & for background jobs like Linux bash
# Use Start-Process or Start-Job instead

Write-Host "`n🔧 LAUNCHING 3 AGENTS IN PARALLEL (CORRECT WINDOWS METHOD)" -ForegroundColor Cyan
Write-Host "=" -repeat 60 -ForegroundColor Cyan
Write-Host ""

# Method 1: Start-Process (opens separate terminal windows)
Write-Host "Starting Agent 2 (Spread Compression)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; .\.venv\Scripts\python.exe .\agents\agent2_spread_compression.py 1800"
Start-Sleep -Milliseconds 500

Write-Host "Starting Agent 3 (Iceberg Sniper)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; .\.venv\Scripts\python.exe .\agents\agent3_iceberg_sniper.py 1800"
Start-Sleep -Milliseconds 500

Write-Host "Starting Agent 5 (Maker Rebate)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; .\.venv\Scripts\python.exe .\agents\agent5_maker_rebate.py 1800"
Start-Sleep -Milliseconds 500

Write-Host ""
Write-Host "✅ All 3 agents launched in separate terminal windows" -ForegroundColor Green
Write-Host "   Each will run for 30 minutes (1800 seconds)" -ForegroundColor White
Write-Host "   Close the terminal windows to stop individual agents" -ForegroundColor White
Write-Host ""
Write-Host "💡 TIP: Use Get-Process python to see all running agents" -ForegroundColor Cyan
Write-Host ""
