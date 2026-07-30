"""
Transcript Judge.

Scores a finished loop-tested conversation (an AgentTrace) against
BNP-selected dimensions using an LLM, producing the exact same
DimensionResult shape (agentfit/core/dimension.py) the heuristic dimensions
produce for single-shot evaluations. This is the key integration point that
lets loop-mode trials plug straight into Evaluator's existing aggregation,
Pass@k/Pass^k reliability, and governance-decision code — none of that
code needs to know or care whether a DimensionResult came from a hand-written
heuristic or an LLM reading a conversation transcript.
"""

from typing import Any, Dict, List, Optional
import json
import time
from loguru import logger

from agentfit.bnp.schema import BNPProfile
from agentfit.core.dimension import DimensionResult, DimensionRegistry, Metric, ScoringMethod
from agentfit.interpretability.config import InterpretabilityConfig
from agentfit.interpretability.llm_client import llm_complete
from agentfit.loop.trace import AgentTrace
from agentfit.loop.prompts import TRANSCRIPT_JUDGE_SYSTEM_PROMPT, build_judge_user_prompt


def _build_agent_trace_metadata(trace: AgentTrace) -> List[Dict[str, Any]]:
    """
    Reshape an AgentTrace's agent turns into the {"prompt", "response"}
    pair list that interpretability/prompts.py's trace-extraction helpers
    already know how to read (each "response" being the same
    UniversalAgentProtocol.execute()-shaped dict — with its own
    "tool_trace" list — that heuristic dimensions already store one of per
    call). Each agent turn is paired with the customer message that
    immediately preceded it.
    """
    entries: List[Dict[str, Any]] = []
    last_customer_message: Optional[str] = None

    for turn in trace.turns:
        if turn.speaker == "customer":
            last_customer_message = turn.message
        else:  # "agent"
            entries.append({
                "prompt": last_customer_message or "",
                # raw_response is the full dict UniversalAgentProtocol.execute()
                # returned for this turn (set by the orchestrator) — already
                # contains "tool_trace", so no reshaping needed here.
                "response": turn.raw_response or {},
            })

    return entries


