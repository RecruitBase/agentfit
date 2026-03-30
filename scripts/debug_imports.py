#!/usr/bin/env python3
"""Debug script to test imports and CLI availability."""

import sys
from pathlib import Path

print("[v0] Starting import tests...")

try:
    print("[v0] Importing agentfit...")
    import agentfit
    print(f"[v0] agentfit imported successfully. Version: {agentfit.__version__}")
    
    print("[v0] Checking DimensionRegistry...")
    from agentfit.core.dimension import DimensionRegistry
    print(f"[v0] Available dimensions: {DimensionRegistry.list_available()}")
    
    print("[v0] Importing CLI...")
    from agentfit import cli
    print("[v0] CLI imported successfully")
    
    print("[v0] Checking CLI commands...")
    print(f"[v0] CLI main group: {cli.main}")
    print(f"[v0] CLI commands available: {[cmd for cmd in dir(cli) if cmd.startswith('_') is False and callable(getattr(cli, cmd))]}")
    
    print("\n[v0] All imports successful!")
    sys.exit(0)
    
except Exception as e:
    print(f"[v0] ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
