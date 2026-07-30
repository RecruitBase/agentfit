"""
AgentFit Command-Line Interface.

Provides CLI commands for running agent evaluations, managing BNP profiles,
and viewing evaluation results.

Usage:
    agentfit evaluate --bnp path/to/bnp.md --output results.json
    agentfit validate --bnp path/to/bnp.md
    agentfit list-dimensions
    agentfit show-bnp --bnp path/to/bnp.md
"""

import click
import json
import yaml
import asyncio
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from loguru import logger

from agentfit.bnp.parser import BNPParser
from agentfit.bnp.schema import BNPProfile
from agentfit.core.evaluator import Evaluator, EvaluationRequest
from agentfit.core.dimension import DimensionRegistry
from agentfit.scenarios import ScenarioLoader
from agentfit.output import OutputFormatter, ReportGenerator
from agentfit.mock_agent import MockAgent
from agentfit.interpretability.config import InterpretabilityConfig, LLMProvider
from agentfit.loop.persona import PersonaParser
from agentfit.loop.config import LoopConfig

# Real adapter imports (lazy — only imported when needed to keep startup fast)
_ADAPTER_CHOICES = [
    "mock",
    "openai",
    "anthropic",
    "openai_compatible",
    "vllm",
    "ollama",
    "lmstudio",
    "localai",
    "groq",
    "together",
    "deepseek",
    "custom_http",
]

_ADAPTER_NEEDS_BASE_URL = {"openai_compatible", "vllm", "ollama", "lmstudio", "localai", "custom_http"}
_ADAPTER_NEEDS_KEY = _ADAPTER_CHOICES[1:]  # everyone except "mock"
_ADAPTER_NO_KEY = {"ollama", "localai", "custom_http"}     # servers that accept any/no key


def _build_real_adapter(
    adapter: str,
    agent_id: str,
    agent_name: str,
    agent_model: Optional[str],
    agent_api_key: Optional[str],
    agent_base_url: Optional[str],
    agent_request_body: Optional[str] = None,
    agent_response_path: Optional[str] = None,
    agent_headers: Optional[str] = None,
    agent_method: str = "POST",
):
    """Instantiate the requested real adapter."""
    from agentfit.adapters import (
        OpenAICompatibleAdapter,
        OpenAIAdapter,
        AnthropicAdapter,
        CustomHTTPAdapter,
    )

    if adapter == "openai":
        return OpenAIAdapter(
            agent_id=agent_id,
            agent_name=agent_name,
            model=agent_model or "gpt-4o",
            api_key=agent_api_key,
        )

    if adapter == "anthropic":
        return AnthropicAdapter(
            agent_id=agent_id,
            agent_name=agent_name,
            model=agent_model or "claude-sonnet-4-6",
            api_key=agent_api_key,
        )

    if adapter == "custom_http":
        body_template = json.loads(agent_request_body) if agent_request_body else {"input": "{task}"}
        headers_template = json.loads(agent_headers) if agent_headers else {}

        # --agent-response-path is either a plain dot-path string (single
        # output field) or a JSON object mapping field name -> path (for
        # agent architectures that expose multiple outputs — tool calls,
        # tokens, model name — not just one answer string). A bare path
        # like "choices.0.message.content" isn't valid JSON, so only treat
        # it as a mapping when it actually parses to a dict.
        response_path = agent_response_path
        if agent_response_path:
            try:
                parsed_response_path = json.loads(agent_response_path)
                if isinstance(parsed_response_path, dict):
                    response_path = parsed_response_path
            except json.JSONDecodeError:
                pass

        return CustomHTTPAdapter(
            agent_id=agent_id,
            agent_name=agent_name,
            base_url=agent_base_url,
            request_body_template=body_template,
            headers_template=headers_template,
            api_key=agent_api_key,
            response_path=response_path,
            method=agent_method,
        )

    # All remaining are OpenAI-compatible endpoints
    default_bases = {
        "ollama": "http://localhost:11434/v1",
        "lmstudio": "http://localhost:1234/v1",
        "localai": "http://localhost:8080/v1",
        "groq": "https://api.groq.com/openai/v1",
        "together": "https://api.together.xyz/v1",
        "deepseek": "https://api.deepseek.com/v1",
        "vllm": "http://localhost:8000/v1",
    }
    default_models = {
        "ollama": "llama3",
        "lmstudio": "local-model",
        "groq": "llama-3.3-70b-versatile",
        "together": "meta-llama/Meta-Llama-3-70B-Instruct-Turbo",
        "deepseek": "deepseek-chat",
        "vllm": "default",
    }

    base_url = agent_base_url or default_bases.get(adapter, "http://localhost:8000/v1")
    model = agent_model or default_models.get(adapter, "default")
    api_key = agent_api_key or "none"

    return OpenAICompatibleAdapter(
        agent_id=agent_id,
        agent_name=agent_name,
        framework=adapter,
        base_url=base_url,
        model=model,
        api_key=api_key,
    )


