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
    "--success-rate",
    type=float,
    default=0.8,
    help="Mock agent success rate (0-1, default: 0.8)"
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
def evaluate(
    bnp: str,
    evals: Optional[str],
    output: str,
    format: str,
    agent_id: str,
    verbose: bool,
    success_rate: float,
    interpret: bool,
    provider: str,
    api_key: Optional[str],
    llm_model: Optional[str],
    base_url: Optional[str],
):
    """Run agent evaluation based on BNP profile.
    
    Example:
        agentfit evaluate --bnp customer_bnp.md --output results.json
        agentfit evaluate --bnp customer_bnp.md --evals task_competence --format yaml
        agentfit evaluate --bnp customer_bnp.md --output results.json --interpret --api-key sk-...
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
        
        # Create mock agent
        click.echo("🤖 Creating mock agent...")
        agent = MockAgent(agent_id=agent_id, success_rate=success_rate)
        agent_interface = agent.to_agent_interface()
        
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
        
        # Create evaluation request
        evaluation_request = EvaluationRequest(
            agent_id=agent_id,
            agent_interface=agent_interface,
            scenario=scenario,
            bnp_profile=bnp_profile,
            dimensions=dimensions,
            context={"verbose": verbose},
            interpretability=interp_config,
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
        
        # Print summary
        click.echo("")
        ReportGenerator.print_summary(result, bnp_profile)
        
        # Final status
        click.echo("")
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
