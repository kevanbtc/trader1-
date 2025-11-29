import os
from pathlib import Path

# Manual load like start_trading.py does
project_root = Path(__file__).parent
env_path = project_root / '.env'

print(f"Loading from: {env_path}")
print(f"Exists: {env_path.exists()}\n")

# Manual parsing
if env_path.exists():
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

# Check what we got
env_mode = os.environ.get('TRADING_MODE', 'PAPER').upper()
paper_mode = os.environ.get('ENABLE_PAPER_MODE', 'false').lower() == 'true'

print(f"TRADING_MODE raw: '{os.environ.get('TRADING_MODE', 'NOT_FOUND')}'")
print(f"env_mode (after .upper()): '{env_mode}'")
print(f"ENABLE_PAPER_MODE raw: '{os.environ.get('ENABLE_PAPER_MODE', 'NOT_FOUND')}'")
print(f"paper_mode (after == 'true'): {paper_mode}")
print(f"\nCondition check:")
print(f"  env_mode == 'LIVE': {env_mode == 'LIVE'}")
print(f"  not paper_mode: {not paper_mode}")
print(f"  Both true: {env_mode == 'LIVE' and not paper_mode}")
