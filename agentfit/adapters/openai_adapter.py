"""
OpenAI Adapter for Universal Agent Protocol.

Extends OpenAICompatibleAdapter targeting OpenAI's own API endpoint.
Supports GPT-4o, GPT-4, GPT-3.5-Turbo and any model hosted at
api.openai.com.

Authentication: pass api_key= or set OPENAI_API_KEY in the environment.
"""

import os
from typing import Any, Dict, List, Optional
from loguru import logger

from agentfit.adapters.openai_compatible_adapter import OpenAICompatibleAdapter
from agentfit.protocol import ToolDefinition, AgentAdapterRegistry


class OpenAIAdapter(OpenAICompatibleAdapter):
    """
    Adapter for OpenAI models (GPT-4o, GPT-4, GPT-3.5-Turbo, etc.).

    Thin subclass of OpenAICompatibleAdapter pre-configured for
    api.openai.com.  All agentic loop and tool-call logic is inherited.

    Example:
        adapter = OpenAIAdapter(
            agent_id="gpt4o",
            agent_name="GPT-4o",
            model="gpt-4o",
            api_key="sk-...",   # or set OPENAI_API_KEY
        )
    """

    _OPENAI_BASE = "https://api.openai.com/v1"

    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        framework: str = "openai",
        model: str = "gpt-4o",
        api_key: Optional[str] = None,
        system_prompt: Optional[str] = None,
        request_timeout: int = 120,
        version: str = "1.0",
    ):
        resolved_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        if not resolved_key:
            logger.warning(
                "OpenAIAdapter: no api_key provided and OPENAI_API_KEY is not set. "
                "API calls will fail with 401."
            )
        super().__init__(
            agent_id=agent_id,
            agent_name=agent_name,
            framework=framework,
            base_url=self._OPENAI_BASE,
            model=model,
            api_key=resolved_key,
            system_prompt=system_prompt,
            request_timeout=request_timeout,
            version=version,
        )

    async def get_capabilities(self) -> Dict[str, Any]:
        caps = await super().get_capabilities()
        caps.update(
            {
                "framework": "openai",
                "supports_vision": "vision" in self.model or "o" in self.model,
                "max_context_tokens": 8192 if "gpt-3.5" in self.model else 128000,
                "supported_response_types": ["text", "json", "function_calls"],
            }
        )
        return caps


# Re-register under "openai" (overrides the stub that was registered before)
AgentAdapterRegistry.register("openai", OpenAIAdapter)
