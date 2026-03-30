#!/usr/bin/env python3
"""Install agentfit and run basic tests."""
import subprocess
import sys
import os

# Get the project root (two levels up from scripts/)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(project_root)

print(f"[v0] Project root: {project_root}")
print("[v0] Installing agentfit package in development mode...")
result = subprocess.run(
    [sys.executable, '-m', 'pip', 'install', '-e', '.'],
    cwd=project_root,
    capture_output=True,
    text=True
)

if result.returncode != 0:
    print(f"[v0] Installation failed!")
    print(result.stdout)
    print(result.stderr)
    sys.exit(1)

print("[v0] Installation successful!")
print("[v0] Testing imports...")

try:
    import agentfit
    print("[v0] agentfit imported successfully")
    
    from agentfit.bnp.parser import BNPParser
    print("[v0] BNPParser imported successfully")
    
    from agentfit.core.evaluator import Evaluator
    print("[v0] Evaluator imported successfully")
    
    from agentfit.mock_agent import MockAgent
    print("[v0] MockAgent imported successfully")
    
    from agentfit.scenarios import ScenarioGenerator
    print("[v0] ScenarioGenerator imported successfully")
    
    from agentfit.output import ResultsFormatter
    print("[v0] ResultsFormatter imported successfully")
    
    from agentfit.cli import main
    print("[v0] CLI main function imported successfully")
    
    print("\n[v0] All imports successful!")
    
except ImportError as e:
    print(f"[v0] Import error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
