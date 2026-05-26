<div align="center">

# AgentFit

### The Agent Evaluation & Interpretability Framework

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-green?style=flat-square)](https://opensource.org/licenses/Apache-2.0)
[![Version](https://img.shields.io/badge/version-0.2.0-orange?style=flat-square)](https://github.com/RecruitBase/agentfit/releases)
[![Tests](https://img.shields.io/github/actions/workflow/status/recruitbase/agentfit/tests.yml?label=tests&style=flat-square)](https://github.com/RecruitBase/agentfit/actions)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000?style=flat-square)](https://github.com/psf/black)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen?style=flat-square)](https://github.com/RecruitBase/agentfit/pulls)
[![Made by RecruitBase](https://img.shields.io/badge/made%20by-RecruitBase-6C3BF5?style=flat-square)](https://recruitbase.work)

**Stop trusting the ai agents hype. Objectively evaluate which agent is appropriate for your business needs.**

[Getting Started](#getting-started) · [Why AgentFit](#why-agentfit) · [Dimensions](#evaluation-dimensions) · [Interpretability](#interpretability-layer) · [Scaling](#scaling) · [Docs](docs/) · [Examples](examples/)

</div>

---

## What is AgentFit?

AgentFit is an **open-source, enterprise-grade agent evaluation and interpretability framework**. It gives teams a structured, reproducible way to assess AI agents across seven behavioural dimensions — then uses an LLM to explain *why* an agent scored the way it did, in the context of your specific business requirements.

It is **framework-agnostic**: bring your OpenAI, Anthropic, Google, or fully custom agent. AgentFit evaluates it through a universal protocol without you changing a single line of agent code.

```
Define requirements  →  Run evaluation  →  Get scores + explanations  →  Act
    (BNP profile)       (7 dimensions)     (grounded in your context)    (recommendations)
```

---

## Why AgentFit?

### The Problem

Organisations are deploying AI agents at speed — for customer service, code generation, data analysis, compliance workflows. But the honest answer to *"how do I know if this agent is good enough?"* is still: **nobody really knows.**

Existing solutions fall into one of three traps:

| Approach | What it gives you | What's missing |
|---|---|---|
| **Benchmark suites** (SWE-Bench, HumanEval, MMLU, HELM) | Standardised task accuracy on curated datasets | No business context; code-centric; no production behaviours |
| **Framework-native evals** (OpenAI Evals, LangSmith) | Tight loop with a single provider | Vendor-locked; can't compare across providers; no compliance model |
| **Manual QA / vibe-checks** | Cheap to start | Unscalable, inconsistent, no audit trail |
| **Raw metrics dashboards** | Latency, token counts, error rates | Operational, not behavioural; doesn't answer "is this agent fit for my use case?" |

None of these answer: *"Is this agent fit for **my** business needs — and can you explain why?"*

### How AgentFit Solves This

AgentFit introduces two concepts that together close the gap:

**1. Business Need Profiles (BNPs)**

A BNP is a lightweight markdown file that expresses your organisation's agent requirements in a structured, machine-readable way: which capabilities matter, how they should be weighted, what compliance standards apply, and what task complexity you're operating at. Every evaluation is anchored to a BNP, so scores are relative to *your context*, not an abstract benchmark.

```markdown
# Profile: Customer Service Agent

## Metadata
- Organization: Acme Corp
- Domain: customer_service
- Description: AI agent for handling billing complaints and refunds

## Agent Requirements
- Task Understanding: Correctly interprets customer issues (required, priority: critical)
- Tool Use: Calls billing and payment APIs reliably (required, priority: critical)
- Error Recovery: Handles API failures gracefully (required, priority: high)

## Evaluation Setup
- Complexity: moderate
- Dimensions:
  - task_competence: 0.6
  - tool_use: 0.4

## Compliance
- GDPR compliant data handling
- Audit trail maintenance
```

**2. LLM-Powered Interpretability**

After scoring, AgentFit packages the full evaluation — scores, sub-metric breakdowns, weighted arithmetic, BNP context — into a structured prompt and sends it to your chosen LLM. The model returns natural-language explanations grounded in your requirements:

> *"task_competence scored 82% (contributing 0.492 to the overall 0.74). The agent completed the primary task (task_success: 100%), but only covered 3 of 5 expected billing workflow steps (step_coverage: 60%, weighted 30%). For a customer service agent in a GDPR-regulated environment, incomplete step coverage is a material risk — a missed "confirm resolution" step creates an audit gap."*

This is not post-hoc commentary. The LLM sees the exact calculation trail — every sub-metric weight, every contribution to the overall score — so its explanations are arithmetically grounded, not hallucinated summaries.

---

## How AgentFit Builds on Existing Benchmarks

AgentFit is **complementary to**, not a replacement for, the established evaluation ecosystem.

| Framework | Focus | AgentFit relationship |
|---|---|---|
| **SWE-Bench** | Code patch correctness | Task Competence dimension can wrap SWE-Bench scenarios as test cases |
| **HumanEval / MBPP** | Python function generation | Feeds into Task Competence and Tool Use dimensions |
| **HELM** | Holistic LLM capability | AgentFit adds *agentic* behaviours HELM doesn't capture: tool calls, escalation, compliance |
| **AgentBench** | Multi-task agent capability | Similar spirit; AgentFit adds business context (BNPs) and interpretability |
| **MT-Bench** | Multi-turn instruction following | Can be embedded as a scenario within Task Competence |
| **TrustLLM / SafetyBench** | Safety and alignment | Extends into AgentFit's Safety & Alignment dimension with production constraints |

The key insight: most benchmarks evaluate *model capability* on canonical tasks. AgentFit evaluates *agent fitness* for a specific business deployment — a higher-order question that only makes sense in context.

---

## Evaluation Dimensions

Seven dimensions cover the full lifecycle of production agent behaviour. Each produces a 0–1 score with sub-metrics, weighted feedback, and an LLM interpretation.

| # | Dimension | What it measures | Default weight |
|---|---|---|---|
| 1 | **Task Competence** | Understanding, planning, step execution, error recovery | 15% |
| 2 | **Tool Use & Integration** | Tool selection correctness, API call success, parameter accuracy | 15% |
| 3 | **Autonomy & Escalation** | When to act independently vs. escalate to a human | 15% |
| 4 | **Safety & Alignment** | Robustness to adversarial inputs, refusal behaviour, PII handling | 15% |
| 5 | **Compliance & Auditability** | Regulatory adherence, audit trail completeness, log quality | 15% |
| 6 | **Operational Performance** | Latency, throughput, token efficiency, cost | 10% |
| 7 | **Deployment Compatibility** | Infrastructure fit, API stability, environment constraints | 15% |

BNPs override these defaults — a fintech company running a compliance-critical workflow might weight Compliance & Auditability at 40%.

---

## Getting Started

### Installation

```bash
# Core framework (includes httpx — enough to evaluate against any local/self-hosted model)
pip install agentfit

# Add provider SDKs for the *agent under test* or for interpretation
pip install agentfit[openai]       # OpenAI (GPT-4o, o1)
pip install agentfit[anthropic]    # Anthropic Claude (required for AnthropicAdapter)
pip install agentfit[google]       # Google Gemini / AgentKit
pip install agentfit[mistral]      # Mistral

# Install all providers and dev tools
pip install agentfit[all]
```

> **Self-hosted models (vLLM, Ollama, LM Studio, llama.cpp):** no extra SDK needed.
> AgentFit's `OpenAICompatibleAdapter` talks directly to any `/v1/chat/completions` endpoint
> using `httpx`, which ships with the core install.
>
> **Groq, Together AI, DeepSeek, Qwen** are cloud-hosted but OpenAI-compatible —
> `agentfit[openai]` covers them, or use `OpenAICompatibleAdapter` without any extra install.

### Step 1 — Define your BNP

Save this as `my_bnp.md`:

```markdown
# Profile: Support Agent

## Metadata
- Organization: My Company
- Domain: customer_service
- Description: Handles refunds and account queries

## Agent Requirements
- Task Completion: Resolves issues end-to-end (required, priority: critical)
- Tool Reliability: Calls APIs without failure (required, priority: high)

## Evaluation Setup
- Complexity: moderate
- Dimensions:
  - task_competence: 0.6
  - tool_use: 0.4
```

### Step 2 — Run via CLI

```bash
# Default: mock agent (no LLM needed — great for CI and pipeline smoke-tests)
agentfit evaluate --bnp my_bnp.md --output results.json

# Reproducible mock run (same seed → same scores every time)
agentfit evaluate --bnp my_bnp.md --output results.json \
  --mock-seed 42 --mock-behavior always_succeed

# ── Real agent: self-hosted vLLM ───────────────────────────────────────────
agentfit evaluate --bnp my_bnp.md --output results.json \
  --agent-adapter vllm \
  --agent-model meta-llama/Meta-Llama-3-70B-Instruct \
  --agent-base-url http://localhost:8000/v1

# ── Real agent: Ollama (no key required) ──────────────────────────────────
agentfit evaluate --bnp my_bnp.md --output results.json \
  --agent-adapter ollama \
  --agent-model llama3

# ── Real agent: LM Studio ─────────────────────────────────────────────────
agentfit evaluate --bnp my_bnp.md --output results.json \
  --agent-adapter lmstudio \
  --agent-model my-local-model \
  --agent-base-url http://localhost:1234/v1

# ── Real agent: OpenAI ────────────────────────────────────────────────────
agentfit evaluate --bnp my_bnp.md --output results.json \
  --agent-adapter openai \
  --agent-model gpt-4o \
  --agent-api-key sk-...

# ── Real agent: Anthropic Claude ──────────────────────────────────────────
agentfit evaluate --bnp my_bnp.md --output results.json \
  --agent-adapter anthropic \
  --agent-model claude-sonnet-4-6 \
  --agent-api-key sk-ant-...

# ── Real agent: Groq / Together / DeepSeek (OpenAI-compatible cloud) ──────
agentfit evaluate --bnp my_bnp.md --output results.json \
  --agent-adapter groq \
  --agent-model llama-3.3-70b-versatile \
  --agent-api-key gsk_...

# ── Add LLM interpretation on top of any of the above ─────────────────────
agentfit evaluate --bnp my_bnp.md --output results.json \
  --agent-adapter vllm --agent-model llama3 \
  --agent-base-url http://localhost:8000/v1 \
  --interpret --provider openai --api-key sk-...

# Use environment variables instead of inline flags
export AGENT_API_KEY="sk-..."
export AGENTFIT_API_KEY="sk-..."
agentfit evaluate --bnp my_bnp.md --output results.json \
  --agent-adapter openai --interpret
```

All `--agent-*` flags control the **agent being evaluated**. The `--provider` / `--api-key` / `--base-url` flags control the **LLM used for interpretation** — they can be different models.

### Step 3 — Run via Python

**Option A — Mock agent (no LLM required)**

```python
import asyncio
from agentfit.core.evaluator import Evaluator, EvaluationRequest
from agentfit.bnp.parser import BNPParser
from agentfit.mock_agent import MockAgent
from agentfit.scenarios import ScenarioLoader
from agentfit.output import ReportGenerator

async def main():
    bnp = BNPParser.parse_markdown(open("my_bnp.md").read())
    scenario = ScenarioLoader.get_scenario(domain=bnp.domain, complexity=bnp.task_complexity)

    # Seeded mock: same seed → identical scores every run (good for CI)
    agent = MockAgent(agent_id="support-bot-v1", success_rate=0.85, seed=42)

    request = EvaluationRequest(
        agent_id="support-bot-v1",
        agent_interface=agent.to_agent_interface(),
        scenario=scenario,
        bnp_profile=bnp,
    )

    result = await Evaluator().evaluate(request)
    ReportGenerator.print_summary(result, bnp)

asyncio.run(main())
```

**Option B — Self-hosted model (vLLM / Ollama / LM Studio / any OpenAI-compatible endpoint)**

```python
import asyncio
from agentfit.core.evaluator import Evaluator, EvaluationRequest
from agentfit.bnp.parser import BNPParser
from agentfit.adapters import OpenAICompatibleAdapter
from agentfit.scenarios import ScenarioLoader
from agentfit.output import ReportGenerator

async def main():
    bnp = BNPParser.parse_markdown(open("my_bnp.md").read())
    scenario = ScenarioLoader.get_scenario(domain=bnp.domain, complexity=bnp.task_complexity)

    # Works with vLLM, Ollama, LM Studio, llama.cpp — anything at /v1/chat/completions
    adapter = OpenAICompatibleAdapter(
        agent_id="llama3-70b",
        agent_name="Llama-3 70B",
        base_url="http://localhost:8000/v1",   # your server
        model="meta-llama/Meta-Llama-3-70B-Instruct",
        api_key="none",                         # omit or set "none" for local servers
    )

    request = EvaluationRequest(
        agent_id="llama3-70b",
        agent_interface=adapter.to_agent_interface(),
        scenario=scenario,
        bnp_profile=bnp,
    )

    result = await Evaluator().evaluate(request)
    ReportGenerator.print_summary(result, bnp)

asyncio.run(main())
```

**Option C — OpenAI / Anthropic / cloud providers**

```python
from agentfit.adapters import OpenAIAdapter, AnthropicAdapter

# OpenAI (reads OPENAI_API_KEY from env if api_key= is omitted)
adapter = OpenAIAdapter(agent_id="gpt4o", agent_name="GPT-4o", model="gpt-4o")

# Anthropic (requires: pip install agentfit[anthropic])
adapter = AnthropicAdapter(
    agent_id="claude", agent_name="Claude Sonnet",
    model="claude-sonnet-4-6", api_key="sk-ant-..."
)
```

**Option D — With LLM interpretation**

```python
from agentfit.interpretability.config import InterpretabilityConfig, LLMProvider

request = EvaluationRequest(
    agent_id="my-agent",
    agent_interface=adapter.to_agent_interface(),
    scenario=scenario,
    bnp_profile=bnp,
    interpretability=InterpretabilityConfig(
        enabled=True,
        provider=LLMProvider.OPENAI,
        api_key="sk-...",
        model="gpt-4o",
    ),
)

result = await Evaluator().evaluate(request)

if result.interpretation:
    print(result.interpretation.overall_interpretation.summary)
    for rec in result.interpretation.recommendations:
        print(f"[{rec.priority.upper()}] {rec.area}: {rec.suggestion}")
```

### Step 4 — REST API

```bash
# Start the server
python -m agentfit.server.app

# Upload your BNP
curl -X POST http://localhost:8000/api/bnp-profiles/upload \
  -F "file=@my_bnp.md"

# Submit evaluation (with interpretation)
curl -X POST http://localhost:8000/api/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "support-bot-v1",
    "scenario": { "id": "cs-001", "task": "Resolve billing complaint", "expected_steps": [...] },
    "bnp_profile_id": "<id from upload>",
    "interpretability": { "provider": "openai", "api_key": "sk-..." }
  }'

# Poll for result
curl http://localhost:8000/api/evaluations/<eval_id>
```

---

## Connecting Self-Hosted & Custom LLMs

AgentFit ships a first-class `OpenAICompatibleAdapter` that lets you evaluate **any model you can run locally or self-host** — no extra dependencies required beyond the core install.

### Supported backends

| Backend | Default URL | `--agent-adapter` | Extra deps |
|---|---|---|---|
| **vLLM** | `http://localhost:8000/v1` | `vllm` | none |
| **Ollama** | `http://localhost:11434/v1` | `ollama` | none |
| **LM Studio** | `http://localhost:1234/v1` | `lmstudio` | none |
| **llama.cpp server** | `http://localhost:8080/v1` | `openai_compatible` | none |
| **LocalAI** | `http://localhost:8080/v1` | `localai` | none |
| **Groq** | `https://api.groq.com/openai/v1` | `groq` | none |
| **Together AI** | `https://api.together.xyz/v1` | `together` | none |
| **DeepSeek** | `https://api.deepseek.com/v1` | `deepseek` | none |
| **Any custom endpoint** | *(you supply)* | `openai_compatible` | none |

### How it works

`OpenAICompatibleAdapter` runs a real multi-step agentic loop:

1. Sends the task + tool definitions to your model via `/v1/chat/completions`
2. If the model responds with tool calls, executes them and feeds the results back
3. Repeats up to `max_steps` or until the model returns a plain text response
4. Captures every `ToolCall`, `ToolResult`, and `Message` into the UAP `ExecutionResult` that all evaluation dimensions inspect

### Custom tool execution

By default the adapter returns a structured mock acknowledgment for every tool call, which is enough to measure whether the model selects the right tools and parameters.
To wire in real tools, subclass and override `_execute_tool()`:

```python
from agentfit.adapters import OpenAICompatibleAdapter
from agentfit.protocol import ToolCall
from typing import Any, List, Optional

class MyVLLMAdapter(OpenAICompatibleAdapter):
    def _execute_tool(self, tc: ToolCall, tools) -> Any:
        if tc.tool_name == "search_kb":
            return my_knowledge_base.search(tc.parameters["query"])
        if tc.tool_name == "create_ticket":
            return ticket_system.create(**tc.parameters)
        return {"status": "unknown_tool", "tool": tc.tool_name}

adapter = MyVLLMAdapter(
    agent_id="support-llm",
    agent_name="Support LLM",
    base_url="http://localhost:8000/v1",
    model="my-finetuned-llama3",
)
```

### Quick start: Ollama

```bash
# 1. Install and start Ollama
ollama pull llama3
ollama serve

# 2. Evaluate against your BNP (no API key needed)
agentfit evaluate \
  --bnp my_bnp.md \
  --output results.json \
  --agent-adapter ollama \
  --agent-model llama3
```

### Quick start: vLLM

```bash
# 1. Start vLLM server
python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Meta-Llama-3-70B-Instruct \
  --port 8000

# 2. Evaluate
agentfit evaluate \
  --bnp my_bnp.md \
  --output results.json \
  --agent-adapter vllm \
  --agent-model meta-llama/Meta-Llama-3-70B-Instruct \
  --agent-base-url http://localhost:8000/v1
```

---

## Interpretability Layer

AgentFit is not a raw score framework. The interpretability layer transforms metric values into business-grounded narratives by sending the *full calculation trail* to an LLM of your choice.

**What the LLM receives:**
- Complete BNP context (requirements, weights, compliance rules, domain)
- Per-dimension scores with every sub-metric, its value, and its weight contribution
- The exact weighted aggregation arithmetic (e.g., `0.82 × 0.60 = 0.492`)
- Pass/fail thresholds and whether they were met

**What comes back (structured JSON):**
- `dimension_interpretations` — per-dimension summary, detailed explanation, strengths, weaknesses
- `overall_interpretation` — overall narrative, verdict, strengths/weaknesses
- `recommendations` — prioritised, actionable improvements tied to weakest areas

### Supported Providers

| Provider | `--provider` | Install | Default model |
|---|---|---|---|
| OpenAI | `openai` | `agentfit[openai]` | `gpt-4o-mini` |
| Anthropic | `anthropic` | `agentfit[anthropic]` | `claude-sonnet-4-20250514` |
| Google | `google` | `agentfit[google]` | `gemini-2.0-flash` |
| Mistral | `mistral` | `agentfit[mistral]` | `mistral-large-latest` |
| DeepSeek | `deepseek` | `agentfit[openai]` | `deepseek-chat` |
| Qwen (Alibaba) | `qwen` | `agentfit[openai]` | `qwen-plus` |
| Groq | `groq` | `agentfit[openai]` | `llama-3.3-70b-versatile` |
| Together AI | `together` | `agentfit[openai]` | `meta-llama/Llama-3-70b-chat-hf` |
| Ollama (local) | `ollama` | `agentfit[openai]` | `llama3.2` *(no key needed)* |
| Any OpenAI-compat | `openai_compatible` | `agentfit[openai]` | *(set `--model`)* |

```bash
# Groq (fast, free tier)
agentfit evaluate --bnp my_bnp.md --output r.json \
  --interpret --provider groq --api-key gsk_...

# Local Ollama (no key, no cost)
agentfit evaluate --bnp my_bnp.md --output r.json \
  --interpret --provider ollama --model llama3.2

# LM Studio / vLLM / any custom endpoint
agentfit evaluate --bnp my_bnp.md --output r.json \
  --interpret --provider openai_compatible \
  --base-url http://localhost:1234/v1 --model my-model
```

---

## Architecture

```
agentfit/
├── core/
│   ├── evaluator.py          # Orchestrator: runs dimensions, aggregates, triggers interpretation
│   └── dimension.py          # Base class, DimensionResult, DimensionRegistry
│
├── dimensions/               # 7 evaluation dimensions (one file each)
│   ├── task_competence.py
│   ├── tool_use.py
│   ├── autonomy_escalation.py
│   ├── safety_alignment.py
│   ├── compliance_auditability.py
│   ├── operational_performance.py
│   └── deployment_compatibility.py
│
├── interpretability/         # LLM-powered explanation engine
│   ├── config.py             # InterpretabilityConfig, LLMProvider, defaults
│   ├── llm_client.py         # Multi-provider async LLM client
│   ├── prompts.py            # Prompt construction with full calculation context
│   └── interpreter.py        # Orchestrates LLM call, parses response
│
├── bnp/
│   ├── schema.py             # BNPProfile, AgentRequirement, DimensionWeight
│   └── parser.py             # Markdown → BNPProfile
│
├── protocol/
│   └── agent_protocol.py     # UniversalAgentProtocol base class + execute() + to_agent_interface()
│
├── adapters/
│   ├── openai_compatible_adapter.py  # Any /v1/chat/completions endpoint (vLLM, Ollama, etc.)
│   ├── openai_adapter.py             # OpenAI api.openai.com (inherits above)
│   ├── anthropic_adapter.py          # Anthropic Claude (real SDK with tool-use loop)
│   ├── google_agentkit_adapter.py    # Google Gemini / AgentKit
│   └── generic_adapter.py            # Wrap any Python callable
│
├── server/
│   └── app.py               # FastAPI REST server
├── cli.py                   # Click CLI
└── scenarios.py             # Built-in test scenarios (customer_service, healthcare, SWE)
```

**Evaluation data flow:**

```
EvaluationRequest
  ├── agent_interface   ──┐
  ├── scenario          ──┤──► 7 × Dimension.evaluate() ──► DimensionResult[]
  ├── bnp_profile       ──┘         (concurrent, asyncio.gather)
  └── interpretability config
                                         │
                              compute_overall_score(bnp_weights)
                                         │
                              Interpreter.interpret(result, bnp, weights)
                                         │
                                    LLM API call
                                         │
                              EvaluationResult
                              ├── dimension_results  (scores + metrics)
                              ├── overall_score
                              └── interpretation     (LLM explanations)
```

---

## Custom Adapters

### Option 1 — Subclass `OpenAICompatibleAdapter` (recommended for any HTTP endpoint)

If your model server exposes `/v1/chat/completions`, the fastest path is to subclass
`OpenAICompatibleAdapter` and override only `_execute_tool()` for real tool execution:

```python
from agentfit.adapters import OpenAICompatibleAdapter
from agentfit.protocol import ToolCall, AgentAdapterRegistry
from typing import Any

class MyModelAdapter(OpenAICompatibleAdapter):
    def _execute_tool(self, tc: ToolCall, tools) -> Any:
        # Replace mock with real tool logic
        if tc.tool_name == "query_db":
            return my_db.query(tc.parameters["sql"])
        return {"status": "ok", "tool": tc.tool_name}

AgentAdapterRegistry.register("my_model", MyModelAdapter)
```

### Option 2 — Implement `UniversalAgentProtocol` from scratch

For non-HTTP agents (local Python objects, custom SDKs, etc.):

```python
from agentfit.protocol import (
    UniversalAgentProtocol, ToolDefinition, ExecutionResult,
    Message, MessageRole, AgentAdapterRegistry,
)
from typing import Any, Dict, List, Optional

class MyAgentAdapter(UniversalAgentProtocol):
    def __init__(self, agent_id: str, agent_name: str, my_client):
        super().__init__(agent_id, agent_name, framework="my_agent")
        self.client = my_client

    async def execute_task(
        self,
        task: str,
        tools: Optional[List[ToolDefinition]] = None,
        context: Optional[Dict[str, Any]] = None,
        max_steps: int = 10,
        timeout_seconds: int = 60,
    ) -> ExecutionResult:
        response = await self.client.run(task)
        return ExecutionResult(
            task_id=f"my-{task[:8]}",
            success=response.ok,
            final_output=response.text,
        )

    async def get_capabilities(self) -> Dict[str, Any]:
        return {"supports_tools": False, "max_context_tokens": 4096}

    async def validate_tools(self, tools) -> Dict[str, Any]:
        return {"valid": True, "supported_tools": [], "unsupported_tools": [], "validation_errors": []}

AgentAdapterRegistry.register("my_agent", MyAgentAdapter)
```

Both approaches inherit `execute()` and `to_agent_interface()` from `UniversalAgentProtocol`,
so your adapter works immediately with `EvaluationRequest` and all evaluation dimensions.

---

## Scaling

AgentFit is designed to grow from a single laptop run to a multi-tenant evaluation platform.

### Parallelism

All seven dimension evaluations run concurrently via `asyncio.gather`. On a 4-core machine, a full 7-dimension evaluation completes in roughly the time of the slowest single dimension, not their sum.

```python
# Evaluate multiple agents in parallel
import asyncio

results = await asyncio.gather(*[
    Evaluator().evaluate(EvaluationRequest(agent_id=f"agent-{v}", ...))
    for v in ["v1", "v2", "v3"]
])
```

### Selective Dimension Evaluation

Skip dimensions that don't apply to reduce evaluation time:

```bash
agentfit evaluate --bnp my_bnp.md --evals task_competence,tool_use --output r.json
```

```python
EvaluationRequest(..., dimensions=["task_competence", "tool_use"])
```

### REST API + Background Tasks

The FastAPI server submits evaluations as background tasks, returning an `evaluation_id` immediately. Poll `GET /api/evaluations/{id}` for results. This pattern supports:

- **Horizontal scaling** — run multiple server instances behind a load balancer
- **Async workflows** — evaluation results pushed to webhooks or message queues
- **Batch pipelines** — CI/CD systems submit evaluations on every agent commit

### Production Deployment Checklist

| Concern | Recommendation |
|---|---|
| **Storage** | Replace in-memory `_evaluations` dict with Postgres (SQLAlchemy model already in `pyproject.toml[server]`) |
| **Auth** | Add API key middleware to the FastAPI app |
| **Queuing** | Route background tasks to Celery + Redis for durability |
| **Observability** | Loguru → stdout, collect with your log aggregator; `total_duration_ms` and `interpretation_time_ms` are emitted on every result |
| **Cost control** | Use `--provider groq` or `--provider ollama` for interpretation in high-volume pipelines |
| **BNP versioning** | Store BNPs in git; pass `bnp_profile_id` references in evaluation requests |

### Building on Top of AgentFit

Register custom dimensions without forking the library:

```python
from agentfit.core.dimension import Dimension, DimensionResult, DimensionRegistry

class MyCustomDimension(Dimension):
    dimension_id = "my_dimension"
    dimension_name = "My Dimension"
    description = "Evaluates something domain-specific"

    async def evaluate(self, input_data) -> DimensionResult:
        # your logic here
        return self._create_result(score=0.9, passed=True, feedback="...")

    async def validate_input(self, input_data) -> bool:
        return "agent" in input_data

DimensionRegistry.register(MyCustomDimension)
# Now available in all evaluations and BNP dimension configs
```

---

## Running Tests

```bash
pip install -e ".[dev]"

pytest tests/ -v                               # all tests
pytest tests/ --cov=agentfit --cov-report=html # with coverage

# Specific suites
pytest tests/test_adapters.py -v              # adapter + OpenAICompatibleAdapter tests
pytest tests/test_mock_agent.py -v            # MockAgent seed/behavior/async tests
pytest tests/test_dimensions.py -v            # dimension unit tests
pytest tests/test_evaluator.py -v             # evaluator integration tests
pytest tests/test_bnp.py -v                   # BNP parsing tests
pytest tests/test_protocol.py -v              # UAP protocol tests
```

The full test suite runs against the mock agent by default — no LLM API key or running server
required. To run integration tests against a real endpoint, set environment variables:

```bash
# Against a local Ollama instance
AGENT_API_KEY=none pytest tests/ -v -k "live"

# Against OpenAI
AGENT_API_KEY=sk-... pytest tests/ -v -k "live"
```

---

## Contributing

Contributions are welcome. Please:

1. Fork the repository and create a branch: `git checkout -b feature/my-feature`
2. Write tests for any new behaviour
3. Run `pytest tests/ -v` and `black agentfit/` before committing
4. Open a pull request with a clear description

For larger changes (new dimensions, provider integrations, architecture changes) please open an issue first to discuss the approach.

---

## About RecruitBase

AgentFit is built and maintained by **[RecruitBase](https://recruitbase.work)** — a hiring intelligence platform that applies structured, objective evaluation to AI agents.

> *"We evaluate AI agents the same way we'd interview a human: define the requirements, set the criteria, run a structured assessment, and explain the result."*

The framework is open-source because the problem — how do you know if an AI agent is fit for a specific role? — is one the whole industry needs to solve together.

- Website: [recruitbase.work](https://recruitbase.work)
- AgentFit issues: [GitHub Issues](https://github.com/RecruitBase/agentfit/issues)
- Early access / enterprise: [recruitbase.work](https://recruitbase.work)

---

## Citation

If you use AgentFit in research, please cite:

```bibtex
@software{agentfit2025,
  title   = {AgentFit: Agent Evaluation and Interpretability Framework},
  author  = {Arnauld, Gabiro N. and RecruitBase Contributors},
  year    = {2025},
  url     = {https://github.com/RecruitBase/agentfit},
  license = {Apache-2.0}
}
```

## License

AgentFit is licensed under the **Apache License 2.0**. See [LICENSE](LICENSE) for details.

---

## Roadmap

- [ ] Web UI for evaluation results and BNP management
- [ ] Native SWE-Bench and AgentBench scenario adapters
- [ ] Streaming interpretation output
- [ ] Evaluation diffing — compare two agent versions side-by-side
- [ ] A/B testing framework for agent rollouts
- [ ] OpenTelemetry integration for production tracing
- [ ] Cloud-hosted evaluation service
- [ ] Multi-language dimension support

---

<div align="center">

Built with care by **[RecruitBase](https://recruitbase.work)** · Apache 2.0 · [Contribute](https://github.com/RecruitBase/agentfit/pulls)

</div>
