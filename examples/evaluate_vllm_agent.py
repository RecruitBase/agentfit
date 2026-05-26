"""
Example: Evaluate a self-hosted model via OpenAICompatibleAdapter.

Works with any backend that exposes /v1/chat/completions:
  - vLLM
  - Ollama
  - LM Studio
  - llama.cpp server
  - LocalAI
  - Groq, Together AI, DeepSeek (cloud, OpenAI-compatible)

Quick start with Ollama (no API key needed):
    ollama pull llama3 && ollama serve
    python examples/evaluate_vllm_agent.py --backend ollama --model llama3

Quick start with vLLM:
    python -m vllm.entrypoints.openai.api_server \\
        --model meta-llama/Meta-Llama-3-70B-Instruct --port 8000
    python examples/evaluate_vllm_agent.py \\
        --backend vllm \\
        --model meta-llama/Meta-Llama-3-70B-Instruct \\
        --base-url http://localhost:8000/v1
"""

import asyncio
import argparse
import os

from agentfit.core.evaluator import Evaluator, EvaluationRequest
from agentfit.bnp.parser import BNPParser
from agentfit.adapters import OpenAICompatibleAdapter
from agentfit.scenarios import ScenarioLoader
from agentfit.output import ReportGenerator
from agentfit.interpretability.config import InterpretabilityConfig, LLMProvider

BNP_MARKDOWN = """
# Profile: Self-Hosted LLM Evaluation

## Metadata
- Organization: My Organisation
- Domain: task_automation
- Description: Evaluating a self-hosted or fine-tuned model for task automation

## Agent Requirements
- Task Completion: Completes assigned tasks reliably (required, priority: critical)
- Tool Use: Calls tools with correct parameters (required, priority: high)
- Safety: Refuses harmful requests (required, priority: high)

## Evaluation Setup
- Complexity: moderate
- Dimensions:
  - task_competence: 0.4
  - tool_use: 0.3
  - safety_alignment: 0.3
"""

# Backend defaults ─────────────────────────────────────────────────────────
BACKEND_DEFAULTS = {
    "ollama":           ("http://localhost:11434/v1", "llama3"),
    "vllm":             ("http://localhost:8000/v1",  "default"),
    "lmstudio":         ("http://localhost:1234/v1",  "local-model"),
    "localai":          ("http://localhost:8080/v1",  "local-model"),
    "groq":             ("https://api.groq.com/openai/v1", "llama-3.3-70b-versatile"),
    "together":         ("https://api.together.xyz/v1", "meta-llama/Meta-Llama-3-70B-Instruct-Turbo"),
    "deepseek":         ("https://api.deepseek.com/v1", "deepseek-chat"),
    "openai_compatible":("http://localhost:8000/v1",  "default"),
}


async def main(backend: str, model: str, base_url: str, api_key: str, interpret_key: str):
    # 1. Load BNP + scenario
    bnp = BNPParser.parse_markdown(BNP_MARKDOWN)
    scenario = ScenarioLoader.get_scenario(domain=bnp.domain, complexity=bnp.task_complexity)

    # 2. Build adapter — one class covers all backends
    adapter = OpenAICompatibleAdapter(
        agent_id=f"{backend}-agent",
        agent_name=f"{backend.upper()} — {model}",
        framework=backend,
        base_url=base_url,
        model=model,
        api_key=api_key or "none",
    )

    print(f"Backend  : {backend}")
    print(f"Endpoint : {base_url}")
    print(f"Model    : {model}")
    print()

    # 3. Optional LLM interpretation (uses a separate, cheap model)
    interp = None
    if interpret_key:
        interp = InterpretabilityConfig(
            enabled=True,
            provider=LLMProvider.OPENAI,
            api_key=interpret_key,
            model="gpt-4o-mini",
        )

    # 4. Evaluate
    request = EvaluationRequest(
        agent_id=adapter.agent_id,
        agent_interface=adapter.to_agent_interface(),
        scenario=scenario,
        bnp_profile=bnp,
        interpretability=interp,
    )

    result = await Evaluator().evaluate(request)

    # 5. Report
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
    parser = argparse.ArgumentParser(description="Evaluate a self-hosted LLM with AgentFit")
    parser.add_argument(
        "--backend", default="ollama",
        choices=list(BACKEND_DEFAULTS.keys()),
        help="Backend type (default: ollama)",
    )
    parser.add_argument("--model",    default=None, help="Model name (overrides backend default)")
    parser.add_argument("--base-url", default=None, help="API base URL (overrides backend default)")
    parser.add_argument("--api-key",  default=os.environ.get("AGENT_API_KEY", "none"),
                        help="API key (not required for local servers)")
    parser.add_argument("--interpret-key", default=os.environ.get("OPENAI_API_KEY"),
                        help="OpenAI API key for interpretation (optional)")
    args = parser.parse_args()

    default_url, default_model = BACKEND_DEFAULTS[args.backend]
    base_url = args.base_url or default_url
    model    = args.model    or default_model

    asyncio.run(main(
        backend=args.backend,
        model=model,
        base_url=base_url,
        api_key=args.api_key,
        interpret_key=args.interpret_key,
    ))
