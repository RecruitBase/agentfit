"""
AgentFit: Enterprise-grade agent evaluation framework.

A modular, extensible framework for evaluating AI agents across multiple
dimensions including task competence, tool use, adaptability, and more.
"""

__version__ = "0.1.0"
__author__ = "RecruitBase"

from agentfit.core.dimension import Dimension, DimensionResult, DimensionRegistry
from agentfit.core.evaluator import Evaluator, EvaluationRequest, EvaluationResult
from agentfit.bnp.schema import BNPProfile, AgentRequirement
from agentfit.bnp.parser import BNPParser

# Universal Agent Protocol
from agentfit.protocol import (
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

# Register dimensions
from agentfit.dimensions.task_competence import TaskCompetence
from agentfit.dimensions.tool_use import ToolUse
from agentfit.dimensions.autonomy_escalation import AutonomyEscalation
from agentfit.dimensions.safety_alignment import SafetyAlignment
from agentfit.dimensions.compliance_auditability import ComplianceAuditability
from agentfit.dimensions.operational_performance import OperationalPerformance
from agentfit.dimensions.deployment_compatibility import DeploymentCompatibility

DimensionRegistry.register(TaskCompetence)
DimensionRegistry.register(ToolUse)
DimensionRegistry.register(AutonomyEscalation)
DimensionRegistry.register(SafetyAlignment)
DimensionRegistry.register(ComplianceAuditability)
DimensionRegistry.register(OperationalPerformance)
DimensionRegistry.register(DeploymentCompatibility)

# Interpretability
from agentfit.interpretability import (
    InterpretabilityConfig,
    LLMProvider,
    Interpreter,
    InterpretationResult,
    DimensionInterpretation,
    OverallInterpretation,
    Recommendation,
)

# Import adapters to register them
import agentfit.adapters  # noqa: F401

__all__ = [
    "Dimension",
    "DimensionResult",
    "DimensionRegistry",
    "Evaluator",
    "EvaluationRequest",
    "EvaluationResult",
    "BNPProfile",
    "AgentRequirement",
    "BNPParser",
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
    # Interpretability
    "InterpretabilityConfig",
    "LLMProvider",
    "Interpreter",
    "InterpretationResult",
    "DimensionInterpretation",
    "OverallInterpretation",
    "Recommendation",
]
