"""Example: Create a custom agent adapter.

This demonstrates how to implement a custom adapter for your own
agent framework that integrates with AgentFit.
"""
from agentfit.protocol import UniversalAgentProtocol, Message, MessageRole
from agentfit.protocol import ToolCall, ToolResult, ExecutionResult, ToolResultType


class MyCustomAgentAdapter(UniversalAgentProtocol):
    """Custom adapter for an internal agent framework."""
    
    def __init__(self, config: dict):
        """Initialize the adapter.
        
        Args:
            config: Configuration dict for your agent
                    (API keys, model params, etc.)
        """
        super().__init__(config)
        self.agent_instance = self._initialize_agent(config)
    
    def _initialize_agent(self, config):
        """Initialize your actual agent."""
        # This is where you initialize your custom agent
        # For demo purposes, we're creating a simple mock
        class MockAgent:
            def __init__(self, cfg):
                self.config = cfg
                self.conversation_history = []
            
            def chat(self, message):
                # Your agent's logic here
                return f"Response to: {message}"
            
            def call_tool(self, tool_name, args):
                # Your agent's tool calling logic
                return {"status": "success", "result": f"Called {tool_name}"}
        
        return MockAgent(config)
    
    async def execute(self, messages: list[Message], tools: list = None) -> ExecutionResult:
        """Execute the agent on the given messages.
        
        This is the main method that AgentFit calls to evaluate your agent.
        
        Args:
            messages: List of messages in the conversation
            tools: List of available tools
            
        Returns:
            ExecutionResult with output and metadata
        """
        try:
            # Convert messages to your agent's format
            formatted_messages = [self._format_message(msg) for msg in messages]
            
            # Get the latest user message
            latest_message = next(
                (m.content for m in messages if m.role == MessageRole.USER),
                "No user message found"
            )
            
            # Call your agent
            response = self.agent_instance.chat(latest_message)
            
            # Extract tool calls if any (your agent-specific logic)
            tool_calls = self._extract_tool_calls(response)
            
            return ExecutionResult(
                success=True,
                message="Execution successful",
                output=response,
                metadata={
                    "tool_calls": len(tool_calls),
                    "agent_framework": "custom"
                }
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                message=f"Execution failed: {str(e)}",
                output=None,
                error=str(e)
            )
    
    def _format_message(self, message: Message) -> dict:
        """Convert UniversalAgentProtocol Message to your agent's format."""
        return {
            "role": message.role.value,
            "content": message.content,
            "tool_calls": message.tool_calls
        }
    
    def _extract_tool_calls(self, response: str) -> list[ToolCall]:
        """Extract tool calls from your agent's response.
        
        This depends on how your agent signals tool calls.
        For example, it might use XML, JSON, or function calls.
        """
        # Example: Look for [TOOL: tool_name]
        tool_calls = []
        # Parse your agent's response format here
        return tool_calls
    
    async def process_tool_result(self, tool_call_id: str, result: ToolResult) -> Message:
        """Process a tool result and return the next message.
        
        Args:
            tool_call_id: ID of the tool call
            result: Result from executing the tool
            
        Returns:
            Message with processed result
        """
        content = f"Tool {result.tool_call_id} returned: {result.result}"
        return Message(
            role=MessageRole.ASSISTANT,
            content=content
        )


# Example usage
if __name__ == "__main__":
    import asyncio
    
    # Initialize your custom adapter
    config = {
        "model": "my-custom-model",
        "temperature": 0.7,
        "max_tokens": 1000
    }
    adapter = MyCustomAgentAdapter(config=config)
    
    # Create a simple conversation
    messages = [
        Message(role=MessageRole.USER, content="What is 2+2?")
    ]
    
    # Execute the agent
    result = asyncio.run(adapter.execute(messages))
    
    print("Agent Response:")
    print(f"  Success: {result.success}")
    print(f"  Output: {result.output}")
    print(f"  Metadata: {result.metadata}")
    
    print("\nHow to integrate with AgentFit:")
    print("1. Register your adapter: AgentAdapterRegistry.register(MyCustomAgentAdapter)")
    print("2. Use in evaluation: eval_request = EvaluationRequest(..., agent_adapter=adapter)")
    print("3. Run evaluation: result = await evaluator.evaluate(eval_request)")
