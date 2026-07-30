"""
Conversation Trace Records.

Structured, serializable record of one full loop-tested conversation: every
turn (customer or agent), whatever tool calls the agent made during that
turn, and the judge's final per-dimension verdicts. This is what gets
written out as the "agent trace" JSON file (--agent-trace-output).

Deliberately reuses ToolCall.to_dict()/ToolResult.to_dict() from
agentfit.protocol rather than inventing a parallel tool-call shape — every
adapter already produces those types, so a trace's tool-call records look
identical regardless of which adapter/platform actually made the call.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid


@dataclass
class TurnRecord:
    """
    One turn of a conversation — either the simulated customer speaking, or
    the target agent responding.

    For agent turns, tool_calls/tool_results are already-typed dicts (via
    ToolCall.to_dict()/ToolResult.to_dict()) so this file's shape matches
    every other trace of tool activity in AgentFit, regardless of which
    specific adapter produced them.
    """

    turn_index: int
    speaker: str  # "customer" | "agent"
    message: str

    # Only populated for agent turns that made tool calls.
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    tool_results: List[Dict[str, Any]] = field(default_factory=list)

    # OS-level side effects observed during this turn (network/filesystem/
    # process), captured independently of whatever the agent's declared
    # tool calls claim happened — see agentfit.protocol.environment_capture.
    environment_events: List[Dict[str, Any]] = field(default_factory=list)

    latency_ms: float = 0.0

    # Raw response from whichever call produced this turn (the persona LLM
    # for customer turns, the target agent for agent turns) — kept for
    # debugging when something looks off in the rendered message, but
    # truncated before serialization (see AgentTrace.to_dict) so one huge
    # tool payload doesn't blow up the trace file.
    raw_response: Any = None

    # Only meaningful for customer turns: whether the persona simulator
    # signalled the conversation is over on this turn.
    done_signal: Optional[bool] = None

    def to_dict(self, max_raw_response_chars: int = 2000) -> Dict[str, Any]:
        raw = self.raw_response
        if raw is not None:
            raw_str = raw if isinstance(raw, str) else str(raw)
            if len(raw_str) > max_raw_response_chars:
                raw_str = raw_str[:max_raw_response_chars] + (
                    f"... [truncated, {len(raw_str) - max_raw_response_chars} more chars]"
                )
            raw = raw_str

        return {
            "turn_index": self.turn_index,
            "speaker": self.speaker,
            "message": self.message,
            "tool_calls": self.tool_calls,
            "tool_results": self.tool_results,
            "environment_events": self.environment_events,
            "latency_ms": self.latency_ms,
            "raw_response": raw,
            "done_signal": self.done_signal,
        }


@dataclass
class AgentTrace:
    """
    The complete record of one loop-tested conversation (one k-trial).

    `judge_verdicts` is populated by the Evaluator after TranscriptJudge
    scores the trace — kept here (not just in the DimensionResult objects
    passed back to the Evaluator) so the standalone trace JSON file is
    self-contained: a reader shouldn't need results.json open side-by-side
    to see how a given conversation was scored.
    """

    scenario_id: str
    persona_source: str  # path to the persona markdown file, for provenance
    trial_index: int = 0
    conversation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    turns: List[TurnRecord] = field(default_factory=list)

    # "loop_agent_done"   — persona simulator signalled done: true
    # "max_turns"         — safety cap reached before the persona signalled done
    # "error"             — persona output was unparseable, or the run aborted
    ended_reason: str = "max_turns"

    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    ended_at: Optional[str] = None

    # dimension_id -> DimensionResult.to_dict(), filled in once
    # TranscriptJudge has scored this trace.
    judge_verdicts: Dict[str, Any] = field(default_factory=dict)

    @property
    def total_turns(self) -> int:
        return len(self.turns)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "trial_index": self.trial_index,
            "scenario_id": self.scenario_id,
            "persona_source": self.persona_source,
            "turns": [t.to_dict() for t in self.turns],
            "ended_reason": self.ended_reason,
            "total_turns": self.total_turns,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "judge_verdicts": self.judge_verdicts,
        }
