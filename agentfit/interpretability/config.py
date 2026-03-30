"""
Interpretability Configuration.

Defines settings for LLM-powered evaluation interpretation including
provider selection, API credentials, and generation parameters.
"""

from typing import Optional
from dataclasses import dataclass, field
from enum import Enum


class LLMProvider(str, Enum):
    """Supported LLM providers for interpretation."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"


# Sensible defaults per provider
DEFAULT_MODELS = {
    LLMProvider.OPENAI: "gpt-4o-mini",
    LLMProvider.ANTHROPIC: "claude-sonnet-4-20250514",
    LLMProvider.GOOGLE: "gemini-2.0-flash",
}


@dataclass
class InterpretabilityConfig:
    """
    Configuration for the LLM-powered interpretability layer.

    Users provide their own API key and choose a provider/model.
    The interpreter uses this to generate natural-language explanations
    of evaluation scores grounded in the BNP profile context.
    """

    enabled: bool = True
    provider: LLMProvider = LLMProvider.OPENAI
    api_key: Optional[str] = None
    model: Optional[str] = None
    temperature: float = 0.3
    max_tokens: int = 4096

    # Granularity controls
    explain_dimensions: bool = True
    explain_overall: bool = True
    include_recommendations: bool = True
    include_calculation_details: bool = True

    def get_model(self) -> str:
        """Resolve the model name, falling back to the provider default."""
        return self.model or DEFAULT_MODELS[self.provider]

    def validate(self) -> None:
        """Raise if the config is incomplete."""
        if self.enabled and not self.api_key:
            raise ValueError(
                "InterpretabilityConfig.api_key is required when interpretation is enabled. "
                "Set your API key or pass enabled=False to skip interpretation."
            )
