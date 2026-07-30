# AgentFit Documentation Index

Welcome to AgentFit! This page helps you navigate all documentation and resources.

## 📖 Start Here

### New Users
1. **[README.md](../README.md)** - Project overview, features, and quick installation
2. **[GETTING_STARTED.md](../GETTING_STARTED.md)** - 5-minute setup and first evaluation
3. **[QUICK_START.md](QUICK_START.md)** - Hands-on walkthrough with code examples

### Want to Test Your Own Agent?
- **[TEST_YOUR_AGENT.md](TEST_YOUR_AGENT.md)** - Quick-test an OpenAI-compatible endpoint + access token, or build/self-host an agent (Sim, Dify, Flowise) and evaluate it

### Want to Run Tests?
- **[TESTING.md](TESTING.md)** - Complete testing guide (for AgentFit itself, not your agent)
- Run `python scripts/run_tests.py` for comprehensive test suite

### Want to Publish to PyPI?
- **[PUBLISHING.md](PUBLISHING.md)** - Step-by-step PyPI publishing guide
- **[COMPLETE_SETUP.md](../COMPLETE_SETUP.md)** - Project status and publishing details

## 📚 Comprehensive Guides

### Understanding AgentFit
- **[UNIVERSAL_AGENT_PROTOCOL.md](UNIVERSAL_AGENT_PROTOCOL.md)** - Protocol specification and adapter development
- **[EVALUATION_DIMENSIONS.md](EVALUATION_DIMENSIONS.md)** - Deep dive into all 7 evaluation dimensions
- **[IMPLEMENTATION_SUMMARY.md](../IMPLEMENTATION_SUMMARY.md)** - Technical architecture overview

### Contributing & Development
- **[CONTRIBUTING.md](../CONTRIBUTING.md)** - Development workflow and contribution guidelines
- **[COMPLETE_SETUP.md](../COMPLETE_SETUP.md)** - Project statistics and development setup

## 🔧 How-To Guides

