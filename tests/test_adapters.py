"""Tests for agent adapters."""
import pytest
from agentfit.adapters import (
    OpenAIAdapter,
    AnthropicAdapter,
    GoogleAgentKitAdapter,
    GenericAdapter,
    AgentAdapterRegistry,
)
from agentfit.protocol import Message, MessageRole, ToolDefinition


class TestAdapterRegistry:
    """Test adapter registry."""

    def test_register_adapter(self):
        """Test registering an adapter."""
        registry = AgentAdapterRegistry()
        adapter_class = OpenAIAdapter
        registry.register(adapter_class)
        assert "openai" in registry._adapters
        assert registry._adapters["openai"] == adapter_class

    def test_get_adapter(self):
        """Test getting an adapter."""
        registry = AgentAdapterRegistry()
        registry.register(OpenAIAdapter)
        adapter_class = registry.get("openai")
        assert adapter_class == OpenAIAdapter

    def test_list_adapters(self):
        """Test listing available adapters."""
        registry = AgentAdapterRegistry()
        registry.register(OpenAIAdapter)
        registry.register(AnthropicAdapter)
        adapters = registry.list()
        assert "openai" in adapters
        assert "anthropic" in adapters


class TestGenericAdapter:
    """Test generic adapter."""

    def test_generic_adapter_initialization(self):
        """Test initializing generic adapter."""
        config = {"model": "test-model"}
        adapter = GenericAdapter(config=config)
        assert adapter.config["model"] == "test-model"

    def test_generic_adapter_format_message(self):
        """Test formatting message."""
        adapter = GenericAdapter(config={})
        message = Message(
            role=MessageRole.USER,
            content="Test message"
        )
        formatted = adapter._format_message(message)
        assert isinstance(formatted, dict)
        assert "content" in formatted


class TestAdapterMethods:
    """Test common adapter methods."""

    def test_tool_definition_conversion(self):
        """Test converting tool definition."""
        adapter = GenericAdapter(config={})
        tool = ToolDefinition(
            name="search",
            description="Search the web",
            input_schema={
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"]
            }
        )
        converted = adapter._convert_tool_definition(tool)
        assert converted["name"] == "search"
        assert converted["description"] == "Search the web"

    def test_validate_response_format(self):
        """Test validating response format."""
        adapter = GenericAdapter(config={})
        response = {
            "content": "test",
            "stop_reason": "end_turn"
        }
        # Should not raise
        adapter._validate_response_format(response)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
