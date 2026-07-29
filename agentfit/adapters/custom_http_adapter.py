"""
Custom HTTP Adapter for Universal Agent Protocol.

Bridges an arbitrary REST endpoint into AgentFit with no Python required:
give it a URL, a JSON request-body template (with a `{task}` placeholder),
and — if the response isn't a bare string — a dot-path telling it where to
find the agent's answer in the JSON response.

Example (a workflow-style agent API):
    CustomHTTPAdapter(
        agent_id="my-agent",
        agent_name="My Agent",
        base_url="https://my-platform.example.com/api/workflows/<id>/execute",
        request_body_template={"input": "{task}"},
        headers_template={"x-api-key": "{api_key}"},
        api_key="<platform api key>",
        response_path="output",
    )

Agent architectures don't all return a single answer string — some expose
tool calls, token usage, or model name as separate fields (e.g. Sim.ai's
`selectedOutputs`: ["agent1.content", "agent1.toolCalls", "agent1.tokens"]).
`response_path` also accepts a dict mapping field name -> response path so
callers can pull out exactly the fields their agent architecture returns:

    CustomHTTPAdapter(
        ...,
        response_path={
            "output": "agent1.content",
            "tool_calls": "agent1.toolCalls",
            "tokens": "agent1.tokens",
        },
    )

The "output" (or "final_output") entry becomes ExecutionResult.final_output;
every extracted field (including that one) is also kept in
ExecutionResult.metadata["extracted_fields"] so nothing is lost.
"""

from typing import Any, Dict, List, Optional, Union
import json
import time
from loguru import logger

import httpx

from agentfit.protocol import (
    UniversalAgentProtocol,
    ToolDefinition,
    ExecutionResult,
    Message,
    MessageRole,
)
from agentfit.protocol.environment_capture import EnvironmentCapture

JSONValue = Union[Dict[str, Any], List[Any], str, int, float, bool, None]


def _substitute(value: JSONValue, replacements: Dict[str, str]) -> JSONValue:
    """Recursively replace `{token}` placeholders inside string leaves.

    Substitution happens on the Python object *before* JSON-encoding, so
    quotes/newlines in the replacement text are escaped correctly by the
    JSON encoder rather than needing to be escaped by the caller.
    """
    if isinstance(value, str):
        for token, replacement in replacements.items():
            if token in value:
                value = value.replace(token, replacement)
        return value
    if isinstance(value, dict):
        return {k: _substitute(v, replacements) for k, v in value.items()}
    if isinstance(value, list):
        return [_substitute(v, replacements) for v in value]
    return value


def _extract_path(data: Any, path: str) -> Any:
    """Resolve a `.`-delimited path into a parsed JSON response.

    Different agent platforms shape their responses differently — some
    nest genuinely (OpenAI's "choices.0.message.content"), others emit a
    single *flat* key that happens to contain literal dots (e.g. Sim.ai's
    `selectedOutputs` come back as a key literally named "agent1.content",
    not a nested {"agent1": {"content": ...}}). To work with either without
    the caller having to know which, at every level this first checks
    whether the *entire remaining path* is a literal key in the current
    dict before falling back to splitting off one segment and descending —
    so a flat "agent1.content" key resolves directly, while genuinely
    nested paths still walk down one segment at a time.
    """
    if isinstance(data, dict) and path in data:
        return data[path]

    if "." not in path:
        if isinstance(data, list):
            try:
                return data[int(path)]
            except (ValueError, IndexError) as exc:
                raise KeyError(
                    f"Cannot index list with '{path}' (list has {len(data)} items)"
                ) from exc
        if isinstance(data, dict):
            raise KeyError(
                f"'{path}' not found in response at this level "
                f"(available keys: {list(data.keys())})"
            )
        raise KeyError(
            f"Cannot look up '{path}' — value at this point is "
            f"{type(data).__name__}, not a dict/list"
        )

    head, rest = path.split(".", 1)
    if isinstance(data, list):
        try:
            nxt = data[int(head)]
        except (ValueError, IndexError) as exc:
            raise KeyError(
                f"Cannot index list with '{head}' (list has {len(data)} items)"
            ) from exc
    elif isinstance(data, dict):
        if head not in data:
            raise KeyError(
                f"'{head}' not found in response at this level "
                f"(available keys: {list(data.keys())})"
            )
        nxt = data[head]
    else:
        raise KeyError(
            f"Cannot descend into '{head}' — value at this point is "
            f"{type(data).__name__}, not a dict/list"
        )
    return _extract_path(nxt, rest)


