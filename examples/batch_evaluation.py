"""
Example: Batch-evaluate and compare multiple agents against the same BNP.

Compares a mock agent, an OpenAI agent, and a self-hosted Ollama model
in parallel, then prints a ranked comparison table.

Run (no API keys → mock + Ollama only):
    python examples/batch_evaluation.py

Run with OpenAI:
    AGENT_API_KEY=sk-... python examples/batch_evaluation.py
"""

import asyncio
import os

from agentfit.core.evaluator import Evaluator, EvaluationRequest
from agentfit.bnp.parser import BNPParser
from agentfit.adapters import OpenAIAdapter, OpenAICompatibleAdapter
from agentfit.mock_agent import MockAgent
from agentfit.scenarios import ScenarioLoader
from agentfit.output import ReportGenerator

BNP_MARKDOWN = """
# Profile: Customer Support Comparison

## Metadata
- Organization: MultiAgent Corp
- Domain: customer_service
- Description: Side-by-side evaluation of multiple agents for support automation

## Agent Requirements
- Task Completion: Resolves tickets end-to-end (required, priority: critical)
- Tool Use: Uses CRM and billing APIs correctly (required, priority: high)
- Safety: Refuses harmful requests (required, priority: high)

## Evaluation Setup
- Complexity: moderate
- Dimensions:
  - task_competence: 0.4
  - tool_use: 0.3
  - safety_alignment: 0.3
"""

DIMENSIONS = ["task_competence", "tool_use", "safety_alignment"]


def _build_agents(api_key: str):
    agents = []

    # Always include the mock (no key needed — good baseline)
    agents.append({
        "id": "mock-baseline",
        "interface": MockAgent(agent_id="mock-baseline", success_rate=0.85, seed=42).to_agent_interface(),
    })

    # Ollama (local, no key) — skip if server is likely not running in CI
    if os.environ.get("AGENTFIT_TEST_OLLAMA"):
        ollama = OpenAICompatibleAdapter(
            agent_id="ollama-llama3",
            agent_name="Ollama Llama3",
            framework="ollama",
            base_url="http://localhost:11434/v1",
            model="llama3",
        )
        agents.append({"id": "ollama-llama3", "interface": ollama.to_agent_interface()})

    # OpenAI GPT-4o (real API)
    if api_key:
        gpt = OpenAIAdapter(
            agent_id="gpt4o",
            agent_name="GPT-4o",
            model="gpt-4o",
            api_key=api_key,
        )
        agents.append({"id": "gpt4o", "interface": gpt.to_agent_interface()})

    return agents


async def evaluate_one(evaluator, agent_id, agent_interface, bnp, scenario):
    req = EvaluationRequest(
        agent_id=agent_id,
        agent_interface=agent_interface,
        scenario=scenario,
        bnp_profile=bnp,
        dimensions=DIMENSIONS,
    )
    return await evaluator.evaluate(req)


async def main():
    api_key = os.environ.get("AGENT_API_KEY") or os.environ.get("OPENAI_API_KEY")

    bnp = BNPParser.parse_markdown(BNP_MARKDOWN)
    scenario = ScenarioLoader.get_scenario(domain=bnp.domain, complexity=bnp.task_complexity)

    agents = _build_agents(api_key)
    evaluator = Evaluator()

    print("=" * 70)
    print("BATCH AGENT EVALUATION")
    print(f"Evaluating {len(agents)} agent(s) across {len(DIMENSIONS)} dimensions")
    print("=" * 70)

    # Run all evaluations in parallel
    tasks = [
        evaluate_one(evaluator, a["id"], a["interface"], bnp, scenario)
        for a in agents
    ]
    results = await asyncio.gather(*tasks)
    results_by_id = {a["id"]: r for a, r in zip(agents, results)}

    # ── Overall ranking ──────────────────────────────────────────────────
    print("\nOverall Fitness Scores (ranked):")
    print("-" * 70)
    for agent_id, result in sorted(results_by_id.items(),
                                   key=lambda x: x[1].overall_score, reverse=True):
        score = result.overall_score
        bar = "█" * int(score * 35) + "░" * (35 - int(score * 35))
        status = "✓ PASS" if result.passed else "✗ FAIL"
        print(f"  {agent_id:<25} | {bar} | {score:5.1%}  {status}")

    # ── Per-dimension breakdown ──────────────────────────────────────────
    print("\nDimension-by-dimension breakdown:")
    for dim in DIMENSIONS:
        print(f"\n  {dim.replace('_', ' ').upper()}")
        print("  " + "-" * 60)
        for agent_id, result in sorted(results_by_id.items(),
                                       key=lambda x: x[1].dimension_results.get(dim, type("o", (), {"score": 0})()).score,
                                       reverse=True):
            dr = result.dimension_results.get(dim)
            if dr:
                bar = "█" * int(dr.score * 30) + "░" * (30 - int(dr.score * 30))
                print(f"    {agent_id:<23} | {bar} | {dr.score:5.1%}")

    # ── Recommendation ───────────────────────────────────────────────────
    best_id = max(results_by_id, key=lambda k: results_by_id[k].overall_score)
    print(f"\nRecommendation: use '{best_id}' "
          f"(overall score: {results_by_id[best_id].overall_score:.1%})")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
