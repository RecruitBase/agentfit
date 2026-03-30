"""
Universal Agent Protocol (UAP) for AgentFit.

A standardized interface protocol that enables integration of diverse agent
frameworks (OpenAI, Anthropic, Google AgentKit, OpenClaw, etc.) into the
AgentFit evaluation framework without framework-specific dependencies.

The protocol defines:
1. Agent Interface - How agents expose capabilities and execute tasks
2. Message Protocol - Standardized communication format
3. Tool Registry - Standard tool interface for agent-tool interactions
4. Response Handling - Normalized response formats across frameworks
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import uuid
import json
from datetime import datetime


class MessageRole(str, Enum):
    """Standard message roles in agent conversations."""
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    SYSTEM = "system"


class ToolResultType(str, Enum):
    """Types of results returned by tool execution."""
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    INVALID_PARAMS = "invalid_params"


@dataclass
class ToolDefinition:
    """Standard tool definition for agent use."""
    
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema format
    required_params: List[str] = field(default_factory=list)
    returns: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "required_params": self.required_params,
            "returns": self.returns,
        }


@dataclass
class ToolCall:
    """Standard representation of a tool call made by an agent."""
    
    tool_name: str
    parameters: Dict[str, Any]
    tool_call_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "tool_call_id": self.tool_call_id,
            "tool_name": self.tool_name,
            "parameters": self.parameters,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ToolResult:
    """Standard representation of a tool execution result."""
    
    tool_call_id: str
    result_type: ToolResultType
    output: Any
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "tool_call_id": self.tool_call_id,
            "result_type": self.result_type.value,
            "output": self.output,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
            "metadata": self.metadata,
        }


@dataclass
class Message:
    """Standard message in agent conversation."""
    
    role: MessageRole
    content: str
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    tool_calls: List[ToolCall] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "message_id": self.message_id,
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "tool_calls": [tc.to_dict() for tc in self.tool_calls],
            "metadata": self.metadata,
        }


@dataclass
class ExecutionResult:
    """Standard result from executing an agent task."""
    
    task_id: str
    success: bool
    final_output: Any
    messages: List[Message] = field(default_factory=list)
    tool_calls: List[ToolCall] = field(default_factory=list)
    tool_results: List[ToolResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    total_steps: int = 0
    execution_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "task_id": self.task_id,
            "success": self.success,
            "final_output": self.final_output,
            "total_steps": self.total_steps,
            "execution_time_ms": self.execution_time_ms,
            "tool_calls_count": len(self.tool_calls),
            "tool_results_count": len(self.tool_results),
            "errors_count": len(self.errors),
            "errors": self.errors,
            "metadata": self.metadata,
        }


class UniversalAgentProtocol(ABC):
    """
    Abstract base class defining the Universal Agent Protocol (UAP).
    
    All agent adapters must implement this protocol to integrate with AgentFit.
    This allows diverse agent frameworks to be evaluated uniformly.
    
    Implementations:
    - OpenAI Assistant adapter
    - Anthropic Claude adapter
    - Google AgentKit adapter
    - OpenClaw adapter
    - Custom in-house agents
    """
    
    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        framework: str,
        version: str = "1.0",
    ):
        """
        Initialize universal agent protocol adapter.
        
        Args:
            agent_id: Unique identifier for this agent
            agent_name: Human-readable name
            framework: Agent framework (e.g., "openai", "anthropic", "google_agentkit")
            version: Version of the agent
        """
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.framework = framework
        self.version = version
        self.execution_log: List[ExecutionResult] = []
    
    @abstractmethod
    async def execute_task(
        self,
        task: str,
        tools: Optional[List[ToolDefinition]] = None,
        context: Optional[Dict[str, Any]] = None,
        max_steps: int = 10,
        timeout_seconds: int = 60,
    ) -> ExecutionResult:
        """
        Execute a task with the agent.
        
        Args:
            task: Task description/prompt
            tools: List of available tools for the agent to use
            context: Additional context/state for the task
            max_steps: Maximum number of steps/iterations allowed
            timeout_seconds: Maximum execution time
        
        Returns:
            ExecutionResult with normalized output
        """
        pass
    
    @abstractmethod
    async def get_capabilities(self) -> Dict[str, Any]:
        """
        Return agent capabilities.
        
        Returns dict with:
        - supports_tools: bool
        - supports_parallel_tool_calls: bool
        - max_context_tokens: int
        - supported_response_types: list
        - framework_version: str
        """
        pass
    
    @abstractmethod
    async def validate_tools(
        self,
        tools: List[ToolDefinition]
    ) -> Dict[str, Any]:
        """
        Validate that the agent can work with provided tools.
        
        Returns:
        {
            "valid": bool,
            "supported_tools": list[str],
            "unsupported_tools": list[str],
            "validation_errors": list[str],
        }
        """
        pass
    
    def add_to_log(self, result: ExecutionResult) -> None:
        """Add execution result to log."""
        self.execution_log.append(result)
    
    def get_execution_history(self) -> List[ExecutionResult]:
        """Get all execution results."""
        return self.execution_log
    
    def clear_execution_log(self) -> None:
        """Clear execution history."""
        self.execution_log = []
    
    def to_metadata(self) -> Dict[str, Any]:
        """Get agent metadata for reporting."""
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "framework": self.framework,
            "version": self.version,
            "total_executions": len(self.execution_log),
        }


class ToolExecutor(ABC):
    """
    Abstract base class for tool execution adapters.
    
    Normalizes tool execution across different framework implementations.
    """
    
    @abstractmethod
    async def execute(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        timeout_seconds: int = 30,
    ) -> ToolResult:
        """
        Execute a tool with standard error handling.
        
        Returns normalized ToolResult.
        """
        pass
    
    @abstractmethod
    def get_available_tools(self) -> List[ToolDefinition]:
        """Return list of available tools."""
        pass
    
    @abstractmethod
    def register_tool(
        self,
        tool_def: ToolDefinition,
        executor: Callable,
    ) -> None:
        """Register a new tool with the executor."""
        pass


class AgentAdapterRegistry:
    """
    Registry for managing agent adapters.
    
    Allows dynamic registration and creation of agent instances
    from different frameworks.
    """
    
    _adapters: Dict[str, type] = {}
    
    @classmethod
    def register(cls, framework: str, adapter_class: type) -> None:
        """Register an adapter for a framework."""
        if not issubclass(adapter_class, UniversalAgentProtocol):
            raise TypeError(
                f"{adapter_class} must inherit from UniversalAgentProtocol"
            )
        cls._adapters[framework] = adapter_class
    
    @classmethod
    def get_adapter(cls, framework: str) -> Optional[type]:
        """Get adapter class for a framework."""
        return cls._adapters.get(framework)
    
    @classmethod
    def list_frameworks(cls) -> List[str]:
        """List all registered frameworks."""
        return list(cls._adapters.keys())
    
    @classmethod
    def create_agent(
        cls,
        framework: str,
        agent_id: str,
        agent_name: str,
        **kwargs
    ) -> Optional[UniversalAgentProtocol]:
        """
        Create an agent instance from a registered framework.
        
        Args:
            framework: Framework key (e.g., "openai", "anthropic")
            agent_id: Unique ID for the agent
            agent_name: Human-readable name
            **kwargs: Framework-specific parameters
        
        Returns:
            Agent instance or None if framework not registered
        """
        adapter_class = cls.get_adapter(framework)
        if adapter_class:
            return adapter_class(agent_id, agent_name, framework, **kwargs)
        return None