class CustomHTTPAdapter(UniversalAgentProtocol):
    """
    Adapter for an arbitrary REST endpoint, configured entirely through a
    URL, headers, and a JSON body template — for agents that don't speak
    OpenAI's `/v1/chat/completions` shape and don't warrant writing a
    subclass or bridge function.

    Single-shot only: sends one request per task and returns whatever text
    it extracts from the response. For a real multi-step tool-use loop
    against a REST endpoint, use OpenAICompatibleAdapter (if OpenAI-shaped)
    or write a GenericAdapter callable instead.
    """

    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        base_url: str,
        request_body_template: JSONValue,
        framework: str = "custom_http",
        method: str = "POST",
        headers_template: Optional[Dict[str, str]] = None,
        api_key: Optional[str] = None,
        response_path: Optional[Union[str, Dict[str, str]]] = None,
        request_timeout: int = 60,
        version: str = "1.0",
    ):
        super().__init__(agent_id, agent_name, framework, version)
        self.base_url = base_url
        self.method = method.upper()
        self.request_body_template = request_body_template
        self.headers_template = headers_template or {}
        self.api_key = api_key or ""
        self.response_path = response_path
        self.request_timeout = request_timeout

    def _build_headers(self) -> Dict[str, str]:
        headers = _substitute(self.headers_template, {"{api_key}": self.api_key})
        headers.setdefault("Content-Type", "application/json")
        return headers

    def _build_body(self, task: str) -> JSONValue:
        return _substitute(self.request_body_template, {"{task}": task})

    async def execute_task(
        self,
        task: str,
        tools: Optional[List[ToolDefinition]] = None,
        context: Optional[Dict[str, Any]] = None,
        max_steps: int = 10,
        timeout_seconds: int = 60,
    ) -> ExecutionResult:
        task_id = f"custom-http-{int(time.time() * 1000)}"
        start = time.time()
        errors: List[str] = []
        final_output: Optional[str] = None
        environment_events: List[Dict[str, Any]] = []
        extracted_fields: Optional[Dict[str, Any]] = None

        body = self._build_body(task)
        headers = self._build_headers()
        timeout = float(timeout_seconds or self.request_timeout)

        try:
            with EnvironmentCapture() as cap:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    resp = await client.request(
                        self.method, self.base_url, headers=headers, json=body,
                    )
                    resp.raise_for_status()
                    try:
                        raw_response: Any = resp.json()
                    except ValueError:
                        raw_response = resp.text
            environment_events = cap.to_list()

            if isinstance(self.response_path, dict):
                if not isinstance(raw_response, (dict, list)):
                    raise ValueError(
                        "--agent-response-path was set but the response body "
                        f"isn't JSON: {str(raw_response)[:200]!r}"
                    )
                extracted: Dict[str, Any] = {}
                field_errors: List[str] = []
                for field_name, field_path in self.response_path.items():
                    try:
                        extracted[field_name] = _extract_path(raw_response, field_path)
                    except KeyError as exc:
                        field_errors.append(
                            f"Could not extract field '{field_name}' via path "
                            f"'{field_path}': {exc}"
                        )

                extracted_fields = extracted
                output_key = "output" if "output" in extracted else (
                    "final_output" if "final_output" in extracted else None
                )
                if output_key is None:
                    raise KeyError(
                        "--agent-response-path is a JSON object but none of its "
                        "keys is 'output' or 'final_output' — one of them is "
                        "required so CustomHTTPAdapter knows which extracted "
                        f"field is the agent's answer. Errors so far: {field_errors}"
                    )
                main_value = extracted[output_key]
                final_output = main_value if isinstance(main_value, str) else json.dumps(main_value)
                # Extra fields (tool_calls, tokens, model, ...) failing to resolve
                # is not fatal — they're supplementary, so just note them.
                errors.extend(field_errors)

            elif self.response_path:
                if not isinstance(raw_response, (dict, list)):
                    raise ValueError(
                        "--agent-response-path was set but the response body "
                        f"isn't JSON: {str(raw_response)[:200]!r}"
                    )
                single_value = _extract_path(raw_response, self.response_path)
                final_output = single_value if isinstance(single_value, str) else json.dumps(single_value)

            else:
                final_output = raw_response if isinstance(raw_response, str) else json.dumps(raw_response)

        except httpx.ConnectError as exc:
            msg = f"Cannot connect to {self.base_url} ({exc})"
            logger.error(f"[{self.agent_name}] {msg}")
            errors.append(msg)
        except httpx.HTTPStatusError as exc:
            msg = f"HTTP {exc.response.status_code}: {exc.response.text[:300]}"
            logger.error(f"[{self.agent_name}] {msg}")
            errors.append(msg)
        except (KeyError, ValueError) as exc:
            msg = f"Failed to extract output via --agent-response-path='{self.response_path}': {exc}"
            logger.error(f"[{self.agent_name}] {msg}")
            errors.append(msg)
        except Exception as exc:
            logger.error(f"[{self.agent_name}] Unexpected error: {exc}")
            errors.append(str(exc))

        messages = [Message(role=MessageRole.USER, content=task)]
        if final_output is not None:
            messages.append(Message(role=MessageRole.ASSISTANT, content=final_output))

        result = ExecutionResult(
            task_id=task_id,
            success=len(errors) == 0,
            final_output=final_output,
            messages=messages,
            total_steps=1,
            errors=errors,
            execution_time_ms=(time.time() - start) * 1000,
            metadata={
                "framework": self.framework,
                "base_url": self.base_url,
                "method": self.method,
                "response_path": self.response_path,
                "extracted_fields": extracted_fields,
                "environment_events": environment_events,
            },
        )
        self.add_to_log(result)
        return result

    async def get_capabilities(self) -> Dict[str, Any]:
        return {
            "framework": self.framework,
            "base_url": self.base_url,
            "supports_tools": False,
            "supports_parallel_tool_calls": False,
            "is_custom_agent": True,
            "supported_response_types": ["text", "raw"],
        }

    async def validate_tools(self, tools: List[ToolDefinition]) -> Dict[str, Any]:
        return {
            "valid": True,
            "supported_tools": [t.name for t in tools],
            "unsupported_tools": [],
            "validation_errors": [],
            "note": (
                "custom_http adapter is single-shot and does not validate tools — "
                "tool selection isn't measured for plain REST endpoints"
            ),
        }


from agentfit.protocol import AgentAdapterRegistry
AgentAdapterRegistry.register("custom_http", CustomHTTPAdapter)
