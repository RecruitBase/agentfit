"""
Loop Testing — Multi-Turn Simulated-Conversation Evaluation.

Where the rest of AgentFit tests an agent against ONE fixed task string per
scenario, this package drives a genuine back-and-forth conversation: an LLM
plays the customer (persona described in a markdown file), the target agent
under test responds turn by turn, and the whole transcript is scored by an
LLM judge once the conversation ends.

Modules:
    trace.py        — TurnRecord / AgentTrace: the structured record of a
                       whole conversation, reusing ToolCall/ToolResult from
                       agentfit.protocol rather than inventing a new shape.
    persona.py       — PersonaConfig/PersonaParser (markdown persona files)
                       and CustomerSimulator (the LLM that roleplays the
                       customer, one turn at a time).
    prompts.py       — System/user prompt templates for both the persona
                       simulator and the transcript judge.
    judge.py         — TranscriptJudge: scores a finished AgentTrace against
                       BNP-selected dimensions, producing the same
                       DimensionResult shape the heuristic dimensions do.
    config.py        — LoopConfig: everything a loop-tested evaluation run
                       needs (persona, LLM config, turn cap, trace output path).
    orchestrator.py  — ConversationOrchestrator: drives the turn-by-turn loop
                       itself, calling the persona simulator and the target
                       agent in turn until a stop condition is hit.
"""

from agentfit.loop.trace import TurnRecord, AgentTrace
from agentfit.loop.persona import PersonaConfig, PersonaParser, CustomerSimulator, PersonaTurn
from agentfit.loop.config import LoopConfig
from agentfit.loop.judge import TranscriptJudge
from agentfit.loop.orchestrator import ConversationOrchestrator

__all__ = [
    "TurnRecord",
    "AgentTrace",
    "PersonaConfig",
    "PersonaParser",
    "CustomerSimulator",
    "PersonaTurn",
    "LoopConfig",
    "TranscriptJudge",
    "ConversationOrchestrator",
]
