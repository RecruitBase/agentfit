# Universal Agent Protocol (UAP)

## Overview

The Universal Agent Protocol (UAP) is a standardized interface that enables integration of diverse AI agent frameworks and implementations into the AgentFit evaluation engine without framework-specific dependencies.

The protocol allows any agent framework or custom agent implementation to be evaluated using AgentFit's 7 evaluation dimensions, regardless of whether it's built with OpenAI, Anthropic, Google AgentKit, OpenClaw, or custom implementations.

## Core Philosophy

- **Framework Agnostic**: Abstracts away framework differences
- **Pluggable Adapters**: Add new framework support without core changes
- **Minimal Interface**: Only requires implementing 3-4 key methods
- **Normalized Communication**: Standardized message and response formats
- **Zero Framework Dependencies**: Core protocol has no vendor lock-in

## Protocol Structure

### 1. UniversalAgentProtocol (Base Interface)

All agents must implement this abstract base class:

```python
class UniversalAgentProtocol(ABC):
    async def execute_task(
        self,
        task: str,
        tools: Optional[List[ToolDefinition]] = None,
        context: Optional[Dict[str, Any]] = None,
        max_steps: int = 10,
        timeout_seconds: int = 60,
    ) -> ExecutionResult
```

**Required Methods:**

1. **execute_task** - Execute a task with the agent
   - Input: task description, available tools, context
   - Output: ExecutionResult with normalized format
   - Handles timeouts, errors, tool calls

2. **get_capabilities** - Report agent capabilities
   - Returns: Dict describing features (tool support, context window, etc.)
   - Allows evaluation system to adapt tests

3. **validate_tools** - Verify tool compatibility
   - Input: List of ToolDefinition objects
   - Output: Validation report with supported/unsupported tools
   - Allows graceful degradation if tools not available

### 2. Message Format (Standard)

All communication uses a normalized message format:

```python
@dataclass
class Message:
    role: MessageRole  # "user", "assistant", "tool", "system"
    content: str       # Message text
    message_id: str    # UUID for tracking
    timestamp: datetime
    tool_calls: List[ToolCall]  # Tools invoked
    metadata: Dict[str, Any]    # Additional context
```

### 3. Tool Interface (Standardized)

Tools are defined with JSON Schema:

```python
@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema format
    required_params: List[str]
    returns: Optional[Dict[str, Any]]
```

Example:

```python
ToolDefinition(
    name="search_documents",
    description="Search internal document repository",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "max_results": {"type": "integer", "default": 10}
        }
    },
    required_params=["query"]
)
```

### 4. Execution Result (Normalized)

All agents return standardized execution results:

```python
@dataclass
class ExecutionResult:
    task_id: str
    success: bool
    final_output: Any
    messages: List[Message]       # Full conversation
    tool_calls: List[ToolCall]    # All tools called
    tool_results: List[ToolResult]  # All tool outputs
    errors: List[str]
    total_steps: int
    execution_time_ms: float
```

## Creating Custom Adapters

### Step 1: Inherit from UniversalAgentProtocol

```python
from agentfit.protocol import UniversalAgentProtocol, ExecutionResult

class CustomAgentAdapter(UniversalAgentProtocol):
    def __init__(self, agent_id: str, agent_name: str, agent_instance):
        super().__init__(agent_id, agent_name, "custom_framework")
        self.agent = agent_instance
```

### Step 2: Implement execute_task

```python
async def execute_task(
    self,
    task: str,
    tools: Optional[List[ToolDefinition]] = None,
    context: Optional[Dict[str, Any]] = None,
    max_steps: int = 10,
    timeout_seconds: int = 60,
) -> ExecutionResult:
    task_id = f"task-{uuid.uuid4()}"
    start_time = time.time()
    
    try:
        # 1. Convert tools to framework format (if needed)
        framework_tools = self._convert_tools(tools)
        
        # 2. Call your agent
        result = await self.agent.run(
            task,
            tools=framework_tools,
            max_steps=max_steps,
            timeout=timeout_seconds
        )
        
        # 3. Convert result to ExecutionResult
        return ExecutionResult(
            task_id=task_id,
            success=result.success,
            final_output=result.output,
            messages=[...],  # Convert framework messages
            tool_calls=[...], # Normalize tool calls
            tool_results=[...], # Normalize results
            errors=result.errors,
            total_steps=result.steps,
            execution_time_ms=(time.time() - start_time) * 1000
        )
    
    except Exception as e:
        return ExecutionResult(
            task_id=task_id,
            success=False,
            final_output=None,
            errors=[str(e)],
            execution_time_ms=(time.time() - start_time) * 1000
        )
```

### Step 3: Implement get_capabilities

```python
async def get_capabilities(self) -> Dict[str, Any]:
    return {
        "framework": "custom_framework",
        "supports_tools": True,
        "supports_parallel_tool_calls": False,
        "max_context_tokens": self.agent.config.max_tokens,
        "supported_response_types": ["text", "tool_calls"],
    }
```

### Step 4: Implement validate_tools

```python
async def validate_tools(self, tools: List[ToolDefinition]) -> Dict[str, Any]:
    supported = []
    unsupported = []
    
    for tool in tools:
        if self.agent.supports_tool(tool.name):
            supported.append(tool.name)
        else:
            unsupported.append(tool.name)
    
    return {
        "valid": len(unsupported) == 0,
        "supported_tools": supported,
        "unsupported_tools": unsupported,
    }
```

### Step 5: Register the Adapter

