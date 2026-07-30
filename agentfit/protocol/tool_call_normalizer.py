"""
Tool-Call Normalizer.

Different agent platforms report tool/function calls under wildly different
key names and shapes:

  - OpenAI-style function calling:
        {"id": "...", "function": {"name": "lookup", "arguments": "{\"id\": 1}"}}
  - Workflow platforms (e.g. Sim.ai's selectedOutputs), commonly:
        {"name": "lookup", "args": {"id": 1}}
        {"toolName": "lookup", "arguments": {"id": 1}}
        {"tool": "lookup", "params": {"id": 1}}

Rather than hard-coding one shape (and silently mis-scoring every agent that
doesn't match it), this module tries a list of common aliases for the tool
name and its parameters, and degrades gracefully — never raises — when a
shape isn't recognized. This is what "robust tool-call capture" means in
practice: an evaluation should never crash because one platform's tool-call
JSON looked slightly different from another's, and a call we can't fully
parse should still show up (as "unknown") rather than vanish silently.

Used by CustomHTTPAdapter (to turn a raw `--agent-response-path` extracted
field into typed ToolCall/ToolResult objects) and reusable by the loop
orchestrator for the same purpose, so tool-call parsing logic lives in
exactly one place instead of being duplicated per caller.
"""

from typing import Any, Dict, List, Optional, Tuple
import json
import uuid
from loguru import logger

from agentfit.protocol.agent_protocol import ToolCall, ToolResult, ToolResultType

# Keys tried, in priority order, to find the tool's name within one raw entry.
# "function.name" is handled separately below since it requires descending
# into a nested dict first (OpenAI's function-calling shape nests the name
# and arguments under a "function" key).
_NAME_KEYS = ("name", "tool_name", "toolName", "tool")

# Keys tried, in priority order, to find the tool's parameters/arguments.
_PARAM_KEYS = ("arguments", "args", "params", "parameters")

# Keys tried, in priority order, to find a tool's reported result/output,
# for platforms that report the call and its outcome in a single entry
# rather than as two separate declared-call / observed-result records.
_RESULT_KEYS = ("result", "output", "response")


def _first_present(entry: Dict[str, Any], keys: Tuple[str, ...]) -> Optional[Any]:
    """Return the value of the first key (in priority order) present in entry."""
    for key in keys:
        if key in entry and entry[key] is not None:
            return entry[key]
    return None


def _resolve_name(entry: Dict[str, Any]) -> str:
    """Best-effort extraction of the tool's name from one raw call entry."""
    name = _first_present(entry, _NAME_KEYS)
    if name:
        return str(name)

    # OpenAI-style: {"function": {"name": "...", "arguments": "..."}}
    function = entry.get("function")
    if isinstance(function, dict) and function.get("name"):
        return str(function["name"])

    return "unknown"


def _resolve_parameters(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Best-effort extraction of the tool's parameters from one raw call entry."""
    params = _first_present(entry, _PARAM_KEYS)

    # OpenAI-style nests arguments one level down under "function", and
    # only checks it if nothing was found at the top level.
    if params is None:
        function = entry.get("function")
        if isinstance(function, dict):
            params = function.get("arguments")

    if params is None:
        return {}

    # OpenAI (and some others) encode arguments as a JSON *string*, not a
    # dict — parse it, but never let a malformed string blow up the whole
    # normalization pass.
    if isinstance(params, str):
        try:
            parsed = json.loads(params)
            return parsed if isinstance(parsed, dict) else {"_raw": parsed}
        except json.JSONDecodeError:
            return {"_raw": params}

    if isinstance(params, dict):
        return params

    # Some list/scalar shape we don't recognize — keep it, but tagged so
    # it's obvious downstream this wasn't a normal parameters dict.
    return {"_raw": params}


def normalize_tool_calls(raw: Optional[List[Any]]) -> Tuple[List[ToolCall], List[ToolResult]]:
    """
    Convert a raw, platform-specific list of tool-call blobs into AgentFit's
    typed ToolCall/ToolResult objects.

    Args:
        raw: whatever the target agent/platform returned for "tool calls" —
             expected to be a list of dicts, but each entry is handled
             defensively since real-world responses vary.

    Returns:
        (tool_calls, tool_results) — tool_results only contains entries for
        raw calls that also reported their own outcome inline (via one of
        _RESULT_KEYS); callers that get results separately (e.g. from a real
        multi-step tool loop) should ignore the empty ones and populate
        their own ToolResult list instead.
    """
    tool_calls: List[ToolCall] = []
    tool_results: List[ToolResult] = []

    if not raw:
        return tool_calls, tool_results

    for entry in raw:
        # A single malformed entry should never take down the whole
        # normalization pass — worst case, it becomes an "unknown" call
        # carrying the raw entry for later inspection.
        try:
            if not isinstance(entry, dict):
                tool_calls.append(
                    ToolCall(tool_name="unknown", parameters={"_raw": entry})
                )
                continue

            call_id = str(entry.get("id") or entry.get("tool_call_id") or uuid.uuid4())
            tc = ToolCall(
                tool_name=_resolve_name(entry),
                parameters=_resolve_parameters(entry),
                tool_call_id=call_id,
            )
            tool_calls.append(tc)

            outcome = _first_present(entry, _RESULT_KEYS)
            if outcome is not None:
                tool_results.append(
                    ToolResult(
                        tool_call_id=call_id,
                        result_type=ToolResultType.SUCCESS,
                        output=outcome,
                    )
                )

        except Exception as exc:  # pragma: no cover - defensive catch-all
            logger.warning(f"Could not normalize tool call entry {entry!r}: {exc}")
            tool_calls.append(
                ToolCall(tool_name="unknown", parameters={"_raw": entry, "_error": str(exc)})
            )

    return tool_calls, tool_results
