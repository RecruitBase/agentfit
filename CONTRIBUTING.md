# Contributing to AgentFit

Thank you for your interest in contributing to AgentFit! This document provides guidelines and instructions for contributing.

## Code of Conduct

We are committed to providing a welcoming and inspiring community for all. Please read and follow our Code of Conduct.

## Getting Started

### Prerequisites
- Python 3.10 or higher
- Git
- pip or uv package manager

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/recruitbase/agentfit.git
cd agentfit

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode with all dependencies
pip install -e ".[all]"

# Install pre-commit hooks
pre-commit install
```

### Verify Setup

```bash
# Run tests
pytest tests/ -v

# Check code style
flake8 agentfit/

# Format code
black agentfit/
isort agentfit/
```

## Development Workflow

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
```

Branch naming conventions:
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation updates
- `test/` - Test additions
- `refactor/` - Code refactoring
- `perf/` - Performance improvements

### 2. Make Your Changes

Write clean, well-documented code following the project standards.

### 3. Write Tests

All new features must include tests:

```bash
# Add tests to tests/
# Run tests to verify
pytest tests/ -v

# Check coverage
pytest tests/ --cov=agentfit
```

### 4. Update Documentation

- Update relevant docs in `docs/`
- Update docstrings in code
- Update `README.md` if needed
- Add entry to `CHANGELOG.md`

### 5. Code Quality Checks

```bash
# Format code
black agentfit/ tests/ examples/
isort agentfit/ tests/ examples/

# Lint
flake8 agentfit/ tests/

# Type check
mypy agentfit/

# Run pre-commit
pre-commit run --all-files
```

### 6. Commit and Push

```bash
git add .
git commit -m "Clear, descriptive commit message"
git push origin feature/your-feature-name
```

Commit message format:
```
Type: Short description (50 chars max)

Longer explanation if needed (wrap at 72 chars).
Explain what and why, not how.

Closes #123
```

Types:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation
- `style:` - Code style (no logic changes)
- `refactor:` - Code refactoring
- `test:` - Test additions/changes
- `perf:` - Performance improvements
- `chore:` - Build, dependencies, etc.

### 7. Create Pull Request

1. Go to GitHub and create a PR
2. Fill out the PR template
3. Link related issues
4. Wait for review

## Types of Contributions

### Adding a New Dimension

1. Create `agentfit/dimensions/your_dimension.py`
2. Implement the `Dimension` base class
3. Add tests to `tests/test_dimensions.py`
4. Register in `agentfit/__init__.py`
5. Update documentation

Example structure:
```python
from agentfit.core.dimension import Dimension, DimensionResult


class YourDimension(Dimension):
    """Your dimension description."""
    
    name = "your_dimension"
    description = "..."
    weight = 0.14  # Keep total weights = 1.0
    
    def get_sub_metrics(self) -> dict[str, float]:
        """Return available sub-metrics."""
        return {
            "metric1": 0.0,
            "metric2": 0.0,
        }
    
    async def evaluate(self, request) -> DimensionResult:
        """Evaluate this dimension."""
        # Implementation
        return DimensionResult(
            dimension_name=self.name,
            score=0.85,
            details={"metric1": 0.9, "metric2": 0.8}
        )
```

### Creating a New Adapter

1. Create `agentfit/adapters/your_adapter.py`
2. Inherit from `UniversalAgentProtocol`
3. Implement required methods
4. Add tests to `tests/test_adapters.py`
5. Register in `agentfit/adapters/__init__.py`

### Improving Documentation

- Update existing docs in `docs/`
- Add examples in `examples/`
- Improve docstrings
- Create tutorials

## Code Style Guidelines

### Python Style

Follow PEP 8:

```python
# Good: Clear variable names, proper spacing
def evaluate_task_competence(messages: list[Message]) -> DimensionResult:
    """Evaluate task competence dimension.
    
    Args:
        messages: List of conversation messages
        
    Returns:
        DimensionResult with score and details
    """
    # Implementation
    return DimensionResult(...)


# Class structure
class TaskCompetence(Dimension):
    """Task competence dimension."""
    
    name = "task_competence"
    weight = 0.15
    
    def __init__(self):
        """Initialize dimension."""
        super().__init__()
    
    async def evaluate(self, request) -> DimensionResult:
        """Evaluate dimension."""
        # Implementation
        pass
```