# Configure logging
logger.remove()  # Remove default handler


@click.group()
@click.version_option()
def main():
    """AgentFit - Enterprise Agent Evaluation Framework"""
    pass


@main.command()
@click.option(
    "--bnp",
    type=click.Path(exists=True),
    required=True,
    help="Path to Business Need Profile (BNP) markdown file"
)
@click.option(
    "--evals",
    type=str,
    default=None,
    help="Comma-separated dimension IDs to evaluate (default: all). Example: task_competence,tool_use"
)
@click.option(
    "--output",
    type=click.Path(),
    required=True,
    help="Path to write evaluation results (JSON or YAML based on extension)"
)
@click.option(
    "--format",
    type=click.Choice(["json", "yaml"], case_sensitive=False),
    default="json",
    help="Output format (default: json)"
)
@click.option(
    "--agent-id",
    type=str,
    default="test-agent",
    help="Agent identifier for tracking (default: test-agent)"
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Enable debug logging"
)
@click.option(
    "--agent-adapter",
    "agent_adapter",
    type=click.Choice(_ADAPTER_CHOICES, case_sensitive=False),
    default="mock",
    show_default=True,
    help=(
        "Agent adapter to use for evaluation. "
        "'mock' runs the built-in mock agent (no LLM required). "
        "All others connect to a real model endpoint: "
        "openai, anthropic, vllm, ollama, lmstudio, localai, groq, together, deepseek, openai_compatible."
    ),
)
@click.option(
    "--agent-model",
    "agent_model",
    type=str,
    default=None,
    help=(
        "Model name for the agent under evaluation (used when --agent-adapter != mock). "
        "Examples: gpt-4o, claude-sonnet-4-6, llama3, "
        "meta-llama/Meta-Llama-3-70B-Instruct."
    ),
)
@click.option(
    "--agent-api-key",
    "agent_api_key",
    type=str,
    default=None,
    envvar=["AGENT_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"],
    help=(
        "API key for the agent endpoint. "
        "Not required for Ollama / local servers. "
        "Can also be set via AGENT_API_KEY env var."
    ),
)
@click.option(
    "--agent-base-url",
    "agent_base_url",
    type=str,
    default=None,
    help=(
        "Base URL for the agent endpoint (required for openai_compatible / vllm / lmstudio / custom_http). "
        "For custom_http this is the exact full URL to call (nothing is appended to it), "
        "e.g. https://my-platform.example.com/api/workflows/<id>/execute"
    ),
)
@click.option(
    "--agent-request-body",
    "agent_request_body",
    type=str,
    default=None,
    help=(
        "[custom_http only] JSON request-body template. Any string containing the "
        "literal token {task} has that token replaced with the task text "
        "(substitution happens before JSON-encoding, so quotes/newlines in the task "
        "are escaped automatically). Default: '{\"input\": \"{task}\"}'. "
        "Example: --agent-request-body '{\"messages\": [{\"role\": \"user\", \"content\": \"{task}\"}]}'"
    ),
)
@click.option(
    "--agent-response-path",
    "agent_response_path",
    type=str,
    default=None,
    help=(
        "[custom_http only] Where the agent's answer lives in the JSON response. "
        "Two forms: (1) a plain dot-path, e.g. 'output' or 'choices.0.message.content' "
        "(numeric segments index into lists; a literal flat key containing dots, e.g. "
        "Sim.ai's 'agent1.content', also resolves directly — no need to know whether "
        "the platform nests or flattens). (2) A JSON object mapping field name -> path, "
        "for architectures that return multiple outputs (content, tool calls, tokens, "
        "model, ...), e.g. --agent-response-path "
        "'{\"output\": \"agent1.content\", \"tool_calls\": \"agent1.toolCalls\"}'. "
        "Exactly one key must be named 'output' or 'final_output' — that one becomes "
        "the evaluated answer; every extracted field is kept in "
        "results.json under metadata.extracted_fields. If omitted, the whole "
        "response body is used as the output."
    ),
)
@click.option(
    "--agent-headers",
    "agent_headers",
    type=str,
    default=None,
    help=(
        "[custom_http only] JSON object of extra request headers. The literal token "
        "{api_key} in any header value is replaced with --agent-api-key. "
        "Example: --agent-headers '{\"x-api-key\": \"{api_key}\"}'. "
        "Content-Type: application/json is added automatically if not set."
    ),
)
@click.option(
    "--agent-method",
    "agent_method",
    type=str,
    default="POST",
    show_default=True,
    help="[custom_http only] HTTP method to use for the request.",
)
@click.option(
    "--success-rate",
    type=float,
    default=0.8,
    help="Mock agent success rate 0-1 (only used when --agent-adapter mock)."
)
@click.option(
    "--mock-seed",
    "mock_seed",
    type=int,
    default=None,
    help="Random seed for mock agent reproducibility (only used when --agent-adapter mock)."
)
@click.option(
    "--mock-behavior",
    "mock_behavior",
    type=click.Choice(["realistic", "always_succeed", "always_fail"], case_sensitive=False),
    default="realistic",
    show_default=True,
    help="Mock agent behavior mode (only used when --agent-adapter mock)."
)
@click.option(
    "--trials",
    "k_trials",
    type=int,
    default=None,
    help=(
        "Number of independent evaluation trials (default: 1 or BNP k_trials). "
        "k>1 enables Pass@k (capability) and Pass^k (reliability) statistics. "
        "Use k=5 or k=10 for autonomous-workflow governance decisions."
    ),
)
@click.option(
    "--interpret",
    is_flag=True,
    default=False,
    help="Enable LLM-powered interpretation of evaluation results"
)
@click.option(
    "--provider",
    type=click.Choice(
        [
            "openai", "anthropic", "google", "mistral",
            "deepseek", "qwen", "groq", "together", "ollama",
            "openai_compatible",
        ],
        case_sensitive=False,
    ),
    default="openai",
    help=(
        "LLM provider for interpretation (default: openai). "
        "OpenAI-compatible providers: deepseek, qwen, groq, together, ollama, openai_compatible."
    ),
)
@click.option(
    "--api-key",
    type=str,
    default=None,
    envvar=["AGENTFIT_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY",
            "MISTRAL_API_KEY", "DEEPSEEK_API_KEY", "DASHSCOPE_API_KEY",
            "GROQ_API_KEY", "TOGETHER_API_KEY"],
    help="API key for the LLM provider (or set AGENTFIT_API_KEY / provider-specific env var). "
         "Not required for Ollama.",
)
@click.option(
    "--model",
    "llm_model",
    type=str,
    default=None,
    help="LLM model name for interpretation (uses provider default if omitted). "
         "Examples: gpt-4o, claude-opus-4-20250514, deepseek-reasoner, "
         "qwen-max, llama-3.3-70b-versatile, mistral-large-latest",
)
@click.option(
    "--base-url",
    type=str,
    default=None,
    help="Base URL for openai_compatible provider or to override any provider's default endpoint. "
         "Example: http://localhost:1234/v1 for LM Studio",
)
@click.option(
    "--enable-loop",
    "enable_loop",
    is_flag=True,
    default=False,
    help=(
        "Enable loop testing: instead of one fixed task, an LLM plays the "
        "customer (per --loop-instructions) and holds a real multi-turn "
        "conversation with the agent under test. Requires --loop-instructions "
        "and the --loop-llm-* flags below."
    ),
)
@click.option(
    "--loop-instructions",
    "loop_instructions",
    type=click.Path(exists=True),
    default=None,
    help=(
        "Path to a persona markdown file describing the simulated customer "
        "(who they are, what they want). Required with --enable-loop. "
        "Optional YAML frontmatter can set opening_message/max_turns/goal/"
        "agent_speaks_first — see docs/TEST_YOUR_AGENT.md."
    ),
)
@click.option(
    "--loop-max-turns",
    "loop_max_turns",
    type=int,
    default=20,
    show_default=True,
    help=(
        "Safety cap on the number of customer<->agent exchanges before the "
        "conversation is forced to stop, even if the simulated customer "
        "hasn't signalled it's done. Overridable per-persona via max_turns: "
        "in the persona file's frontmatter."
    ),
)
@click.option(
    "--loop-llm-provider",
    "loop_llm_provider",
    type=click.Choice(
        [
            "openai", "anthropic", "google", "mistral",
            "deepseek", "qwen", "groq", "together", "ollama",
            "openai_compatible",
        ],
        case_sensitive=False,
    ),
    default="openai",
    help=(
        "LLM provider driving BOTH the simulated-customer persona and the "
        "transcript judge that scores the finished conversation. Kept "
        "separate from --provider/--interpret, which is an unrelated, "
        "optional post-hoc narrative layer on top of governance results."
    ),
)
@click.option(
    "--loop-llm-api-key",
    "loop_llm_api_key",
    type=str,
    default=None,
    envvar=["LOOP_LLM_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"],
    help="API key for --loop-llm-provider. Not required for Ollama. "
         "Can also be set via the LOOP_LLM_API_KEY env var.",
)
@click.option(
    "--loop-llm-model",
    "loop_llm_model",
    type=str,
    default=None,
    help="Model name for --loop-llm-provider (uses the provider default if omitted).",
)
@click.option(
    "--loop-llm-base-url",
    "loop_llm_base_url",
    type=str,
    default=None,
    help="Base URL override for --loop-llm-provider (required for openai_compatible).",
)
@click.option(
    "--agent-trace-output",
    "agent_trace_output",
    type=click.Path(),
    default=None,
    help=(
        "[--enable-loop only] Where to write the full conversation trace "
        "JSON (every turn, declared tool calls, judge verdicts). Defaults "
        "to '<output>.trace.json' when omitted."
    ),
)
def evaluate(
    bnp: str,
    evals: Optional[str],
    output: str,
    format: str,
    agent_id: str,
    verbose: bool,
    agent_adapter: str,
    agent_model: Optional[str],
    agent_api_key: Optional[str],
    agent_base_url: Optional[str],
    agent_request_body: Optional[str],
    agent_response_path: Optional[str],
    agent_headers: Optional[str],
    agent_method: str,
    success_rate: float,
    mock_seed: Optional[int],
    mock_behavior: str,
    k_trials: Optional[int],
    interpret: bool,
    provider: str,
    api_key: Optional[str],
    llm_model: Optional[str],
    base_url: Optional[str],
    enable_loop: bool,
    loop_instructions: Optional[str],
    loop_max_turns: int,
    loop_llm_provider: str,
    loop_llm_api_key: Optional[str],
    loop_llm_model: Optional[str],
    loop_llm_base_url: Optional[str],
    agent_trace_output: Optional[str],
):
    """Run agent evaluation based on BNP profile.

    Examples:

    \b
    # Mock agent (no LLM needed)
    agentfit evaluate --bnp customer_bnp.md --output results.json

    \b
    # vLLM self-hosted endpoint
    agentfit evaluate --bnp customer_bnp.md --output results.json \\
        --agent-adapter vllm \\
        --agent-model meta-llama/Meta-Llama-3-70B-Instruct \\
        --agent-base-url http://localhost:8000/v1

    \b
    # Ollama (no key required)
    agentfit evaluate --bnp customer_bnp.md --output results.json \\
        --agent-adapter ollama --agent-model llama3

    \b
    # Real OpenAI + LLM interpretation
    agentfit evaluate --bnp customer_bnp.md --output results.json \\
        --agent-adapter openai --agent-model gpt-4o --agent-api-key sk-... \\
        --interpret --provider openai --api-key sk-...

    \b
    # Custom REST endpoint (not OpenAI-shaped) — no Python required
    agentfit evaluate --bnp customer_bnp.md --output results.json \\
        --agent-adapter custom_http \\
        --agent-base-url https://my-platform.example.com/api/workflows/abc/execute \\
        --agent-request-body '{"input": "{task}"}' \\
        --agent-headers '{"x-api-key": "{api_key}"}' \\
        --agent-api-key sk-... \\
        --agent-response-path output

    \b
    # Loop testing: simulate a real multi-turn customer conversation
    agentfit evaluate --bnp customer_bnp.md --output results.json \\
        --agent-adapter openai --agent-model gpt-4o --agent-api-key sk-... \\
        --enable-loop --loop-instructions persona.md --loop-max-turns 15 \\
        --loop-llm-provider openai --loop-llm-api-key sk-... \\
        --agent-trace-output trace.json
    """
    
    # Setup logging
    log_level = "DEBUG" if verbose else "INFO"
    logger.add(lambda msg: click.echo(msg, err=True), level=log_level)
    
    try:
        click.echo(f"📋 Loading BNP profile from {bnp}...")
        
        # Parse BNP file
        bnp_content = Path(bnp).read_text()
        bnp_profile = BNPParser.parse_markdown(bnp_content)
        
        click.echo(f"✓ Loaded BNP: {bnp_profile.name} ({bnp_profile.domain})")
        
        # Parse dimension filters if provided
        dimensions = None
        if evals:
            dimensions = [d.strip() for d in evals.split(",")]
            click.echo(f"📊 Evaluating dimensions: {', '.join(dimensions)}")
        else:
            click.echo("📊 Evaluating all dimensions")
        
        # Load scenario
        click.echo("🎯 Loading test scenario...")
        scenario = ScenarioLoader.get_scenario(
            domain=bnp_profile.domain,
            complexity=bnp_profile.task_complexity
        )
        click.echo(f"✓ Scenario: {scenario['id']} ({scenario['complexity']})")
        
        # Build agent interface
        agent_name = agent_id
        if agent_adapter == "mock":
            click.echo(
                f"🤖 Using mock agent "
                f"(behavior={mock_behavior}, success_rate={success_rate}"
                + (f", seed={mock_seed}" if mock_seed is not None else "")
                + ")"
            )
            agent = MockAgent(
                agent_id=agent_id,
                success_rate=success_rate,
                seed=mock_seed,
                behavior=mock_behavior,
            )
            agent_interface = agent.to_agent_interface()
        else:
            # Validate flags before building the adapter
            if agent_adapter in _ADAPTER_NEEDS_BASE_URL and not agent_base_url:
                # Some have a sensible localhost default; vllm/openai_compatible/custom_http don't
                if agent_adapter in ("vllm", "openai_compatible", "custom_http"):
                    click.secho(
                        f"✗ --agent-base-url is required for --agent-adapter {agent_adapter}. "
                        "Example: --agent-base-url http://localhost:8000/v1",
                        fg="red",
                    )
                    raise click.Exit(1)

            if agent_adapter not in _ADAPTER_NO_KEY and not agent_api_key:
                if agent_adapter not in ("lmstudio", "localai", "vllm", "ollama"):
                    click.secho(
                        f"⚠  --agent-api-key not set for '{agent_adapter}'. "
                        "Set AGENT_API_KEY or pass --agent-api-key if the server requires auth.",
                        fg="yellow",
                    )

            if agent_adapter == "custom_http":
                for flag_name, flag_value in (
                    ("--agent-request-body", agent_request_body),
                    ("--agent-headers", agent_headers),
                ):
                    if flag_value is None:
                        continue
                    try:
                        json.loads(flag_value)
                    except json.JSONDecodeError as e:
                        click.secho(f"✗ {flag_name} is not valid JSON: {e}", fg="red")
                        raise click.Exit(1)

                # --agent-response-path may be a plain dot-path (not JSON, e.g.
                # "choices.0.message.content") or a JSON object mapping field
                # name -> path. Only flag it as broken when it clearly *looks*
                # like an attempted JSON object (starts with '{') but fails to
                # parse — a plain path is never expected to be valid JSON.
                if agent_response_path and agent_response_path.strip().startswith("{"):
                    try:
                        parsed = json.loads(agent_response_path)
                    except json.JSONDecodeError as e:
                        click.secho(f"✗ --agent-response-path is not valid JSON: {e}", fg="red")
                        raise click.Exit(1)
                    if isinstance(parsed, dict) and not ({"output", "final_output"} & parsed.keys()):
                        click.secho(
                            "✗ --agent-response-path is a JSON object but has no "
                            "'output' or 'final_output' key — add one so CustomHTTPAdapter "
                            "knows which extracted field is the agent's answer.",
                            fg="red",
                        )
                        raise click.Exit(1)

            click.echo(
                f"🤖 Using {agent_adapter} adapter"
                + (f" → {agent_base_url}" if agent_base_url else "")
                + (f" (model: {agent_model})" if agent_model else "")
            )
            real_adapter = _build_real_adapter(
                adapter=agent_adapter,
                agent_id=agent_id,
                agent_name=agent_name,
                agent_model=agent_model,
                agent_api_key=agent_api_key,
                agent_base_url=agent_base_url,
                agent_request_body=agent_request_body,
                agent_response_path=agent_response_path,
                agent_headers=agent_headers,
                agent_method=agent_method,
            )
            agent_interface = real_adapter.to_agent_interface()
        
        # Build interpretability config if requested
        interp_config = None
        if interpret:
            llm_provider = LLMProvider(provider.lower())

            # Ollama is local and needs no key; openai_compatible needs a base_url
            needs_key = llm_provider.value not in ("ollama",)
            if needs_key and not api_key:
                click.secho(
                    f"✗ --api-key is required for provider '{provider}' "
                    "(or set AGENTFIT_API_KEY / provider-specific env var)",
                    fg="red",
                )
                raise click.Exit(1)

            if llm_provider == LLMProvider.OPENAI_COMPATIBLE and not base_url:
                click.secho(
                    "✗ --base-url is required when using --provider openai_compatible. "
                    "Example: --base-url http://localhost:1234/v1",
                    fg="red",
                )
                raise click.Exit(1)

            interp_config = InterpretabilityConfig(
                enabled=True,
                provider=llm_provider,
                api_key=api_key,
                model=llm_model,
                base_url=base_url,
            )
            resolved_model = interp_config.get_model()
            base_info = f" → {interp_config.get_base_url()}" if interp_config.get_base_url() else ""
            click.echo(
                f"🧠 Interpretation enabled: {interp_config.provider.value} "
                f"({resolved_model}){base_info}"
            )
        
        if k_trials is not None:
            k_display = f"{k_trials} trial{'s' if k_trials != 1 else ''}"
            click.echo(
                f"🔁 Reliability mode: {k_display} "
                f"(Pass@{k_trials} + Pass^{k_trials} will be computed)"
            )

        # Build loop-testing config if requested. Kept separate from the
        # --interpret block above: --interpret is an optional post-hoc
        # narrative pass over already-computed governance results, whereas
        # --enable-loop changes how the evaluation itself is *run* (a real
        # multi-turn conversation instead of one task) — the two are
        # orthogonal and can be combined or used independently.
        loop_config = None
        if enable_loop:
            if not loop_instructions:
                click.secho(
                    "✗ --loop-instructions is required with --enable-loop. "
                    "It should point at a persona markdown file describing "
                    "the simulated customer.",
                    fg="red",
                )
                raise click.Exit(1)

            persona = PersonaParser.parse_file(loop_instructions)

            loop_provider = LLMProvider(loop_llm_provider.lower())
            if loop_provider.value not in ("ollama",) and not loop_llm_api_key:
                click.secho(
                    f"✗ --loop-llm-api-key is required for provider '{loop_llm_provider}' "
                    "(or set LOOP_LLM_API_KEY).",
                    fg="red",
                )
                raise click.Exit(1)
            if loop_provider == LLMProvider.OPENAI_COMPATIBLE and not loop_llm_base_url:
                click.secho(
                    "✗ --loop-llm-base-url is required when using "
                    "--loop-llm-provider openai_compatible.",
                    fg="red",
                )
                raise click.Exit(1)

            loop_llm_config = InterpretabilityConfig(
                enabled=True,
                provider=loop_provider,
                api_key=loop_llm_api_key,
                model=loop_llm_model,
                base_url=loop_llm_base_url,
            )

            # Default the trace output alongside the results file
            # (results.json -> results.trace.json) when the user didn't
            # pick an explicit path, so a run always leaves a matching
            # trace next to its scores without extra flags.
            resolved_trace_output = agent_trace_output or str(
                Path(output).with_suffix("").with_suffix(".trace.json")
            )

            loop_config = LoopConfig(
                persona=persona,
                llm_config=loop_llm_config,
                max_turns=loop_max_turns,
                agent_trace_output=resolved_trace_output,
            )

            # Each trial = one full simulated conversation, so k_trials (if
            # set) directly multiplies the number of persona/judge LLM
            # calls made — surfaced here so cost isn't a surprise.
            effective_k = max(1, k_trials or (bnp_profile.k_trials if bnp_profile else 1))
            approx_calls_per_trial = loop_config.effective_max_turns + 1  # + 1 for the judge call
            click.echo(
                f"🔁 Loop testing enabled: persona={loop_instructions}, "
                f"max_turns={loop_config.effective_max_turns}, "
                f"agent={agent_adapter}"
                + (f" (mock — conversation will lack real customer awareness)" if agent_adapter == "mock" else "")
            )
            click.echo(
                f"   Estimated LLM calls: up to ~{approx_calls_per_trial} per trial "
                f"× {effective_k} trial(s) = ~{approx_calls_per_trial * effective_k} "
                f"(persona + judge, not counting the agent under test itself)"
            )

        # Create evaluation request
        evaluation_request = EvaluationRequest(
            agent_id=agent_id,
            agent_interface=agent_interface,
            scenario=scenario,
            bnp_profile=bnp_profile,
            dimensions=dimensions,
            context={"verbose": verbose},
            interpretability=interp_config,
            k_trials=k_trials,
            loop_config=loop_config,
        )
        
        # Run evaluation
        click.echo("⚙️  Running evaluation...")
        if interpret:
            click.echo("🧠 Running LLM interpretation pass (this may take a moment)...")
        evaluator = Evaluator()
        result = asyncio.run(evaluator.evaluate(evaluation_request))
        
        # Save results
        click.echo(f"💾 Saving results to {output}...")
        output_format = format.lower()
        OutputFormatter.write_to_file(
            result=result,
            output_path=output,
            format=output_format,
            bnp_profile=bnp_profile
        )

        # Write the standalone conversation-trace file for loop-tested runs.
        # Evaluator stashed one AgentTrace.to_dict() per k-trial under
        # result.metadata["loop_traces"] (see Evaluator.evaluate()) —
        # written separately from results.json so a reader can inspect the
        # full turn-by-turn conversation without wading through the
        # governance/dimension-score JSON.
        if loop_config is not None:
            loop_traces = result.metadata.get("loop_traces", [])
            trace_path = Path(loop_config.agent_trace_output)
            trace_path.parent.mkdir(parents=True, exist_ok=True)
            trace_path.write_text(json.dumps(loop_traces, indent=2, default=str))
            click.echo(f"🗒️  Agent trace ({len(loop_traces)} conversation(s)) written to: {trace_path}")

        # Print summary
        click.echo("")
        ReportGenerator.print_summary(result, bnp_profile)
        
        # Final governance decision
        click.echo("")
        if result.governance:
            if result.governance.passed:
                click.secho(
                    f"✓ GOVERNANCE DECISION: PASS  — {result.governance.rationale}",
                    fg="green", bold=True,
                )
            else:
                click.secho(
                    f"✗ GOVERNANCE DECISION: FAIL  — {result.governance.rationale}",
                    fg="red", bold=True,
                )
        else:
            if result.passed:
                click.secho("✓ Evaluation PASSED", fg="green", bold=True)
            else:
                click.secho("✗ Evaluation FAILED", fg="red", bold=True)
        
        click.echo(f"📄 Results written to: {output}")
        
    except FileNotFoundError as e:
        click.secho(f"✗ Error: File not found - {e}", fg="red")
        raise click.Exit(1)
    except Exception as e:
        click.secho(f"✗ Error: {str(e)}", fg="red")
        if verbose:
            import traceback
            click.echo(traceback.format_exc())
        raise click.Exit(1)


