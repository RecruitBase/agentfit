"""
Conversation Orchestrator.

Drives one full loop-tested conversation: alternates between asking the
CustomerSimulator for the customer's next message and calling the target
agent under test, until the simulator signals it's done or a safety-cap on
turns is hit. Produces an AgentTrace recording every turn.

Turn-order default: the CUSTOMER speaks first (a persona's
`agent_speaks_first: true` frontmatter overrides this) — this matches how
most real support conversations start (the customer opens with their
issue), and is the simpler case to reason about.

History handling: the target agent is called through the *same*
`to_agent_interface()._call(scenario, context)` signature every adapter
already implements — no new adapter method needed. Conversation history is
threaded via `context={"conversation_history": [...]}`, which
OpenAICompatibleAdapter/CustomHTTPAdapter/GenericAdapter now all read (see
their execute_task() implementations). Importantly, the history passed for
a given turn is everything *before* that turn's new customer message —
the new message is the `task` argument itself, appended by the adapter
after the prepended history, so passing the full post-append history would
duplicate the newest message.
"""

from typing import Any, Callable, Dict, List, Optional
import time
from loguru import logger

from agentfit.loop.config import LoopConfig
from agentfit.loop.persona import CustomerSimulator
from agentfit.loop.trace import AgentTrace, TurnRecord


class ConversationOrchestrator:
    """Runs one simulated multi-turn conversation between a CustomerSimulator
    persona and the target agent under test, producing an AgentTrace."""

    def __init__(self, loop_config: LoopConfig, simulator: Optional[CustomerSimulator] = None):
        self.loop_config = loop_config
        # Injectable for testing (a scripted fake simulator can be passed in
        # instead of one that makes real LLM calls).
        self.simulator = simulator or CustomerSimulator()

    async def run_conversation(
        self,
        agent_interface: Callable,
        scenario: Dict[str, Any],
        trial_idx: int = 0,
    ) -> AgentTrace:
        persona = self.loop_config.persona
        max_exchanges = self.loop_config.effective_max_turns

        trace = AgentTrace(
            scenario_id=scenario.get("id", "unknown"),
            persona_source=persona.source_path,
            trial_index=trial_idx,
        )

        # Plain OpenAI-chat-message-shaped history, threaded to the target
        # agent via context — see module docstring. Kept separate from
        # trace.turns (the rich, typed record) since adapters only need the
        # simple {"role","content"} shape, not the full TurnRecord.
        history: List[Dict[str, str]] = []

        ended_reason = "max_turns"  # overwritten below if we break out early

        try:
            if persona.agent_speaks_first:
                # The agent opens the conversation. There's no customer
                # message yet to use as the "task", so fall back to the
                # scenario's own task description as a generic opening
                # prompt (e.g. "Greet the customer and offer help").
                opening_task = scenario.get("task") or "Begin the conversation with the customer."
                agent_out, latency_ms = await self._call_agent(
                    agent_interface, scenario, task=opening_task, history=[],
                )
                trace.turns.append(self._agent_turn_record(len(trace.turns), agent_out, latency_ms))
                history.append({"role": "assistant", "content": str(agent_out.get("output", "") or "")})

            for exchange_idx in range(max_exchanges):
                is_opening = exchange_idx == 0 and not persona.agent_speaks_first

                customer_turn = await self.simulator.next_turn(
                    persona=persona,
                    llm_config=self.loop_config.llm_config,
                    history=history,
                    scenario=scenario,
                    is_opening=is_opening,
                )
                trace.turns.append(TurnRecord(
                    turn_index=len(trace.turns),
                    speaker="customer",
                    message=customer_turn.message,
                    raw_response=customer_turn.raw,
                    done_signal=customer_turn.done,
                ))

                if customer_turn.done:
                    ended_reason = "error" if customer_turn.parse_failed else "loop_agent_done"
                    break

                # Everything the agent should see *before* this new message
                # — the message itself is passed separately as `task` and
                # the adapter appends it after this history (see module
                # docstring for why history[:-1]-equivalent ordering matters).
                history_before_this_turn = list(history)
                history.append({"role": "user", "content": customer_turn.message})

                agent_out, latency_ms = await self._call_agent(
                    agent_interface, scenario,
                    task=customer_turn.message,
                    history=history_before_this_turn,
                )
                trace.turns.append(self._agent_turn_record(len(trace.turns), agent_out, latency_ms))
                history.append({"role": "assistant", "content": str(agent_out.get("output", "") or "")})

        except Exception as exc:
            # A hard failure (agent adapter exception, persona LLM outage
            # that somehow escaped CustomerSimulator's own try/except, etc.)
            # ends the conversation rather than propagating and losing the
            # partial transcript gathered so far.
            logger.error(f"ConversationOrchestrator: conversation {trace.conversation_id} aborted: {exc}")
            ended_reason = "error"

        trace.ended_reason = ended_reason
        trace.ended_at = _now_iso()
        return trace

    async def _call_agent(
        self,
        agent_interface: Callable,
        scenario: Dict[str, Any],
        task: str,
        history: List[Dict[str, str]],
    ) -> tuple[Dict[str, Any], float]:
        """
        Call the target agent for one turn, via the same
        `to_agent_interface()._call(scenario, context)` signature every
        adapter already implements (agentfit/protocol/agent_protocol.py) —
        no adapter-specific code needed here.
        """
        turn_scenario = {"task": task, "expected_tools": scenario.get("expected_tools", [])}
        start = time.time()
        agent_out = await agent_interface(turn_scenario, context={"conversation_history": history})
        latency_ms = (time.time() - start) * 1000
        return agent_out, latency_ms

    def _agent_turn_record(
        self,
        turn_index: int,
        agent_out: Dict[str, Any],
        latency_ms: float,
    ) -> TurnRecord:
        """
        Build a TurnRecord from the dict UniversalAgentProtocol.execute()
        returns. `tool_trace` entries (agentfit/protocol/agent_protocol.py
        execute()) already carry tool_name/parameters/output/error/
        environment_events per call, so they're stored directly as
        tool_calls here rather than re-normalized — outcomes are already
        embedded per-call, so tool_results is left empty to avoid
        duplicating that data in two places.
        """
        tool_trace = agent_out.get("tool_trace", []) or []
        environment_events = [
            ev for call in tool_trace for ev in (call.get("environment_events") or [])
        ]
        return TurnRecord(
            turn_index=turn_index,
            speaker="agent",
            message=str(agent_out.get("output", "") or ""),
            tool_calls=tool_trace,
            tool_results=[],
            environment_events=environment_events,
            latency_ms=latency_ms,
            # Kept whole (not just the "output" string) so the transcript
            # judge can later reconstruct the {"prompt","response"} shape
            # interpretability/prompts.py's declared-vs-observed rendering
            # already expects — see loop/judge.py::_build_agent_trace_metadata.
            raw_response=agent_out,
        )


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