### Type Hints

Use type hints everywhere:

```python
# Good
def process_message(msg: Message, tools: list[Tool]) -> str:
    ...

# Avoid
def process_message(msg, tools):
    ...
```

### Docstrings

Use Google-style docstrings:

```python
def evaluate(self, request: EvaluationRequest) -> DimensionResult:
    """Evaluate the dimension.
    
    Long description with more details about what this does.
    
    Args:
        request: Evaluation request containing agent and scenarios
        
    Returns:
        DimensionResult with computed score and details
        
    Raises:
        ValueError: If request is invalid
    """
    pass
```

## Testing Guidelines

### Test Coverage

- Aim for >80% code coverage
- Test both success and failure paths
- Test edge cases

### Writing Tests

```python
import pytest
from agentfit.dimensions.task_competence import TaskCompetence


class TestTaskCompetence:
    """Test TaskCompetence dimension."""
    
    def test_initialization(self):
        """Test dimension initializes correctly."""
        dim = TaskCompetence()
        assert dim.name == "task_competence"
        assert dim.weight == 0.15
    
    @pytest.mark.asyncio
    async def test_evaluation(self):
        """Test evaluation returns valid result."""
        dim = TaskCompetence()
        # Create test request
        result = await dim.evaluate(request)
        assert 0 <= result.score <= 1
    
    def test_invalid_input_raises_error(self):
        """Test error handling for invalid input."""
        with pytest.raises(ValueError):
            TaskCompetence().evaluate(None)
```

### Running Tests

```bash
# All tests
pytest tests/ -v

# Specific file
pytest tests/test_dimensions.py -v

# Specific test
pytest tests/test_dimensions.py::TestTaskCompetence::test_initialization -v

# With coverage
pytest tests/ --cov=agentfit --cov-report=html

# Show slowest tests
pytest tests/ --durations=10
```

## Documentation Standards

### README
- Keep examples current
- Update version numbers
- Test all code examples

### Docstrings
- Document all public classes and methods
- Include type hints
- Provide examples when helpful
- Explain parameters and return values

### Comments
- Explain why, not what
- Keep comments up to date
- Remove commented-out code

## Performance Guidelines

- Profile before optimizing
- Benchmark critical paths
- Document performance implications
- Avoid premature optimization

## Security Guidelines

- Never commit API keys or secrets
- Use environment variables for configuration
- Validate all inputs
- Follow OWASP guidelines
- Report security issues privately

## Release Process

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Create release notes
4. Tag release: `git tag v0.2.0`
5. Build and test: `python -m build`
6. Upload to TestPyPI: `twine upload --repository testpypi dist/*`
7. Test installation
8. Upload to PyPI: `twine upload dist/*`
9. Create GitHub release

See [docs/PUBLISHING.md](docs/PUBLISHING.md) for detailed instructions.

## Review Process

PRs will be reviewed for:
- Code quality and style
- Test coverage
- Documentation completeness
- Adherence to project standards
- Performance implications

Reviewers may request changes. Please address feedback:

```bash
# Make requested changes
# Commit changes
git add .
git commit -m "Address review feedback"
git push origin feature/your-feature-name
```

## Troubleshooting

### Tests fail locally but pass in CI
- Check Python version
- Check for platform-specific issues
- Try in clean virtual environment

### Merge conflicts
```bash
git fetch origin
git rebase origin/main
# Fix conflicts
git add .
git rebase --continue
git push origin feature/your-feature-name --force-with-lease
```

### Pre-commit hooks fail
```bash
# Check what's failing
pre-commit run --all-files

# Format code
black agentfit/
isort agentfit/

# Try again
pre-commit run --all-files
```

## Getting Help

- **Questions**: Create a [GitHub Discussion](https://github.com/recruitbase/agentfit/discussions)
- **Issues**: Check [existing issues](https://github.com/recruitbase/agentfit/issues)
- **Documentation**: See [docs/](docs/) directory
- **Examples**: See [examples/](examples/) directory

## Recognition

Contributors will be recognized in:
- `CONTRIBUTORS.md`
- Release notes
- GitHub contributors page

Thank you for contributing to AgentFit!
