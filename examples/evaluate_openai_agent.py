"""Example: Evaluate an OpenAI-based agent.

This example demonstrates how to use AgentFit to evaluate an agent
built with OpenAI's API.
"""
import asyncio
from agentfit.core.evaluator import Evaluator, EvaluationRequest
from agentfit.adapters import OpenAIAdapter
from agentfit.bnp.schema import BNPProfile, Domain
from agentfit.scenarios import ScenarioGenerator


async def main():
    """Run evaluation on an OpenAI agent."""
    
    # 1. Create a BNP profile for your organization
    bnp_profile = BNPProfile(
        organization_name="Tech Startup",
        industry="Software Development",
        agent_domain=Domain.CUSTOMER_SERVICE,
        required_dimensions=[
            "task_competence",
            "tool_use",
            "safety_alignment",
            "operational_performance"
        ],
        performance_requirements={
            "max_latency_ms": 5000,
            "min_throughput_req_per_sec": 10,
            "max_cost_per_request": 0.10
        }
    )
    
    # 2. Initialize the OpenAI adapter with your agent
    adapter_config = {
        "api_key": "your-openai-api-key",
        "model": "gpt-4-turbo",
        "timeout": 30
    }
    adapter = OpenAIAdapter(config=adapter_config)
    
    # 3. Generate test scenarios for your domain
    scenario_gen = ScenarioGenerator()
    scenarios = scenario_gen.generate_for_domain(
        domain=Domain.CUSTOMER_SERVICE,
        complexity_levels=["basic", "intermediate"],
        count=5
    )
    
    print(f"Generated {len(scenarios)} test scenarios\n")
    
    # 4. Create evaluation request
    eval_request = EvaluationRequest(
        agent_id="openai-agent-v1",
        agent_adapter=adapter,
        bnp_profile=bnp_profile,
        dimensions=[
            "task_competence",
            "tool_use",
            "safety_alignment",
            "operational_performance"
        ],
        test_scenarios=scenarios
    )
    
    # 5. Run evaluation
    evaluator = Evaluator()
    print("Running evaluation...")
    result = await evaluator.evaluate(eval_request)
    
    # 6. Display results
    print("\n" + "="*60)
    print(f"EVALUATION RESULTS FOR {eval_request.agent_id}")
    print("="*60)
    print(f"Overall Score: {result.overall_score:.2%}\n")
    
    print("Dimension Scores:")
    for dimension, score in result.dimension_scores.items():
        print(f"  {dimension.replace('_', ' ').title()}: {score:.2%}")
    
    # 7. Print detailed analysis
    if hasattr(result, 'detailed_analysis'):
        print("\nDetailed Analysis:")
        for dim, analysis in result.detailed_analysis.items():
            print(f"\n  {dim.replace('_', ' ').title()}:")
            print(f"    Strengths: {analysis.get('strengths', [])}")
            print(f"    Weaknesses: {analysis.get('weaknesses', [])}")
    
    print("\n" + "="*60)
    
    return result


if __name__ == "__main__":
    result = asyncio.run(main())
