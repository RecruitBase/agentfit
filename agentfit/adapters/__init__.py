"""
Agent Framework Adapters.

Adapters implementing the Universal Agent Protocol for different
agent frameworks and providers.

Included adapters:
- OpenAICompatibleAdapter  — any /v1/chat/completions endpoint
                             (vLLM, Ollama, LM Studio, llama.cpp, LocalAI,
                              Groq, Together AI, DeepSeek, …)
- OpenAIAdapter            — OpenAI api.openai.com (inherits above)
- AnthropicAdapter         — Anthropic Claude (requires anthropic SDK)
- GoogleAgentKitAdapter    — Google Gemini / AgentKit
- GenericAdapter           — Wrap any Python callable

To create a custom adapter inherit from UniversalAgentProtocol and
register with AgentAdapterRegistry.
"""

from agentfit.protocol import AgentAdapterRegistry

# OpenAI-compatible MUST be imported before OpenAIAdapter so the base
# class is available when the subclass module is loaded.
from agentfit.adapters.openai_compatible_adapter import OpenAICompatibleAdapter
from agentfit.adapters.openai_adapter import OpenAIAdapter
from agentfit.adapters.anthropic_adapter import AnthropicAdapter
from agentfit.adapters.google_agentkit_adapter import GoogleAgentKitAdapter
from agentfit.adapters.generic_adapter import GenericAdapter

__all__ = [
    "AgentAdapterRegistry",
    "OpenAICompatibleAdapter",
    "OpenAIAdapter",
    "AnthropicAdapter",
    "GoogleAgentKitAdapter",
    "GenericAdapter",
]
