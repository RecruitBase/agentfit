"""
Anthropic Claude Adapter for Universal Agent Protocol.

Implements a real multi-step agentic loop using the Anthropic SDK.
Requires: pip install agentfit[anthropic]

The Anthropic API is NOT OpenAI-compatible (different auth, different
tool-call format, different message schema) so this adapter has its own
implementation rather than inheriting from OpenAICompatibleAdapter.
"""

import os
import json
import time
import asyncio
from typing import Any, Dict, List, Optional
from loguru import logger

from agentfit.protocol import (
    UniversalAgentProtocol,
    ToolDefinition,
    ExecutionResult,
    Message,
    MessageRole,
    ToolCall,
    ToolResult,
    ToolResultType,
    AgentAdapterRegistry,
)
from agentfit.protocol.environment_capture import EnvironmentCapture

try:
    import anthropic as _anthropic_sdk

    _HAS_SDK = True
except ImportError:
    _HAS_SDK = False


def _tool_to_anthropic(tool: ToolDefinition) -> Dict[str, Any]:
    """Convert UAP ToolDefinition → Anthropic tool format."""
    return {
        "name": tool.name,
        "description": tool.description,
        "input_schema": {
            "type": "object",
            "properties": tool.parameters,
            "required": tool.required_params,
        },
    }


