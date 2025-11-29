#  APEX AWS DEPLOYMENT HELPER
# Run this in VS Code after connecting to AWS

Write-Host "
 APEX DEPLOYMENT STARTING..." -ForegroundColor Green
Write-Host "============================
" -ForegroundColor Cyan

# Check if we're on AWS
if ($env:USER -eq 'ubuntu' -or $env:LOGNAME -eq 'ubuntu') {
    Write-Host " Connected to AWS EC2" -ForegroundColor Green
    
    # Navigate to deployment directory
    if (Test-Path ~/aws-deploy) {
        cd ~/aws-deploy
        Write-Host " Found deployment directory
" -ForegroundColor Green
        
        # Make script executable
        chmod +x deploy.sh check_deployment.sh
        
        Write-Host " Starting deployment...
" -ForegroundColor Yellow
        Write-Host "This will:" -ForegroundColor White
        Write-Host "  1. Install all dependencies" -ForegroundColor Gray
        Write-Host "  2. Create Python environment" -ForegroundColor Gray
        Write-Host "  3. Setup supervisor services" -ForegroundColor Gray
        Write-Host "  4. Configure firewall" -ForegroundColor Gray
        Write-Host "  5. Start trading dragon
" -ForegroundColor Gray
        
        ./deploy.sh
    } else {
        Write-Host " aws-deploy directory not found!" -ForegroundColor Red
        Write-Host "   Upload aws-deploy/ folder first
" -ForegroundColor Yellow
    }
} else {
    Write-Host " Not connected to AWS!" -ForegroundColor Red
    Write-Host "   Follow these steps:
" -ForegroundColor Yellow
    Write-Host "   1. Ctrl+Shift+P" -ForegroundColor White
    Write-Host "   2. Remote-SSH: Connect to Host" -ForegroundColor White
    Write-Host "   3. Select: ubuntu@54.158.163.67
" -ForegroundColor White
}
