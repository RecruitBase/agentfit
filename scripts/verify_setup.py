#!/usr/bin/env python3
"""Verify AgentFit installation and setup.

This script checks:
1. Python version
2. All dependencies are installed
3. AgentFit package is properly installed
4. All modules can be imported
5. Basic functionality works
"""
import sys
from pathlib import Path


def print_section(title):
    """Print a section header."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def check_python_version():
    """Check Python version."""
    print_section("Checking Python Version")
    version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    print(f"Python version: {version}")
    
    if sys.version_info >= (3, 10):
        print("✓ Python version is compatible (3.10+)")
        return True
    else:
        print("✗ Python 3.10+ required")
        return False


def check_dependencies():
    """Check if all dependencies are installed."""
    print_section("Checking Dependencies")
    
    dependencies = {
        'pydantic': 'Pydantic (data validation)',
        'click': 'Click (CLI framework)',
        'loguru': 'Loguru (logging)',
        'markdown': 'Markdown (parsing)',
        'yaml': 'YAML (configuration)',
    }
    
    all_found = True
    for package, description in dependencies.items():
        try:
            __import__(package)
            print(f"✓ {description}")
        except ImportError:
            print(f"✗ {description} - NOT FOUND")
            all_found = False
    
    return all_found


def check_agentfit_import():
    """Check if AgentFit can be imported."""
    print_section("Checking AgentFit Import")
    
    try:
        import agentfit
        print(f"✓ AgentFit imported successfully")
        print(f"  Location: {agentfit.__file__}")
        return True
    except ImportError as e:
        print(f"✗ Failed to import agentfit: {e}")
        return False


def check_protocol():
    """Check Protocol module."""
    print_section("Checking Universal Agent Protocol")
    
    try:
        from agentfit.protocol import (
            UniversalAgentProtocol,
            Message,
            MessageRole,
            ToolCall,
            ToolResult,
            ExecutionResult,
        )
        print("✓ Protocol module imports successful")
        print("  - UniversalAgentProtocol")
        print("  - Message, MessageRole")
        print("  - ToolCall, ToolResult")
        print("  - ExecutionResult")
        return True
    except Exception as e:
        print(f"✗ Protocol module error: {e}")
        return False


def check_adapters():
    """Check Adapter modules."""
    print_section("Checking Adapters")
    
    try:
        from agentfit.adapters import (
            OpenAIAdapter,
            AnthropicAdapter,
            GoogleAgentKitAdapter,
            GenericAdapter,
            AgentAdapterRegistry,
        )
        print("✓ Adapter modules import successful")
        print("  - OpenAIAdapter")
        print("  - AnthropicAdapter")
        print("  - GoogleAgentKitAdapter")
        print("  - GenericAdapter")
        print("  - AgentAdapterRegistry")
        return True
    except Exception as e:
        print(f"✗ Adapter module error: {e}")
        return False


def check_dimensions():
    """Check Dimension modules."""
    print_section("Checking Evaluation Dimensions")
    
    dimensions_to_check = [
        ('TaskCompetence', 'task_competence'),
        ('ToolUse', 'tool_use'),
        ('AutonomyEscalation', 'autonomy_escalation'),
        ('SafetyAlignment', 'safety_alignment'),
        ('ComplianceAuditability', 'compliance_auditability'),
        ('OperationalPerformance', 'operational_performance'),
        ('DeploymentCompatibility', 'deployment_compatibility'),
    ]
    
    all_found = True
    for class_name, module_name in dimensions_to_check:
        try:
            if class_name == 'TaskCompetence':
                from agentfit.dimensions.task_competence import TaskCompetence as DimClass
            elif class_name == 'ToolUse':
                from agentfit.dimensions.tool_use import ToolUse as DimClass
            elif class_name == 'AutonomyEscalation':
                from agentfit.dimensions.autonomy_escalation import AutonomyEscalation as DimClass
            elif class_name == 'SafetyAlignment':
                from agentfit.dimensions.safety_alignment import SafetyAlignment as DimClass
            elif class_name == 'ComplianceAuditability':
                from agentfit.dimensions.compliance_auditability import ComplianceAuditability as DimClass
            elif class_name == 'OperationalPerformance':
                from agentfit.dimensions.operational_performance import OperationalPerformance as DimClass
            elif class_name == 'DeploymentCompatibility':
                from agentfit.dimensions.deployment_compatibility import DeploymentCompatibility as DimClass
            
            # Verify it's a dimension
            dim_instance = DimClass()
            print(f"✓ {class_name} ({module_name})")
        except Exception as e:
            print(f"✗ {class_name} - {str(e)[:50]}")
            all_found = False
    
    return all_found


def check_core():
    """Check Core modules."""
    print_section("Checking Core Modules")
    
    try:
        from agentfit.core.evaluator import Evaluator, EvaluationRequest, EvaluationResult
        from agentfit.core.dimension import Dimension, DimensionRegistry
        print("✓ Core modules import successful")
        print("  - Evaluator, EvaluationRequest, EvaluationResult")
        print("  - Dimension, DimensionRegistry")
        return True
    except Exception as e:
        print(f"✗ Core module error: {e}")
        return False


def check_bnp():
    """Check BNP modules."""
    print_section("Checking Business Need Profile")
    
    try:
        from agentfit.bnp.schema import BNPProfile, Domain
        from agentfit.bnp.parser import BNPParser
        print("✓ BNP modules import successful")
        print("  - BNPProfile, Domain")
        print("  - BNPParser")
        return True
    except Exception as e:
        print(f"✗ BNP module error: {e}")
        return False


def check_cli():
    """Check CLI module."""
    print_section("Checking CLI Module")
    
    try:
        from agentfit.cli import main
        print("✓ CLI module import successful")
        print("  - main function")
        return True
    except Exception as e:
        print(f"✗ CLI module error: {e}")
        return False


def check_test_dependencies():
    """Check test dependencies."""
    print_section("Checking Test Dependencies")
    
    test_deps = {
        'pytest': 'pytest (testing framework)',
        'pytest_asyncio': 'pytest-asyncio (async testing)',
    }
    
    all_found = True
    for package, description in test_deps.items():
        try:
            __import__(package)
            print(f"✓ {description}")
        except ImportError:
            print(f"⚠ {description} - NOT FOUND (optional)")
    
    return True


def check_directory_structure():
    """Check project directory structure."""
    print_section("Checking Directory Structure")
    
    required_dirs = [
        'agentfit',
        'agentfit/protocol',
        'agentfit/adapters',
        'agentfit/dimensions',
        'agentfit/core',
        'agentfit/bnp',
        'tests',
        'examples',
        'docs',
    ]
    
    all_found = True
    for dir_name in required_dirs:
        if Path(dir_name).is_dir():
            print(f"✓ {dir_name}/")
        else:
            print(f"✗ {dir_name}/ - NOT FOUND")
            all_found = False
    
    return all_found


def main():
    """Run all checks."""
    print("\n" + "="*70)
    print("  AgentFit Setup Verification")
    print("="*70)
    
    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", check_dependencies),
        ("Directory Structure", check_directory_structure),
        ("AgentFit Import", check_agentfit_import),
        ("Protocol Module", check_protocol),
        ("Adapter Module", check_adapters),
        ("Dimension Module", check_dimensions),
        ("Core Module", check_core),
        ("BNP Module", check_bnp),
        ("CLI Module", check_cli),
        ("Test Dependencies", check_test_dependencies),
    ]
    
    results = {}
    for check_name, check_func in checks:
        try:
            results[check_name] = check_func()
        except Exception as e:
            print(f"\n✗ {check_name} failed: {e}")
            results[check_name] = False
    
    # Summary
    print_section("Setup Verification Summary")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    print(f"Passed: {passed}/{total}")
    print()
    
    for check_name, result in results.items():
        status = "✓" if result else "✗"
        print(f"{status} {check_name}")
    
    print("\n" + "="*70)
    
    if all(results.values()):
        print("✓ All checks passed! AgentFit is ready to use.\n")
        print("Next steps:")
        print("  1. Run tests: python scripts/run_tests.py")
        print("  2. Try examples: python examples/custom_adapter_example.py")
        print("  3. Read docs: docs/QUICK_START.md")
        return 0
    else:
        print("✗ Some checks failed. Please fix the issues above.\n")
        return 1


if __name__ == '__main__':
    sys.exit(main())