```python
from agentfit.protocol import AgentAdapterRegistry

AgentAdapterRegistry.register("my_framework", CustomAgentAdapter)
```

## Example Adapters

### OpenAI/GPT Adapter

```python
from agentfit.protocol import UniversalAgentProtocol

class OpenAIAdapter(UniversalAgentProtocol):
    def __init__(self, agent_id, agent_name, model="gpt-4", api_key=None):
        super().__init__(agent_id, agent_name, "openai")
        self.model = model
        self.api_key = api_key
    
    async def execute_task(self, task, tools=None, **kwargs):
        # Implement OpenAI API calls
        # Convert tools to OpenAI function format
        # Return normalized ExecutionResult
        pass
```

### Anthropic Claude Adapter

```python
class AnthropicAdapter(UniversalAgentProtocol):
    def __init__(self, agent_id, agent_name, model="claude-opus", api_key=None):
        super().__init__(agent_id, agent_name, "anthropic")
        self.model = model
        self.api_key = api_key
    
    async def execute_task(self, task, tools=None, **kwargs):
        # Implement Anthropic API calls
        # Convert tools to Claude tool_use format
        # Return normalized ExecutionResult
        pass
```

### Custom In-House Agent Adapter

```python
class InHouseAgentAdapter(UniversalAgentProtocol):
    def __init__(self, agent_id, agent_name, agent_callable):
        super().__init__(agent_id, agent_name, "inhouse")
        self.agent = agent_callable
    
    async def execute_task(self, task, tools=None, **kwargs):
        # Call custom agent
        # Track execution with logging
        # Return normalized ExecutionResult
        pass
```

## Usage with AgentFit

Once registered, use any adapter with AgentFit:

```python
from agentfit import Evaluator, AgentAdapterRegistry
from agentfit.bnp import BNPParser

# Create agent using adapter
agent = AgentAdapterRegistry.create_agent(
    framework="openai",
    agent_id="gpt4-v1",
    agent_name="GPT-4 Agent",
    model="gpt-4",
    api_key="sk-..."
)

# Parse BNP
bnp = BNPParser.parse_file("my_bnp.md")

# Create scenario
scenario = {
    "task": "Analyze customer support ticket",
    "expected_steps": ["understand", "classify", "respond"],
}

# Evaluate
evaluator = Evaluator()
result = await evaluator.evaluate(
    agent=agent,
    bnp_profile=bnp,
    scenario=scenario,
    dimensions=["task_competence", "tool_use", "safety_alignment"]
)

print(result)
```

## Message Format Examples

### Tool Call Message

```python
Message(
    role=MessageRole.ASSISTANT,
    content="I'll search for relevant documents.",
    tool_calls=[
        ToolCall(
            tool_name="search_documents",
            parameters={"query": "customer support policies"}
        )
    ]
)
```

### Tool Result Message

```python
Message(
    role=MessageRole.TOOL,
    content="Found 3 relevant documents",
    metadata={
        "tool_call_id": "call-123",
        "execution_time_ms": 245
    }
)
```

## Protocol Versioning

Current version: **1.0**

The protocol uses semantic versioning. Adapters should declare their compatibility:

```python
class MyAdapter(UniversalAgentProtocol):
    PROTOCOL_VERSION = "1.0"
    
    async def get_capabilities(self):
        return {
            "protocol_version": self.PROTOCOL_VERSION,
            ...
        }
```

## Error Handling

All exceptions must be caught and returned in ExecutionResult.errors:

```python
try:
    result = await agent.execute(task)
except TimeoutError:
    return ExecutionResult(
        task_id=task_id,
        success=False,
        final_output=None,
        errors=["Execution timeout after 60 seconds"]
    )
except ToolNotFoundError as e:
    return ExecutionResult(
        task_id=task_id,
        success=False,
        final_output=None,
        errors=[f"Tool '{e.tool_name}' not found"]
    )
```

## Performance Considerations

1. **Timeouts**: Always respect timeout_seconds parameter
2. **Resource Limits**: Handle memory/CPU constraints gracefully
3. **Concurrent Execution**: Support parallel task execution
4. **Caching**: Cache tool definitions and capabilities when possible
5. **Logging**: Include execution logs for debugging

## Security Guidelines

1. **API Key Management**: Never log or expose API keys
2. **Tool Validation**: Always validate tool parameters before execution
3. **Input Sanitization**: Sanitize task inputs if needed
4. **Rate Limiting**: Implement rate limiting for external APIs
5. **Audit Trail**: Maintain complete audit logs for compliance

## Contributing Custom Adapters

To contribute your adapter:

1. Create a new file: `agentfit/adapters/yourframework_adapter.py`
2. Implement UniversalAgentProtocol
3. Include comprehensive docstrings
4. Add unit tests
5. Submit PR with documentation

## FAQ

**Q: Do I need to modify my existing agent code?**
A: No. The adapter sits between your agent and AgentFit, translating between formats.

**Q: Can I use multiple adapters?**
A: Yes. Register multiple adapters and switch between them as needed.

**Q: What if my agent doesn't support a feature (e.g., tools)?**
A: Return False in capabilities and handle gracefully. AgentFit adapts.

**Q: How do I handle framework-specific features?**
A: Store in ExecutionResult.metadata for optional consumption.

**Q: What about async vs sync agents?**
A: GenericAdapter supports both using asyncio.to_thread for sync callables.

## See Also

- [Evaluation Dimensions](./EVALUATION_DIMENSIONS.md)
- [BNP Schema](./BNP_SCHEMA.md)
- [API Reference](./API_REFERENCE.md)
