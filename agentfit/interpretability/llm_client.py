"""
Multi-Provider LLM Client.

Routes interpretation requests to the correct provider backend.

Architecture
------------
- OpenAI, first-party SDK                  → _openai_complete()
- Anthropic, first-party SDK               → _anthropic_complete()
- Google Gemini, first-party SDK           → _google_complete()
- Mistral, first-party SDK                 → _mistral_complete()
- DeepSeek / Qwen / Groq / Together AI /   → _openai_compat_complete()
  Ollama / openai_compatible                 (openai SDK + custom base_url)
"""

from typing import List, Dict, Optional
from loguru import logger

from agentfit.interpretability.config import (
    InterpretabilityConfig,
    LLMProvider,
    OPENAI_COMPATIBLE_PROVIDERS,
)


async def llm_complete(
    config: InterpretabilityConfig,
    system_prompt: str,
    user_prompt: str,
) -> str:
    """
    Send a chat-completion request to the configured LLM provider.

    Returns the assistant's text response.
    Raises RuntimeError when the provider SDK is missing or the call fails.
    """
    p = config.provider

    if p == LLMProvider.OPENAI:
        return await _openai_complete(config, system_prompt, user_prompt)
    elif p == LLMProvider.ANTHROPIC:
        return await _anthropic_complete(config, system_prompt, user_prompt)
    elif p == LLMProvider.GOOGLE:
        return await _google_complete(config, system_prompt, user_prompt)
    elif p == LLMProvider.MISTRAL:
        return await _mistral_complete(config, system_prompt, user_prompt)
    elif p in OPENAI_COMPATIBLE_PROVIDERS:
        return await _openai_compat_complete(config, system_prompt, user_prompt)
    else:
        raise ValueError(f"Unsupported LLM provider: {p}")


# ── OpenAI ────────────────────────────────────────────────────────────────────

async def _openai_complete(
    config: InterpretabilityConfig,
    system_prompt: str,
    user_prompt: str,
) -> str:
    try:
        from openai import AsyncOpenAI
    except ImportError:
        raise RuntimeError(
            "The 'openai' package is required for OpenAI interpretation. "
            "Install it with: pip install agentfit[openai]"
        )

    model = config.get_model()
    client = AsyncOpenAI(api_key=config.api_key)
    messages: List[Dict[str, str]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    logger.debug(f"Calling OpenAI {model}")
    response = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
    )
    return response.choices[0].message.content or ""


# ── Anthropic ─────────────────────────────────────────────────────────────────

async def _anthropic_complete(
    config: InterpretabilityConfig,
    system_prompt: str,
    user_prompt: str,
) -> str:
    try:
        from anthropic import AsyncAnthropic
    except ImportError:
        raise RuntimeError(
            "The 'anthropic' package is required for Anthropic interpretation. "
            "Install it with: pip install agentfit[anthropic]"
        )

    model = config.get_model()
    client = AsyncAnthropic(api_key=config.api_key)
    logger.debug(f"Calling Anthropic {model}")
    response = await client.messages.create(
        model=model,
        max_tokens=config.max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
        temperature=config.temperature,
    )
    return response.content[0].text


# ── Google Gemini ─────────────────────────────────────────────────────────────

async def _google_complete(
    config: InterpretabilityConfig,
    system_prompt: str,
    user_prompt: str,
) -> str:
    try:
        import google.generativeai as genai
    except ImportError:
        raise RuntimeError(
            "The 'google-generativeai' package is required for Google interpretation. "
            "Install it with: pip install agentfit[google]"
        )

    model = config.get_model()
    genai.configure(api_key=config.api_key)
    gen_model = genai.GenerativeModel(model, system_instruction=system_prompt)
    logger.debug(f"Calling Google Gemini {model}")
    response = await gen_model.generate_content_async(
        user_prompt,
        generation_config=genai.GenerationConfig(
            temperature=config.temperature,
            max_output_tokens=config.max_tokens,
        ),
    )
    return response.text


# ── Mistral ───────────────────────────────────────────────────────────────────

async def _mistral_complete(
    config: InterpretabilityConfig,
    system_prompt: str,
    user_prompt: str,
) -> str:
    try:
        from mistralai import Mistral
    except ImportError:
        raise RuntimeError(
            "The 'mistralai' package is required for Mistral interpretation. "
            "Install it with: pip install agentfit[mistral]"
        )

    model = config.get_model()
    client = Mistral(api_key=config.api_key)
    logger.debug(f"Calling Mistral {model}")
    response = await client.chat.complete_async(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=config.temperature,
        max_tokens=config.max_tokens,
    )
    return response.choices[0].message.content or ""


# ── OpenAI-compatible (DeepSeek, Qwen, Groq, Together, Ollama, custom) ────────

async def _openai_compat_complete(
    config: InterpretabilityConfig,
    system_prompt: str,
    user_prompt: str,
) -> str:
    """
    Generic handler for any OpenAI-compatible endpoint.

    Providers covered:
      deepseek  → https://api.deepseek.com/v1
      qwen      → https://dashscope.aliyuncs.com/compatible-mode/v1
      groq      → https://api.groq.com/openai/v1
      together  → https://api.together.xyz/v1
      ollama    → http://localhost:11434/v1  (no API key required)
      openai_compatible → user-supplied base_url
    """
    try:
        from openai import AsyncOpenAI
    except ImportError:
        raise RuntimeError(
            "The 'openai' package is required for OpenAI-compatible providers. "
            "Install it with: pip install openai"
        )

    model = config.get_model()
    base_url = config.get_base_url()

    # Ollama accepts any non-empty string as the api_key
    api_key = config.api_key or "ollama"

    client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    messages: List[Dict[str, str]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    logger.debug(f"Calling {config.provider.value} ({model}) at {base_url}")
    response = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
    )
    return response.choices[0].message.content or ""
