# 🐉 APEX TRADING DRAGON - AWS DEPLOYMENT GUIDE

**Transform your EC2 instance into a 24/7 autonomous trading powerhouse**

---

## 📋 Prerequisites

- **AWS EC2 Instance**: c5.xlarge or better
- **OS**: Ubuntu 22.04 LTS
- **IP**: 54.158.163.67 (your instance)
- **Security Group**: Ports 22, 8547, 8548 open to your IP
- **PEM Key**: `donkx-prod.pem` (update path if different)

---

## 🛰️ PHASE 1: Connect VS Code to AWS

### 1.1 Install Remote-SSH Extension
- Open VS Code
- Press `Ctrl+Shift+X`
- Search for "Remote - SSH"
- Install by Microsoft

### 1.2 Add SSH Host
- Press `Ctrl+Shift+P`
- Type: "Remote-SSH: Add New SSH Host"
- Paste this command:

```bash
ssh -i "C:\Users\Kevan\donkx-xrpl-sg\donkx-prod.pem" ubuntu@54.158.163.67
```

### 1.3 Connect to Instance
- Press `Ctrl+Shift+P`
- Type: "Remote-SSH: Connect to Host"
- Select: `ubuntu@54.158.163.67`
- Wait for connection (~30 seconds first time)
- Open folder: `/home/ubuntu/apex`

---

## ⚙️ PHASE 2: Deploy Trading Engine

### 2.1 Upload Deployment Package

**Option A: Using VS Code Remote Explorer**
1. In VS Code connected to EC2, open terminal (`Ctrl+~`)
2. Run:
```bash
mkdir -p ~/apex/engine
cd ~/apex/engine
```
3. In VS Code Explorer, drag and drop these files from `c:\trading-engine-clean\` to `~/apex/engine/`:
   - All files from `agents/` folder
   - All files from `config/` folder
   - `start_trading.py`
   - `requirements.txt`
   
4. Drag and drop from `c:\trading-engine-clean\aws-deploy\` to `~/apex/engine/`:
   - `rpc_mirror.py`
   - `mempool_sniffer.py`
   - `apex_trading_dragon.py`
   - `.env.aws` (rename to `.env`)
   - `supervisor-apex.conf`

**Option B: Using SCP (from local Windows)**
```powershell
# From c:\trading-engine-clean\ directory
scp -i "C:\Users\Kevan\donkx-xrpl-sg\donkx-prod.pem" -r agents config start_trading.py requirements.txt ubuntu@54.158.163.67:~/apex/engine/

