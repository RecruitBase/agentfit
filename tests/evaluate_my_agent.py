import asyncio
from agentfit.core.evaluator import Evaluator, EvaluationRequest
from agentfit.adapters import OpenAIAdapter
from agentfit.bnp.schema import BNPProfile, Domain
from agentfit.scenarios import ScenarioLoader


async def main():
    # 1. Define your organization's needs
    bnp_profile = BNPProfile(
        organization_name="My Company",
        industry="Technology",
        agent_domain=Domain.CUSTOMER_SERVICE,
        required_dimensions=[
            "task_competence",
            "tool_use",
            "safety_alignment"
        ]
    )
    
    # 2. Create an adapter for your agent
    # For OpenAI:
    adapter = OpenAIAdapter(
        agent_id="my-agent-v1",
        agent_name="My Agent",
        model="gpt-4-turbo",
        api_key="your-openai-api-key",
    )
    scenario = ScenarioLoader.get_scenario(
        domain=bnp_profile.domain,
        complexity=bnp_profile.task_complexity.value,
    )
    
    # 3. Create evaluation request
    request = EvaluationRequest(
        agent_id="my-agent-v1",
        agent_interface=adapter,
        scenario=scenario,
        bnp_profile=bnp_profile
    )
    
    # 4. Run evaluation
    evaluator = Evaluator()
    result = await evaluator.evaluate(request)
    
    # 5. View results
    print(f"\nAgent: {result.agent_id}")
    print(f"Overall Score: {result.overall_score:.1%}")
    print("\nDimension Scores:")
    for dimension, dimension_result in result.dimension_results.items():
        print(f"  {dimension.replace('_', ' ').title()}: {dimension_result.score:.1%}")


if __name__ == "__main__":
    asyncio.run(main())
