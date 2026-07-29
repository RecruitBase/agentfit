"""
OpenAI-Compatible Endpoint Adapter for Universal Agent Protocol.

Works with any server that exposes /v1/chat/completions:
  - vLLM          (self-hosted, e.g. http://localhost:8000/v1)
  - Ollama        (http://localhost:11434/v1)
  - LM Studio     (http://localhost:1234/v1)
  - llama.cpp     (http://localhost:8080/v1)
  - LocalAI
  - Together AI, Groq, DeepSeek (cloud, OpenAI-compatible)

Usage:
    # vLLM
    adapter = OpenAICompatibleAdapter(
        agent_id="my-llm",
        agent_name="Llama-3 70B",
        base_url="http://localhost:8000/v1",
        model="meta-llama/Meta-Llama-3-70B-Instruct",
    )

    # Ollama
    adapter = OpenAICompatibleAdapter(
        agent_id="ollama-llama3",
        agent_name="Ollama Llama3",
        base_url="http://localhost:11434/v1",
        model="llama3",
    )
"""

from typing import Any, Dict, List, Optional
import asyncio
import json
import time
import uuid
from loguru import logger

import httpx

from agentfit.protocol import (
    UniversalAgentProtocol,
    ToolDefinition,
    ExecutionResult,
    Message,
    MessageRole,
    ToolCall,
    ToolResult,
    ToolResultType,
)
from agentfit.protocol.environment_capture import EnvironmentCapture


def _tool_to_openai(tool: ToolDefinition) -> Dict[str, Any]:
    """Convert UAP ToolDefinition → OpenAI function-calling format."""
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": {
                "type": "object",
                "properties": tool.parameters,
                "required": tool.required_params,
            },
        },
    }


