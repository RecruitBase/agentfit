"""Example: Evaluate an Anthropic Claude-based agent.

This example demonstrates how to evaluate an agent built with
Anthropic's Claude API.
"""
import asyncio
from agentfit.core.evaluator import Evaluator, EvaluationRequest
from agentfit.adapters import AnthropicAdapter
from agentfit.bnp.schema import BNPProfile, Domain


async def main():
    """Run evaluation on an Anthropic agent."""
    
    # 1. Define your organization's needs
    bnp_profile = BNPProfile(
        organization_name="Enterprise Corp",
        industry="Financial Services",
        agent_domain=Domain.DATA_ANALYSIS,
        required_dimensions=[
            "task_competence",
            "compliance_auditability",
            "safety_alignment",
            "operational_performance"
        ],
        compliance_requirements={
            "gdpr": True,
            "hipaa": False,
            "sox": True
        }
    )
    
    # 2. Configure the Anthropic adapter
    adapter_config = {
        "api_key": "your-anthropic-api-key",
        "model": "claude-opus-4",
        "timeout": 60
    }
    adapter = AnthropicAdapter(config=adapter_config)
    
    # 3. Create evaluation request
    eval_request = EvaluationRequest(
        agent_id="anthropic-agent-production",
        agent_adapter=adapter,
        bnp_profile=bnp_profile,
        dimensions=[
            "task_competence",
            "compliance_auditability",
            "safety_alignment"
        ]
    )
    
    # 4. Run evaluation
    evaluator = Evaluator()
    print("Starting evaluation of Anthropic-based agent...\n")
    result = await evaluator.evaluate(eval_request)
    
    # 5. Display results
    print("\n" + "="*70)
    print(f"ANTHROPIC AGENT EVALUATION - {eval_request.agent_id}")
    print("="*70)
    print(f"\nOverall Fitness Score: {result.overall_score:.1%}\n")
    
    print("Dimension Breakdown:")
    print("-" * 70)
    for dimension in sorted(result.dimension_scores.keys()):
        score = result.dimension_scores[dimension]
        bar_length = int(score * 30)
        bar = "█" * bar_length + "░" * (30 - bar_length)
        print(f"{dimension:30} | {bar} | {score:6.1%}")
    
    print("-" * 70)
    print(f"Overall Score:                    ", end="")
    bar_length = int(result.overall_score * 30)
    bar = "█" * bar_length + "░" * (30 - bar_length)
    print(f"| {bar} | {result.overall_score:6.1%}")
    
    # 6. Compliance assessment
    print("\nCompliance Assessment:")
    print(f"  GDPR Compliant: {'✓' if result.overall_score > 0.7 else '✗'}")
    print(f"  SOX Audit Ready: {'✓' if result.overall_score > 0.75 else '✗'}")
    
    print("\n" + "="*70)


if __name__ == "__main__":
    asyncio.run(main())
