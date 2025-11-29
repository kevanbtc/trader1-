#!/usr/bin/env python3
"""
Kraken Balance Checker
Fetches current Kraken account balances and writes a timestamped log entry to logs/kraken_balances.json.
Prints a human-readable summary for quick review.
"""

import os
import json
from datetime import datetime
from dotenv import load_dotenv
from kraken_live_trader_v2 import KrakenAPI


def main():
    load_dotenv()
    api = KrakenAPI()
    resp = api.get_balance()
    if resp.get("error"):
        print(f"❌ Kraken error: {resp['error']}")
        return 1

    balances = resp.get("result", {})
    # Normalize BTC key to XBT if present
    if "BTC" in balances and "XBT" not in balances:
        balances["XBT"] = balances["BTC"]
        del balances["BTC"]

    # Build summary focusing on USDC and XRP (plus any non-zero assets)
    focus_assets = ["USDC", "XRP", "XBT", "ETH", "SOL"]
    non_zero = {k: float(v) for k, v in balances.items() if float(v) > 0}
    summary_focus = {k: non_zero.get(k, 0.0) for k in focus_assets}

    # Prepare log entry
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "balances": non_zero,
        "focus": summary_focus
    }

    # Ensure logs directory exists
    os.makedirs("logs", exist_ok=True)
    log_path = os.path.join("logs", "kraken_balances.json")

    # Append to JSONL-style log
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

    # Print human summary
    print("\n📦 Kraken Balances (focus):")
    for k in focus_assets:
        print(f"  {k}: {summary_focus.get(k, 0.0):.8f}")
    print("\nAll non-zero assets:")
    for k, v in sorted(non_zero.items()):
        print(f"  {k}: {v:.8f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