class OpenAICompatibleAdapter(UniversalAgentProtocol):
    """
    Adapter for any OpenAI-compatible /v1/chat/completions endpoint.

    Implements a real multi-step agentic loop:
      1. Send task + tools to the model
      2. If the model returns tool calls, execute them and feed results back
      3. Repeat up to max_steps or until the model stops with a text reply

    Tool execution during evaluation is handled by _execute_tool(), which by
    default returns a structured mock acknowledgment.  Subclass and override
    _execute_tool() to plug in real tools.
    """

    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        framework: str = "openai_compatible",
        base_url: str = "http://localhost:11434/v1",
        model: str = "llama3",
        api_key: str = "none",
        system_prompt: Optional[str] = None,
        request_timeout: int = 120,
        version: str = "1.0",
    ):
        super().__init__(agent_id, agent_name, framework, version)
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.request_timeout = request_timeout
        self.system_prompt = system_prompt or (
            "You are a helpful AI agent. Complete tasks step by step. "
            "Use available tools when necessary. Explain your reasoning."
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def _chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]],
        timeout: int,
    ) -> Dict[str, Any]:
        """Single /v1/chat/completions round-trip."""
        payload: Dict[str, Any] = {"model": self.model, "messages": messages}
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        async with httpx.AsyncClient(timeout=float(timeout)) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()

    def _execute_tool(self, tc: ToolCall, tools: Optional[List[ToolDefinition]]) -> Any:
        """
        Execute a tool call during evaluation.

        Default implementation returns a structured mock acknowledgment so
        the model can continue the conversation.  Override in a subclass to
        wire up real tool implementations.
        """
        return {
            "status": "success",
            "tool": tc.tool_name,
            "result": f"Tool '{tc.tool_name}' called with params: {tc.parameters}",
        }

    # ------------------------------------------------------------------
    # UAP interface
    # ------------------------------------------------------------------

    async def execute_task(
        self,
        task: str,
        tools: Optional[List[ToolDefinition]] = None,
        context: Optional[Dict[str, Any]] = None,
        max_steps: int = 10,
        timeout_seconds: int = 60,
    ) -> ExecutionResult:
        task_id = f"oai-compat-{int(time.time() * 1000)}"
        start = time.time()

        uap_messages: List[Message] = []
        all_tool_calls: List[ToolCall] = []
        all_tool_results: List[ToolResult] = []
        errors: List[str] = []
        final_output: Optional[str] = None

        chat_history: List[Dict[str, Any]] = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": task},
        ]
        uap_messages.append(Message(role=MessageRole.USER, content=task))

        openai_tools = [_tool_to_openai(t) for t in tools] if tools else None

        try:
            for step in range(1, max_steps + 1):
                logger.debug(f"[{self.agent_name}] step {step}/{max_steps}")

                resp = await self._chat(chat_history, openai_tools, timeout_seconds)

                choice = resp["choices"][0]
                assistant_msg = choice["message"]
                finish_reason = choice.get("finish_reason", "stop")

                chat_history.append(assistant_msg)

                content = assistant_msg.get("content") or ""
                raw_tool_calls = assistant_msg.get("tool_calls") or []

                # Parse tool calls
                step_tcs: List[ToolCall] = []
                for raw in raw_tool_calls:
                    fn = raw.get("function", {})
                    try:
                        params = json.loads(fn.get("arguments", "{}"))
                    except json.JSONDecodeError:
                        params = {}
                    tc = ToolCall(
                        tool_name=fn.get("name", "unknown"),
                        parameters=params,
                        tool_call_id=raw.get("id", str(uuid.uuid4())),
                    )
                    step_tcs.append(tc)
                    all_tool_calls.append(tc)

                uap_messages.append(
                    Message(role=MessageRole.ASSISTANT, content=content, tool_calls=step_tcs)
                )

                # No tool calls → model is done
                if finish_reason == "stop" or not step_tcs:
                    final_output = content
                    break

                # Execute each tool and feed results back
                for tc in step_tcs:
                    with EnvironmentCapture() as cap:
                        tool_output = self._execute_tool(tc, tools)
                    tr = ToolResult(
                        tool_call_id=tc.tool_call_id,
                        result_type=ToolResultType.SUCCESS,
                        output=tool_output,
                        environment_events=cap.to_list(),
                    )
                    all_tool_results.append(tr)

                    chat_history.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.tool_call_id,
                            "content": json.dumps(tool_output),
                        }
                    )
                    uap_messages.append(
                        Message(role=MessageRole.TOOL, content=json.dumps(tool_output))
                    )
            else:
                # Exhausted max_steps
                errors.append(f"Reached max_steps limit ({max_steps})")
                final_output = f"[max_steps={max_steps} reached] {content}"

        except httpx.ConnectError as exc:
            msg = f"Cannot connect to {self.base_url} — is the server running? ({exc})"
            logger.error(f"[{self.agent_name}] {msg}")
            errors.append(msg)

        except httpx.HTTPStatusError as exc:
            msg = f"HTTP {exc.response.status_code}: {exc.response.text[:300]}"
            logger.error(f"[{self.agent_name}] {msg}")
            errors.append(msg)

        except asyncio.TimeoutError:
            msg = f"Request timed out after {timeout_seconds}s"
            logger.warning(f"[{self.agent_name}] {msg}")
            errors.append(msg)

        except Exception as exc:
            logger.error(f"[{self.agent_name}] Unexpected error: {exc}")
            errors.append(str(exc))

        result = ExecutionResult(
            task_id=task_id,
            success=len(errors) == 0,
            final_output=final_output,
            messages=uap_messages,
            tool_calls=all_tool_calls,
            tool_results=all_tool_results,
            errors=errors,
            total_steps=len([m for m in uap_messages if m.role == MessageRole.ASSISTANT]),
            execution_time_ms=(time.time() - start) * 1000,
            metadata={
                "model": self.model,
                "base_url": self.base_url,
                "framework": self.framework,
                "tools_available": len(tools) if tools else 0,
            },
        )
        self.add_to_log(result)
        return result

    async def get_capabilities(self) -> Dict[str, Any]:
        return {
            "framework": self.framework,
            "model": self.model,
            "base_url": self.base_url,
            "supports_tools": True,
            "supports_parallel_tool_calls": True,
            "supports_vision": False,
            "max_context_tokens": 8192,
            "supported_response_types": ["text", "function_calls"],
        }

    async def validate_tools(self, tools: List[ToolDefinition]) -> Dict[str, Any]:
        supported, errors = [], []
        for tool in tools:
            if tool.parameters and isinstance(tool.parameters, dict):
                supported.append(tool.name)
            else:
                errors.append(f"Tool '{tool.name}': parameters must be a JSON Schema dict")
        return {
            "valid": len(errors) == 0,
            "supported_tools": supported,
            "unsupported_tools": [],
            "validation_errors": errors,
        }


# Register under all common aliases so users can pass any of these as framework=
from agentfit.protocol import AgentAdapterRegistry

for _alias in ("openai_compatible", "vllm", "ollama", "lmstudio", "localai"):
    AgentAdapterRegistry.register(_alias, OpenAICompatibleAdapter)
