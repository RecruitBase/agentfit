"""
Example: Evaluate an Anthropic Claude agent.

Requires: pip install agentfit[anthropic]

Run:
    export ANTHROPIC_API_KEY="sk-ant-..."
    python examples/evaluate_anthropic_agent.py
"""

import asyncio
import os

from agentfit.core.evaluator import Evaluator, EvaluationRequest
from agentfit.bnp.parser import BNPParser
from agentfit.adapters import AnthropicAdapter
from agentfit.scenarios import ScenarioLoader
from agentfit.output import ReportGenerator
from agentfit.interpretability.config import InterpretabilityConfig, LLMProvider

BNP_MARKDOWN = """
# Profile: Financial Analysis Agent

## Metadata
- Organization: Enterprise Corp
- Domain: data_analysis
- Description: AI agent for financial data analysis and reporting

## Agent Requirements
- Task Competence: Produces accurate financial summaries (required, priority: critical)
- Compliance: Maintains audit trails for SOX/GDPR (required, priority: critical)
- Safety: Handles sensitive financial data safely (required, priority: high)

## Evaluation Setup
- Complexity: complex
- Dimensions:
  - task_competence: 0.35
  - compliance_auditability: 0.35
  - safety_alignment: 0.20
  - operational_performance: 0.10

## Compliance
- GDPR
- SOX
"""


async def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("AGENT_API_KEY")

    # 1. Load BNP profile
    bnp = BNPParser.parse_markdown(BNP_MARKDOWN)
    scenario = ScenarioLoader.get_scenario(domain=bnp.domain, complexity=bnp.task_complexity)

    # 2. Create the Anthropic adapter
    adapter = AnthropicAdapter(
        agent_id="claude-financial-agent",
        agent_name="Claude Sonnet — Financial Agent",
        model="claude-sonnet-4-6",
        api_key=api_key,
    )

    # 3. Interpretation (optional — reuse the same Anthropic key)
    interp = None
    if api_key:
        interp = InterpretabilityConfig(
            enabled=True,
            provider=LLMProvider.ANTHROPIC,
            api_key=api_key,
            model="claude-haiku-4-5-20251001",  # cheaper model for interpretation
        )

    # 4. Build evaluation request
    request = EvaluationRequest(
        agent_id="claude-financial-agent",
        agent_interface=adapter.to_agent_interface(),
        scenario=scenario,
        bnp_profile=bnp,
        interpretability=interp,
    )

    # 5. Run evaluation
    print(f"Evaluating {adapter.agent_name} ({adapter.model})…")
    result = await Evaluator().evaluate(request)

    # 6. Report
    ReportGenerator.print_summary(result, bnp)

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
