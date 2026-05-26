"""
Example: Evaluate an OpenAI agent.

Run:
    export OPENAI_API_KEY="sk-..."
    python examples/evaluate_openai_agent.py

Or pass the key inline:
    python examples/evaluate_openai_agent.py  # reads OPENAI_API_KEY from env
"""

import asyncio
import os

from agentfit.core.evaluator import Evaluator, EvaluationRequest
from agentfit.bnp.parser import BNPParser
from agentfit.adapters import OpenAIAdapter
from agentfit.scenarios import ScenarioLoader
from agentfit.output import ReportGenerator
from agentfit.interpretability.config import InterpretabilityConfig, LLMProvider

BNP_MARKDOWN = """
# Profile: Customer Support Bot

## Metadata
- Organization: Tech Startup
- Domain: customer_service
- Description: AI agent for handling billing and account queries

## Agent Requirements
- Task Completion: Resolves issues end-to-end (required, priority: critical)
- Tool Reliability: Calls CRM and billing APIs reliably (required, priority: high)
- Safety: Handles adversarial inputs gracefully (required, priority: high)

## Evaluation Setup
- Complexity: moderate
- Dimensions:
  - task_competence: 0.4
  - tool_use: 0.3
  - safety_alignment: 0.2
  - operational_performance: 0.1

## Constraints
- Max Latency: 5000ms
"""


async def main():
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("AGENT_API_KEY")

    # 1. Load BNP profile
    bnp = BNPParser.parse_markdown(BNP_MARKDOWN)
    scenario = ScenarioLoader.get_scenario(domain=bnp.domain, complexity=bnp.task_complexity)

    # 2. Create the OpenAI adapter (reads OPENAI_API_KEY from env if api_key= is omitted)
    adapter = OpenAIAdapter(
        agent_id="gpt4o-support-bot",
        agent_name="GPT-4o Support Bot",
        model="gpt-4o",
        api_key=api_key,
    )

    # 3. Optionally enable LLM-powered interpretation of results
    interp = None
    if api_key:
        interp = InterpretabilityConfig(
            enabled=True,
            provider=LLMProvider.OPENAI,
            api_key=api_key,
            model="gpt-4o-mini",  # cheaper model for interpretation
        )

    # 4. Build evaluation request
    request = EvaluationRequest(
        agent_id="gpt4o-support-bot",
        agent_interface=adapter.to_agent_interface(),
        scenario=scenario,
        bnp_profile=bnp,
        interpretability=interp,
    )

    # 5. Run evaluation
    print(f"Evaluating {adapter.agent_name} ({adapter.model})…")
    result = await Evaluator().evaluate(request)

    # 6. Print report
    ReportGenerator.print_summary(result, bnp)

    # 7. Programmatic access
    print(f"\nOverall score : {result.overall_score:.1%}")
    print(f"Passed        : {result.passed}")
    for dim_id, dr in result.dimension_results.items():
        print(f"  {dim_id:<35} {dr.score:.1%}  {'✓' if dr.passed else '✗'}")

    if result.interpretation:
        print("\n── Interpretation ──────────────────────────────────")
        print(result.interpretation.overall_interpretation.summary)
        for rec in result.interpretation.recommendations:
            print(f"  [{rec.priority.upper()}] {rec.area}: {rec.suggestion}")


if __name__ == "__main__":
    asyncio.run(main())
