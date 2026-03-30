# Testing Guide for AgentFit

This guide explains how to run tests, create new tests, and ensure your contributions meet quality standards.

## Quick Start

### Install test dependencies:
```bash
pip install -e ".[dev]"
```

### Run all tests:
```bash
pytest tests/ -v
```

### Run tests with coverage:
```bash
pytest tests/ --cov=agentfit --cov-report=html
```

## Test Structure

AgentFit's test suite is organized by module:

```
tests/
├── __init__.py
├── test_protocol.py          # Protocol and message format tests
├── test_adapters.py          # Adapter integration tests
├── test_dimensions.py        # Evaluation dimension tests
├── test_evaluator.py         # Evaluator core functionality
└── test_bnp.py              # BNP parsing and validation
```

## Running Specific Tests

### Run a single test file:
```bash
pytest tests/test_protocol.py -v
```

### Run a specific test class:
```bash
pytest tests/test_protocol.py::TestMessage -v
```

### Run a specific test:
```bash
pytest tests/test_protocol.py::TestMessage::test_message_creation -v
```

### Run tests matching a pattern:
```bash
pytest tests/ -k "protocol" -v
```

### Run with markers:
```bash
pytest tests/ -m "slow" -v      # Run only marked slow tests
pytest tests/ -m "not slow" -v  # Skip slow tests
```

## Test Categories

### 1. Unit Tests
Tests for individual components in isolation.

**Location:** `tests/test_*.py` (most tests)

**Example:**
```python
def test_message_creation(self):
    """Test creating a message."""
    msg = Message(
        role=MessageRole.USER,
        content="Hello, agent!"
    )
    assert msg.role == MessageRole.USER
    assert msg.content == "Hello, agent!"
```

### 2. Integration Tests
Tests that verify components work together.

**Location:** `tests/test_evaluator.py`, `tests/test_bnp.py`

**Example:**
```python
@pytest.mark.asyncio
async def test_evaluator_basic_evaluation(self):
    """Test basic evaluation with multiple dimensions."""
    evaluator = Evaluator()
    request = EvaluationRequest(
        agent_id="test-agent",
        dimensions=["task_competence", "tool_use"]
    )
    result = await evaluator.evaluate(request)
    assert result is not None
    assert result.agent_id == "test-agent"
```

### 3. Async Tests
Tests for async code using pytest-asyncio.

**Mark with:** `@pytest.mark.asyncio`

**Example:**
```python
@pytest.mark.asyncio
async def test_async_evaluation(self):
    evaluator = Evaluator()
    result = await evaluator.evaluate(request)
    assert result is not None
```

## Writing New Tests

### Test naming conventions:
- Test files: `test_<module_name>.py`
- Test classes: `Test<Feature>`
- Test methods: `test_<specific_behavior>`

### Template:
```python
"""Tests for module_name."""
import pytest
from agentfit.module import ClassName


class TestFeature:
    """Test Feature class."""
    
    def test_basic_behavior(self):
        """Test basic functionality."""
        instance = ClassName()
        result = instance.method()
        assert result == expected_value
    
    def test_error_handling(self):
        """Test error handling."""
        with pytest.raises(ValueError):
            ClassName(invalid_param="bad")
    
    @pytest.mark.asyncio
    async def test_async_behavior(self):
        """Test async functionality."""
        result = await async_function()
        assert result is not None
```

### Best practices:

1. **One assertion per test (when possible)**
   ```python
   # Good
   def test_score_validation(self):
       assert 0 <= DimensionResult(dimension_name="test", score=0.75).score <= 1
   
   # Okay when testing related assertions
   def test_message_creation(self):
       msg = Message(role=MessageRole.USER, content="Test")
       assert msg.role == MessageRole.USER
       assert msg.content == "Test"
   ```

2. **Use descriptive names**
   ```python
   # Good
   def test_invalid_score_above_one_raises_value_error(self):
       with pytest.raises(ValueError):
           DimensionResult(dimension_name="test", score=1.5)
   
   # Poor
   def test_score(self):
       ...
   ```