### Getting Started
- How to install AgentFit → [GETTING_STARTED.md](../GETTING_STARTED.md#installation)
- How to run your first evaluation → [QUICK_START.md](QUICK_START.md)
- How to verify installation → `python scripts/verify_setup.py`

### Working with Adapters
- How to use OpenAI adapter → [examples/evaluate_openai_agent.py](../examples/evaluate_openai_agent.py)
- How to use Anthropic adapter → [examples/evaluate_anthropic_agent.py](../examples/evaluate_anthropic_agent.py)
- How to create a custom adapter → [examples/custom_adapter_example.py](../examples/custom_adapter_example.py)
- How to batch evaluate agents → [examples/batch_evaluation.py](../examples/batch_evaluation.py)

### Testing & Quality
- How to run tests → [TESTING.md](TESTING.md#quick-start)
- How to write new tests → [TESTING.md](TESTING.md#writing-new-tests)
- How to check code coverage → [TESTING.md](TESTING.md#coverage-requirements)

### Publishing & Deployment
- How to publish to PyPI → [PUBLISHING.md](PUBLISHING.md)
- How to automate publishing → [PUBLISHING.md](PUBLISHING.md#automated-publishing-with-github-actions)
- How to maintain the package → [PUBLISHING.md](PUBLISHING.md#maintaining-the-package)

## 📁 Documentation Structure

```
docs/
├── INDEX.md (this file)
├── QUICK_START.md - Get running in 5 minutes
├── UNIVERSAL_AGENT_PROTOCOL.md - Protocol specs
├── EVALUATION_DIMENSIONS.md - Dimension details
├── TESTING.md - Testing guide
├── PUBLISHING.md - PyPI publishing

../
├── README.md - Project overview
├── GETTING_STARTED.md - Setup and intro
├── COMPLETE_SETUP.md - Project status
├── CONTRIBUTING.md - Developer guide
├── IMPLEMENTATION_SUMMARY.md - Technical details
├── CHANGELOG.md - Release history
├── LICENSE - Business Source License 1.1 (BUSL-1.1)

examples/
├── evaluate_openai_agent.py
├── evaluate_anthropic_agent.py
├── custom_adapter_example.py
└── batch_evaluation.py

scripts/
├── run_tests.py - Comprehensive test runner
└── verify_setup.py - Setup verification
```

## 🎯 Quick Navigation by Task

### I want to...

**Evaluate an agent with AgentFit**
→ [QUICK_START.md](QUICK_START.md)

**Use a specific adapter (OpenAI, Anthropic, etc.)**
→ [examples/evaluate_*_agent.py](../examples/)

**Create a custom adapter for my framework**
→ [examples/custom_adapter_example.py](../examples/custom_adapter_example.py) + [UNIVERSAL_AGENT_PROTOCOL.md](UNIVERSAL_AGENT_PROTOCOL.md)

**Run tests and verify quality**
→ `python scripts/run_tests.py` or [TESTING.md](TESTING.md)

**Publish AgentFit to PyPI**
→ [PUBLISHING.md](PUBLISHING.md)

**Understand the evaluation framework**
→ [EVALUATION_DIMENSIONS.md](EVALUATION_DIMENSIONS.md)

**Contribute to AgentFit**
→ [CONTRIBUTING.md](../CONTRIBUTING.md)

**Set up development environment**
→ [GETTING_STARTED.md](../GETTING_STARTED.md#installation)

**Understand the architecture**
→ [COMPLETE_SETUP.md](../COMPLETE_SETUP.md#-architecture)

## 📊 Documentation Statistics

| Document | Lines | Focus |
|----------|-------|-------|
| README.md | 305 | Overview & features |
| GETTING_STARTED.md | 469 | Setup & intro |
| QUICK_START.md | 398 | First evaluation |
| UNIVERSAL_AGENT_PROTOCOL.md | 425 | Protocol spec |
| EVALUATION_DIMENSIONS.md | 446 | Dimension details |
| TESTING.md | 375 | Testing guide |
| PUBLISHING.md | 266 | PyPI publishing |
| CONTRIBUTING.md | 436 | Development |
| COMPLETE_SETUP.md | 550 | Project status |
| **Total** | **3,670** | **Complete docs** |

## 🔑 Key Concepts

### Universal Agent Protocol
- Framework-agnostic protocol for evaluating any agent
- Works with OpenAI, Anthropic, Google, or custom agents
- Minimal implementation overhead (3-4 methods)

### 7 Evaluation Dimensions
1. **Task Competence** (15%)
2. **Tool Use & Integration** (15%)
3. **Autonomy & Escalation** (15%)
4. **Safety & Alignment** (15%)
5. **Compliance & Auditability** (15%)
6. **Operational Performance** (10%)
7. **Deployment Compatibility** (15%)

### Business Need Profile (BNP)
- Define organization-specific requirements in markdown
- Weight dimensions based on priorities
- Specify compliance and performance requirements
- Domain-specific evaluation scenarios

## 🚀 Quick Commands

```bash
# Install
pip install -e ".[all]"

# Verify setup
python scripts/verify_setup.py

# Run tests
python scripts/run_tests.py

# Run example
python examples/custom_adapter_example.py

# Build for PyPI
python -m build

# Publish (after testing)
twine upload dist/*
```

## 📞 Need Help?

1. **First time?** → [GETTING_STARTED.md](../GETTING_STARTED.md)
2. **Setup issue?** → Run `python scripts/verify_setup.py`
3. **Want to evaluate?** → [QUICK_START.md](QUICK_START.md)
4. **Creating adapter?** → [UNIVERSAL_AGENT_PROTOCOL.md](UNIVERSAL_AGENT_PROTOCOL.md)
5. **Testing?** → [TESTING.md](TESTING.md)
6. **Publishing?** → [PUBLISHING.md](PUBLISHING.md)
7. **Contributing?** → [CONTRIBUTING.md](../CONTRIBUTING.md)

## 📌 Useful Links

- **GitHub**: https://github.com/RecruitBase/agentfit
- **PyPI**: https://pypi.org/project/agentfit
- **Issues**: https://github.com/RecruitBase/agentfit/issues
- **Discussions**: https://github.com/RecruitBase/agentfit/discussions

## ✅ Checklist for Getting Started

- [ ] Read README.md
- [ ] Read GETTING_STARTED.md
- [ ] Run `python scripts/verify_setup.py`
- [ ] Run tests: `python scripts/run_tests.py`
- [ ] Try an example: `python examples/custom_adapter_example.py`
- [ ] Read QUICK_START.md
- [ ] Create your own evaluation script
- [ ] (Optional) Read UNIVERSAL_AGENT_PROTOCOL.md to create custom adapter
- [ ] (Optional) Read CONTRIBUTING.md if you want to contribute

---

## Document Reading Order

### For New Users (Recommended Path)
1. README.md (5 min)
2. GETTING_STARTED.md (10 min)
3. QUICK_START.md (15 min)
4. Run examples (10 min)
5. Try your own agent (30 min)

### For Developers (Recommended Path)
1. README.md (5 min)
2. CONTRIBUTING.md (15 min)
3. COMPLETE_SETUP.md (10 min)
4. UNIVERSAL_AGENT_PROTOCOL.md (20 min)
5. TESTING.md (15 min)
6. Create custom adapter (30 min)

### For DevOps/Publishers (Recommended Path)
1. README.md (5 min)
2. GETTING_STARTED.md - Installation section (5 min)
3. COMPLETE_SETUP.md (15 min)
4. PUBLISHING.md (20 min)
5. Run full test suite (10 min)
6. Publish to TestPyPI (10 min)
7. Publish to PyPI (5 min)

---

Happy learning! 🎓
