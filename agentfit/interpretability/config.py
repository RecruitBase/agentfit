"""
Interpretability Configuration.

Defines settings for LLM-powered evaluation interpretation including
provider selection, API credentials, and generation parameters.

Supported providers
-------------------
First-party SDKs:
  openai      — OpenAI (GPT-4o, GPT-4o-mini, o1, …)
  anthropic   — Anthropic (Claude 3.5/4 series)
  google      — Google Gemini via google-generativeai SDK
  mistral     — Mistral AI via mistralai SDK

OpenAI-compatible endpoints (all use the openai SDK, different base_url):
  deepseek    — DeepSeek (deepseek-chat, deepseek-reasoner)
  qwen        — Alibaba Qwen via DashScope (qwen-plus, qwen-max, …)
  groq        — Groq (llama-3.3-70b-versatile, deepseek-r1-distill-llama-70b, …)
  together    — Together AI (Llama-3, Mixtral, DBRX, …)
  ollama      — Local Ollama server (no API key required)
  openai_compatible — Generic catch-all for any OpenAI-compatible endpoint
                      (LM Studio, vLLM, Fireworks, Perplexity, etc.);
                      set base_url to your endpoint.
"""

from typing import Optional
from dataclasses import dataclass, field
from enum import Enum


class LLMProvider(str, Enum):
    """Supported LLM providers for interpretation."""
    # First-party SDKs
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    MISTRAL = "mistral"

    # OpenAI-compatible REST endpoints
    DEEPSEEK = "deepseek"
    QWEN = "qwen"
    GROQ = "groq"
    TOGETHER = "together"
    OLLAMA = "ollama"
    OPENAI_COMPATIBLE = "openai_compatible"


# Default model per provider
DEFAULT_MODELS: dict[LLMProvider, str] = {
    LLMProvider.OPENAI:             "gpt-4o-mini",
    LLMProvider.ANTHROPIC:          "claude-sonnet-5",
    LLMProvider.GOOGLE:             "gemini-flash-latest",
    LLMProvider.MISTRAL:            "mistral-large-latest",
    LLMProvider.DEEPSEEK:           "deepseek-chat",
    LLMProvider.QWEN:               "qwen-plus",
    LLMProvider.GROQ:               "llama-3.3-70b-versatile",
    LLMProvider.TOGETHER:           "meta-llama/Llama-3-70b-chat-hf",
    LLMProvider.OLLAMA:             "llama3.2",
    LLMProvider.OPENAI_COMPATIBLE:  "",          # user must specify
}

# Base URLs for OpenAI-compatible providers
PROVIDER_BASE_URLS: dict[LLMProvider, str] = {
    LLMProvider.DEEPSEEK:  "https://api.deepseek.com/v1",
    LLMProvider.QWEN:      "https://dashscope.aliyuncs.com/compatible-mode/v1",
    LLMProvider.GROQ:      "https://api.groq.com/openai/v1",
    LLMProvider.TOGETHER:  "https://api.together.xyz/v1",
    LLMProvider.OLLAMA:    "http://localhost:11434/v1",
}

# Providers that use the OpenAI SDK under the hood
OPENAI_COMPATIBLE_PROVIDERS = {
    LLMProvider.DEEPSEEK,
    LLMProvider.QWEN,
    LLMProvider.GROQ,
    LLMProvider.TOGETHER,
    LLMProvider.OLLAMA,
    LLMProvider.OPENAI_COMPATIBLE,
}

# Providers that don't require an API key
NO_KEY_PROVIDERS = {LLMProvider.OLLAMA}


@dataclass
class InterpretabilityConfig:
    """
    Configuration for the LLM-powered interpretability layer.

    Users provide their own API key and choose a provider/model.
    The interpreter uses this to generate natural-language explanations
    of evaluation scores grounded in the BNP profile context.

    For OpenAI-compatible providers (deepseek, qwen, groq, together, ollama,
    openai_compatible) the openai SDK is used with an appropriate base_url.
    Set base_url explicitly when using openai_compatible.
    Ollama does not require an api_key.
    """

    enabled: bool = True
    provider: LLMProvider = LLMProvider.OPENAI
    api_key: Optional[str] = None
    model: Optional[str] = None
    base_url: Optional[str] = None      # override base URL (required for openai_compatible)
    temperature: float = 0.3
    max_tokens: int = 4096

    # Granularity controls
    explain_dimensions: bool = True
    explain_overall: bool = True
    include_recommendations: bool = True
    include_calculation_details: bool = True

    def get_model(self) -> str:
        """Resolve the model name, falling back to the provider default."""
        if self.model:
            return self.model
        default = DEFAULT_MODELS.get(self.provider, "")
        if not default:
            raise ValueError(
                f"No default model for provider '{self.provider.value}'. "
                "Please set InterpretabilityConfig.model explicitly."
            )
        return default

    def get_base_url(self) -> Optional[str]:
        """Resolve the base URL for OpenAI-compatible providers."""
        if self.base_url:
            return self.base_url
        return PROVIDER_BASE_URLS.get(self.provider)

    def validate(self) -> None:
        """Raise if the config is incomplete."""
        if not self.enabled:
            return

        if self.provider == LLMProvider.OPENAI_COMPATIBLE and not self.get_base_url():
            raise ValueError(
                "base_url is required when using provider='openai_compatible'. "
                "Set it to your endpoint, e.g. 'http://localhost:1234/v1' for LM Studio."
            )

        if self.provider not in NO_KEY_PROVIDERS and not self.api_key:
            raise ValueError(
                f"InterpretabilityConfig.api_key is required for provider '{self.provider.value}'. "
                "Set your API key or pass enabled=False to skip interpretation."
            )