@main.command()
@click.option(
    "--bnp",
    type=click.Path(exists=True),
    required=True,
    help="Path to Business Need Profile markdown file"
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Show detailed information"
)
def validate(bnp: str, verbose: bool):
    """Validate a BNP profile markdown file.
    
    Example:
        agentfit validate --bnp customer_bnp.md
        agentfit validate --bnp customer_bnp.md --verbose
    """
    try:
        click.echo(f"🔍 Validating BNP profile: {bnp}")
        
        # Parse BNP file
        bnp_content = Path(bnp).read_text()
        bnp_profile = BNPParser.parse_markdown(bnp_content)
        
        # Basic validation
        errors = []
        warnings = []
        
        if not bnp_profile.name:
            errors.append("Missing profile name")
        if not bnp_profile.organization:
            warnings.append("Missing organization")
        if not bnp_profile.domain:
            errors.append("Missing domain")
        if not bnp_profile.description:
            warnings.append("Missing description")
        
        # Show results
        if errors or warnings:
            click.echo("")
            if errors:
                click.secho("Errors found:", fg="red", bold=True)
                for error in errors:
                    click.secho(f"  ✗ {error}", fg="red")
            
            if warnings:
                click.secho("Warnings:", fg="yellow", bold=True)
                for warning in warnings:
                    click.secho(f"  ⚠ {warning}", fg="yellow")
            
            if errors:
                raise click.Exit(1)
        else:
            click.secho("✓ BNP profile is valid", fg="green")
        
        # Show profile details
        if verbose:
            click.echo("")
            click.echo("Profile Details:")
            click.echo(f"  Name: {bnp_profile.name}")
            click.echo(f"  Organization: {bnp_profile.organization}")
            click.echo(f"  Domain: {bnp_profile.domain}")
            click.echo(f"  Description: {bnp_profile.description}")
            click.echo(f"  Task Complexity: {bnp_profile.task_complexity}")
            click.echo(f"  Requirements: {len(bnp_profile.agent_requirements)}")
        
    except Exception as e:
        click.secho(f"✗ Error: {str(e)}", fg="red")
        raise click.Exit(1)


