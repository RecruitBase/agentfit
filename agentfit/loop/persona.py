"""
Persona Markdown Parsing + Customer-Simulator LLM.

A "persona" is the markdown file a user writes to describe how the
simulated customer should behave — e.g. "You are Alex, a frustrated but
polite customer whose laptop arrived damaged...". This is deliberately a
much looser format than a BNP profile (agentfit/bnp/parser.py): a BNP
requires a name/domain/requirements/etc. because it drives dimension
selection and governance thresholds, whereas a persona is just freeform
instructions for an LLM to roleplay — there's nothing to validate beyond
"is there a system prompt here."

CustomerSimulator is the LLM caller that, each turn, decides what the
simulated customer says next (and whether the conversation is over),
reusing AgentFit's existing multi-provider llm_complete() rather than
introducing a second way to call an LLM.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path
import json
import yaml
from loguru import logger

from agentfit.interpretability.config import InterpretabilityConfig
from agentfit.interpretability.llm_client import llm_complete
from agentfit.loop.prompts import build_persona_system_prompt, build_persona_user_prompt


@dataclass
class PersonaConfig:
    """
    Parsed persona markdown file.

    system_prompt_body is the raw markdown body verbatim (the user's actual
    persona instructions) — AgentFit wraps it with its own stop-signal
    instructions at call time (see prompts.build_persona_system_prompt),
    rather than baking that wrapper into the parsed config, so the persona
    file itself stays pure "who is this customer" content.
    """

    system_prompt_body: str
    source_path: str = ""

    # Optional YAML-frontmatter overrides — all optional since a persona
    # author may just want to write instructions and rely on CLI defaults
    # for everything else.
    opening_message: Optional[str] = None
    max_turns_override: Optional[int] = None
    goal: Optional[str] = None
    agent_speaks_first: bool = False


class PersonaParser:
    """Parse a persona markdown file into a PersonaConfig."""

    @staticmethod
    def parse_file(path: str) -> PersonaConfig:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Persona instructions file not found: {path}")
        return PersonaParser.parse_markdown(p.read_text(encoding="utf-8"), source_path=path)

    @staticmethod
    def parse_markdown(content: str, source_path: str = "") -> PersonaConfig:
        """
        Parse persona markdown.

        Format (frontmatter optional):
            ---
            opening_message: "Hi, my order arrived damaged."
            max_turns: 15
            goal: "Get a full refund."
            agent_speaks_first: false
            ---
            You are Alex, a frustrated but polite customer...

        Unlike BNPParser, the body after the frontmatter is NOT split into
        `##` sections — the whole remainder is the persona's system-prompt
        text, used verbatim.
        """
        frontmatter: Dict[str, Any] = {}
        body = content

        # Same "---\n...\n---" frontmatter idiom BNPParser uses, but without
        # BNPParser's `##` section splitting afterward — a persona file is
        # just narrative instructions, not structured fields.
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = yaml.safe_load(parts[1]) or {}
                body = parts[2]

        body = body.strip()
        if not body:
            raise ValueError(
                f"Persona file '{source_path}' has no instructions body — "
                "write who the simulated customer is and what they want, "
                "after the optional --- frontmatter block."
            )

        return PersonaConfig(
            system_prompt_body=body,
            source_path=source_path,
            opening_message=frontmatter.get("opening_message"),
            max_turns_override=frontmatter.get("max_turns"),
            goal=frontmatter.get("goal"),
            agent_speaks_first=bool(frontmatter.get("agent_speaks_first", False)),
        )


@dataclass
class PersonaTurn:
    """One turn's worth of output from the customer simulator."""

    message: str
    done: bool
    raw: str
    # True when the LLM's response couldn't be parsed as the expected JSON
    # shape — the orchestrator treats this as an error-terminated
    # conversation rather than silently guessing what the customer meant.
    parse_failed: bool = False


class CustomerSimulator:
    """
    Calls the configured LLM to produce the simulated customer's next
    message, one turn at a time.

    Deliberately stateless between calls — the orchestrator is the one
    holding the conversation history and passes it in fresh each time. This
    keeps CustomerSimulator trivially reusable/testable (it's a pure
    "history in, next turn out" function) and matches how the target-agent
    adapters themselves are called (they don't hold state either).
    """

    async def next_turn(
        self,
        persona: PersonaConfig,
        llm_config: InterpretabilityConfig,
        history: List[Dict[str, str]],
        scenario: Dict[str, Any],
        is_opening: bool,
    ) -> PersonaTurn:
        """
        Ask the persona LLM for the customer's next message.

        If this is the very first turn and the persona file supplied a
        fixed `opening_message`, that's used directly with no LLM call —
        both cheaper and more deterministic for scenarios that want a
        consistent, reproducible opener.
        """
        if is_opening and persona.opening_message:
            return PersonaTurn(message=persona.opening_message, done=False, raw="")

        system_prompt = build_persona_system_prompt(persona)
        user_prompt = build_persona_user_prompt(history, scenario, is_opening)

        logger.debug(
            f"CustomerSimulator: requesting {'opening' if is_opening else 'next'} "
            f"turn from {llm_config.provider.value} ({llm_config.get_model()})"
        )

        try:
            raw = await llm_complete(config=llm_config, system_prompt=system_prompt, user_prompt=user_prompt)
        except Exception as exc:
            # An LLM call failure ends the conversation rather than
            # retrying indefinitely or fabricating a customer message —
            # the orchestrator records this as ended_reason="error".
            logger.error(f"CustomerSimulator LLM call failed: {exc}")
            return PersonaTurn(message="", done=True, raw=str(exc), parse_failed=True)

        return CustomerSimulator._parse_turn(raw)

    @staticmethod
    def _parse_turn(raw: str) -> PersonaTurn:
        """
        Parse the persona LLM's JSON reply: {"message": ..., "done": bool, "reason": ...}

        Mirrors Interpreter._parse_response's fence-stripping idiom
        (agentfit/interpretability/interpreter.py) so both LLM-judge-style
        call sites in AgentFit tolerate models that wrap JSON in ```
        fences despite being asked not to.
        """
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            first_newline = cleaned.index("\n") if "\n" in cleaned else len(cleaned)
            last_fence = cleaned.rfind("```")
            if last_fence > first_newline:
                cleaned = cleaned[first_newline + 1 : last_fence].strip()

        try:
            data = json.loads(cleaned)
            message = str(data.get("message", "")).strip()
            done = bool(data.get("done", False))
            if not message and not done:
                # Nothing to say and not done — treat as done rather than
                # sending an empty message to the target agent.
                return PersonaTurn(message="", done=True, raw=raw)
            return PersonaTurn(message=message, done=done, raw=raw)
        except (json.JSONDecodeError, AttributeError, TypeError) as exc:
            logger.warning(f"CustomerSimulator: could not parse persona LLM reply as JSON ({exc}): {raw[:200]!r}")
            # Fail safe: never loop forever on malformed persona output.
            return PersonaTurn(message="", done=True, raw=raw, parse_failed=True)
