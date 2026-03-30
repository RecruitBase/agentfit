#!/usr/bin/env python
"""
Quick test script for AgentFit CLI.

Tests the basic CLI evaluation workflow.
"""

import subprocess
import sys
import json
from pathlib import Path

def run_command(cmd):
    """Run a shell command and print output."""
    print(f"\n▶ Running: {' '.join(cmd)}")
    print("-" * 60)
    result = subprocess.run(cmd, cwd="/vercel/share/v0-project")
    print("-" * 60)
    return result.returncode == 0

def main():
    """Run CLI tests."""
    print("🧪 Testing AgentFit CLI")
    print("=" * 60)
    
    # Test 1: List dimensions
    print("\n📋 Test 1: List available dimensions")
    if not run_command([sys.executable, "-m", "agentfit", "list-dimensions"]):
        print("❌ Test 1 failed")
        return 1
    print("✓ Test 1 passed")
    
    # Test 2: Validate BNP
    print("\n✅ Test 2: Validate BNP profile")
    if not run_command([
        sys.executable, "-m", "agentfit", 
        "validate", 
        "--bnp", "examples/customer_service_bnp.md"
    ]):
        print("❌ Test 2 failed")
        return 1
    print("✓ Test 2 passed")
    
    # Test 3: Show BNP
    print("\n👀 Test 3: Show BNP profile")
    if not run_command([
        sys.executable, "-m", "agentfit", 
        "show-bnp", 
        "--bnp", "examples/customer_service_bnp.md"
    ]):
        print("❌ Test 3 failed")
        return 1
    print("✓ Test 3 passed")
    
    # Test 4: Run evaluation
    print("\n⚙️  Test 4: Run evaluation")
    output_file = "/tmp/agentfit_test_results.json"
    if not run_command([
        sys.executable, "-m", "agentfit", 
        "evaluate", 
        "--bnp", "examples/customer_service_bnp.md",
        "--output", output_file,
        "--format", "json"
    ]):
        print("❌ Test 4 failed")
        return 1
    print("✓ Test 4 passed")
    
    # Check if output file was created and is valid JSON
    output_path = Path(output_file)
    if not output_path.exists():
        print(f"❌ Output file not created: {output_file}")
        return 1
    
    try:
        results = json.loads(output_path.read_text())
        print(f"\n📊 Results Summary:")
        print(f"   Overall Score: {results['evaluation']['overall_score']:.2f}")
        print(f"   Passed: {results['evaluation']['passed']}")
        print(f"   Dimensions evaluated: {list(results['dimensions'].keys())}")
    except json.JSONDecodeError:
        print("❌ Output file is not valid JSON")
        return 1
    
    # Test 5: Run with filtered dimensions
    print("\n🎯 Test 5: Run evaluation with filtered dimensions")
    output_file2 = "/tmp/agentfit_test_results_filtered.json"
    if not run_command([
        sys.executable, "-m", "agentfit", 
        "evaluate", 
        "--bnp", "examples/customer_service_bnp.md",
        "--output", output_file2,
        "--format", "json",
        "--evals", "task_competence"
    ]):
        print("❌ Test 5 failed")
        return 1
    print("✓ Test 5 passed")
    
    print("\n" + "=" * 60)
    print("✅ All tests passed!")
    print("=" * 60)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
