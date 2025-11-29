# ⚡ APEX AWS QUICKSTART - 5 MINUTES TO 24/7 TRADING

**Deploy your trading engine to AWS in 5 simple steps.**

---

## ⭐ STEP 1 - Connect VS Code to AWS

1. **Install Remote-SSH Extension** (if not already installed)
   - `Ctrl+Shift+P` → "Extensions: Install Extensions"
   - Search: "Remote - SSH"
   - Install by Microsoft

2. **Add SSH Host**
   - `Ctrl+Shift+P` → "Remote-SSH: Add New SSH Host"
   - Paste this command:
     ```
     ssh -i "C:\Users\Kevan\donkx-prod.pem" ubuntu@54.158.163.67
     ```
   - Select first config file option

3. **Connect to AWS**
   - `Ctrl+Shift+P` → "Remote-SSH: Connect to Host"
   - Select: `ubuntu@54.158.163.67`
   - Wait 20-30 seconds for connection
   - Bottom-left corner will show: `SSH: ubuntu@54.158.163.67`

---

## ⭐ STEP 2 - Upload Deployment Package

**Option A: Drag & Drop (Easiest)**
1. In VS Code, open folder: `/home/ubuntu`
2. Drag the entire `aws-deploy/` folder from Windows Explorer into VS Code's file tree
3. Confirm upload

**Option B: Using SCP from Windows PowerShell**
```powershell
cd C:\trading-engine-clean
scp -i "C:\Users\Kevan\donkx-prod.pem" -r aws-deploy ubuntu@54.158.163.67:~/
```

**Option C: Upload trading engine too**
```powershell
# Upload everything at once
cd C:\trading-engine-clean
scp -i "C:\Users\Kevan\donkx-prod.pem" -r aws-deploy agents config start_trading.py requirements.txt ubuntu@54.158.163.67:~/aws-deploy/
```

---

## ⭐ STEP 3 - Run Deployment Script

In VS Code's integrated terminal (connected to AWS):

```bash
cd ~/aws-deploy
chmod +x deploy.sh
./deploy.sh
```

**What this does automatically:**
- ✅ Installs all system dependencies
- ✅ Applies Linux kernel performance tuning
- ✅ Creates Python virtual environment
- ✅ Installs Web3, FastAPI, all trading packages
- ✅ Copies deployment files to ~/apex/engine/
- ✅ Sets up Supervisor for auto-restart
- ✅ Configures firewall rules
- ✅ Sets up log rotation

**During deployment:**
- Press Enter when prompted to open .env editor
- Update `PRIVATE_KEY` and `PUBLIC_ADDRESS` with your values
- Save with `Ctrl+X`, `Y`, `Enter`
- Enter your home IP when asked (for secure RPC access)

---

## ⭐ STEP 4 - Verify Deployment

Check services are running:

```bash
sudo supervisorctl status
```

**Expected output:**
```
apex-full-stack:apex-mempool-sniffer    RUNNING   pid 1234, uptime 0:00:10
apex-full-stack:apex-rpc-mirror         RUNNING   pid 1235, uptime 0:00:10
apex-full-stack:apex-trading-dragon     RUNNING   pid 1236, uptime 0:00:10
```

**All three should say `RUNNING`** ✅

---

## ⭐ STEP 5 - Monitor Live Trading

**Watch trading activity:**
```bash
tail -f ~/apex/logs/trading-dragon.out.log
```

**Watch mempool sniffer:**
```bash
tail -f ~/apex/logs/mempool-sniffer.out.log
```

**Watch all logs:**
```bash
tail -f ~/apex/logs/*.log
```

**Check RPC health:**
```bash
curl http://localhost:8547/health
```

---

## 🎯 You're Live!

Your trading engine is now:
- ✅ Running 24/7 on AWS
- ✅ Scanning markets every 250ms (4x/second)
- ✅ Using private RPC (no rate limits)
- ✅ Monitoring mempool for front-running
- ✅ Auto-restarting on crashes
- ✅ Logging everything to files

---

## 🔧 Common Commands

```bash
# Check service status
sudo supervisorctl status

# Restart all services
sudo supervisorctl restart apex-full-stack:*

# Stop all services
sudo supervisorctl stop apex-full-stack:*

# Start all services
sudo supervisorctl start apex-full-stack:*

# View live logs
tail -f ~/apex/logs/trading-dragon.out.log

# Edit configuration
nano ~/apex/engine/.env

# Run deployment check
~/apex/engine/check_deployment.sh
```

---

## 🔒 Security Notes

- **Firewall**: Only your IP can access RPC and SSH
- **Private key**: Stored in ~/.apex/.env (not exposed)
- **Logs**: Rotated daily, compressed after 14 days
- **Auto-restart**: Services restart automatically on failure

---

## 📊 Performance Tuning

**Adjust scan speed** (edit ~/apex/engine/.env):
```bash
SCAN_INTERVAL_MS=250  # 4 scans/sec (default)
SCAN_INTERVAL_MS=200  # 5 scans/sec (more aggressive)
SCAN_INTERVAL_MS=500  # 2 scans/sec (conservative)
```

**Adjust profit threshold:**
```bash
MIN_PROFIT_USD=0.02  # Default
MIN_PROFIT_USD=0.01  # Find more opportunities
MIN_PROFIT_USD=0.05  # Only big opportunities
```

**After changes:**
```bash
sudo supervisorctl restart apex-full-stack:apex-trading-dragon
```

---

## 🆘 Troubleshooting

**Services won't start:**
```bash
sudo supervisorctl tail -f apex-full-stack:apex-trading-dragon stderr
```

**Check deployment:**
```bash
cd ~/apex/engine
./check_deployment.sh
```

**RPC not responding:**
```bash
# Check if port is listening
sudo netstat -tulpn | grep 8547

# Check RPC logs
tail -50 ~/apex/logs/rpc-mirror.err.log
```

**Need help:**
- Check full documentation: `~/aws-deploy/README.md`
- View error logs: `tail -50 ~/apex/logs/*.err.log`
- Restart everything: `sudo supervisorctl restart apex-full-stack:*`

---

## 🚀 Next Level Features

Want to add:
- 🔥 **Failover node** (automatic backup)
- 🔐 **Private RPC auth** (password protection)
- ⚔️ **MEV bundles** (Flashbots integration)
- 💰 **Auto-withdraw** (profits to cold wallet)
- 🎛️ **Portfolio rebalancing** (multi-token management)

Just ask and I'll add them to your deployment!

---

**Your trading dragon is alive and hunting 24/7!** 🐉💰
