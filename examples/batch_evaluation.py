"""Example: Batch evaluate multiple agents.

This demonstrates how to evaluate multiple agents against the same
business requirements and compare results.
"""
import asyncio
from agentfit.core.evaluator import Evaluator, EvaluationRequest
from agentfit.adapters import OpenAIAdapter, AnthropicAdapter, GenericAdapter
from agentfit.bnp.schema import BNPProfile, Domain
from agentfit.output import ResultExporter


async def evaluate_agent(evaluator, agent_id, adapter, bnp_profile, dimensions):
    """Evaluate a single agent."""
    request = EvaluationRequest(
        agent_id=agent_id,
        agent_adapter=adapter,
        bnp_profile=bnp_profile,
        dimensions=dimensions
    )
    
    print(f"Evaluating {agent_id}...")
    result = await evaluator.evaluate(request)
    return result


async def main():
    """Batch evaluate multiple agents."""
    
    # Define shared requirements
    bnp_profile = BNPProfile(
        organization_name="MultiAgent Corp",
        industry="Enterprise",
        agent_domain=Domain.CUSTOMER_SERVICE,
        required_dimensions=[
            "task_competence",
            "tool_use",
            "safety_alignment",
            "operational_performance",
            "compliance_auditability"
        ]
    )
    
    # Define agents to evaluate
    agents = [
        {
            "id": "gpt-4-agent",
            "adapter": OpenAIAdapter(config={
                "model": "gpt-4-turbo",
                "api_key": "your-api-key"
            })
        },
        {
            "id": "claude-opus-agent",
            "adapter": AnthropicAdapter(config={
                "model": "claude-opus-4",
                "api_key": "your-api-key"
            })
        },
        {
            "id": "custom-local-agent",
            "adapter": GenericAdapter(config={
                "model": "local-llm",
                "timeout": 30
            })
        }
    ]
    
    dimensions = [
        "task_competence",
        "tool_use",
        "safety_alignment"
    ]
    
    # Run evaluations
    evaluator = Evaluator()
    results = {}
    
    print("="*70)
    print("BATCH AGENT EVALUATION")
    print("="*70 + "\n")
    
    for agent_config in agents:
        result = await evaluate_agent(
            evaluator,
            agent_config["id"],
            agent_config["adapter"],
            bnp_profile,
            dimensions
        )
        results[agent_config["id"]] = result
    
    # Compare results
    print("\n" + "="*70)
    print("EVALUATION RESULTS COMPARISON")
    print("="*70 + "\n")
    
    # Overall scores
    print("Overall Fitness Scores:")
    print("-" * 70)
    for agent_id, result in sorted(results.items(), 
                                   key=lambda x: x[1].overall_score, 
                                   reverse=True):
        score = result.overall_score
        bar_length = int(score * 35)
        bar = "█" * bar_length + "░" * (35 - bar_length)
        print(f"{agent_id:25} | {bar} | {score:6.1%}")
    
    # Dimension comparison
    print("\n" + "="*70)
    print("DIMENSION-BY-DIMENSION COMPARISON")
    print("="*70)
    
    for dimension in dimensions:
        print(f"\n{dimension.replace('_', ' ').upper()}:")
        print("-" * 70)
        
        for agent_id, result in sorted(results.items(),
                                       key=lambda x: x[1].dimension_scores.get(dimension, 0),
                                       reverse=True):
            score = result.dimension_scores.get(dimension, 0)
            bar_length = int(score * 30)
            bar = "█" * bar_length + "░" * (30 - bar_length)
            print(f"  {agent_id:23} | {bar} | {score:6.1%}")
    
    # Recommendation
    print("\n" + "="*70)
    print("RECOMMENDATION")
    print("="*70)
    
    best_agent_id = max(results.items(), key=lambda x: x[1].overall_score)[0]
    best_result = results[best_agent_id]
    
    print(f"\nBest Agent: {best_agent_id}")
    print(f"Overall Score: {best_result.overall_score:.1%}")
    print("\nStrengths:")
    for dim, score in best_result.dimension_scores.items():
        if score > 0.8:
            print(f"  ✓ {dim.replace('_', ' ').title()}: {score:.1%}")
    
    print("\nAreas for Improvement:")
    for dim, score in best_result.dimension_scores.items():
        if score < 0.7:
            print(f"  ✗ {dim.replace('_', ' ').title()}: {score:.1%}")
    
    # Export results
    print("\n" + "="*70)
    print("Exporting results...")
    
    exporter = ResultExporter()
    exporter.export_comparison(
        results=results,
        output_path="evaluation_results.json",
        format="json"
    )
    
    print("Results exported to: evaluation_results.json")
    print("="*70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