scp -i "C:\Users\Kevan\donkx-xrpl-sg\donkx-prod.pem" aws-deploy/*.py aws-deploy/.env.aws aws-deploy/supervisor-apex.conf ubuntu@54.158.163.67:~/apex/engine/
```

### 2.2 Run Deployment Script

In VS Code terminal connected to EC2:

```bash
cd ~/apex/engine
chmod +x deploy.sh
./deploy.sh
```

Follow prompts to:
1. Wait for system updates
2. Enter your wallet private key and address in `.env`
3. Enter your home IP address for firewall rules
4. Confirm deployment

---

## 🔐 PHASE 3: Configure Wallet

Edit `.env` file on AWS:

```bash
cd ~/apex/engine
nano .env
```

**Update these lines:**
```bash
PRIVATE_KEY=0x0bfa55c1460df66d9b50ce72fb53ff06a2a67a3e4289c7b8fc08580e2321fb3b
PUBLIC_ADDRESS=0x5fc05DA8cB29f08754ac120Ab6F4F6176774b53E
WALLET_ADDRESS=0x5fc05DA8cB29f08754ac120Ab6F4F6176774b53E
```

Save with `Ctrl+X`, `Y`, `Enter`

---

## 🚀 PHASE 4: Start Services

### 4.1 Manual Start (Testing)

```bash
cd ~/apex/engine
source venv/bin/activate

# Terminal 1: RPC Mirror
uvicorn rpc_mirror:app --host 0.0.0.0 --port 8547 --workers 3 &

# Terminal 2: Mempool Sniffer  
python3 mempool_sniffer.py &

# Terminal 3: Trading Dragon
python3 apex_trading_dragon.py
```

### 4.2 Production Start (24/7 with Supervisor)

```bash
sudo supervisorctl start apex-full-stack:*
```

### 4.3 Check Status

```bash
sudo supervisorctl status
```

Expected output:
```
apex-full-stack:apex-mempool-sniffer    RUNNING   pid 1234, uptime 0:00:05
apex-full-stack:apex-rpc-mirror         RUNNING   pid 1235, uptime 0:00:05
apex-full-stack:apex-trading-dragon     RUNNING   pid 1236, uptime 0:00:05
```

---

## 📊 PHASE 5: Monitor Operations

### 5.1 Real-Time Logs

**All logs combined:**
```bash
tail -f ~/apex/logs/*.log
```

**Trading Dragon only:**
```bash
tail -f ~/apex/logs/trading-dragon.out.log
```

**Mempool sniffer:**
```bash
tail -f ~/apex/logs/mempool-sniffer.out.log
```

**RPC mirror:**
```bash
tail -f ~/apex/logs/rpc-mirror.out.log
```

### 5.2 Service Management

```bash
# Restart all services
sudo supervisorctl restart apex-full-stack:*

# Stop all services
sudo supervisorctl stop apex-full-stack:*

# Start all services
sudo supervisorctl start apex-full-stack:*

# Restart specific service
sudo supervisorctl restart apex-full-stack:apex-trading-dragon
```

### 5.3 System Resources

```bash
# CPU and Memory
htop

# Disk usage
df -h

# Network connections
netstat -tulpn | grep LISTEN
```

---

## 🔧 PHASE 6: Configuration Tuning

### 6.1 Adjust Profit Threshold

```bash
nano ~/apex/engine/.env
```

Change `MIN_PROFIT_USD=0.02` to desired value (e.g., `0.01` for more opportunities)

Restart:
```bash
sudo supervisorctl restart apex-full-stack:apex-trading-dragon
```

### 6.2 Adjust Scan Speed

Change `SCAN_INTERVAL_MS=250` (default: 4 scans/sec)
- `200` = 5 scans/sec (more aggressive)
- `500` = 2 scans/sec (more conservative)

### 6.3 Adjust Position Size

Change `MAX_POSITION_USD=15.00` to desired max trade size

---

## 🛡️ PHASE 7: Security Hardening

### 7.1 Firewall Status

```bash
sudo ufw status verbose
```

### 7.2 Update Allowed IPs

```bash
# Add new IP
sudo ufw allow from NEW_IP_ADDRESS to any port 22

# Remove old IP
sudo ufw delete allow from OLD_IP_ADDRESS to any port 22
```

### 7.3 Fail2Ban (SSH Protection)

```bash
sudo apt install fail2ban -y
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

---

## 📈 PHASE 8: Performance Monitoring

### 8.1 Trading Statistics

```bash
cd ~/apex/engine
python3 -c "
import json
from pathlib import Path

sessions = list(Path('logs').glob('session_*.json'))
if sessions:
    latest = max(sessions, key=lambda p: p.stat().st_mtime)
    data = json.loads(latest.read_text())
    print(f\"Total Scans: {data['total_scans']}\")
    print(f\"Opportunities: {data['opportunities_detected']}\")
    print(f\"Trades: {data['trades_executed']}\")
    print(f\"PnL: \${data['session_pnl_usd']:.4f}\")
"
```

### 8.2 RPC Mirror Stats

```bash
curl http://localhost:8547/stats
```

### 8.3 Mempool Opportunities

```bash
tail -50 ~/apex/logs/mempool_feed.log | jq .
```

---

## 🔄 PHASE 9: Updates & Maintenance

### 9.1 Update Trading Code

```bash
cd ~/apex/engine
git pull  # If using git
# Or upload new files via VS Code

sudo supervisorctl restart apex-full-stack:*
```

### 9.2 Update Python Dependencies

```bash
cd ~/apex/engine
source venv/bin/activate
pip install --upgrade -r requirements.txt

sudo supervisorctl restart apex-full-stack:*
```

### 9.3 View Error Logs

```bash
tail -50 ~/apex/logs/trading-dragon.err.log
tail -50 ~/apex/logs/mempool-sniffer.err.log
tail -50 ~/apex/logs/rpc-mirror.err.log
```

---

## 🆘 Troubleshooting

### Services Won't Start

```bash
# Check supervisor logs
sudo tail -50 /var/log/supervisor/supervisord.log

# Check individual service logs
sudo supervisorctl tail -f apex-full-stack:apex-trading-dragon stderr
```

### RPC Connection Issues

```bash
# Test RPC mirror
curl -X POST http://localhost:8547 \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'

# Check if port is listening
sudo netstat -tulpn | grep 8547
```

### No Opportunities Found

```bash
# Check if scanner is working
tail -f ~/apex/logs/trading-dragon.out.log

# Verify MIN_PROFIT_USD threshold
grep MIN_PROFIT_USD ~/apex/engine/.env

# Check mempool feed
tail -f ~/apex/logs/mempool_feed.log
```

---

## 📞 Quick Reference

### Key Files
- **Main config**: `~/apex/engine/.env`
- **Trading dragon**: `~/apex/engine/apex_trading_dragon.py`
- **Supervisor config**: `/etc/supervisor/conf.d/apex.conf`
- **Logs**: `~/apex/logs/`

### Key Commands
```bash
# Status
sudo supervisorctl status

# Restart all
sudo supervisorctl restart apex-full-stack:*

# View logs
tail -f ~/apex/logs/trading-dragon.out.log

# Stop all
sudo supervisorctl stop apex-full-stack:*
```

### Endpoints
- **HTTP RPC**: http://54.158.163.67:8547
- **WebSocket**: ws://54.158.163.67:8548
- **Health check**: http://54.158.163.67:8547/health
- **RPC stats**: http://54.158.163.67:8547/stats

---

## 🎯 What You Get

✅ **Private Arbitrum RPC** - No rate limits, unlimited throughput  
✅ **Mempool Sniffer** - Real-time pending transaction analysis  
✅ **24/7 Trading Dragon** - Autonomous execution, never stops  
✅ **Auto-restart** - Survives crashes, reboots, network issues  
✅ **Full monitoring** - Comprehensive logging and statistics  
✅ **Security hardened** - Firewall, Fail2Ban, IP restrictions  
✅ **Performance tuned** - Optimized kernel parameters  

---

## 🚀 Ready to Launch

Your Apex Trading Dragon is now configured for **24/7 autonomous operation**.

The system will:
- Scan markets every 250ms (4x per second)
- Execute profitable opportunities automatically
- Log every scan and trade
- Restart on failures
- Run forever until you stop it

**Monitor your dragon and watch it hunt!** 🐉💰
