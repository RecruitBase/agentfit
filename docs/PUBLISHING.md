# Publishing AgentFit to PyPI

This guide explains how to package and publish AgentFit to PyPI so others can install it with `pip install agentfit`.

## Prerequisites

You'll need:
- A PyPI account (create one at https://pypi.org/account/register/)
- A TestPyPI account (for testing, at https://test.pypi.org/account/register/)
- Python 3.10 or higher
- `build` and `twine` packages

## Step 1: Install Build Tools

```bash
pip install build twine
```

## Step 2: Verify Package Structure

Ensure your package structure looks like this:
```
agentfit/
├── agentfit/
│   ├── __init__.py
│   ├── protocol/
│   ├── adapters/
│   ├── core/
│   ├── dimensions/
│   ├── bnp/
│   ├── cli.py
│   └── ...
├── tests/
├── examples/
├── docs/
├── pyproject.toml
├── README.md
└── LICENSE
```

## Step 3: Update Version Number

Edit `pyproject.toml` and update the version:
```toml
[project]
version = "0.2.0"  # Increment this
```

Follow semantic versioning: MAJOR.MINOR.PATCH

## Step 4: Test Locally

### Test installation from local build:
```bash
# Build the package
python -m build

# Install locally in editable mode
pip install -e .

# Test imports
python -c "import agentfit; print(agentfit.__version__)"
```

### Run the test suite:
```bash
pytest tests/ -v
```

## Step 5: Prepare for Publishing

### Create/update important files:

1. **README.md** - Project overview (already created)
2. **LICENSE** - Apache 2.0 license
   ```bash
   curl -o LICENSE https://www.apache.org/licenses/LICENSE-2.0.txt
   ```
3. **CHANGELOG.md** - Document version changes

### Verify pyproject.toml:
- Version number is updated
- Description is clear and concise
- All dependencies are correct
- Authors and email are accurate
- URLs point to correct repositories

## Step 6: Test on TestPyPI (Recommended)

TestPyPI is a practice ground before publishing to the real PyPI.

### Create ~/.pypirc config file:
```ini
[distutils]
index-servers =
    pypi
    testpypi

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-XXXXXXXXXXXXXXXXXXXX

[pypi]
repository = https://upload.pypi.org/legacy/
username = __token__
password = pypi-XXXXXXXXXXXXXXXXXXXX
```

Get your API token from: https://test.pypi.org/manage/account/token/

### Build the distribution:
```bash
python -m build
```

This creates:
- `dist/agentfit-0.2.0.tar.gz` (source distribution)
- `dist/agentfit-0.2.0-py3-none-any.whl` (wheel)

### Upload to TestPyPI:
```bash
twine upload --repository testpypi dist/*
```

### Test installation from TestPyPI:
```bash
# In a new virtual environment
python -m venv test_env
source test_env/bin/activate  # On Windows: test_env\Scripts\activate

# Install from TestPyPI
pip install --index-url https://test.pypi.org/simple/ agentfit

# Test it works
python -c "from agentfit import Evaluator; print('Success!')"
```

## Step 7: Publish to Real PyPI

Once testing is successful:

### Generate API token:
1. Go to https://pypi.org/manage/account/token/
2. Create a new token with scope "Entire account"
3. Update ~/.pypirc with the token

### Upload to PyPI:
```bash
twine upload dist/*
```

### Verify publication:
```bash
# Check PyPI page
# https://pypi.org/project/agentfit/

# Install from real PyPI
pip install agentfit

# Verify installation
agentfit --version
```

## Step 8: Create GitHub Release

After publishing to PyPI:

```bash
# Create git tag
git tag v0.2.0
git push origin v0.2.0

# Create GitHub release on: https://github.com/RecruitBase/agentfit/releases
# Include:
# - Release notes
# - Link to PyPI
# - changelog
```

## Step 9: Update Documentation

- Update docs site with new version
- Create release notes
- Update installation instructions to reference PyPI
- Add to changelog

## Troubleshooting

### Upload fails with "Invalid distribution"
- Check wheel compatibility: `twine check dist/*`
- Ensure all dependencies are properly specified
- Verify Python version support in classifiers

### Module not found after pip install
- Check package name matches `[project] name` in pyproject.toml
- Verify `__init__.py` files exist in all packages
- Check `[tool.setuptools] packages` config

### Version conflicts
- Increment version in pyproject.toml
- Rebuild with `python -m build`
- Delete old `dist/` before rebuilding

## Automated Publishing with GitHub Actions

Create `.github/workflows/publish.yml`:

```yaml
name: Publish to PyPI

on:
  release:
    types: [created]

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install build tools
      run: |
        python -m pip install --upgrade pip
        pip install build twine
    
    - name: Build distribution
      run: python -m build
    
    - name: Publish to PyPI
      env:
        TWINE_USERNAME: __token__
        TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
      run: twine upload dist/*
```

Then set `PYPI_API_TOKEN` in GitHub Settings > Secrets.

## Maintaining the Package

### For each new release:

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Run tests: `pytest tests/ -v`
4. Update documentation if needed
5. Build: `python -m build`
6. Upload to TestPyPI first
7. Test installation from TestPyPI
8. Upload to PyPI
9. Create GitHub release
10. Announce on social media/forums

## Additional Resources

- [PyPI Help](https://pypi.org/help/)
- [Twine Documentation](https://twine.readthedocs.io/)
- [setuptools Documentation](https://setuptools.pypa.io/)
- [PEP 427 - Wheel Binary Package Format](https://www.python.org/dev/peps/pep-0427/)
- [PEP 440 - Version Identification](https://www.python.org/dev/peps/pep-0440/)
