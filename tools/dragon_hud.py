import json
import time
import os

LOG_DIR = "logs"
LATEST = None

def find_latest_log():
    global LATEST
    files = [f for f in os.listdir(LOG_DIR) if f.startswith("session_") and f.endswith(".json")]
    if not files:
        return None
    return os.path.join(LOG_DIR, sorted(files)[-1])

def load_log(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except:
        return None

def clear():
    os.system("cls" if os.name == "nt" else "clear")

print("🐉 Dragon HUD Monitor Active")
print("Waiting for live trading logs...\n")

while True:
    path = find_latest_log()
    if not path:
        time.sleep(2)
        continue

    if LATEST != path:
        print(f"🔄 Tracking session log: {path}")
        LATEST = path

    log = load_log(path)

    clear()
    print("====================================================================")
    print(" 🐉 TRADING DRAGON — LIVE MONITOR")
    print("====================================================================")

    if log:
        print(f"🕒 Updated: {log.get('timestamp','N/A')}")
        print(f"💰 Balance: {log.get('account_balance','N/A')}")
        print(f"📈 Opportunities: {log.get('opportunities_detected','N/A')}")
        print(f"💸 Trades Executed: {log.get('trades_executed','N/A')}")
        print(f"📊 PnL: {log.get('session_pnl','N/A')}")
        print("--------------------------------------------------------------------")

        signals = log.get("active_signals", [])
        if signals:
            print("🔥 ACTIVE SIGNALS:")
            for s in signals:
                print(f" - {s}")
        else:
            print("No active trading signals yet (market may be quiet)")

    time.sleep(2)
