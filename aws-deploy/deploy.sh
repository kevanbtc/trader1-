#!/bin/bash

# 🐉 APEX TRADING DRAGON - AWS DEPLOYMENT SCRIPT
# This script deploys your trading engine to AWS EC2 with full 24/7 capabilities

set -e

echo "=========================================================="
echo " 🐉 APEX TRADING DRAGON - AWS DEPLOYMENT"
echo "=========================================================="
echo ""

# Get current directory (where script is uploaded)
DEPLOY_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
echo "📁 Deployment files located at: $DEPLOY_DIR"
echo ""

# Update system
echo "➡ Updating system packages..."
sudo apt update -y && sudo apt upgrade -y

# Install dependencies
echo "➡ Installing system dependencies..."
sudo apt install -y build-essential git curl wget unzip python3 python3-venv python3-pip supervisor ufw htop net-tools

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
    sudo sysctl -p
else
    echo "   ✅ Performance tuning already applied"
fi

# Create directory structure
echo "➡ Creating Apex directory structure..."
mkdir -p ~/apex/engine
mkdir -p ~/apex/logs
mkdir -p ~/apex/logs/sessions

# Copy deployment files to apex directory
echo "➡ Copying deployment files..."
cp "$DEPLOY_DIR/rpc_mirror.py" ~/apex/engine/
cp "$DEPLOY_DIR/mempool_sniffer.py" ~/apex/engine/
cp "$DEPLOY_DIR/apex_trading_dragon.py" ~/apex/engine/
cp "$DEPLOY_DIR/.env.aws" ~/apex/engine/.env
cp "$DEPLOY_DIR/check_deployment.sh" ~/apex/engine/
chmod +x ~/apex/engine/check_deployment.sh

echo "   ✅ Core Apex files copied"

# Copy trading engine files if they exist in deploy directory
if [ -d "$DEPLOY_DIR/agents" ]; then
    echo "➡ Copying trading engine files..."
    cp -r "$DEPLOY_DIR/agents" ~/apex/engine/
    cp -r "$DEPLOY_DIR/config" ~/apex/engine/
    cp "$DEPLOY_DIR/start_trading.py" ~/apex/engine/ 2>/dev/null || true
    cp "$DEPLOY_DIR/requirements.txt" ~/apex/engine/ 2>/dev/null || true
    echo "   ✅ Trading engine files copied"
else
    echo "⚠️  Trading engine files not found in deployment directory"
    echo "   You'll need to upload them separately to ~/apex/engine/"
fi

# Create Python virtual environment
echo "➡ Creating Python virtual environment..."
cd ~/apex/engine
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "➡ Installing Python packages..."
pip install --upgrade pip
pip install fastapi uvicorn[standard] aiohttp websockets psutil \
            pandas numpy scipy web3 eth-account python-decouple \
            requests rich python-dotenv orjson pyyaml

# Install additional requirements if file exists
if [ -f "requirements.txt" ]; then
    echo "   Installing from requirements.txt..."
    pip install -r requirements.txt
fi

echo "   ✅ Python packages installed"

# Configure environment
echo ""
echo "=========================================================="
echo " 🔐 WALLET CONFIGURATION REQUIRED"
echo "=========================================================="
echo ""
echo "Opening .env file for configuration..."
echo "Please update these values:"
echo "  1. PRIVATE_KEY=YOUR_PRIVATE_KEY_HERE"
echo "  2. PUBLIC_ADDRESS=YOUR_WALLET_ADDRESS_HERE"
echo ""
echo "Press any key to open nano editor..."
read -n 1 -s
nano ~/apex/engine/.env

# Setup supervisor
echo ""
echo "➡ Installing supervisor configuration..."
sudo cp "$DEPLOY_DIR/supervisor-apex.conf" /etc/supervisor/conf.d/apex.conf

# Update paths in supervisor config to use correct home directory
sudo sed -i "s|/home/ubuntu|$HOME|g" /etc/supervisor/conf.d/apex.conf

# Enable supervisor
echo "➡ Enabling supervisor..."
sudo systemctl enable supervisor
sudo systemctl restart supervisor

# Wait for supervisor to start
sleep 2

# Configure firewall
echo "➡ Configuring firewall..."
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH from your current IP
CURRENT_IP=$(echo $SSH_CLIENT | awk '{print $1}')
if [ ! -z "$CURRENT_IP" ]; then
    echo "   Detected SSH from: $CURRENT_IP"
    sudo ufw allow from $CURRENT_IP to any port 22 proto tcp comment 'SSH from deployment IP'
fi

# Allow RPC access from your IP
echo ""
read -p "Enter your home/office IP for RPC access (or press Enter to allow from anywhere): " HOME_IP
if [ ! -z "$HOME_IP" ]; then
    sudo ufw allow from $HOME_IP to any port 8547 proto tcp comment 'RPC HTTP'
    sudo ufw allow from $HOME_IP to any port 8548 proto tcp comment 'RPC WS'
else
    sudo ufw allow 8547/tcp comment 'RPC HTTP - public'
    sudo ufw allow 8548/tcp comment 'RPC WS - public'
fi

# Enable firewall
echo "y" | sudo ufw enable || true

# Setup logrotate
echo "➡ Configuring log rotation..."
sudo tee /etc/logrotate.d/apex-trading > /dev/null <<EOF
$HOME/apex/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 ubuntu ubuntu
    missingok
    sharedscripts
    postrotate
        /usr/bin/supervisorctl restart apex-full-stack:* > /dev/null 2>&1 || true
    endscript
}
EOF

# Reload and start services
echo "➡ Starting Apex services..."
sudo supervisorctl reread
sudo supervisorctl update

# Give services a moment to initialize
sleep 3

# Start all services
sudo supervisorctl start apex-full-stack:*

# Wait for services to start
sleep 2

echo ""
echo "=========================================================="
echo " 🎯 DEPLOYMENT COMPLETE"
echo "=========================================================="
echo ""
echo "Your Apex Trading Dragon is now running 24/7!"
echo ""
echo "📊 Service status:"
sudo supervisorctl status apex-full-stack:*
echo ""
echo "📝 Useful commands:"
echo "  → View all logs:        tail -f ~/apex/logs/*.log"
echo "  → Dragon logs:          tail -f ~/apex/logs/trading-dragon.out.log"
echo "  → Mempool logs:         tail -f ~/apex/logs/mempool-sniffer.out.log"
echo "  → RPC mirror logs:      tail -f ~/apex/logs/rpc-mirror.out.log"
echo "  → Check status:         sudo supervisorctl status"
echo "  → Restart services:     sudo supervisorctl restart apex-full-stack:*"
echo "  → Stop services:        sudo supervisorctl stop apex-full-stack:*"
echo "  → Check deployment:     ~/apex/engine/check_deployment.sh"
echo ""
echo "🌐 RPC Endpoints:"
echo "  → HTTP: http://$(curl -s ifconfig.me):8547"
echo "  → WS:   ws://$(curl -s ifconfig.me):8548"
echo "  → Health: http://$(curl -s ifconfig.me):8547/health"
echo ""
echo "🔍 Next steps:"
echo "  1. Verify services: sudo supervisorctl status"
echo "  2. Watch logs: tail -f ~/apex/logs/trading-dragon.out.log"
echo "  3. Check RPC: curl http://localhost:8547/health"
echo ""
echo "🚀 Happy hunting!"
echo "=========================================================="
