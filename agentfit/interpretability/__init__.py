"""
Interpretability Layer.

LLM-powered explanation engine that transforms raw evaluation scores
into human-readable, BNP-grounded narratives with actionable recommendations.
"""

from agentfit.interpretability.config import InterpretabilityConfig, LLMProvider
from agentfit.interpretability.interpreter import (
    Interpreter,
    InterpretationResult,
    DimensionInterpretation,
    OverallInterpretation,
    Recommendation,
)

__all__ = [
    "InterpretabilityConfig",
    "LLMProvider",
    "Interpreter",
    "InterpretationResult",
    "DimensionInterpretation",
    "OverallInterpretation",
    "Recommendation",
]
