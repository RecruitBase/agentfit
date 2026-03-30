# AgentFit Quick Start Guide

Get up and running with AgentFit in 5 minutes.

## Installation

```bash
cd /vercel/share/v0-project

# Install in development mode
pip install -e .
```

## Step 1: Create a Business Need Profile (BNP)

Create `my_bnp.md`:

```markdown
# Business Need Profile: Customer Support Agent

## Organization
- Name: TechCorp Customer Support
- Industry: SaaS

## Primary Task Domain
- Domain: Customer Support
- Difficulty: Medium (L2)

## Autonomy Level
- Required: human_in_loop
- Reasoning: Critical customer interactions need human approval

## Tool & System Integrations
- CRM System: Salesforce
- Knowledge Base: Internal Wiki
- Ticketing System: Jira
- Email System: Gmail API

## Latency Budget
- Target: < 5 seconds for standard queries
- Max: < 30 seconds for complex queries

## Data Sensitivity
- Class: Confidential
- Regulations: GDPR, SOC2
- Audit Requirements: Full audit trail required

## Infrastructure
- Deployment: On-premise Kubernetes
- Network: Airgapped environment
- Concurrent Users: 100+

## Success Criteria
- Must handle 95% of tickets autonomously
- Error rate < 2%
- 99.9% uptime SLA
```

## Step 2: Evaluate an Agent

### Using OpenAI

```python
import asyncio
from agentfit import (
    Evaluator,
    AgentAdapterRegistry,
    BNPParser,
)

async def main():
    # 1. Create agent using OpenAI adapter
    agent = AgentAdapterRegistry.create_agent(
        framework="openai",
        agent_id="gpt4-support",
        agent_name="GPT-4 Support Agent",
        model="gpt-4",
        api_key="sk-..."  # Your OpenAI API key
    )
    
    # 2. Load BNP
    bnp = BNPParser.parse_file("my_bnp.md")
    
    # 3. Define scenario
    scenario = {
        "task": "Respond to customer: 'My subscription isn't working'",
        "expected_steps": [
            "understand_issue",
            "look_up_customer",
            "check_system_status",
            "draft_response"
        ],
        "expected_tools": ["lookup_customer", "check_subscription"],
    }
    
    # 4. Evaluate
    evaluator = Evaluator()
    result = await evaluator.evaluate(
        agent=agent,
        bnp_profile=bnp,
        scenario=scenario,
    )
    
    # 5. View results
    print(f"\nOverall AgentFit Score: {result.overall_score:.2f}/1.00\n")
    
    for dim_id, dim_result in result.dimension_results.items():
        score_pct = dim_result.get_percentage()
        status = "✓" if dim_result.passed else "✗"
        print(f"{status} {dim_result.dimension_name}")
        print(f"   Score: {score_pct:.1f}%")
        print(f"   Feedback: {dim_result.feedback}\n")

asyncio.run(main())
```

### Using Anthropic

```python
agent = AgentAdapterRegistry.create_agent(
    framework="anthropic",
    agent_id="claude-support",
    agent_name="Claude Support Agent",
    model="claude-opus-4.6",
    api_key="sk-ant-..."  # Your Anthropic API key
)
```

### Using Google AgentKit

```python
agent = AgentAdapterRegistry.create_agent(
    framework="google_agentkit",
    agent_id="gemini-support",
    agent_name="Gemini Support Agent",
    model="gemini-3-flash",
    api_key="sk-..."  # Your Google API key
)
```

### Using Custom Agent

```python
# Your existing agent
my_agent = MyCustomAgent()

agent = AgentAdapterRegistry.create_agent(
    framework="generic",
    agent_id="custom-support",
    agent_name="Custom Support Agent",
    agent_callable=my_agent.execute
)
```

## Step 3: Compare Multiple Agents

```python
async def compare_agents():
    bnp = BNPParser.parse_file("my_bnp.md")
    scenario = {...}
    evaluator = Evaluator()
    
    agents = [
        AgentAdapterRegistry.create_agent("openai", "gpt4", "GPT-4", model="gpt-4"),
        AgentAdapterRegistry.create_agent("anthropic", "claude", "Claude", model="claude-opus-4.6"),
    ]
    
    print("=== Agent Comparison ===\n")
    for agent in agents:
        result = await evaluator.evaluate(agent=agent, bnp_profile=bnp, scenario=scenario)
        
        print(f"{agent.agent_name}:")
        print(f"  Overall Score: {result.overall_score:.2%}")
        
        for dim_id, dim_result in result.dimension_results.items():
            pct = dim_result.get_percentage()
            print(f"  {dim_result.dimension_name}: {pct:.0f}%")
        print()

asyncio.run(compare_agents())
```

## Step 4: Create a Custom Adapter

If you have a proprietary agent framework:

