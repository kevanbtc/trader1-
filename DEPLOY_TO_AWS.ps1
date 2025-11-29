# 🐉 APEX AWS AUTO-DEPLOY
# One-click deployment to AWS - Run this script and walk away

param(
    [string]$Mode = "safe",  # safe = $1 max position, live = full capital, paper = simulation
    [string]$PemPath = "C:\Users\Kevan\donkx-xrpl-sg\donkx-prod.pem",
    [string]$AwsHost = "54.158.163.67"
)

$ErrorActionPreference = "Stop"

Write-Host "`n🐉 APEX AWS AUTO-DEPLOYMENT" -ForegroundColor Green
Write-Host "============================`n" -ForegroundColor Cyan

# Validate PEM file
if (-not (Test-Path $PemPath)) {
    Write-Host "❌ PEM file not found: $PemPath" -ForegroundColor Red
    Write-Host "   Update the -PemPath parameter or place donkx-prod.pem in correct location`n" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ Found PEM file: $PemPath" -ForegroundColor Green
Write-Host "✅ Target AWS: ubuntu@$AwsHost" -ForegroundColor Green
Write-Host "✅ Mode: $Mode" -ForegroundColor Green

# Set trading parameters based on mode
switch ($Mode) {
    "safe" {
        $MaxPosition = "1.00"
        $MinProfit = "0.05"
        $TradingMode = "LIVE"
        Write-Host "✅ Safe mode: Max \$$MaxPosition per trade, \$$MinProfit min profit" -ForegroundColor Yellow
    }
    "live" {
        $MaxPosition = "15.00"
        $MinProfit = "0.02"
        $TradingMode = "LIVE"
        Write-Host "✅ Live mode: Max \$$MaxPosition per trade, \$$MinProfit min profit" -ForegroundColor Yellow
    }
    "paper" {
        $MaxPosition = "15.00"
        $MinProfit = "0.02"
        $TradingMode = "PAPER"
        Write-Host "✅ Paper mode: Simulation only, no real trades" -ForegroundColor Yellow
    }
}

Write-Host ""

# Step 1: Prepare deployment package
Write-Host "📦 STEP 1: Preparing deployment package..." -ForegroundColor Cyan

# Update .env.aws with mode settings
$envContent = Get-Content "aws-deploy\.env.aws" -Raw
$envContent = $envContent -replace "TRADING_MODE=.*", "TRADING_MODE=$TradingMode"
$envContent = $envContent -replace "MIN_PROFIT_USD=.*", "MIN_PROFIT_USD=$MinProfit"
$envContent = $envContent -replace "MAX_POSITION_USD=.*", "MAX_POSITION_USD=$MaxPosition"
$envContent = $envContent -replace "PRIVATE_KEY=.*", "PRIVATE_KEY=0x0bfa55c1460df66d9b50ce72fb53ff06a2a67a3e4289c7b8fc08580e2321fb3b"
$envContent = $envContent -replace "PUBLIC_ADDRESS=.*", "PUBLIC_ADDRESS=0x5fc05DA8cB29f08754ac120Ab6F4F6176774b53E"
$envContent = $envContent -replace "WALLET_ADDRESS=.*", "WALLET_ADDRESS=0x5fc05DA8cB29f08754ac120Ab6F4F6176774b53E"
$envContent | Set-Content "aws-deploy\.env.aws" -NoNewline

Write-Host "   ✅ Configured .env for $Mode mode" -ForegroundColor Green
Write-Host "   ✅ Wallet: 0x5fc05DA8cB29f08754ac120Ab6F4F6176774b53E" -ForegroundColor Green
Write-Host "   ✅ Max position: \$$MaxPosition" -ForegroundColor Green
Write-Host ""

# Step 2: Upload to AWS
Write-Host "📤 STEP 2: Uploading to AWS..." -ForegroundColor Cyan
Write-Host "   This may take 30-60 seconds depending on your connection" -ForegroundColor Gray
Write-Host ""

# Create tar for faster upload
if (Get-Command tar -ErrorAction SilentlyContinue) {
    Write-Host "   Creating deployment archive..." -ForegroundColor Gray
    tar -czf apex-deploy.tar.gz -C . aws-deploy agents config start_trading.py requirements.txt
    
    Write-Host "   Uploading archive to AWS..." -ForegroundColor Gray
    scp -i $PemPath -o StrictHostKeyChecking=no apex-deploy.tar.gz ubuntu@${AwsHost}:~/
    
    Remove-Item apex-deploy.tar.gz -Force
    Write-Host "   ✅ Archive uploaded" -ForegroundColor Green
} else {
    Write-Host "   Uploading files directly..." -ForegroundColor Gray
    scp -i $PemPath -o StrictHostKeyChecking=no -r aws-deploy agents config start_trading.py requirements.txt ubuntu@${AwsHost}:~/
    Write-Host "   ✅ Files uploaded" -ForegroundColor Green
}

Write-Host ""

# Step 3: Deploy on AWS
Write-Host "🚀 STEP 3: Deploying on AWS..." -ForegroundColor Cyan
Write-Host "   This will take 2-3 minutes" -ForegroundColor Gray
Write-Host ""

$deployScript = @"
#!/bin/bash
set -e

echo '🐉 Starting autonomous deployment...'

# Extract if archive exists
if [ -f apex-deploy.tar.gz ]; then
    echo '📦 Extracting archive...'
    tar -xzf apex-deploy.tar.gz
    rm apex-deploy.tar.gz
fi

# Run deployment
cd ~/aws-deploy
chmod +x deploy.sh check_deployment.sh

echo '⚙️ Installing dependencies and configuring services...'
./deploy.sh <<EOF


y
EOF

echo ''
echo '✅ Deployment complete!'
echo ''
echo '📊 Service status:'
sudo supervisorctl status

echo ''
echo '🌐 Your endpoints:'
echo '  HTTP RPC: http://$(curl -s ifconfig.me):8547'
echo '  WS RPC:   ws://$(curl -s ifconfig.me):8548'
echo ''
echo '📝 View logs:'
echo '  tail -f ~/apex/logs/trading-dragon.out.log'
"@

# Write deploy script to temp file
$deployScript | Out-File -FilePath "deploy_remote.sh" -Encoding ASCII -NoNewline

# Upload and execute
scp -i $PemPath -o StrictHostKeyChecking=no deploy_remote.sh ubuntu@${AwsHost}:~/
ssh -i $PemPath -o StrictHostKeyChecking=no ubuntu@$AwsHost "chmod +x deploy_remote.sh && ./deploy_remote.sh"

Remove-Item deploy_remote.sh -Force

Write-Host ""
Write-Host "=============================" -ForegroundColor Cyan
Write-Host "🎯 DEPLOYMENT COMPLETE!" -ForegroundColor Green
Write-Host "=============================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Your Apex Trading Dragon is now running 24/7 on AWS!" -ForegroundColor White
Write-Host ""
Write-Host "🌐 Endpoints:" -ForegroundColor Yellow
Write-Host "   HTTP RPC: http://${AwsHost}:8547" -ForegroundColor White
Write-Host "   WS RPC:   ws://${AwsHost}:8548" -ForegroundColor White
Write-Host "   Health:   http://${AwsHost}:8547/health" -ForegroundColor White
Write-Host ""
Write-Host "📊 Monitor Services:" -ForegroundColor Yellow
Write-Host "   ssh -i `"$PemPath`" ubuntu@$AwsHost" -ForegroundColor Gray
Write-Host "   sudo supervisorctl status" -ForegroundColor Gray
Write-Host ""
Write-Host "📝 View Live Logs:" -ForegroundColor Yellow
Write-Host "   ssh -i `"$PemPath`" ubuntu@$AwsHost 'tail -f ~/apex/logs/trading-dragon.out.log'" -ForegroundColor Gray
Write-Host ""
Write-Host "🔧 Quick Commands:" -ForegroundColor Yellow
Write-Host "   Restart: ssh -i `"$PemPath`" ubuntu@$AwsHost 'sudo supervisorctl restart apex-full-stack:*'" -ForegroundColor Gray
Write-Host "   Stop:    ssh -i `"$PemPath`" ubuntu@$AwsHost 'sudo supervisorctl stop apex-full-stack:*'" -ForegroundColor Gray
Write-Host ""
Write-Host "💰 Trading Configuration:" -ForegroundColor Yellow
Write-Host "   Mode: $TradingMode" -ForegroundColor White
Write-Host "   Max Position: \$$MaxPosition" -ForegroundColor White
Write-Host "   Min Profit: \$$MinProfit" -ForegroundColor White
Write-Host "   Wallet: 0x5fc05DA8cB29f08754ac120Ab6F4F6176774b53E" -ForegroundColor White
Write-Host ""
Write-Host "✨ Your dragon is hunting!" -ForegroundColor Green
Write-Host "============================`n" -ForegroundColor Cyan
