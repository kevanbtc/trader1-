import os
from pathlib import Path

# Manual load
env_path = Path(__file__).parent / '.env'
print(f"Loading from: {env_path}")
print(f"File exists: {env_path.exists()}")

if env_path.exists():
    print("\n=== RAW .ENV CONTENT ===")
    with open(env_path, 'r', encoding='utf-8') as f:
        content = f.read()
        print(content[:500])
    
    print("\n=== PARSING .ENV ===")
    with open(env_path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                k = key.strip()
                v = value.strip()
                os.environ[k] = v
                print(f"Line {i}: Set {k} = '{v}'")

print("\n=== ENVIRONMENT CHECK ===")
print(f"TRADING_MODE = '{os.environ.get('TRADING_MODE', 'NOT_FOUND')}'")
print(f"ENABLE_PAPER_MODE = '{os.environ.get('ENABLE_PAPER_MODE', 'NOT_FOUND')}'")
print(f"ENABLE_MCP = '{os.environ.get('ENABLE_MCP', 'NOT_FOUND')}'")
print(f"ENABLE_SWARM = '{os.environ.get('ENABLE_SWARM', 'NOT_FOUND')}'")
