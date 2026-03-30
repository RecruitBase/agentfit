# AgentFit: Universal Agent Evaluation Framework

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Tests](https://github.com/recruitbase/agentfit/actions/workflows/tests.yml/badge.svg)](https://github.com/recruitbase/agentfit/actions)

**AgentFit** is an enterprise-grade evaluation framework for AI agents that works with any agent framework or provider. Evaluate OpenAI agents, Anthropic Claude, Google AgentKit, or custom agents using a unified protocol.

## Features

### 🎯 Universal Agent Protocol
- Framework-agnostic protocol for evaluating any agent
- Pre-built adapters for OpenAI, Anthropic, Google AgentKit
- Easy-to-implement interface for custom agent frameworks
- Zero vendor lock-in

### 📊 7 Comprehensive Evaluation Dimensions
1. **Task Competence** (15%) - Ability to understand and execute tasks
2. **Tool Use & Integration** (15%) - Correct tool selection and invocation
3. **Autonomy & Escalation** (15%) - Appropriate independence and escalation handling
4. **Safety & Alignment** (15%) - Safety under adversarial conditions
5. **Compliance & Auditability** (15%) - Regulatory compliance and audit trails
6. **Operational Performance** (10%) - Latency, throughput, and cost efficiency
7. **Deployment Compatibility** (15%) - Infrastructure and deployment readiness

### 🏢 Business-Centric Evaluation
- Define organization-specific requirements via Business Need Profiles (BNPs)
- Weighted dimensions based on your priorities
- Compliance and performance requirements
- Domain-specific test scenarios

### 🔌 Multi-Framework Support
- **Built-in Adapters**: OpenAI, Anthropic, Google AgentKit
- **Custom Adapters**: Implement 3-4 methods to add your own framework
- **No Source Code Changes**: Evaluate agents without modifying them

## Quick Start

### Installation

```bash
# Basic installation
pip install agentfit

# With specific adapter support
pip install agentfit[openai]
pip install agentfit[anthropic]

# With all adapters and dev tools
pip install agentfit[all]
```

### 5-Minute Example

```python
import asyncio
from agentfit.core.evaluator import Evaluator, EvaluationRequest
from agentfit.adapters import OpenAIAdapter
from agentfit.bnp.schema import BNPProfile, Domain


async def main():
    # 1. Define your organization's needs
    bnp_profile = BNPProfile(
        organization_name="My Company",
        industry="Finance",
        agent_domain=Domain.DATA_ANALYSIS,
        required_dimensions=[
            "task_competence",
            "safety_alignment",
            "compliance_auditability"
        ]
    )
    
    # 2. Create adapter for your agent
    adapter = OpenAIAdapter(config={
        "api_key": "your-key",
        "model": "gpt-4-turbo"
    })
    
    # 3. Run evaluation
    evaluator = Evaluator()
    result = await evaluator.evaluate(
        EvaluationRequest(
            agent_id="my-agent-v1",
            agent_adapter=adapter,
            bnp_profile=bnp_profile
        )
    )
    
    # 4. View results
    print(f"Overall Score: {result.overall_score:.1%}")
    for dimension, score in result.dimension_scores.items():
        print(f"  {dimension}: {score:.1%}")


asyncio.run(main())
```

### CLI Usage

```bash
# Evaluate using BNP markdown file
agentfit evaluate \
    --bnp path/to/bnp.md \
    --evals task_competence,tool_use \
    --output results.json \
    --agent openai

# Batch evaluate multiple agents
agentfit batch-evaluate \
    --bnp path/to/bnp.md \
    --agents openai,anthropic,custom \
    --output batch_results.json
```

## Documentation

- **[Quick Start Guide](docs/QUICK_START.md)** - Get running in 5 minutes
- **[Universal Agent Protocol](docs/UNIVERSAL_AGENT_PROTOCOL.md)** - Technical specifications and adapter development
- **[Evaluation Dimensions](docs/EVALUATION_DIMENSIONS.md)** - Deep dive into each dimension
- **[Testing Guide](docs/TESTING.md)** - Running and writing tests
- **[Publishing Guide](docs/PUBLISHING.md)** - Publishing to PyPI

## Examples

All examples are in the `examples/` directory:

```bash
# Evaluate an OpenAI agent
python examples/evaluate_openai_agent.py

# Evaluate an Anthropic agent
python examples/evaluate_anthropic_agent.py

# Create a custom adapter
python examples/custom_adapter_example.py

# Batch evaluate multiple agents
python examples/batch_evaluation.py
```

## Architecture

### Core Components

```
agentfit/
├── protocol/          # Universal Agent Protocol
│   └── agent_protocol.py
├── adapters/          # Pre-built and custom adapters
│   ├── openai_adapter.py
│   ├── anthropic_adapter.py
│   ├── google_agentkit_adapter.py
│   └── generic_adapter.py
├── dimensions/        # 7 evaluation dimensions
│   ├── task_competence.py
│   ├── tool_use.py
│   ├── autonomy_escalation.py
│   ├── safety_alignment.py
│   ├── compliance_auditability.py
│   ├── operational_performance.py
│   └── deployment_compatibility.py
├── core/             # Core evaluator
│   ├── evaluator.py
│   ├── dimension.py
│   └── types.py
├── bnp/              # Business Need Profiles
│   ├── schema.py
│   └── parser.py
└── cli.py            # Command-line interface
```

## Creating a Custom Adapter

Implementing a custom adapter is simple:

```python
from agentfit.protocol import UniversalAgentProtocol, Message, ExecutionResult


class MyCustomAdapter(UniversalAgentProtocol):
    """Adapter for my agent framework."""
    
    def __init__(self, config: dict):
        super().__init__(config)
        # Initialize your agent
    
    async def execute(self, messages: list[Message], tools=None) -> ExecutionResult:
        """Execute agent on messages."""
        # 1. Format messages for your agent
        formatted = self._format_for_agent(messages)
        
        # 2. Call your agent
        response = await self.agent.call(formatted)
        
        # 3. Return standardized result
        return ExecutionResult(
            success=True,
            output=response,
            message="Success"
        )
    
    def _format_for_agent(self, messages):
        # Convert UniversalAgentProtocol messages to your format
        return [m.model_dump() for m in messages]
```

See `examples/custom_adapter_example.py` for a complete example.

## Running Tests

```bash
# Install test dependencies
pip install -e ".[dev]"

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=agentfit --cov-report=html

# Run specific test category
pytest tests/test_protocol.py -v
pytest tests/test_adapters.py -v
pytest tests/test_dimensions.py -v
```

## Publishing to PyPI

See [docs/PUBLISHING.md](docs/PUBLISHING.md) for detailed instructions.

Quick version:
```bash
# Install build tools
pip install build twine

# Build distribution
python -m build

# Test on TestPyPI
twine upload --repository testpypi dist/*

# Upload to real PyPI
twine upload dist/*
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Write or update tests
5. Run `pytest tests/ -v` to verify
6. Commit: `git commit -am "Add feature"`
7. Push: `git push origin feature/my-feature`
8. Create a Pull Request

## Support

- **Documentation**: See the [docs/](docs/) directory
- **Examples**: See the [examples/](examples/) directory
- **Issues**: Report on [GitHub Issues](https://github.com/recruitbase/agentfit/issues)
- **Discussions**: Start a [GitHub Discussion](https://github.com/recruitbase/agentfit/discussions)

## License

AgentFit is licensed under the Apache License 2.0. See [LICENSE](LICENSE) for details.

## Citation

If you use AgentFit in your research, please cite:

```bibtex
@software{agentfit2024,
  title={AgentFit: Universal Agent Evaluation Framework},
  author={AgentFit Contributors},
  year={2024},
  url={https://github.com/recruitbase/agentfit},
  license={Apache-2.0}
}
```

## Roadmap

- [ ] Web UI for evaluation results
- [ ] Integration with popular agent benchmarks (SWE-Bench, etc.)
- [ ] Automatic performance profiling
- [ ] A/B testing framework for agent versions
- [ ] Integration with MLOps platforms
- [ ] Multi-language support for dimensions
- [ ] Cloud-based evaluation service

## Acknowledgments

AgentFit is built on research in agent evaluation, AI safety, and enterprise AI governance.

---

**Made with ❤️ by Gabiro N. Arnauld (Founder at Recruit Base)**

Join us in creating a standard for evaluating AI agents across the industry!
