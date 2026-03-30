"""
Universal Agent Protocol (UAP) module.

Provides standardized interfaces for integrating diverse agent frameworks
with AgentFit evaluation engine.
"""

from agentfit.protocol.agent_protocol import (
    UniversalAgentProtocol,
    ToolExecutor,
    AgentAdapterRegistry,
    Message,
    MessageRole,
    ToolCall,
    ToolResult,
    ToolDefinition,
    ToolResultType,
    ExecutionResult,
)

__all__ = [
    "UniversalAgentProtocol",
    "ToolExecutor",
    "AgentAdapterRegistry",
    "Message",
    "MessageRole",
    "ToolCall",
    "ToolResult",
    "ToolDefinition",
    "ToolResultType",
    "ExecutionResult",
]
