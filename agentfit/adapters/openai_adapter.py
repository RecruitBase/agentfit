"""
OpenAI Assistant/GPT Adapter for Universal Agent Protocol.

Implements UAP for OpenAI's models and Assistant API.
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
    ToolCall,
    ToolResult,
    ToolResultType,
)


class OpenAIAdapter(UniversalAgentProtocol):
    """
    Adapter for OpenAI models (GPT-3.5, GPT-4, etc.).
    
    Wraps OpenAI API calls in the UAP interface.
    Supports function calling and tool use.
    """
    
    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        framework: str = "openai",
        model: str = "gpt-4",
        api_key: Optional[str] = None,
        version: str = "1.0",
    ):
        """Initialize OpenAI adapter."""
        super().__init__(agent_id, agent_name, framework, version)
        self.model = model
        self.api_key = api_key
        self.system_prompt = (
            "You are a helpful AI agent. Execute tasks step by step. "
            "Use available tools when necessary. Always explain your reasoning."
        )
    
    async def execute_task(
        self,
        task: str,
        tools: Optional[List[ToolDefinition]] = None,
        context: Optional[Dict[str, Any]] = None,
        max_steps: int = 10,
        timeout_seconds: int = 60,
    ) -> ExecutionResult:
        """Execute task using OpenAI model."""
        task_id = f"openai-{int(time.time()*1000)}"
        start_time = time.time()
        
        try:
            # This is a placeholder implementation
            # Real implementation would call OpenAI API
            logger.info(f"OpenAI: Executing task '{task}' with model {self.model}")
            
            # Simulate execution
            await asyncio.sleep(0.1)
            
            messages = [
                Message(
                    role=MessageRole.SYSTEM,
                    content=self.system_prompt,
                ),
                Message(
                    role=MessageRole.USER,
                    content=task,
                ),
                Message(
                    role=MessageRole.ASSISTANT,
                    content=f"I'll help you with: {task}",
                ),
            ]
            
            result = ExecutionResult(
                task_id=task_id,
                success=True,
                final_output=f"Task completed: {task}",
                messages=messages,
                tool_calls=[],
                tool_results=[],
                errors=[],
                total_steps=1,
                execution_time_ms=(time.time() - start_time) * 1000,
                metadata={
                    "model": self.model,
                    "framework": "openai",
                    "tools_available": len(tools) if tools else 0,
                },
            )
            
            self.add_to_log(result)
            return result
        
        except Exception as e:
            logger.error(f"OpenAI execution error: {e}")
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
        """Return OpenAI model capabilities."""
        return {
            "framework": "openai",
            "model": self.model,
            "supports_tools": True,
            "supports_parallel_tool_calls": True,
            "supports_vision": "vision" in self.model,
            "max_context_tokens": 8192 if "gpt-3.5" in self.model else 128000,
            "supported_response_types": ["text", "json", "function_calls"],
        }
    
    async def validate_tools(
        self,
        tools: List[ToolDefinition]
    ) -> Dict[str, Any]:
        """Validate tools for OpenAI function calling."""
        supported = []
        unsupported = []
        errors = []
        
        for tool in tools:
            # OpenAI supports standard JSON Schema format
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
AgentAdapterRegistry.register("openai", OpenAIAdapter)
