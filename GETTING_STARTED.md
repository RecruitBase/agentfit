## End-to-End Testing Guide

### Step 1: Activate your environment

```bash
cd "c:/Users/HP/Desktop/Projects/Recruit Base/AgentFit Tool"
source venv/Scripts/activate
```

### Step 2: Install the provider SDK you want for interpretation

Pick one (or more):

```bash
pip install openai        # for --provider openai
pip install anthropic     # for --provider anthropic
pip install google-generativeai  # for --provider google
```

### Step 3: Define a BNP profile

You already have one at `examples/customer_service_bnp.md`. Here's what it looks like:

```1:30:examples/customer_service_bnp.md
# Profile: Customer Service Agent

## Metadata
- Organization: TechCorp Support
- Domain: customer_service
- Description: AI agent for handling customer support inquiries with API integrations
- Agent Name: SupportBot Pro
- Tags: support, customer-service, api-integration

## Agent Requirements
- Task Understanding: Can correctly interpret customer issues and context (required, priority: critical)
- Tool Use: Can call support APIs to retrieve tickets and customer data (required, priority: critical)
- Error Recovery: Can handle API errors gracefully and retry appropriately (required, priority: high)
- Step Completion: Can break down complex issues into logical steps (required, priority: high)
- Response Quality: Provides helpful and professional responses (required, priority: medium)

## Evaluation Setup
- Complexity: moderate
- Dimensions:
  - task_competence: 0.6
  - tool_use: 0.4

## Constraints
- Max Latency: 5000ms
- Max Errors per Task: 2

## Compliance
- GDPR compliant data handling
- PII redaction in logs
- Audit trail maintenance
```

This BNP tells AgentFit: *"I'm a customer service org, I need task_competence weighted at 60% and tool_use at 40%, moderate complexity, with GDPR compliance."*

### Step 4: Run evaluation WITHOUT interpretation (baseline)

This uses the built-in `MockAgent` and verifies the scoring pipeline works:

```bash
agentfit evaluate \
  --bnp examples/customer_service_bnp.md \
  --output results_raw.json \
  --agent-id "supportbot-v1" \
  --success-rate 0.8 \
  --verbose
```

Open `results_raw.json` — you'll see raw scores, per-dimension metrics, and the weighted overall score. No explanations yet.

### Step 5: Run evaluation WITH interpretation

Replace `sk-your-key-here` with your actual API key:

```bash
agentfit evaluate \
  --bnp examples/customer_service_bnp.md \
  --output results_interpreted.json \
  --agent-id "supportbot-v1" \
  --success-rate 0.8 \
  --interpret \
  --provider deepseek \
  --api-key sk-key-goes-here \
  --verbose
```

Or with Anthropic:

```bash
agentfit evaluate \
  --bnp examples/customer_service_bnp.md \
  --output results_interpreted.json \
  --interpret \
  --provider anthropic \
  --api-key sk-ant-your-key-here
```

Or set the key as an env var so you don't pass it every time:

```bash
export AGENTFIT_API_KEY="sk-your-key-here"
agentfit evaluate \
  --bnp examples/customer_service_bnp.md \
  --output results_interpreted.json \
  --interpret \
  --provider openai
```

The terminal report will now include inline interpretations per dimension, an overall narrative, and prioritized recommendations. The JSON file will have the full structured `interpretation` block.

### Step 6: Run it programmatically (Python)

Create a file `test_e2e.py` in the project root:

