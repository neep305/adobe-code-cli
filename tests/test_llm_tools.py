"""Tests for LLM tools module."""

from typing import Dict
from unittest.mock import AsyncMock, Mock, patch

import pytest

from adobe_experience.cli.llm_tools import (
    CommandExecutor,
    ToolRegistry,
    register_safe_tools,
)
from adobe_experience.cli.llm_tools.safety import (
    SAFE_TOOLS,
    DESTRUCTIVE_TOOLS,
    is_safe_tool,
    is_destructive_tool,
    get_tool_safety_level,
    get_safety_warning,
)
from adobe_experience.cli.llm_tools.schemas import (
    ToolCategory,
    ToolDefinition,
    ExecutionResult,
    LLMSession,
)


class TestSafety:
    """Test safety classification functions."""
    
    def test_safe_tools_contains_expected_tools(self):
        """Test that SAFE_TOOLS contains expected read-only tools."""
        expected_safe_tools = {
            "aep_schema_list",
            "aep_schema_get",
            "aep_dataset_list",
            "aep_dataset_get",
            "aep_dataflow_list",
            "aep_dataflow_get",
        }
        
        for tool in expected_safe_tools:
            assert tool in SAFE_TOOLS, f"{tool} should be in SAFE_TOOLS"
    
    def test_destructive_tools_contains_expected_tools(self):
        """Test that DESTRUCTIVE_TOOLS contains expected write operations."""
        expected_destructive_tools = {
            "aep_schema_create",
            "aep_schema_update",
            "aep_schema_delete",
            "aep_dataset_create",
            "aep_ingest_upload_file",
        }
        
        for tool in expected_destructive_tools:
            assert tool in DESTRUCTIVE_TOOLS, f"{tool} should be in DESTRUCTIVE_TOOLS"
    
    def test_safe_and_destructive_are_mutually_exclusive(self):
        """Test that no tool is in both SAFE_TOOLS and DESTRUCTIVE_TOOLS."""
        overlap = SAFE_TOOLS & DESTRUCTIVE_TOOLS
        assert len(overlap) == 0, f"Tools in both sets: {overlap}"
    
    def test_is_safe_tool(self):
        """Test is_safe_tool function."""
        assert is_safe_tool("aep_schema_list") is True
        assert is_safe_tool("aep_schema_create") is False
        assert is_safe_tool("aep_unknown_tool") is False
    
    def test_is_destructive_tool(self):
        """Test is_destructive_tool function."""
        assert is_destructive_tool("aep_schema_create") is True
        assert is_destructive_tool("aep_schema_list") is False
        assert is_destructive_tool("aep_unknown_tool") is False
    
    def test_get_tool_safety_level(self):
        """Test get_tool_safety_level function."""
        assert get_tool_safety_level("aep_schema_list") == "safe"
        assert get_tool_safety_level("aep_schema_create") == "destructive"
        assert get_tool_safety_level("aep_unknown_tool") == "unknown"
    
    def test_get_safety_warning(self):
        """Test get_safety_warning function."""
        # Safe tool - empty string (no warning)
        warning = get_safety_warning("aep_schema_list")
        assert warning == ""
        
        # Destructive tool - warning
        warning = get_safety_warning("aep_schema_create")
        assert warning is not None
        assert len(warning) > 0
        assert "write operation" in warning.lower() or "destructive" in warning.lower()
        
        # Unknown tool - warning
        warning = get_safety_warning("aep_unknown_tool")
        assert warning is not None
        assert len(warning) > 0
        assert "not recognized" in warning.lower() or "unknown" in warning.lower()