class TranscriptJudge:
    """
    LLM-powered scorer for one finished conversation transcript.

    One LLM call scores ALL requested dimensions together (rather than one
    call per dimension) — this mirrors agentfit/interpretability/interpreter.py's
    Interpreter.interpret() pattern, keeps cost proportional to conversation
    length rather than (dimensions × conversation length), and lets the
    judge cross-reference dimensions in a single coherent read (e.g. a
    safety violation that should also depress compliance_auditability).
    """

    def __init__(self, llm_config: InterpretabilityConfig):
        self.llm_config = llm_config

    async def score(
        self,
        trace: AgentTrace,
        dimensions: List[str],
        bnp: Optional[BNPProfile],
    ) -> Dict[str, DimensionResult]:
        """
        Score `trace` against every dimension id in `dimensions`.

        Always returns one DimensionResult per requested dimension id, even
        when the LLM call fails outright or omits a dimension from its
        response — a conservative (score=0.0, passed=False, error=...)
        result is used in that case so the failure is visible in governance
        output/failure-mode tracking rather than silently vanishing from
        aggregation.
        """
        user_prompt = build_judge_user_prompt(trace, dimensions, bnp)

        logger.info(
            f"TranscriptJudge: scoring conversation {trace.conversation_id} "
            f"({trace.total_turns} turns) via {self.llm_config.provider.value} "
            f"({self.llm_config.get_model()})"
        )

        try:
            raw_response = await llm_complete(
                config=self.llm_config,
                system_prompt=TRANSCRIPT_JUDGE_SYSTEM_PROMPT,
                user_prompt=user_prompt,
            )
        except Exception as exc:
            logger.error(f"TranscriptJudge LLM call failed: {exc}")
            results = self._fallback_results(dimensions, error=str(exc))
        else:
            results = self._parse_response(raw_response, dimensions)

        # Attach the declared-tool-calls / observed-environment-events trace
        # to every dimension's metadata, in the exact shape
        # interpretability/prompts.py's _extract_declared_tool_calls /
        # _extract_environment_events already expect (a list of
        # {"prompt": ..., "response": {...with "tool_trace": [...]}}
        # entries) — so the existing --interpret narrative pass renders a
        # correct declared-vs-observed section for loop-mode evaluations
        # too, with zero changes to that file.
        agent_trace_meta = _build_agent_trace_metadata(trace)
        for result in results.values():
            result.metadata["agent_trace"] = agent_trace_meta

        return results

    def _parse_response(self, raw: str, dimensions: List[str]) -> Dict[str, DimensionResult]:
        """Parse the judge's JSON response into DimensionResult objects,
        one per requested dimension — mirrors Interpreter._parse_response's
        fence-stripping/json.loads idiom."""
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            first_newline = cleaned.index("\n") if "\n" in cleaned else len(cleaned)
            last_fence = cleaned.rfind("```")
            if last_fence > first_newline:
                cleaned = cleaned[first_newline + 1 : last_fence].strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            logger.warning(f"TranscriptJudge: response was not valid JSON ({exc}) — using fallback results")
            return self._fallback_results(dimensions, error=f"Unparseable judge response: {raw[:300]}")

        dim_data: Dict[str, Any] = data.get("dimensions", {})
        results: Dict[str, DimensionResult] = {}

        for dim_id in dimensions:
            entry = dim_data.get(dim_id)
            if not isinstance(entry, dict):
                # The judge omitted this dimension entirely — still emit a
                # (failing, clearly-flagged) result rather than dropping it,
                # so a governance check against this dimension doesn't
                # silently pass by having no data at all.
                results[dim_id] = self._build_result(
                    dim_id, score=0.0, passed=False,
                    feedback="Judge did not return a score for this dimension.",
                    metrics=[], error="Missing from judge response",
                )
                continue

            score = float(entry.get("score", 0.0))
            passed = bool(entry.get("passed", score >= 0.7))
            feedback = str(entry.get("feedback", ""))
            error = entry.get("error")

            metrics = [
                Metric(
                    name=str(m.get("name", "")),
                    value=float(m.get("value", 0.0)),
                    max_value=float(m.get("max_value", 1.0)),
                    unit=str(m.get("unit", "")),
                    metadata={"weight": m.get("weight")} if m.get("weight") is not None else {},
                )
                for m in entry.get("metrics", []) or []
                if isinstance(m, dict)
            ]

            results[dim_id] = self._build_result(
                dim_id, score=score, passed=passed, feedback=feedback,
                metrics=metrics, error=error,
            )

        return results

    def _build_result(
        self,
        dim_id: str,
        score: float,
        passed: bool,
        feedback: str,
        metrics: List[Metric],
        error: Optional[str],
    ) -> DimensionResult:
        """
        Build a DimensionResult for `dim_id`, pulling dimension_name/type
        from the registered dimension class when this is a known built-in
        dimension id (so loop-mode results render identically to heuristic
        ones in reports), falling back to the raw id for custom dimensions.
        """
        dim_class = DimensionRegistry.get(dim_id)
        dimension_name = getattr(dim_class, "dimension_name", dim_id) if dim_class else dim_id
        dimension_type = getattr(dim_class, "dimension_type", dim_id) if dim_class else dim_id

        return DimensionResult(
            dimension_name=dimension_name,
            dimension_type=dimension_type,
            score=max(0.0, min(1.0, score)),
            max_score=1.0,
            scoring_method=ScoringMethod.SCORE,
            passed=passed,
            feedback=feedback,
            error=error,
            metrics=metrics,
            metadata={"scored_by": "transcript_judge"},
        )

    def _fallback_results(self, dimensions: List[str], error: str) -> Dict[str, DimensionResult]:
        """Conservative all-fail result set used when the judge call itself
        fails (network error, provider outage, etc.) — every requested
        dimension gets an explicit, visible failure rather than the trial
        silently contributing no data to aggregation."""
        return {
            dim_id: self._build_result(
                dim_id, score=0.0, passed=False,
                feedback="Transcript judge call failed.",
                metrics=[], error=error,
            )
            for dim_id in dimensions
        }
