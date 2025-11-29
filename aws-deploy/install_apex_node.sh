#!/bin/bash

set -e

echo "=========================================================="
echo " 🚀 APEX ULTRA RPC INSTALLER - PRIVATE ARBITRUM NODE"
echo "=========================================================="

sudo apt update -y
sudo apt upgrade -y

echo "➡ Installing dependencies..."
sudo apt install -y build-essential git curl wget unzip jq ufw fail2ban python3-pip

echo "➡ Installing Node.js LTS..."
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs

echo "➡ Installing Python 3.12 + venv..."
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update -y
sudo apt install -y python3.12 python3.12-venv python3.12-dev python3-pip

echo "➡ Installing Go (for turbo RPC)..."
wget https://go.dev/dl/go1.23.2.linux-amd64.tar.gz
sudo tar -C /usr/local -xzf go1.23.2.linux-amd64.tar.gz
rm go1.23.2.linux-amd64.tar.gz
echo "export PATH=\$PATH:/usr/local/go/bin" >> ~/.bashrc
export PATH=$PATH:/usr/local/go/bin

echo "➡ Installing Turbo-Geth Arbitrum Light Node..."
cd /home/ubuntu
git clone https://github.com/OffchainLabs/nitro.git
cd nitro
make nitro

echo "➡ Creating node directories..."
sudo mkdir -p /var/lib/arbitrum
sudo chown ubuntu:ubuntu /var/lib/arbitrum
sudo chmod 755 /var/lib/arbitrum

echo "➡ Creating systemd service..."
sudo tee /etc/systemd/system/arbi-rpc.service > /dev/null <<EOF
[Unit]
Description=Arbitrum Ultra RPC Node
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/nitro
ExecStart=/home/ubuntu/nitro/target/bin/nitro --l1.url="wss://arb1.arbitrum.io/ws" --l2.chain-id=42161 --node.data-availability.enable --http.addr=0.0.0.0 --http.port=8547 --ws.addr=0.0.0.0 --ws.port=8548 --http.api="eth,net,web3,txpool" --ws.api="eth,net,web3,txpool" --http.corsdomain="*" --http.vhosts="*" --ws.origins="*"
Restart=always
RestartSec=5
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
EOF

echo "➡ Starting RPC service..."
sudo systemctl daemon-reload
sudo systemctl enable arbi-rpc
sudo systemctl start arbi-rpc

echo "➡ Configuring firewall..."
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow from 76.240.18.238 to any port 22 proto tcp comment 'SSH from your IP'
sudo ufw allow from 76.240.18.238 to any port 8547 proto tcp comment 'RPC from your IP'
sudo ufw allow from 76.240.18.238 to any port 8548 proto tcp comment 'WS from your IP'
sudo ufw --force enable

echo "➡ Installing Fail2Ban..."
sudo tee /etc/fail2ban/jail.local > /dev/null <<EOF
[sshd]
enabled = true
port = 22
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 3600
EOF

sudo systemctl enable fail2ban
sudo systemctl restart fail2ban

echo "➡ Setting up logrotate for RPC logs..."
sudo tee /etc/logrotate.d/arbitrum-rpc > /dev/null <<EOF
/var/log/arbitrum-rpc.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    create 0640 ubuntu ubuntu
}
EOF

echo "=========================================================="
echo " 🎯 INSTALL COMPLETE"
echo " Your private RPC is now syncing and will be live soon."
echo ""
echo " Check status:"
echo "   sudo systemctl status arbi-rpc"
echo ""
echo " View logs:"
echo "   sudo journalctl -u arbi-rpc -f"
echo ""
echo " Your endpoints:"
echo "   → HTTP RPC: http://54.158.163.67:8547"
echo "   → WS RPC:   ws://54.158.163.67:8548"
echo ""
echo " Add these to your .env file for unlimited speed!"
echo "=========================================================="
