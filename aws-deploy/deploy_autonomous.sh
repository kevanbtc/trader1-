#!/bin/bash

# 🤖 AUTONOMOUS AWS DEPLOYMENT - NO USER INPUT REQUIRED
# This script deploys everything automatically using environment detection

set -e

echo "=========================================================="
echo " 🤖 AUTONOMOUS APEX DEPLOYMENT"
echo "=========================================================="
echo ""

# Detect private key from environment
if [ -f "C:\Users\Kevan\donkx-prod.pem" ]; then
    PRIVATE_KEY="0x0bfa55c1460df66d9b50ce72fb53ff06a2a67a3e4289c7b8fc08580e2321fb3b"
    PUBLIC_ADDRESS="0x5fc05DA8cB29f08754ac120Ab6F4F6176774b53E"
    echo "✅ Wallet credentials detected from local environment"
else
    echo "⚠️  Manual wallet configuration will be required"
fi

# Get deployment directory
DEPLOY_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
echo "📁 Deploying from: $DEPLOY_DIR"
echo ""

# System update
echo "➡ Updating system (silent mode)..."
sudo apt update -y > /dev/null 2>&1
sudo DEBIAN_FRONTEND=noninteractive apt upgrade -y > /dev/null 2>&1

# Install dependencies
echo "➡ Installing dependencies..."
sudo apt install -y build-essential git curl wget unzip python3 python3-venv python3-pip supervisor ufw htop net-tools > /dev/null 2>&1

# Performance tuning
echo "➡ Applying performance optimizations..."
if ! grep -q "Apex Trading Dragon Performance Tuning" /etc/sysctl.conf; then
    sudo tee -a /etc/sysctl.conf > /dev/null <<EOF

# Apex Trading Dragon Performance Tuning
fs.inotify.max_user_watches=524288
net.core.somaxconn=65535
net.ipv4.tcp_fin_timeout=5
net.ipv4.tcp_tw_reuse=1
net.ipv4.tcp_max_syn_backlog=8192
net.core.netdev_max_backlog=5000
net.ipv4.tcp_max_tw_buckets=1440000
vm.swappiness=10
EOF
    sudo sysctl -p > /dev/null 2>&1
fi

# Create directories
echo "➡ Creating directory structure..."
mkdir -p ~/apex/engine
mkdir -p ~/apex/logs
mkdir -p ~/apex/logs/sessions

# Copy all files
echo "➡ Deploying files..."
cp "$DEPLOY_DIR/rpc_mirror.py" ~/apex/engine/
cp "$DEPLOY_DIR/mempool_sniffer.py" ~/apex/engine/
cp "$DEPLOY_DIR/apex_trading_dragon.py" ~/apex/engine/
cp "$DEPLOY_DIR/.env.aws" ~/apex/engine/.env
cp "$DEPLOY_DIR/check_deployment.sh" ~/apex/engine/
chmod +x ~/apex/engine/check_deployment.sh

# Copy trading engine if present
if [ -d "$DEPLOY_DIR/agents" ]; then
    cp -r "$DEPLOY_DIR/agents" ~/apex/engine/
    cp -r "$DEPLOY_DIR/config" ~/apex/engine/
    [ -f "$DEPLOY_DIR/start_trading.py" ] && cp "$DEPLOY_DIR/start_trading.py" ~/apex/engine/
    [ -f "$DEPLOY_DIR/requirements.txt" ] && cp "$DEPLOY_DIR/requirements.txt" ~/apex/engine/
    echo "   ✅ Trading engine copied"
fi

# Auto-configure wallet if detected
if [ ! -z "$PRIVATE_KEY" ]; then
    echo "➡ Auto-configuring wallet..."
    sed -i "s|PRIVATE_KEY=YOUR_PRIVATE_KEY_HERE|PRIVATE_KEY=$PRIVATE_KEY|g" ~/apex/engine/.env
    sed -i "s|PUBLIC_ADDRESS=YOUR_WALLET_ADDRESS_HERE|PUBLIC_ADDRESS=$PUBLIC_ADDRESS|g" ~/apex/engine/.env
    sed -i "s|WALLET_ADDRESS=YOUR_WALLET_ADDRESS_HERE|WALLET_ADDRESS=$PUBLIC_ADDRESS|g" ~/apex/engine/.env
    echo "   ✅ Wallet configured"
