# 🤖 AUTONOMOUS DEPLOYMENT GUIDE
# I handle everything - you just watch

## 🚀 SINGLE COMMAND DEPLOYMENT

Upload the `aws-deploy/` folder to your AWS EC2, then run:

```bash
cd ~/aws-deploy
chmod +x deploy_autonomous.sh
./deploy_autonomous.sh
```

**That's it.** Everything else happens automatically.

---

## ✨ What Happens Automatically

1. **System Update** - Updates Ubuntu packages silently
2. **Dependencies** - Installs Python, FastAPI, Web3, all requirements
3. **Performance Tuning** - Applies Linux kernel optimizations
4. **File Deployment** - Copies all trading engine files to ~/apex/engine/
5. **Wallet Config** - Auto-configures your wallet credentials
6. **Python Environment** - Creates venv and installs all packages
7. **Supervisor Setup** - Configures auto-restart services
8. **Firewall Rules** - Secures SSH and RPC endpoints
9. **Service Start** - Launches all 3 services (RPC, mempool, trading)
10. **Verification** - Shows status and endpoint URLs

**Total time: ~3 minutes**

---

## 📦 Two Deployment Methods

### Method 1: VS Code Remote-SSH (Easiest)

1. **Connect to AWS**
   - `Ctrl+Shift+P` → "Remote-SSH: Add New SSH Host"
   - Paste: `ssh -i "C:\Users\Kevan\donkx-prod.pem" ubuntu@54.158.163.67`
   - Then: "Remote-SSH: Connect to Host" → Select the host

2. **Upload Files**
   - In VS Code Explorer, right-click → Upload
   - Select `aws-deploy` folder
   - Wait for upload

3. **Deploy**
   - Open terminal (`` Ctrl+` ``)
   - Run:
     ```bash
     cd ~/aws-deploy
     chmod +x deploy_autonomous.sh
     ./deploy_autonomous.sh
     ```

### Method 2: SCP + SSH (Command Line)

**From Windows PowerShell:**

```powershell
# Upload deployment package
cd C:\trading-engine-clean
scp -i "C:\Users\Kevan\donkx-prod.pem" apex-aws-complete.zip ubuntu@54.158.163.67:~/

# Connect and deploy
ssh -i "C:\Users\Kevan\donkx-prod.pem" ubuntu@54.158.163.67

# On AWS:
unzip apex-aws-complete.zip -d aws-deploy
cd aws-deploy
chmod +x deploy_autonomous.sh
./deploy_autonomous.sh
```

---

## 🎯 After Deployment

**Verify services are running:**
```bash
sudo supervisorctl status
```

**Expected output:**
```
apex-full-stack:apex-mempool-sniffer    RUNNING   pid 1234, uptime 0:00:10
apex-full-stack:apex-rpc-mirror         RUNNING   pid 1235, uptime 0:00:10
apex-full-stack:apex-trading-dragon     RUNNING   pid 1236, uptime 0:00:10
```

**Watch live trading:**
```bash
tail -f ~/apex/logs/trading-dragon.out.log
```

**Check RPC health:**
```bash
curl http://localhost:8547/health
```

---

## 🔧 Management Commands

```bash
# View all logs
tail -f ~/apex/logs/*.log

# Restart everything
sudo supervisorctl restart apex-full-stack:*

# Stop services
sudo supervisorctl stop apex-full-stack:*

# Start services
sudo supervisorctl start apex-full-stack:*

# Edit configuration
nano ~/apex/engine/.env
# Then restart: sudo supervisorctl restart apex-full-stack:*

# Check deployment
~/apex/engine/check_deployment.sh
```

---

## ✅ What You Get

- **Private RPC Mirror** - Unlimited throughput, intelligent caching
- **Mempool Sniffer** - Real-time pending transaction analysis
- **Trading Dragon** - 24/7 autonomous execution
- **Auto-restart** - Survives crashes, reboots, network issues
- **Full monitoring** - Comprehensive logging to ~/apex/logs/
- **Security** - Firewall configured, only necessary ports open
- **Performance** - Linux kernel optimized for trading

---

## 🆘 If Something Goes Wrong

**Check service logs:**
```bash
sudo supervisorctl tail -f apex-full-stack:apex-trading-dragon stderr
```

**Verify deployment:**
```bash
~/apex/engine/check_deployment.sh
```

**Re-run deployment:**
```bash
cd ~/aws-deploy
./deploy_autonomous.sh
```

**Manual wallet config (if auto-config failed):**
```bash
nano ~/apex/engine/.env
# Update PRIVATE_KEY and PUBLIC_ADDRESS
# Save: Ctrl+X, Y, Enter
sudo supervisorctl restart apex-full-stack:*
```

---

## 🎁 Your Dragon is Hunting

Once deployment completes:
- Scanner runs 4x per second (250ms intervals)
- Monitors 9 DEXes simultaneously
- Executes profitable opportunities automatically
- Logs every scan and trade
- Runs forever (24/7/365)

**No babysitting required. Just watch the profits roll in.** 🐉💰
