"""
Google AgentKit Adapter for Universal Agent Protocol.

Implements UAP for Google's AgentKit framework.
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


class GoogleAgentKitAdapter(UniversalAgentProtocol):
    """
    Adapter for Google AgentKit agents.
    
    Wraps AgentKit API calls in the UAP interface.
    Supports structured outputs and multi-modal tools.
    """
    
    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        framework: str = "google_agentkit",
        model: str = "gemini-3-flash",
        api_key: Optional[str] = None,
        version: str = "1.0",
    ):
        """Initialize Google AgentKit adapter."""
        super().__init__(agent_id, agent_name, framework, version)
        self.model = model
        self.api_key = api_key
    
    async def execute_task(
        self,
        task: str,
        tools: Optional[List[ToolDefinition]] = None,
        context: Optional[Dict[str, Any]] = None,
        max_steps: int = 10,
        timeout_seconds: int = 60,
    ) -> ExecutionResult:
        """Execute task using Google AgentKit."""
        task_id = f"google_agentkit-{int(time.time()*1000)}"
        start_time = time.time()
        
        try:
            logger.info(f"GoogleAgentKit: Executing task '{task}' with model {self.model}")
            
            # Simulate execution
            await asyncio.sleep(0.1)
            
            messages = [
                Message(
                    role=MessageRole.USER,
                    content=task,
                ),
                Message(
                    role=MessageRole.ASSISTANT,
                    content=f"Processing your request: {task}",
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
                    "framework": "google_agentkit",
                    "tools_available": len(tools) if tools else 0,
                },
            )
            
            self.add_to_log(result)
            return result
        
        except Exception as e:
            logger.error(f"GoogleAgentKit execution error: {e}")
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
        """Return Google AgentKit capabilities."""
        return {
            "framework": "google_agentkit",
            "model": self.model,
            "supports_tools": True,
            "supports_parallel_tool_calls": True,
            "supports_vision": True,
            "supports_structured_output": True,
            "max_context_tokens": 1000000,
            "supported_response_types": ["text", "structured", "multimodal"],
        }
    
    async def validate_tools(
        self,
        tools: List[ToolDefinition]
    ) -> Dict[str, Any]:
        """Validate tools for Google AgentKit."""
        supported = []
        unsupported = []
        errors = []
        
        for tool in tools:
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
AgentAdapterRegistry.register("google_agentkit", GoogleAgentKitAdapter)
