# ⚡ ULTIMATE 429 / RPC / ALCHEMY PURGE DEBUGGING PROTOCOL

## 🎯 ROOT CAUSE ANALYSIS

### PROBLEM IDENTIFIED:
**AWS bot still calling Alchemy despite config changes**

### RESOLUTION CHAIN (traced):

```
1. AWS .env → CONTAINS ALCHEMY (✓ Fixed via sed)
2. AWS config JSON → rpc_url field CONTAINS ALCHEMY (✓ Fixed via PowerShell)
3. AWS supervisor → UPSTREAM_RPC CONTAINS ALCHEMY (✓ Fixed via sed)
4. AWS Python cache → CACHED ALCHEMY imports (⚠️ Needs clearing)
5. AWS rpc_utils.py → Tries ALCHEMY_ARB_HTTPS FIRST (⚠️ Priority issue)
```

---

## 📊 DIAGNOSTIC PROTOCOL

### Step 1: Environment Variable Scan
```powershell
# Local check
.\.venv\Scripts\python.exe -c "import os; from dotenv import load_dotenv; load_dotenv(); print('ARB_RPC_1:', os.getenv('ARB_RPC_1')); print('ALCHEMY:', os.getenv('ALCHEMY_ARB_HTTPS'))"

# AWS check
ssh -i "path/to/key.pem" ubuntu@IP "cd /home/ubuntu/apex && python3 -c \"import os; from dotenv import load_dotenv; load_dotenv(); print('ARB_RPC_1:', os.getenv('ARB_RPC_1')); print('ALCHEMY:', os.getenv('ALCHEMY_ARB_HTTPS'))\""
```

**Expected:** ARB_RPC_1 = public RPC, ALCHEMY = None

---

### Step 2: RPC Provider Collection Test
```powershell
# Local
.\.venv\Scripts\python.exe -c "from agents.rpc_utils import _collect_arbitrum_providers; import json; print(json.dumps(_collect_arbitrum_providers(), indent=2))"

# AWS
ssh -i "key.pem" ubuntu@IP "cd /home/ubuntu/apex && python3 -c 'from agents.rpc_utils import _collect_arbitrum_providers; import json; print(json.dumps(_collect_arbitrum_providers(), indent=2))'"
```

**Expected:** Only public RPCs (arb1.arbitrum.io, llamarpc.com, ankr.com)

**If ALCHEMY appears:** Check priority order in `rpc_utils.py` line 51

---

### Step 3: Cache Verification
```powershell
# Local
Get-ChildItem -Path . -Filter "__pycache__" -Recurse -Directory | Remove-Item -Recurse -Force
Get-ChildItem -Path . -Filter "*.pyc" -Recurse | Remove-Item -Force

# AWS
ssh -i "key.pem" ubuntu@IP "cd /home/ubuntu/apex && find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null; find . -name '*.pyc' -delete"
```

**Must run BEFORE any config change takes effect**

---

### Step 4: Config File Audit
```powershell
# Local
grep -r "_SZloFUZ5eS1b1UVy2ODg" . --include="*.py" --include="*.json" --include="*.env*"

# AWS
ssh -i "key.pem" ubuntu@IP "cd /home/ubuntu/apex && grep -r '_SZloFUZ5eS1b1UVy2ODg' . --include='*.py' --include='*.json' --include='.env*'"
```

**Expected:** 0 matches (or only in .backup files)

---

### Step 5: Live RPC URL Extraction
```powershell
# During bot runtime, extract actual RPC being used
tail -50 logs/trading-dragon.out.log | grep -oP "https://[^'\"]*" | sort | uniq
```

**If Alchemy appears:** RPC is hardcoded in DEX adapter objects (initialized at import time)

---

## 🔧 FIX PRIORITY ORDER

### Issue: `rpc_utils.py` lines 51-52
```python
env_keys: List[str] = [
    "ALCHEMY_ARB_HTTPS",  # ← THIS CHECKS FIRST!
    "INFURA_ARB_HTTPS",
    "ARB_RPC_1",
    ...
]
```

**Problem:** If `ALCHEMY_ARB_HTTPS` exists ANYWHERE (system env, .env.backup, etc.), it wins.

**Fix:** Remove from priority list or move to bottom:

```python
env_keys: List[str] = [
    "ARB_RPC_1",      # ← Public RPC first
    "ARB_RPC_2",
    "ARB_RPC_3",
    "ARBITRUM_RPC",
    # Legacy (deprecated)
    # "ALCHEMY_ARB_HTTPS",
    # "INFURA_ARB_HTTPS",
]
```

---

## 🚨 AWS-SPECIFIC DIAGNOSIS