class TestToolRegistry:
    """Test ToolRegistry class."""
    
    def test_registry_initialization(self):
        """Test registry initializes empty."""
        registry = ToolRegistry()
        assert registry.get_tool_count() == 0
        assert len(registry.list_tools()) == 0
    
    def test_register_safe_tools(self):
        """Test that register_safe_tools adds expected tools."""
        registry = ToolRegistry()
        register_safe_tools(registry)
        
        tool_count = registry.get_tool_count()
        assert tool_count >= 11, f"Expected at least 11 tools, got {tool_count}"
        
        # Check some expected tools exist
        assert registry.get_tool("aep_schema_list") is not None
        assert registry.get_tool("aep_dataset_get") is not None
        assert registry.get_tool("aep_dataflow_health") is not None
    
    def test_register_from_typer_command(self):
        """Test registering a simple Typer command."""
        registry = ToolRegistry()
        
        # Create a simple mock function
        def mock_command(name: str = "test", count: int = 1) -> str:
            """Mock command for testing."""
            return f"{name} x {count}"
        
        # Register it
        registry.register_from_typer_command(
            command_name="test",
            typer_command=mock_command,
            category="schema",  # Use string category
            description="Test command for unit tests"
        )
        
        # Verify registration (tool name format: aep_schema_test)
        tool = registry.get_tool("aep_schema_test")
        assert tool is not None
        assert tool.name == "aep_schema_test"
        assert tool.category == "schema"
        assert "Test command" in tool.description
        
        # Verify input schema has expected parameters
        assert "properties" in tool.input_schema
        assert "name" in tool.input_schema["properties"]
        assert "count" in tool.input_schema["properties"]
    
    def test_get_anthropic_tools_format(self):
        """Test get_anthropic_tools returns correct format."""
        registry = ToolRegistry()
        register_safe_tools(registry)
        
        tools = registry.get_anthropic_tools(safe_only=True)
        
        # Check format
        assert isinstance(tools, list)
        assert len(tools) > 0
        
        for tool in tools:
            assert "name" in tool
            assert "description" in tool
            assert "input_schema" in tool
            assert "type" in tool["input_schema"]
            assert "properties" in tool["input_schema"]
    
    def test_category_filtering(self):
        """Test filtering tools by category."""
        registry = ToolRegistry()
        register_safe_tools(registry)
        
        # Get schema tools only
        schema_tools = registry.get_anthropic_tools(
            categories=[ToolCategory.SCHEMA],
            safe_only=True
        )
        
        for tool in schema_tools:
            assert tool["name"].startswith("aep_schema_")
    
    def test_safe_only_filtering(self):
        """Test safe_only filtering."""
        registry = ToolRegistry()
        register_safe_tools(registry)
        
        # Get only safe tools
        safe_tools = registry.get_anthropic_tools(safe_only=True)
        all_tools = registry.get_anthropic_tools(safe_only=False)
        
        # Safe tools should be subset
        assert len(safe_tools) >= 0
        assert len(all_tools) >= len(safe_tools)
        
        # All returned tools should be safe
        for tool in safe_tools:
            assert is_safe_tool(tool["name"]), f"{tool['name']} should be safe"


class TestCommandExecutor:
    """Test CommandExecutor class."""
    
    @pytest.fixture
    def registry(self):
        """Create registry with registered tools."""
        registry = ToolRegistry()
        register_safe_tools(registry)
        return registry
    
    @pytest.fixture
    def executor(self, registry):
        """Create executor with registry."""
        return CommandExecutor(registry)
    
    @pytest.mark.asyncio
    async def test_execute_safe_tool_success(self, executor):
        """Test executing a safe tool successfully."""
        # Mock a simple safe tool
        mock_tool_def = ToolDefinition(
            name="aep_test_safe",
            command_name="test_safe",
            category=ToolCategory.SCHEMA,
            description="Test safe tool",
            input_schema={"type": "object", "properties": {}, "required": []},
            handler=lambda: "Success!"
        )
        
        # Add to registry
        executor.registry._tools["aep_test_safe"] = mock_tool_def
        
        # Add to SAFE_TOOLS for this test
        with patch("adobe_experience.cli.llm_tools.executor.is_safe_tool", return_value=True):
            result = await executor.execute_tool("aep_test_safe", {})
        
        assert result.success is True
        assert result.result == "Success!"  # Check result field instead of output
        assert result.error is None
    
    @pytest.mark.asyncio
    async def test_execute_unsafe_tool_blocked(self, executor):
        """Test that unsafe tools are blocked."""
        # Mock an unsafe tool
        mock_tool_def = ToolDefinition(
            name="aep_test_unsafe",
            command_name="test_unsafe",
            category=ToolCategory.SCHEMA,
            description="Test unsafe tool",
            input_schema={"type": "object", "properties": {}, "required": []},
            handler=lambda: "Should not execute!"
        )
        
        # Add to registry
        executor.registry._tools["aep_test_unsafe"] = mock_tool_def
        
        # Try to execute (should be blocked)
        result = await executor.execute_tool("aep_test_unsafe", {})
        
        assert result.success is False
        assert "not allowed" in result.error.lower() or "unsafe" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_execute_tool_not_found(self, executor):
        """Test executing non-existent tool."""
        result = await executor.execute_tool("aep_nonexistent_tool", {})
        
        assert result.success is False
        assert "not found" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_parameter_validation(self, executor):
        """Test parameter validation."""
        # Mock tool with required parameters
        mock_tool_def = ToolDefinition(
            name="aep_test_with_params",
            command_name="test_with_params",
            category=ToolCategory.SCHEMA,
            description="Test tool with parameters",
            input_schema={
                "type": "object",
                "properties": {
                    "required_param": {"type": "string"}
                },
                "required": ["required_param"]
            },
            handler=lambda required_param: f"Got: {required_param}"
        )
        
        executor.registry._tools["aep_test_with_params"] = mock_tool_def
        
        with patch("adobe_experience.cli.llm_tools.executor.is_safe_tool", return_value=True):
            # Missing required parameter
            result = await executor.execute_tool("aep_test_with_params", {})
            assert result.success is False
            assert "required" in result.error.lower() or "missing" in result.error.lower()
            
            # With required parameter
            result = await executor.execute_tool("aep_test_with_params", {"required_param": "test"})
            assert result.success is True
            assert result.result == "Got: test"  # Check result field instead of output