3. **Test both success and failure cases**
   ```python
   def test_adapter_registration_success(self):
       registry = AgentAdapterRegistry()
       registry.register(OpenAIAdapter)
       assert "openai" in registry._adapters
   
   def test_adapter_registration_duplicate_raises_error(self):
       registry = AgentAdapterRegistry()
       registry.register(OpenAIAdapter)
       with pytest.raises(ValueError):
           registry.register(OpenAIAdapter)  # Duplicate
   ```

4. **Use fixtures for common setup**
   ```python
   @pytest.fixture
   def sample_message():
       return Message(
           role=MessageRole.USER,
           content="Test message"
       )
   
   def test_message_serialization(self, sample_message):
       data = sample_message.model_dump()
       assert data["content"] == "Test message"
   ```

5. **Mock external dependencies**
   ```python
   from unittest.mock import Mock, patch
   
   @patch('agentfit.adapters.openai_adapter.OpenAI')
   def test_openai_adapter_with_mock(self, mock_openai):
       mock_openai.return_value.chat.completions.create.return_value = "response"
       adapter = OpenAIAdapter(config={})
       # Test with mocked OpenAI
   ```

## Coverage Requirements

Maintain >80% code coverage:

```bash
# Generate coverage report
pytest tests/ --cov=agentfit --cov-report=term-missing --cov-report=html

# View detailed report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

## Performance Testing

For performance-critical code, use pytest benchmarks:

```bash
pip install pytest-benchmark
```

```python
def test_evaluation_performance(benchmark):
    evaluator = Evaluator()
    result = benchmark(
        evaluator.evaluate,
        EvaluationRequest(agent_id="test")
    )
    assert result is not None
```

## Continuous Integration

Tests run automatically on:
- Every push to main branch
- Every pull request
- Every scheduled run (daily)

Configuration in `.github/workflows/tests.yml`

## Testing Adapters

### Testing a new adapter:

```python
from agentfit.protocol import UniversalAgentProtocol, Message, MessageRole
from agentfit.adapters import AgentAdapterRegistry


class TestMyAdapter:
    """Test custom adapter."""
    
    def test_adapter_initialization(self):
        """Test adapter can be initialized."""
        adapter = MyCustomAdapter(config={"model": "test"})
        assert adapter.config["model"] == "test"
    
    @pytest.mark.asyncio
    async def test_adapter_execution(self):
        """Test adapter can execute messages."""
        adapter = MyCustomAdapter(config={})
        messages = [Message(role=MessageRole.USER, content="Test")]
        result = await adapter.execute(messages)
        assert result.success
        assert result.output is not None
    
    def test_adapter_tool_handling(self):
        """Test adapter handles tools correctly."""
        adapter = MyCustomAdapter(config={})
        tools = [...]  # Your tool definitions
        # Test tool execution
```

### Registering adapter in tests:

```python
from agentfit.adapters import AgentAdapterRegistry

def test_custom_adapter_registration():
    """Test registering custom adapter."""
    registry = AgentAdapterRegistry()
    registry.register(MyCustomAdapter)
    assert registry.get("my_custom") == MyCustomAdapter
```

## Debugging Tests

### Run with verbose output:
```bash
pytest tests/test_file.py -vv
```

### Show print statements:
```bash
pytest tests/test_file.py -s
```

### Drop into debugger on failure:
```bash
pytest tests/test_file.py --pdb
```

### Stop on first failure:
```bash
pytest tests/test_file.py -x
```

### Show slowest tests:
```bash
pytest tests/test_file.py --durations=10
```

## Pre-commit Hooks

Setup automatic testing before commits:

```bash
# Install pre-commit
pip install pre-commit

# Setup hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

Configuration in `.pre-commit-config.yaml`

## Common Issues

### Test fails locally but passes in CI
- Check Python version: `python --version`
- Check dependencies: `pip list | grep agentfit`
- Try in clean environment: `python -m venv test_env`

### Async test hangs
- Ensure `@pytest.mark.asyncio` decorator is present
- Check for missing `await` calls
- Verify event loop is running

### Import errors in tests
- Ensure package is installed: `pip install -e .`
- Check `__init__.py` files exist
- Verify import paths

### Coverage not calculated correctly
- Clear cache: `rm -rf .pytest_cache`
- Reinstall: `pip install -e . --force-reinstall`

## Additional Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://github.com/pytest-dev/pytest-asyncio)
- [unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
- [pytest-benchmark](https://pytest-benchmark.readthedocs.io/)
