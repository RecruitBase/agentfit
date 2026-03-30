"""
Agent Framework Adapters.

Adapters implementing the Universal Agent Protocol for different
agent frameworks and libraries.

Included adapters:
- OpenAI (GPT-3.5, GPT-4, etc.)
- Anthropic Claude
- Google AgentKit
- Generic/Custom agents

To create a custom adapter, inherit from UniversalAgentProtocol
and register with AgentAdapterRegistry.
"""

# Import and register all adapters
from agentfit.protocol import AgentAdapterRegistry
from agentfit.adapters.openai_adapter import OpenAIAdapter
from agentfit.adapters.anthropic_adapter import AnthropicAdapter
from agentfit.adapters.google_agentkit_adapter import GoogleAgentKitAdapter
from agentfit.adapters.generic_adapter import GenericAdapter

__all__ = [
    "AgentAdapterRegistry",
    "OpenAIAdapter",
    "AnthropicAdapter",
    "GoogleAgentKitAdapter",
    "GenericAdapter",
]
