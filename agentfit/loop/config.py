"""
Loop-Testing Configuration.

Everything one loop-tested evaluation run needs, bundled together so
Evaluator/CLI only have to thread a single object through instead of a
handful of loose parameters.
"""

from typing import Optional
from dataclasses import dataclass

from agentfit.interpretability.config import InterpretabilityConfig
from agentfit.loop.persona import PersonaConfig


@dataclass
class LoopConfig:
    """
    Configuration for one loop-tested (multi-turn conversation) evaluation.

    llm_config is reused, as-is, for BOTH the customer-simulator persona
    LLM and the transcript judge LLM — both are "meta" calls made on behalf
    of the evaluation harness (not the target agent under test), so sharing
    one config keeps the CLI surface small and avoids asking the user to
    configure the same provider/model twice for two roles that usually want
    the same answer anyway.
    """

    persona: PersonaConfig
    llm_config: InterpretabilityConfig

    # Safety cap on conversation length — the persona's own frontmatter
    # max_turns (if set) takes precedence; this is the fallback/default.
    max_turns: int = 20

    # Where the full conversation trace JSON gets written. Resolved by the
    # CLI (defaults to "<output>.trace.json" when not explicitly set).
    agent_trace_output: Optional[str] = None

    @property
    def effective_max_turns(self) -> int:
        """The persona file's own override wins over the CLI/config default."""
        return self.persona.max_turns_override or self.max_turns
