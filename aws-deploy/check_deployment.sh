#!/bin/bash

# 🔍 Quick deployment verification script

echo "🐉 APEX TRADING DRAGON - DEPLOYMENT CHECK"
echo "=========================================="
echo ""

# Check if files exist
echo "📁 Checking deployment files..."
FILES=(
    "rpc_mirror.py"
    "mempool_sniffer.py"
    "apex_trading_dragon.py"
    ".env"
    "supervisor-apex.conf"
)

for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file - MISSING"
    fi
done
echo ""

# Check Python environment
echo "🐍 Checking Python environment..."
if [ -d "venv" ]; then
    echo "  ✅ Virtual environment exists"
    source venv/bin/activate
    echo "  Python: $(python --version)"
    echo "  Pip: $(pip --version)"
else
    echo "  ❌ Virtual environment not found"
fi
echo ""

# Check configuration
echo "🔐 Checking configuration..."
if [ -f ".env" ]; then
    if grep -q "YOUR_PRIVATE_KEY_HERE" .env; then
        echo "  ⚠️  Private key not configured"
    else
        echo "  ✅ Private key configured"
    fi
    
    if grep -q "YOUR_WALLET_ADDRESS_HERE" .env; then
        echo "  ⚠️  Wallet address not configured"
    else
        echo "  ✅ Wallet address configured"
    fi
else
    echo "  ❌ .env file not found"
fi
echo ""

# Check supervisor
echo "🔄 Checking supervisor..."
if systemctl is-active --quiet supervisor; then
    echo "  ✅ Supervisor is running"
    sudo supervisorctl status apex-full-stack:* 2>/dev/null || echo "  ⚠️  Apex services not configured yet"
else
    echo "  ⚠️  Supervisor not running"
fi
echo ""

# Check logs directory
echo "📊 Checking logs directory..."
if [ -d "../logs" ]; then
    echo "  ✅ Logs directory exists"
    LOG_COUNT=$(ls -1 ../logs/*.log 2>/dev/null | wc -l)
    echo "  Log files: $LOG_COUNT"
else
    echo "  ⚠️  Logs directory not found"
fi
echo ""

# Check network ports
echo "🌐 Checking network ports..."
if netstat -tuln | grep -q ":8547"; then
    echo "  ✅ Port 8547 (HTTP RPC) is listening"
else
    echo "  ⚠️  Port 8547 not listening"
fi

if netstat -tuln | grep -q ":8548"; then
    echo "  ✅ Port 8548 (WebSocket) is listening"
else
    echo "  ⚠️  Port 8548 not listening"
fi
echo ""

echo "=========================================="
echo "✨ Deployment check complete"
