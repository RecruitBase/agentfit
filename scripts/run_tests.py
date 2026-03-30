#!/usr/bin/env python3
"""Comprehensive test runner for AgentFit.

This script runs all tests, checks code quality, and generates coverage reports.
"""
import subprocess
import sys
import os
from pathlib import Path


class Colors:
    """ANSI color codes."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(text):
    """Print a formatted header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}\n")


def print_success(text):
    """Print success message."""
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")


def print_error(text):
    """Print error message."""
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")


def print_warning(text):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")


def run_command(cmd, description, exit_on_error=False):
    """Run a shell command and report results."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print_success(description)
        return True
    else:
        if result.stderr:
            print(result.stderr)
        if exit_on_error:
            print_error(description)
            sys.exit(1)
        else:
            print_warning(description)
            return False


def main():
    """Run all tests and quality checks."""
    
    # Get project root
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    print_header("AgentFit Test Suite")
    print(f"Project root: {project_root}\n")
    
    # Track results
    all_passed = True
    
    # 1. Check Python version
    print_header("1. Checking Environment")
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    if sys.version_info >= (3, 10):
        print_success(f"Python version: {python_version}")
    else:
        print_error(f"Python 3.10+ required, got {python_version}")
        sys.exit(1)
    
    # 2. Check dependencies
    print_header("2. Checking Dependencies")
    required_packages = ['pytest', 'pydantic', 'click']
    for package in required_packages:
        try:
            __import__(package)
            print_success(f"Found {package}")
        except ImportError:
            print_error(f"Missing {package}")
            all_passed = False
    
    # 3. Run unit tests
    print_header("3. Running Unit Tests")
    if run_command(
        [sys.executable, '-m', 'pytest', 'tests/', '-v', '--tb=short'],
        "Unit tests passed"
    ):
        pass
    else:
        all_passed = False
    
    # 4. Run tests with coverage
    print_header("4. Running Tests with Coverage")
    coverage_cmd = [
        sys.executable, '-m', 'pytest', 'tests/',
        '--cov=agentfit',
        '--cov-report=term-missing',
        '--cov-report=html',
        '-v'
    ]
    if run_command(coverage_cmd, "Coverage report generated"):
        print_success("Coverage report: htmlcov/index.html")
    else:
        all_passed = False
    
    # 5. Code style checks (optional, warn if fail)
    print_header("5. Code Quality Checks")
    
    # Black formatting
    if run_command(
        [sys.executable, '-m', 'black', '--check', 'agentfit/', 'tests/', 'examples/'],
        "Code formatting is correct",
        exit_on_error=False
    ):
        pass
    else:
        print_warning("Run 'black agentfit/ tests/ examples/' to fix formatting")
    
    # isort imports
    if run_command(
        [sys.executable, '-m', 'isort', '--check-only', 'agentfit/', 'tests/', 'examples/'],
        "Import ordering is correct",
        exit_on_error=False
    ):
        pass
    else:
        print_warning("Run 'isort agentfit/ tests/ examples/' to fix imports")
    
    # flake8 linting
    if run_command(
        [sys.executable, '-m', 'flake8', 'agentfit/', '--max-line-length=100'],
        "Linting passed",
        exit_on_error=False
    ):
        pass
    else:
        print_warning("Fix linting errors above")
    
    # 6. Type checking
    print_header("6. Type Checking")
    if run_command(
        [sys.executable, '-m', 'mypy', 'agentfit/', '--ignore-missing-imports'],
        "Type checking passed",
        exit_on_error=False
    ):
        pass
    else:
        print_warning("Fix type errors above")
    
    # 7. Test specific modules
    print_header("7. Testing Individual Modules")
    test_modules = [
        'tests/test_protocol.py',
        'tests/test_adapters.py',
        'tests/test_dimensions.py',
        'tests/test_evaluator.py',
        'tests/test_bnp.py',
    ]
    
    for test_module in test_modules:
        module_name = Path(test_module).stem
        if run_command(
            [sys.executable, '-m', 'pytest', test_module, '-v'],
            f"{module_name} tests passed",
            exit_on_error=False
        ):
            pass
        else:
            all_passed = False
    
    # 8. Test examples (if they have tests)
    print_header("8. Verifying Examples")
    example_files = [
        'examples/custom_adapter_example.py',
    ]
    
    for example_file in example_files:
        if Path(example_file).exists():
            print(f"Found: {example_file}")
    
    # 9. Summary
    print_header("Test Summary")
    
    if all_passed:
        print_success("All tests passed!")
        print(f"\n{Colors.GREEN}Ready to commit and push!{Colors.RESET}")
        return 0
    else:
        print_error("Some tests failed. Please review above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