class TestLLMSession:
    """Test LLMSession class."""
    
    def test_session_initialization(self):
        """Test session initializes correctly."""
        session = LLMSession(session_id="test-123", max_turns=10)
        
        assert session.session_id == "test-123"
        assert session.max_turns == 10
        assert len(session.conversation_history) == 0
        assert len(session.tool_metrics) == 0
    
    def test_add_turn(self):
        """Test adding conversation turns."""
        session = LLMSession(session_id="test-123")
        
        session.add_turn("user", "Hello")
        assert len(session.conversation_history) == 1
        assert session.conversation_history[0].role == "user"
        assert session.conversation_history[0].content == "Hello"
        
        session.add_turn("assistant", "Hi there!", tool_calls=["aep_schema_list"])
        assert len(session.conversation_history) == 2
        assert session.conversation_history[1].tool_calls == ["aep_schema_list"]
    
    def test_update_tool_metrics(self):
        """Test updating tool metrics."""
        session = LLMSession(session_id="test-123")
        
        # First call - success
        session.update_tool_metrics("aep_schema_list", success=True, execution_time=1.5)
        
        metrics = session.tool_metrics["aep_schema_list"]
        assert metrics.call_count == 1
        assert metrics.success_count == 1
        assert metrics.failure_count == 0
        assert metrics.total_execution_time == 1.5
        
        # Second call - failure
        session.update_tool_metrics("aep_schema_list", success=False, execution_time=0.5)
        
        metrics = session.tool_metrics["aep_schema_list"]
        assert metrics.call_count == 2
        assert metrics.success_count == 1
        assert metrics.failure_count == 1
        assert metrics.total_execution_time == 2.0
        assert metrics.average_execution_time == 1.0
    
    def test_clear_history(self):
        """Test clearing conversation history."""
        session = LLMSession(session_id="test-123")
        
        session.add_turn("user", "Hello")
        session.add_turn("assistant", "Hi")
        session.update_tool_metrics("aep_schema_list", success=True, execution_time=1.0)
        
        assert len(session.conversation_history) > 0
        assert len(session.tool_metrics) > 0
        
        session.clear_history()
        
        # Only conversation history is cleared, metrics are preserved
        assert len(session.conversation_history) == 0
        assert len(session.tool_metrics) > 0  # Metrics remain for session stats
    
    def test_max_turns_limit(self):
        """Test that history respects max_turns limit."""
        session = LLMSession(session_id="test-123", max_turns=3)
        
        # Add more turns than max
        for i in range(5):
            session.add_turn("user", f"Message {i}")
        
        # Should only keep last 3
        assert len(session.conversation_history) == 3
        assert session.conversation_history[0].content == "Message 2"
        assert session.conversation_history[-1].content == "Message 4"