```python
from agentfit.protocol import (
    UniversalAgentProtocol,
    ExecutionResult,
    Message,
    MessageRole,
    AgentAdapterRegistry,
)
import asyncio

class MyFrameworkAdapter(UniversalAgentProtocol):
    """Adapter for my proprietary agent framework."""
    
    def __init__(self, agent_id, agent_name, my_agent):
        super().__init__(agent_id, agent_name, "my_framework")
        self.agent = my_agent
    
    async def execute_task(self, task, tools=None, context=None, max_steps=10, timeout_seconds=60):
        """Execute task with my agent."""
        try:
            start = asyncio.get_event_loop().time()
            
            # Call my agent
            result = await asyncio.wait_for(
                self.agent.run(task, tools=tools),
                timeout=timeout_seconds
            )
            
            # Normalize result
            return ExecutionResult(
                task_id=f"task-{start}",
                success=result.success,
                final_output=result.output,
                messages=[
                    Message(
                        role=MessageRole.USER,
                        content=task,
                    ),
                    Message(
                        role=MessageRole.ASSISTANT,
                        content=result.output,
                    ),
                ],
                tool_calls=[],
                tool_results=[],
                errors=result.errors if not result.success else [],
                total_steps=result.steps,
                execution_time_ms=(asyncio.get_event_loop().time() - start) * 1000,
            )
        
        except asyncio.TimeoutError:
            return ExecutionResult(
                task_id=f"task-{asyncio.get_event_loop().time()}",
                success=False,
                final_output=None,
                errors=[f"Timeout after {timeout_seconds}s"],
                execution_time_ms=timeout_seconds * 1000,
            )
    
    async def get_capabilities(self):
        """Report agent capabilities."""
        return {
            "framework": "my_framework",
            "supports_tools": True,
            "supports_parallel_tool_calls": False,
            "max_context_tokens": 4096,
        }
    
    async def validate_tools(self, tools):
        """Check tool compatibility."""
        return {
            "valid": True,
            "supported_tools": [t.name for t in tools],
            "unsupported_tools": [],
        }

# Register the adapter
AgentAdapterRegistry.register("my_framework", MyFrameworkAdapter)

# Use it
my_agent_instance = MyAgent()
agent = AgentAdapterRegistry.create_agent(
    framework="my_framework",
    agent_id="my-custom",
    agent_name="My Custom Agent",
    my_agent=my_agent_instance
)
```

## Step 5: Run via CLI

```bash
# Basic evaluation
agentfit evaluate \
    --bnp my_bnp.md \
    --output results.json

# With specific dimensions
agentfit evaluate \
    --bnp my_bnp.md \
    --evals task_competence,safety_alignment \
    --output results.json

# With verbose output
agentfit evaluate \
    --bnp my_bnp.md \
    --output results.json \
    --verbose

# List available dimensions
agentfit list-dimensions

# View BNP
agentfit show-bnp my_bnp.md
```

## Understanding the Results

### Overall Score
0-100% scale where:
- **90-100%**: Excellent fit for your organization
- **70-89%**: Good fit with some areas for improvement
- **50-69%**: Moderate fit with significant gaps
- **<50%**: Poor fit - major misalignment

### Dimension Scores

Each of the 7 dimensions has:
- **Score**: 0-100% for that dimension
- **Passed**: Yes/No - meets threshold for your org
- **Feedback**: Specific issues and recommendations

Example interpretation:

```
✓ Task Competence: 92%
   Agent can understand and execute tasks well

✗ Compliance & Auditability: 45%
   Audit trail logging is incomplete - critical for GDPR compliance

✓ Safety & Alignment: 87%
   Good resistance to adversarial attacks

✗ Deployment Compatibility: 62%
   Limited on-premise deployment support - needed for your airgapped environment
```

## Next Steps

1. **Customize BNP**: Adjust organization profile to match your needs
2. **Create Custom Adapter**: If using proprietary agents
3. **Run Evaluations**: Test multiple agents and compare
4. **Iterate**: Use results to improve agent selection or implementation
5. **Monitor**: Track agent performance over time

## Common Issues

### Q: "Agent not registered"
A: Make sure to register your adapter before creating an agent:
```python
AgentAdapterRegistry.register("my_framework", MyAdapter)
```

### Q: "Timeout errors"
A: Increase timeout_seconds in the scenario:
```python
scenario = {
    "task": "...",
    "timeout_seconds": 120,  # 2 minutes
}
```

### Q: "Tool validation fails"
A: Implement validate_tools in your adapter to handle unsupported tools gracefully.

### Q: "API key errors"
A: Ensure your API keys are valid and have appropriate permissions.

## Resources

- [Universal Agent Protocol](./UNIVERSAL_AGENT_PROTOCOL.md) - Detailed protocol docs
- [Evaluation Dimensions](./EVALUATION_DIMENSIONS.md) - Dimension specifications
- [BNP Schema](./BNP_SCHEMA.md) - Business Need Profile format
- [IMPLEMENTATION_SUMMARY.md](../IMPLEMENTATION_SUMMARY.md) - Technical overview

## Support

For issues or questions:

1. Check the documentation files
2. Review example implementations in `agentfit/adapters/`
3. Check existing BNP examples in `examples/`
4. Review error messages and debug logs

## Example Projects

Try these examples to get started:

```bash
# Customer support agent
agentfit evaluate --bnp examples/customer_service_bnp.md

# Code review agent
agentfit evaluate --bnp examples/code_review_bnp.md

# Data extraction agent
agentfit evaluate --bnp examples/data_extraction_bnp.md
```

Happy evaluating!
