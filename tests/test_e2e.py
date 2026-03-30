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