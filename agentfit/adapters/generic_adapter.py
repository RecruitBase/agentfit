"""
Generic/Custom Agent Adapter for Universal Agent Protocol.

Implements UAP for custom or user-provided agents.
Supports callable-based agents and frameworks not otherwise covered.
"""

from typing import Any, Dict, List, Optional, Callable
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


class GenericAdapter(UniversalAgentProtocol):
    """
    Generic adapter for custom/user-defined agents.
    
    Wraps any callable agent in the UAP interface.
    Supports both sync and async callables.
    """
    
    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        framework: str = "generic",
        agent_callable: Optional[Callable] = None,
        version: str = "1.0",
    ):
        """
        Initialize generic adapter.
        
        Args:
            agent_id: Unique identifier
            agent_name: Human-readable name
            framework: Framework identifier (default: "generic")
            agent_callable: Callable that executes the agent (optional)
            version: Agent version
        """
        super().__init__(agent_id, agent_name, framework, version)
        self.agent_callable = agent_callable
    
    async def execute_task(
        self,
        task: str,
        tools: Optional[List[ToolDefinition]] = None,
        context: Optional[Dict[str, Any]] = None,
        max_steps: int = 10,
        timeout_seconds: int = 60,
    ) -> ExecutionResult:
        """Execute task using the provided agent callable."""
        task_id = f"generic-{int(time.time()*1000)}"
        start_time = time.time()
        
        try:
            if not self.agent_callable:
                raise ValueError("No agent callable provided")
            
            logger.info(f"Generic: Executing task with agent '{self.agent_name}'")
            
            # Prepare execution context
            exec_context = {
                "task": task,
                "tools": tools or [],
                "context": context or {},
                "max_steps": max_steps,
            }
            
            # Execute agent (support both sync and async)
            if asyncio.iscoroutinefunction(self.agent_callable):
                output = await asyncio.wait_for(
                    self.agent_callable(task, tools=tools, context=context),
                    timeout=timeout_seconds
                )
            else:
                # Run sync callable in executor to avoid blocking
                loop = asyncio.get_event_loop()
                output = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        self.agent_callable,
                        task,
                    ),
                    timeout=timeout_seconds
                )
            
            messages = [
                Message(
                    role=MessageRole.USER,
                    content=task,
                ),
                Message(
                    role=MessageRole.ASSISTANT,
                    content=str(output),
                ),
            ]
            
            result = ExecutionResult(
                task_id=task_id,
                success=True,
                final_output=output,
                messages=messages,
                total_steps=1,
                execution_time_ms=(time.time() - start_time) * 1000,
                metadata={
                    "framework": "generic",
                    "agent_callable": self.agent_callable.__name__ if hasattr(self.agent_callable, "__name__") else "unknown",
                    "tools_available": len(tools) if tools else 0,
                },
            )
            
            self.add_to_log(result)
            return result
        
        except asyncio.TimeoutError:
            logger.warning(f"Generic adapter timeout after {timeout_seconds}s")
            elapsed = (time.time() - start_time) * 1000
            
            result = ExecutionResult(
                task_id=task_id,
                success=False,
                final_output=None,
                errors=[f"Execution timeout after {timeout_seconds} seconds"],
                execution_time_ms=elapsed,
            )
            self.add_to_log(result)
            return result
        
        except Exception as e:
            logger.error(f"Generic adapter execution error: {e}")
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
        """Return generic agent capabilities."""
        return {
            "framework": "generic",
            "agent_name": self.agent_name,
            "supports_tools": False,  # Custom agents may vary
            "supports_parallel_tool_calls": False,
            "is_custom_agent": True,
            "supported_response_types": ["text", "raw"],
        }
    
    async def validate_tools(
        self,
        tools: List[ToolDefinition]
    ) -> Dict[str, Any]:
        """
        Generic agents don't have tool validation.
        Return that tools are provided but not validated.
        """
        return {
            "valid": True,
            "supported_tools": [t.name for t in tools],
            "unsupported_tools": [],
            "validation_errors": [],
            "note": "Generic agent does not validate tools - responsibility falls on the agent implementation",
        }


# Register adapter
from agentfit.protocol import AgentAdapterRegistry
AgentAdapterRegistry.register("generic", GenericAdapter)