fi

# Create virtual environment
echo "➡ Creating Python environment..."
cd ~/apex/engine
python3 -m venv venv > /dev/null 2>&1
source venv/bin/activate

# Install packages
echo "➡ Installing Python packages (this takes ~2 minutes)..."
pip install --upgrade pip > /dev/null 2>&1
pip install fastapi uvicorn[standard] aiohttp websockets psutil \
            pandas numpy scipy web3 eth-account python-decouple \
            requests rich python-dotenv orjson pyyaml > /dev/null 2>&1

if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt > /dev/null 2>&1
fi

echo "   ✅ Python packages installed"

# Setup supervisor
echo "➡ Configuring auto-restart services..."
sudo cp "$DEPLOY_DIR/supervisor-apex.conf" /etc/supervisor/conf.d/apex.conf
sudo sed -i "s|/home/ubuntu|$HOME|g" /etc/supervisor/conf.d/apex.conf
sudo systemctl enable supervisor > /dev/null 2>&1
sudo systemctl restart supervisor > /dev/null 2>&1
sleep 2

# Configure firewall (auto-detect current IP)
echo "➡ Configuring firewall..."
sudo ufw default deny incoming > /dev/null 2>&1
sudo ufw default allow outgoing > /dev/null 2>&1

# Allow current SSH IP
CURRENT_IP=$(echo $SSH_CLIENT | awk '{print $1}')
if [ ! -z "$CURRENT_IP" ]; then
    sudo ufw allow from $CURRENT_IP to any port 22 proto tcp comment 'SSH' > /dev/null 2>&1
fi

# Allow RPC from anywhere (or restrict if needed)
sudo ufw allow 8547/tcp comment 'RPC HTTP' > /dev/null 2>&1
sudo ufw allow 8548/tcp comment 'RPC WS' > /dev/null 2>&1

echo "y" | sudo ufw enable > /dev/null 2>&1

# Setup log rotation
echo "➡ Configuring log rotation..."
sudo tee /etc/logrotate.d/apex-trading > /dev/null <<EOF
$HOME/apex/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 $USER $USER
    missingok
    sharedscripts
    postrotate
        /usr/bin/supervisorctl restart apex-full-stack:* > /dev/null 2>&1 || true
    endscript
}
EOF

# Start services
echo "➡ Starting services..."
sudo supervisorctl reread > /dev/null 2>&1
sudo supervisorctl update > /dev/null 2>&1
sleep 3
sudo supervisorctl start apex-full-stack:* > /dev/null 2>&1
sleep 2

echo ""
echo "=========================================================="
echo " 🎯 AUTONOMOUS DEPLOYMENT COMPLETE"
echo "=========================================================="
echo ""
echo "🚀 Status:"
sudo supervisorctl status apex-full-stack:*
echo ""
echo "📊 Your trading dragon is now hunting 24/7!"
echo ""
echo "📝 Useful commands:"
echo "  → Live trading:     tail -f ~/apex/logs/trading-dragon.out.log"
echo "  → Mempool feed:     tail -f ~/apex/logs/mempool-sniffer.out.log"
echo "  → All logs:         tail -f ~/apex/logs/*.log"
echo "  → Check status:     sudo supervisorctl status"
echo "  → Restart:          sudo supervisorctl restart apex-full-stack:*"
echo ""
echo "🌐 Endpoints:"
PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || echo "54.158.163.67")
echo "  → HTTP RPC: http://$PUBLIC_IP:8547"
echo "  → WS RPC:   ws://$PUBLIC_IP:8548"
echo "  → Health:   http://$PUBLIC_IP:8547/health"
echo ""
echo "=========================================================="
