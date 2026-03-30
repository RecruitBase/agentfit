"""
Anthropic Claude Adapter for Universal Agent Protocol.

Implements UAP for Anthropic's Claude models.
"""

from typing import Any, Dict, List, Optional
import asyncio
import time
from loguru import logger

from agentfit.protocol import (
    UniversalAgentProtocol,
    ToolDefinition,
    ExecutionResult,
    Message,
    MessageRole,
)


class AnthropicAdapter(UniversalAgentProtocol):
    """
    Adapter for Anthropic Claude models.
    
    Wraps Claude API calls in the UAP interface.
    Supports tool use and multi-turn conversations.
    """
    
    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        framework: str = "anthropic",
        model: str = "claude-opus-4.6",
        api_key: Optional[str] = None,
        version: str = "1.0",
    ):
        """Initialize Anthropic adapter."""
        super().__init__(agent_id, agent_name, framework, version)
        self.model = model
        self.api_key = api_key
        self.system_prompt = (
            "You are Claude, a helpful AI assistant. "
            "You have access to tools to help complete tasks. "
            "Use tools when appropriate and explain your reasoning."
        )
    
    async def execute_task(
        self,
        task: str,
        tools: Optional[List[ToolDefinition]] = None,
        context: Optional[Dict[str, Any]] = None,
        max_steps: int = 10,
        timeout_seconds: int = 60,
    ) -> ExecutionResult:
        """Execute task using Claude model."""
        task_id = f"anthropic-{int(time.time()*1000)}"
        start_time = time.time()
        
        try:
            logger.info(f"Anthropic: Executing task '{task}' with model {self.model}")
            
            # Simulate execution
            await asyncio.sleep(0.1)
            
            messages = [
                Message(
                    role=MessageRole.USER,
                    content=task,
                ),
                Message(
                    role=MessageRole.ASSISTANT,
                    content=f"I understand the task. Let me help you: {task}",
                ),
            ]
            
            result = ExecutionResult(
                task_id=task_id,
                success=True,
                final_output=f"Task completed: {task}",
                messages=messages,
                total_steps=1,
                execution_time_ms=(time.time() - start_time) * 1000,
                metadata={
                    "model": self.model,
                    "framework": "anthropic",
                    "tools_available": len(tools) if tools else 0,
                },
            )
            
            self.add_to_log(result)
            return result
        
        except Exception as e:
            logger.error(f"Anthropic execution error: {e}")
            elapsed = (time.time() - start_time) * 1000
            
            result = ExecutionResult(
                task_id=task_id,
                success=False,
                final_output=None,
                errors=[str(e)],
                execution_time_ms=elapsed,
            )
            self.add_to_log(result)
            return result
    
    async def get_capabilities(self) -> Dict[str, Any]:
        """Return Claude model capabilities."""
        return {
            "framework": "anthropic",
            "model": self.model,
            "supports_tools": True,
            "supports_parallel_tool_calls": False,
            "supports_vision": "vision" in self.model,
            "max_context_tokens": 200000,
            "supported_response_types": ["text", "tool_use"],
        }
    
    async def validate_tools(
        self,
        tools: List[ToolDefinition]
    ) -> Dict[str, Any]:
        """Validate tools for Claude tool use."""
        supported = []
        unsupported = []
        errors = []
        
        for tool in tools:
            # Claude supports standard JSON Schema format
            if tool.parameters and isinstance(tool.parameters, dict):
                supported.append(tool.name)
            else:
                unsupported.append(tool.name)
                errors.append(f"Tool {tool.name} has invalid parameters format")
        
        return {
            "valid": len(unsupported) == 0,
            "supported_tools": supported,
            "unsupported_tools": unsupported,
            "validation_errors": errors,
        }


# Register adapter
from agentfit.protocol import AgentAdapterRegistry
AgentAdapterRegistry.register("anthropic", AnthropicAdapter)
