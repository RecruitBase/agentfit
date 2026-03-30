#!/usr/bin/env python3
"""Simple test of CLI functionality."""
import subprocess
import sys

print("[v0] Installing agentfit package...")
result = subprocess.run(
    [sys.executable, '-m', 'pip', 'install', '-e', '.', '-q'],
    capture_output=True,
    text=True
)

if result.returncode != 0:
    print(f"[v0] Installation error: {result.stderr}")
    sys.exit(1)

print("[v0] Installation successful!")

print("\n[v0] Testing imports...")
try:
    import agentfit
    from agentfit import Evaluator, BNPParser
    from agentfit.scenarios import ScenarioGenerator
    from agentfit.output import ResultFormatter
    print("[v0] All imports successful!")
except Exception as e:
    print(f"[v0] Import error: {e}")
    sys.exit(1)

print("\n[v0] Testing CLI help...")
result = subprocess.run(
    [sys.executable, '-m', 'agentfit', '--help'],
    capture_output=True,
    text=True
)

if result.returncode == 0:
    print("[v0] CLI help output:")
    print(result.stdout)
else:
    print(f"[v0] CLI error: {result.stderr}")
    sys.exit(1)

print("\n[v0] All tests passed!")