### The AWS bot shows Alchemy URLs in error logs even after:
- ✅ .env updated
- ✅ config JSON updated  
- ✅ supervisor config updated
- ✅ Cache cleared

### Root cause:
1. **Web3 provider objects initialized at module import time**
2. **DEX adapters cache RPC URLs in __init__()**
3. **Supervisor restart != Python module reload**

### Solution:
```bash
# Full restart (not just supervisor restart)
ssh ubuntu@IP "sudo supervisorctl stop apex-full-stack: && sleep 5 && sudo supervisorctl start apex-full-stack:"
```

Or reboot EC2:
```bash
ssh ubuntu@IP "sudo reboot"
```

---

## ✅ VERIFICATION CHECKLIST

After applying fixes:

- [ ] .env has NO alchemy references
- [ ] .env.backup deleted or moved
- [ ] Config JSON has public RPC only
- [ ] supervisor config has public UPSTREAM_RPC
- [ ] Python cache cleared (`__pycache__`, `*.pyc`)
- [ ] `_collect_arbitrum_providers()` returns public RPCs only
- [ ] Bot startup log shows public RPC block number
- [ ] Quote errors show public RPC URLs (not Alchemy)
- [ ] No 429 errors for 5+ minutes

---

## 🎬 QUICK FIX SCRIPT

```bash
#!/bin/bash
# Run on AWS to purge all Alchemy

cd /home/ubuntu/apex

# Backup
cp .env .env.backup.$(date +%s)

# Remove Alchemy from .env
sed -i 's|_SZloFUZ5eS1b1UVy2ODg|PUBLIC_RPC_REMOVED|g' .env
sed -i 's|arb-mainnet.g.alchemy.com/v2/PUBLIC_RPC_REMOVED|arb1.arbitrum.io/rpc|g' .env

# Update supervisor
sudo sed -i 's|https://arb-mainnet.g.alchemy.com/v2/.*|https://arb1.arbitrum.io/rpc"|' /etc/supervisor/conf.d/supervisor-apex.conf

# Clear cache
find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null
find . -name '*.pyc' -delete 2>/dev/null

# Restart
sudo supervisorctl restart apex-full-stack:

echo "✅ Alchemy purged. Wait 30s for restart..."
sleep 30

# Verify
tail -50 logs/trading-dragon.out.log | grep -i "connected\|block:"
```

---

## 📞 WHEN TO USE THIS DOCUMENT

Use this protocol when:
- ✅ Bot shows 429 rate limit errors
- ✅ Logs show Alchemy URLs after config changes
- ✅ Quote requests fail with "Too Many Requests"
- ✅ Bot can't get price data despite RPC being "fixed"
- ✅ Supervisor restart doesn't fix the issue
- ✅ You see `url='https://arb-mainnet.g.alchemy.com/v2/...'` in errors

---

## 🔥 NUCLEAR OPTION

If all else fails (bot STILL calling Alchemy):

### 1. Find the actual code making the call
```bash
grep -rn "Web3(Web3.HTTPProvider" agents/
grep -rn "requests.post.*alchemy" agents/
grep -rn "self.rpc_url" agents/
```

### 2. Add debug print to trace source
```python
# Add to defi_price_feed.py __init__
print(f"🔍 DeFiPriceFeed RPC URL: {self.rpc_url}")

# Add to rpc_utils.py _collect_arbitrum_providers
print(f"🔍 Collected providers: {providers}")
```

### 3. Check if DEX contracts have hardcoded endpoints
```bash
grep -rn "0xaf88d065e77c8cC2239327C5EDb3A432268e5831" agents/
# USDC contract - if appears with Alchemy URL = hardcoded
```

---

## 📈 SUCCESS METRICS

Bot is FIXED when logs show:

```
✅ Connected! Block: 405,XXX,XXX, Gas: 0.01XX Gwei
🔍 Scan #10: 0 opportunities (market quiet)
🔍 Scan #20: 0 opportunities (market quiet)
```

**WITHOUT any:**
- ❌ `429 Client Error`
- ❌ `arb-mainnet.g.alchemy.com`
- ❌ `rate limited`
- ❌ `compute units per second`

---

## 🎓 KEY LEARNINGS

1. **Environment variables can be shadowed** - system env > .env file
2. **Python imports cache modules** - must clear `__pycache__`
3. **Web3 providers init at import time** - not at function call time
4. **Supervisor restart != process reload** - old modules stay in memory
5. **Priority order matters** - first valid RPC in list wins
6. **Config files can conflict** - JSON vs .env vs supervisor vars
7. **Free RPC tiers exhaust fast** - 4 scans/sec = 240 calls/min = rate limit

---

**Last Updated:** 2025-11-28
**Author:** Copilot Refactor Agent
**Status:** PROTOCOL ACTIVE