```python
import asyncio
from agentfit import (
    Evaluator,
    EvaluationRequest,
    BNPParser,
    InterpretabilityConfig,
    LLMProvider,
)
from agentfit.mock_agent import MockAgent
from agentfit.scenarios import ScenarioLoader
from agentfit.output import ReportGenerator, OutputFormatter


async def main():
    # 1. Load BNP
    with open("examples/customer_service_bnp.md") as f:
        bnp = BNPParser.parse_markdown(f.read())
    print(f"BNP: {bnp.name} | Domain: {bnp.domain} | Weights: {bnp.get_dimension_weights()}")

    # 2. Load a matching scenario
    scenario = ScenarioLoader.get_scenario(domain=bnp.domain, complexity=bnp.task_complexity)
    print(f"Scenario: {scenario['id']} — {scenario['task'][:80]}...")

    # 3. Create the mock agent
    agent = MockAgent(agent_id="supportbot-v1", success_rate=0.85)
    agent_interface = agent.to_agent_interface()

    # 4. Build the request WITH interpretability
    request = EvaluationRequest(
        agent_id="supportbot-v1",
        agent_interface=agent_interface,
        scenario=scenario,
        bnp_profile=bnp,
        interpretability=InterpretabilityConfig(
            provider=LLMProvider.OPENAI,       # swap to ANTHROPIC or GOOGLE
            api_key="sk-your-key-here",        # <-- replace this
        ),
    )

    # 5. Evaluate
    evaluator = Evaluator()
    result = await evaluator.evaluate(request)

    # 6. Print the full report (scores + interpretation)
    ReportGenerator.print_summary(result, bnp)

    # 7. Save to file
    OutputFormatter.write_to_file(result, "results_e2e.json", bnp_profile=bnp)
    print("\nResults saved to results_e2e.json")

    # 8. Inspect interpretation programmatically
    if result.interpretation:
        interp = result.interpretation
        print("\n--- Programmatic Access ---")
        print(f"Overall: {interp.overall_interpretation.summary}")
        print(f"Verdict: {interp.overall_interpretation.verdict}")
        for dim_id, di in interp.dimension_interpretations.items():
            print(f"\n{dim_id}:")
            print(f"  Summary:    {di.summary}")
            print(f"  Strengths:  {di.strengths}")
            print(f"  Weaknesses: {di.weaknesses}")
        print("\nRecommendations:")
        for r in interp.recommendations:
            print(f"  [{r.priority.upper()}] {r.area}: {r.suggestion}")


asyncio.run(main())
```

Run it:

```bash
python test_e2e.py
```

### Step 7: Test via the REST API

Start the server:

```bash
python -m agentfit.server.app
```

In another terminal, first upload the BNP, then submit an evaluation with interpretation:

```bash
# Upload BNP profile
curl -X POST http://localhost:8000/api/bnp-profiles/upload \
  -F "file=@examples/customer_service_bnp.md"

# Note the returned "id" — use it below as BNP_ID

# Submit evaluation with interpretation
curl -X POST http://localhost:8000/api/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "supportbot-v1",
    "scenario": {
      "id": "cs-moderate-001",
      "task": "Resolve a customer complaint about a billing error and process a refund.",
      "expected_steps": ["Listen to issue", "Verify billing", "Identify error", "Process refund", "Confirm resolution"],
      "expected_tools": ["billing_system", "payment_processor", "notification_service"]
    },
    "bnp_profile_id": "BNP_ID_HERE",
    "interpretability": {
      "provider": "openai",
      "api_key": "sk-your-key-here"
    }
  }'

# Poll for results (replace EVAL_ID with the returned evaluation_id)
curl http://localhost:8000/api/evaluations/EVAL_ID
```

### What to look for in the output

**In `results_raw.json`** (without interpretation) you see bare numbers:

```json
{
  "evaluation": { "overall_score": 0.78, "passed": true },
  "dimensions": {
    "task_competence": { "score": 0.82, "metrics": [...] },
    "tool_use": { "score": 0.72, "metrics": [...] }
  }
}
```

**In `results_interpreted.json`** you get the same scores PLUS the `interpretation` block:

```json
{
  "evaluation": { "overall_score": 0.78, "passed": true },
  "dimensions": { ... },
  "interpretation": {
    "dimension_interpretations": {
      "task_competence": {
        "summary": "The agent scored 82% on task competence...",
        "explanation": "task_success contributed 40% of the dimension score and achieved 1.0/1.0, but step_coverage at 70% (weighted 30%) pulled the score down...",
        "strengths": ["Successfully completed the primary task", ...],
        "weaknesses": ["Missed 2 of 5 expected workflow steps", ...]
      }
    },
    "overall_interpretation": {
      "summary": "The agent passed with 78%, meeting the 70% threshold...",
      "explanation": "task_competence (0.82 * 0.60 = 0.492) contributed most...",
      "verdict": "PASSED — meets minimum requirements but..."
    },
    "recommendations": [
      { "priority": "high", "area": "tool_use", "suggestion": "Improve tool selection..." }
    ]
  }
}
```

The terminal report also prints all of this inline — dimension-by-dimension interpretations followed by the overall narrative and recommendations.

### Quick cheat sheet

| What | Command |
|------|---------|
| Scores only | `agentfit evaluate --bnp ... --output results.json` |
| Scores + interpretation | Add `--interpret --provider openai --api-key sk-...` |
| Use env var for key | `export AGENTFIT_API_KEY=sk-...` then just `--interpret` |
| Change provider | `--provider anthropic` or `--provider google` |
| Change model | `--model gpt-4o` or `--model claude-sonnet-4-20250514` |
| Specific dimensions | `--evals task_competence,tool_use` |
| Higher agent quality | `--success-rate 0.95` (mock agent succeeds more) |
| Lower agent quality | `--success-rate 0.4` (to see failure interpretations) |