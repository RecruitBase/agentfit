"""
Multi-Provider LLM Client.

Thin abstraction over OpenAI, Anthropic, and Google SDKs so the
interpreter can call whichever provider the user configures without
leaking SDK details into the rest of the codebase.
"""

from typing import List, Dict
from loguru import logger

from agentfit.interpretability.config import InterpretabilityConfig, LLMProvider


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
    model = config.get_model()

    if config.provider == LLMProvider.OPENAI:
        return await _openai_complete(config.api_key, model, system_prompt, user_prompt, config)
    elif config.provider == LLMProvider.ANTHROPIC:
        return await _anthropic_complete(config.api_key, model, system_prompt, user_prompt, config)
    elif config.provider == LLMProvider.GOOGLE:
        return await _google_complete(config.api_key, model, system_prompt, user_prompt, config)
    else:
        raise ValueError(f"Unsupported LLM provider: {config.provider}")


async def _openai_complete(
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    config: InterpretabilityConfig,
) -> str:
    try:
        from openai import AsyncOpenAI
    except ImportError:
        raise RuntimeError(
            "The 'openai' package is required for OpenAI interpretation. "
            "Install it with: pip install agentfit[openai]"
        )

    client = AsyncOpenAI(api_key=api_key)
    messages: List[Dict[str, str]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    logger.debug(f"Calling OpenAI {model} for interpretation")
    response = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
    )
    return response.choices[0].message.content or ""


async def _anthropic_complete(
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    config: InterpretabilityConfig,
) -> str:
    try:
        from anthropic import AsyncAnthropic
    except ImportError:
        raise RuntimeError(
            "The 'anthropic' package is required for Anthropic interpretation. "
            "Install it with: pip install agentfit[anthropic]"
        )

    client = AsyncAnthropic(api_key=api_key)

    logger.debug(f"Calling Anthropic {model} for interpretation")
    response = await client.messages.create(
        model=model,
        max_tokens=config.max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
        temperature=config.temperature,
    )
    return response.content[0].text


async def _google_complete(
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    config: InterpretabilityConfig,
) -> str:
    try:
        import google.generativeai as genai
    except ImportError:
        raise RuntimeError(
            "The 'google-generativeai' package is required for Google interpretation. "
            "Install it with: pip install agentfit[google]"
        )

    genai.configure(api_key=api_key)
    gen_model = genai.GenerativeModel(
        model,
        system_instruction=system_prompt,
    )

    logger.debug(f"Calling Google {model} for interpretation")
    response = await gen_model.generate_content_async(
        user_prompt,
        generation_config=genai.GenerationConfig(
            temperature=config.temperature,
            max_output_tokens=config.max_tokens,
        ),
    )
    return response.text
