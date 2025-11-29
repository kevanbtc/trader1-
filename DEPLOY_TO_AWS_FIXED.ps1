# APEX AWS AUTO-DEPLOY
# One-click deployment to AWS

param(
    [string]$Mode = "safe",  # safe = $1 max position, live = full capital, paper = simulation
    [string]$PemPath = "C:\Users\Kevan\.unykorn-keys\donkx-prod.pem",
    [string]$AwsHost = "54.158.163.67"
)

$ErrorActionPreference = "Stop"

Write-Host "`n>>> APEX AWS AUTO-DEPLOYMENT <<<" -ForegroundColor Green
Write-Host "============================`n" -ForegroundColor Cyan

# Validate PEM file
if (-not (Test-Path $PemPath)) {
    Write-Host "[ERROR] PEM file not found: $PemPath" -ForegroundColor Red
    Write-Host "   Update the -PemPath parameter or place donkx-prod.pem in correct location`n" -ForegroundColor Yellow
    exit 1
}

Write-Host "[OK] Found PEM file: $PemPath" -ForegroundColor Green
Write-Host "[OK] Target AWS: ubuntu@$AwsHost" -ForegroundColor Green
Write-Host "[OK] Mode: $Mode" -ForegroundColor Green

# Set trading parameters based on mode
switch ($Mode) {
    "safe" {
        $MaxPosition = "1.00"
        $MinProfit = "0.05"
        $TradingMode = "LIVE"
        Write-Host "[SAFETY] Max position: $1.00, Min profit: 5 cents" -ForegroundColor Yellow
    }
    "live" {
        $MaxPosition = "15.00"
        $MinProfit = "0.02"
        $TradingMode = "LIVE"
        Write-Host "[LIVE] Max position: $15.00, Min profit: 2 cents" -ForegroundColor Red
        Write-Host "[WARNING] REAL MONEY TRADING ENABLED" -ForegroundColor Red
    }
    "paper" {
        $MaxPosition = "1000.00"
        $MinProfit = "0.01"
        $TradingMode = "PAPER"
        Write-Host "[PAPER] Simulation mode - no real trades" -ForegroundColor Cyan
    }
}

# Your wallet credentials
$PrivateKey = "0x0bfa55c1460df66d9b50ce72fb53ff06a2a67a3e4289c7b8fc08580e2321fb3b"
$WalletAddress = "0x5fc05DA8cB29f08754ac120Ab6F4F6176774b53E"

Write-Host "`n[1/5] Creating deployment package..." -ForegroundColor Cyan

# Create temp directory for deployment
$TempDir = Join-Path $env:TEMP "apex-deploy-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
New-Item -ItemType Directory -Path $TempDir -Force | Out-Null

# Copy deployment files
Copy-Item -Path "aws-deploy\*" -Destination $TempDir -Recurse -Force
Copy-Item -Path "agents\*" -Destination "$TempDir\agents\" -Recurse -Force
Copy-Item -Path "config\*" -Destination "$TempDir\config\" -Recurse -Force
Copy-Item -Path "requirements.txt" -Destination $TempDir -Force

# Update .env.aws with actual credentials and mode
$EnvContent = @"
# === APEX PRODUCTION CONFIG ===
# Deployed: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
# Mode: $Mode

TRADING_MODE=$TradingMode
MAX_POSITION_USD=$MaxPosition
MIN_PROFIT_USD=$MinProfit

PRIVATE_KEY=$PrivateKey
WALLET_ADDRESS=$WalletAddress

# RPC Endpoints (using local mirror on 127.0.0.1:8547)
ARBITRUM_RPC_URL=http://127.0.0.1:8547
ARBITRUM_RPC_FALLBACK=http://127.0.0.1:8547
BASE_RPC_URL=http://127.0.0.1:8547
OPTIMISM_RPC_URL=http://127.0.0.1:8547
POLYGON_RPC_URL=http://127.0.0.1:8547
MAINNET_RPC_URL=http://127.0.0.1:8547

# DEXes (all enabled)
ENABLE_UNISWAP_V3=true
ENABLE_UNISWAP_V2=true
ENABLE_SUSHISWAP=true
ENABLE_CAMELOT=true
ENABLE_PANCAKESWAP=true
ENABLE_CURVE=true
ENABLE_BALANCER=true
ENABLE_TRADER_JOE=true
ENABLE_ZYBERSWAP=true

# Intelligence modules
ENABLE_FLASH_CRASH_DETECTION=true
ENABLE_WHALE_SHADOW_TRADING=true
ENABLE_SMART_MONEY_TRACKING=true
ENABLE_VOLUME_SPIKE_SCANNER=true

