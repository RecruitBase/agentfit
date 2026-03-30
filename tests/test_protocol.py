"""Tests for Universal Agent Protocol."""
import pytest
from agentfit.protocol import (
    Message,
    MessageRole,
    ToolCall,
    ToolResult,
    ToolDefinition,
    ToolResultType,
    ExecutionResult,
    UniversalAgentProtocol,
)


class TestMessage:
    """Test Message class."""

    def test_message_creation(self):
        """Test creating a message."""
        msg = Message(
            role=MessageRole.USER,
            content="Hello, agent!"
        )
        assert msg.role == MessageRole.USER
        assert msg.content == "Hello, agent!"
        assert msg.tool_calls is None

    def test_message_with_tool_calls(self):
        """Test message with tool calls."""
        tool_call = ToolCall(
            id="call_123",
            name="search",
            arguments={"query": "python"}
        )
        msg = Message(
            role=MessageRole.ASSISTANT,
            content="I'll search for that.",
            tool_calls=[tool_call]
        )
        assert len(msg.tool_calls) == 1
        assert msg.tool_calls[0].name == "search"

    def test_message_to_dict(self):
        """Test serializing message to dict."""
        msg = Message(
            role=MessageRole.USER,
            content="Test"
        )
        data = msg.model_dump(exclude_none=True)
        assert data["role"] == MessageRole.USER.value
        assert data["content"] == "Test"


class TestToolDefinition:
    """Test ToolDefinition class."""

    def test_tool_definition_creation(self):
        """Test creating a tool definition."""
        tool = ToolDefinition(
            name="search",
            description="Search the web",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                },
                "required": ["query"]
            }
        )
        assert tool.name == "search"
        assert tool.description == "Search the web"
        assert "query" in tool.input_schema["properties"]

    def test_tool_definition_validation(self):
        """Test tool definition validation."""
        with pytest.raises(ValueError):
            ToolDefinition(
                name="",  # Empty name
                description="Test",
                input_schema={}
            )


class TestToolCall:
    """Test ToolCall class."""

    def test_tool_call_creation(self):
        """Test creating a tool call."""
        call = ToolCall(
            id="call_1",
            name="get_weather",
            arguments={"location": "NYC"}
        )
        assert call.id == "call_1"
        assert call.name == "get_weather"
        assert call.arguments["location"] == "NYC"

    def test_tool_call_serialization(self):
        """Test serializing tool call."""
        call = ToolCall(
            id="call_1",
            name="search",
            arguments={"q": "test"}
        )
        data = call.model_dump()
        assert data["id"] == "call_1"
        assert data["name"] == "search"


class TestToolResult:
    """Test ToolResult class."""

    def test_tool_result_success(self):
        """Test successful tool result."""
        result = ToolResult(
            tool_call_id="call_1",
            result="Success",
            result_type=ToolResultType.SUCCESS
        )
        assert result.tool_call_id == "call_1"
        assert result.result == "Success"
        assert result.result_type == ToolResultType.SUCCESS

    def test_tool_result_error(self):
        """Test error tool result."""
        result = ToolResult(
            tool_call_id="call_1",
            result="Tool not found",
            result_type=ToolResultType.ERROR
        )
        assert result.result_type == ToolResultType.ERROR


class TestExecutionResult:
    """Test ExecutionResult class."""

    def test_execution_result_creation(self):
        """Test creating execution result."""
        result = ExecutionResult(
            success=True,
            message="Task completed",
            output="Result data"
        )
        assert result.success is True
        assert result.message == "Task completed"
        assert result.output == "Result data"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