@main.command()
def list_dimensions():
    """List all available evaluation dimensions.
    
    Example:
        agentfit list-dimensions
    """
    try:
        click.echo("📋 Available Evaluation Dimensions")
        click.echo("-" * 50)
        
        registry = DimensionRegistry()
        dimensions = registry.list_dimensions()
        
        if not dimensions:
            click.echo("No dimensions registered")
            return
        
        for dim_id in sorted(dimensions.keys()):
            dim_class = dimensions[dim_id]
            click.echo(f"  • {dim_id}")
            if hasattr(dim_class, '__doc__') and dim_class.__doc__:
                doc = dim_class.__doc__.strip().split('\n')[0]
                click.echo(f"    {doc}")
        
        click.echo(f"\nTotal: {len(dimensions)} dimensions")
        
    except Exception as e:
        click.secho(f"✗ Error: {str(e)}", fg="red")
        raise click.Exit(1)


@main.command("show-bnp")
@click.option(
    "--bnp",
    type=click.Path(exists=True),
    required=True,
    help="Path to Business Need Profile markdown file"
)
@click.option(
    "--format",
    type=click.Choice(["json", "yaml", "text"], case_sensitive=False),
    default="text",
    help="Output format (default: text)"
)
def show_bnp(bnp: str, format: str):
    """Display a parsed BNP profile.
    
    Example:
        agentfit show-bnp --bnp customer_bnp.md
        agentfit show-bnp --bnp customer_bnp.md --format json
    """
    try:
        click.echo(f"📄 Loading BNP profile from {bnp}...")
        
        # Parse BNP file
        bnp_content = Path(bnp).read_text()
        bnp_profile = BNPParser.parse_markdown(bnp_content)
        
        # Format output
        format = format.lower()
        
        if format == "json":
            output_data = {
                "name": bnp_profile.name,
                "organization": bnp_profile.organization,
                "domain": bnp_profile.domain,
                "description": bnp_profile.description,
                "task_complexity": bnp_profile.task_complexity,
                "agent_requirements": len(bnp_profile.agent_requirements),
                "constraints": bnp_profile.max_latency_ms,
                "created_at": bnp_profile.created_at,
                "updated_at": bnp_profile.updated_at,
            }
            click.echo(json.dumps(output_data, indent=2, default=str))
        elif format == "yaml":
            output_data = {
                "name": bnp_profile.name,
                "organization": bnp_profile.organization,
                "domain": bnp_profile.domain,
                "description": bnp_profile.description,
                "task_complexity": bnp_profile.task_complexity,
                "agent_requirements": len(bnp_profile.agent_requirements),
                "constraints": bnp_profile.max_latency_ms,
            }
            click.echo(yaml.dump(output_data, default_flow_style=False))
        else:  # text
            click.echo(f"\nProfile Name: {bnp_profile.name}")
            click.echo(f"Organization: {bnp_profile.organization}")
            click.echo(f"Domain: {bnp_profile.domain}")
            click.echo(f"Description: {bnp_profile.description}")
            click.echo(f"Task Complexity: {bnp_profile.task_complexity}")
            click.echo(f"Agent Requirements: {len(bnp_profile.agent_requirements)}")
            if bnp_profile.max_latency_ms:
                click.echo(f"Max Latency: {bnp_profile.max_latency_ms}ms")
            click.echo(f"Created: {bnp_profile.created_at}")
            click.echo(f"Updated: {bnp_profile.updated_at}")
        
    except Exception as e:
        click.secho(f"✗ Error: {str(e)}", fg="red")
        raise click.Exit(1)


if __name__ == "__main__":
    main()
