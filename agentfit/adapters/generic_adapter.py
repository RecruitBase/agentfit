"""
Generic/Custom Agent Adapter for Universal Agent Protocol.

Implements UAP for custom or user-provided agents.
Supports callable-based agents and frameworks not otherwise covered.
"""

from typing import Any, Dict, List, Optional, Callable
import asyncio
import inspect
import time
from loguru import logger

from agentfit.protocol import (
    UniversalAgentProtocol,
    ToolDefinition,
    ExecutionResult,
    Message,
    MessageRole,
)
from agentfit.protocol.environment_capture import EnvironmentCapture


def _supported_kwargs(func: Callable, candidates: Dict[str, Any]) -> Dict[str, Any]:
    """
    Filter `candidates` down to whichever keyword args `func` actually accepts.

    GenericAdapter wraps arbitrary user callables, which range from a bare
    `lambda task: ...` up to `async def agent(task, tools=None, context=None)`.
    Always forwarding tools/context unconditionally would break every
    simpler callable with a TypeError ("unexpected keyword argument"). This
    inspects the callable's signature so both styles work: callables that
    declare (or accept **kwargs for) `tools`/`context` receive them —
    needed so bridge functions can read `context["conversation_history"]`
    during loop testing — while simpler callables are still called with
    just `task`, unchanged from before.
    """
    try:
        params = inspect.signature(func).parameters
    except (TypeError, ValueError):
        # Some callables (certain builtins, C extensions) aren't
        # introspectable — fail safe by passing nothing extra rather than
        # risking a spurious TypeError on every call.
        return {}

    accepts_kwargs = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values())
    return {
        name: value
        for name, value in candidates.items()
        if accepts_kwargs or name in params
    }


class GenericAdapter(UniversalAgentProtocol):
    """
    Generic adapter for custom/user-defined agents.

    Wraps any callable agent in the UAP interface.
    Supports both sync and async callables.

    Conversation-history convention (used by AgentFit's loop-testing mode):
    during a multi-turn simulated conversation, the orchestrator passes the
    prior turns as `context["conversation_history"]` — a list of
    {"role": "user"|"assistant", "content": str} dicts, oldest first. Bridge
    callables that want multi-turn memory should read that key themselves
    (this adapter has no chat state of its own to seed it with); callables
    that ignore `context` simply behave statelessly per call, same as today.
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
            
            # Only pass tools/context to callables that actually declare
            # (or **kwargs-accept) them — see _supported_kwargs() above.
            # Both the sync and async paths use the same filtered kwargs so
            # a bridge callable behaves identically regardless of whether
            # it happens to be sync or async.
            call_kwargs = _supported_kwargs(
                self.agent_callable, {"tools": tools, "context": context}
            )

            # Execute agent (support both sync and async), capturing actual
            # OS-level side effects (network/filesystem/process) on whichever
            # thread runs the callable — independent of whatever the
            # callable's return value claims it did.
            if asyncio.iscoroutinefunction(self.agent_callable):
                with EnvironmentCapture() as cap:
                    output = await asyncio.wait_for(
                        self.agent_callable(task, **call_kwargs),
                        timeout=timeout_seconds
                    )
                environment_events = cap.to_list()
            else:
                # Run sync callable in executor to avoid blocking; the
                # capture must be entered on that worker thread, not here.
                #
                # NOTE: tools/context are forwarded here too (matching the
                # async branch above) when the callable accepts them, so
                # sync bridge callables can read
                # context["conversation_history"] during loop testing —
                # previously this dropped both silently and unconditionally,
                # making history unreachable for every sync callable.
                def _run_sync_callable():
                    with EnvironmentCapture() as cap:
                        result = self.agent_callable(task, **call_kwargs)
                    return result, cap.to_list()

                loop = asyncio.get_event_loop()
                output, environment_events = await asyncio.wait_for(
                    loop.run_in_executor(None, _run_sync_callable),
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
                    "environment_events": environment_events,
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