class AnthropicAdapter(UniversalAgentProtocol):
    """
    Adapter for Anthropic Claude models (claude-opus-4-*, claude-sonnet-4-*, etc.).

    Uses the official Anthropic SDK for real API calls with full tool-use
    support and a multi-step agentic loop.

    Install SDK:
        pip install anthropic>=0.18

    Example:
        adapter = AnthropicAdapter(
            agent_id="claude",
            agent_name="Claude Opus",
            model="claude-opus-4-7-20251101",
            api_key="sk-ant-...",   # or set ANTHROPIC_API_KEY
        )
    """

    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        framework: str = "anthropic",
        model: str = "claude-sonnet-4-6",
        api_key: Optional[str] = None,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        version: str = "1.0",
    ):
        super().__init__(agent_id, agent_name, framework, version)
        self.model = model
        self.max_tokens = max_tokens
        self.system_prompt = system_prompt or (
            "You are Claude, a helpful AI assistant. "
            "Complete tasks step by step, using tools when appropriate. "
            "Explain your reasoning clearly."
        )

        resolved_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if not resolved_key:
            logger.warning(
                "AnthropicAdapter: no api_key and ANTHROPIC_API_KEY not set. "
                "API calls will fail with 401."
            )

        if _HAS_SDK:
            self._client = _anthropic_sdk.AsyncAnthropic(api_key=resolved_key or "placeholder")
        else:
            self._client = None
            logger.warning(
                "AnthropicAdapter: 'anthropic' SDK not installed. "
                "Install it with: pip install agentfit[anthropic]"
            )

    # ------------------------------------------------------------------
    # Tool execution hook — override to provide real tools
    # ------------------------------------------------------------------

    def _execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Any:
        """
        Execute a tool call during evaluation.

        Default returns a structured mock result.  Override to wire real tools.
        """
        return {
            "status": "success",
            "tool": tool_name,
            "result": f"Tool '{tool_name}' called with input: {tool_input}",
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
        task_id = f"anthropic-{int(time.time() * 1000)}"
        start = time.time()

        if not _HAS_SDK or self._client is None:
            result = ExecutionResult(
                task_id=task_id,
                success=False,
                final_output=None,
                errors=["Anthropic SDK not installed. Run: pip install agentfit[anthropic]"],
                execution_time_ms=(time.time() - start) * 1000,
            )
            self.add_to_log(result)
            return result

        uap_messages: List[Message] = []
        all_tool_calls: List[ToolCall] = []
        all_tool_results: List[ToolResult] = []
        errors: List[str] = []
        final_output: Optional[str] = None

        # Anthropic uses a list-of-dicts message format
        chat_messages: List[Dict[str, Any]] = [{"role": "user", "content": task}]
        uap_messages.append(Message(role=MessageRole.USER, content=task))

        anthropic_tools = [_tool_to_anthropic(t) for t in tools] if tools else None

        try:
            for step in range(1, max_steps + 1):
                logger.debug(f"[{self.agent_name}] step {step}/{max_steps}")

                kwargs: Dict[str, Any] = {
                    "model": self.model,
                    "max_tokens": self.max_tokens,
                    "system": self.system_prompt,
                    "messages": chat_messages,
                }
                if anthropic_tools:
                    kwargs["tools"] = anthropic_tools
                    kwargs["tool_choice"] = {"type": "auto"}

                response = await asyncio.wait_for(
                    self._client.messages.create(**kwargs),
                    timeout=float(timeout_seconds),
                )

                stop_reason = response.stop_reason  # "end_turn" | "tool_use" | "max_tokens"

                # Collect text and tool-use blocks from response
                text_parts: List[str] = []
                step_tcs: List[ToolCall] = []
                assistant_content_blocks = []

                for block in response.content:
                    if block.type == "text":
                        text_parts.append(block.text)
                        assistant_content_blocks.append({"type": "text", "text": block.text})
                    elif block.type == "tool_use":
                        tc = ToolCall(
                            tool_name=block.name,
                            parameters=block.input,
                            tool_call_id=block.id,
                        )
                        step_tcs.append(tc)
                        all_tool_calls.append(tc)
                        assistant_content_blocks.append(
                            {
                                "type": "tool_use",
                                "id": block.id,
                                "name": block.name,
                                "input": block.input,
                            }
                        )

                content_text = "\n".join(text_parts)
                chat_messages.append({"role": "assistant", "content": assistant_content_blocks})
                uap_messages.append(
                    Message(
                        role=MessageRole.ASSISTANT,
                        content=content_text,
                        tool_calls=step_tcs,
                    )
                )

                # Done if no tool calls
                if stop_reason == "end_turn" or not step_tcs:
                    final_output = content_text
                    break

                # Build tool_result blocks for next user turn
                tool_result_blocks = []
                for tc in step_tcs:
                    with EnvironmentCapture() as cap:
                        tool_output = self._execute_tool(tc.tool_name, tc.parameters)
                    tr = ToolResult(
                        tool_call_id=tc.tool_call_id,
                        result_type=ToolResultType.SUCCESS,
                        output=tool_output,
                        environment_events=cap.to_list(),
                    )
                    all_tool_results.append(tr)
                    tool_result_blocks.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tc.tool_call_id,
                            "content": json.dumps(tool_output),
                        }
                    )
                    uap_messages.append(
                        Message(
                            role=MessageRole.TOOL,
                            content=json.dumps(tool_output),
                        )
                    )

                chat_messages.append({"role": "user", "content": tool_result_blocks})

            else:
                errors.append(f"Reached max_steps limit ({max_steps})")
                final_output = f"[max_steps={max_steps} reached] {content_text}"

        except asyncio.TimeoutError:
            msg = f"Request timed out after {timeout_seconds}s"
            logger.warning(f"[{self.agent_name}] {msg}")
            errors.append(msg)

        except Exception as exc:
            logger.error(f"[{self.agent_name}] Error: {exc}")
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
                "framework": "anthropic",
                "tools_available": len(tools) if tools else 0,
            },
        )
        self.add_to_log(result)
        return result

    async def get_capabilities(self) -> Dict[str, Any]:
        return {
            "framework": "anthropic",
            "model": self.model,
            "supports_tools": True,
            "supports_parallel_tool_calls": False,
            "supports_vision": True,
            "max_context_tokens": 200000,
            "supported_response_types": ["text", "tool_use"],
            "sdk_installed": _HAS_SDK,
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


AgentAdapterRegistry.register("anthropic", AnthropicAdapter)