# Performance tuning
SCAN_INTERVAL_MS=250
MAX_SLIPPAGE_PERCENT=1.0
GAS_PRICE_MULTIPLIER=1.2
FLASHBOTS_ENABLED=true

# Logging
LOG_LEVEL=INFO
"@

Set-Content -Path "$TempDir\.env.aws" -Value $EnvContent -Force

Write-Host "[OK] Package created in: $TempDir" -ForegroundColor Green

Write-Host "`n[2/5] Uploading to AWS..." -ForegroundColor Cyan

# Create tarball for faster upload
$TarFile = "$TempDir.tar.gz"
Push-Location $TempDir
tar -czf $TarFile .
Pop-Location

Write-Host "[INFO] Uploading tarball (~5MB, 30-60 seconds)..." -ForegroundColor Yellow
scp -i $PemPath -o StrictHostKeyChecking=no $TarFile ubuntu@${AwsHost}:~/apex-deploy.tar.gz

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Upload failed!" -ForegroundColor Red
    exit 1
}

Write-Host "[OK] Upload complete" -ForegroundColor Green

Write-Host "`n[3/5] Extracting on AWS..." -ForegroundColor Cyan
ssh -i $PemPath -o StrictHostKeyChecking=no ubuntu@$AwsHost "mkdir -p ~/apex && cd ~/apex && tar -xzf ~/apex-deploy.tar.gz && rm ~/apex-deploy.tar.gz"

Write-Host "`n[4/5] Running deployment script..." -ForegroundColor Cyan
Write-Host "[INFO] This will install Python, dependencies, and start services (~3 minutes)..." -ForegroundColor Yellow

# Run deploy.sh on remote server
ssh -i $PemPath -o StrictHostKeyChecking=no ubuntu@$AwsHost "cd ~/apex && chmod +x deploy.sh && sudo ./deploy.sh"

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Deployment failed!" -ForegroundColor Red
    Write-Host "[INFO] Check logs with: ssh -i $PemPath ubuntu@$AwsHost 'cat ~/apex/logs/deployment.log'" -ForegroundColor Yellow
    exit 1
}

Write-Host "`n[5/5] Verifying deployment..." -ForegroundColor Cyan
$Status = ssh -i $PemPath -o StrictHostKeyChecking=no ubuntu@$AwsHost "sudo supervisorctl status"

Write-Host "`n$Status" -ForegroundColor White

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "    DEPLOYMENT COMPLETE!" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Green

Write-Host "Trading Configuration:" -ForegroundColor Yellow
Write-Host "  Mode: $TradingMode" -ForegroundColor White
Write-Host "  Max Position: $MaxPosition USD" -ForegroundColor White
Write-Host "  Min Profit: $MinProfit USD" -ForegroundColor White
Write-Host "  Wallet: $WalletAddress" -ForegroundColor White

Write-Host "`nRPC Endpoints:" -ForegroundColor Yellow
Write-Host "  HTTP: http://${AwsHost}:8547" -ForegroundColor White
Write-Host "  WebSocket: ws://${AwsHost}:8548" -ForegroundColor White

Write-Host "`nMonitoring Commands:" -ForegroundColor Yellow
Write-Host "  # Check service status" -ForegroundColor Gray
Write-Host "  ssh -i $PemPath ubuntu@$AwsHost 'sudo supervisorctl status'" -ForegroundColor White
Write-Host "`n  # View trading logs (live)" -ForegroundColor Gray
Write-Host "  ssh -i $PemPath ubuntu@$AwsHost 'tail -f ~/apex/logs/trading.log'" -ForegroundColor White
Write-Host "`n  # View mempool feed" -ForegroundColor Gray
Write-Host "  ssh -i $PemPath ubuntu@$AwsHost 'tail -f ~/apex/logs/mempool_feed.log'" -ForegroundColor White
Write-Host "`n  # Restart services" -ForegroundColor Gray
Write-Host "  ssh -i $PemPath ubuntu@$AwsHost 'sudo supervisorctl restart apex-full-stack:*'" -ForegroundColor White

Write-Host "`nYour 24/7 trading engine is now LIVE!" -ForegroundColor Green
Write-Host "All services auto-restart on failure.`n" -ForegroundColor Cyan

# Cleanup
Remove-Item -Path $TempDir -Recurse -Force
Remove-Item -Path $TarFile -Force

Write-Host "[OK] Cleanup complete`n" -ForegroundColor Green
