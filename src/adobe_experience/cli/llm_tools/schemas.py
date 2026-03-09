"""Pydantic models for LLM tools system."""

from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field


class ToolCategory(str, Enum):
    """Tool category classification."""
    
    SCHEMA = "schema"
    DATASET = "dataset"
    DATAFLOW = "dataflow"
    SEGMENT = "segment"
    DESTINATION = "destination"
    INGEST = "ingest"
    AUTH = "auth"


class ToolDefinition(BaseModel):
    """Definition of a CLI command as an LLM tool."""
    
    name: str = Field(description="Unique tool name (e.g., aep_schema_list)")
    command_name: str = Field(description="Original CLI command name")
    category: ToolCategory = Field(description="Tool category")
    description: str = Field(description="Human-readable description of what the tool does")
    input_schema: Dict[str, Any] = Field(description="JSON schema for tool parameters")
    handler: Any = Field(description="Callable function to execute", exclude=True)
    
    class Config:
        """Pydantic config."""
        arbitrary_types_allowed = True


class ExecutionResult(BaseModel):
    """Result of tool execution."""
    
    success: bool = Field(description="Whether execution succeeded")
    tool_name: str = Field(description="Name of the tool that was executed")
    output: Optional[str] = Field(default=None, description="Captured stdout output")
    result: Optional[Any] = Field(default=None, description="Structured result if available")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    error_code: Optional[str] = Field(default=None, description="Error code for categorization")
    suggestion: Optional[str] = Field(default=None, description="Suggestion for fixing the error")
    execution_time_seconds: float = Field(default=0.0, description="Execution duration")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Execution timestamp")
    
    class Config:
        """Pydantic config."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ConversationTurn(BaseModel):
    """A single turn in the conversation."""
    
    role: str = Field(description="Role: 'user' or 'assistant'")
    content: Any = Field(description="Message content")
    tool_calls: Optional[List[str]] = Field(default=None, description="Tools called in this turn")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        """Pydantic config."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ToolCallMetrics(BaseModel):
    """Metrics for tool usage."""
    
    tool_name: str
    call_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    total_execution_time: float = 0.0
    average_execution_time: float = 0.0
    last_called: Optional[datetime] = None


class LLMSession(BaseModel):
    """LLM conversation session."""
    
    session_id: str
    started_at: datetime = Field(default_factory=datetime.utcnow)
    conversation_history: List[ConversationTurn] = Field(default_factory=list)
    tool_metrics: Dict[str, ToolCallMetrics] = Field(default_factory=dict)
    max_turns: int = 20
    
    def add_turn(self, role: str, content: Any, tool_calls: Optional[List[str]] = None) -> None:
        """Add a conversation turn."""
        turn = ConversationTurn(role=role, content=content, tool_calls=tool_calls)
        self.conversation_history.append(turn)
        
        # Keep only last max_turns
        if len(self.conversation_history) > self.max_turns:
            self.conversation_history = self.conversation_history[-self.max_turns:]
    
    def update_tool_metrics(self, tool_name: str, success: bool, execution_time: float) -> None:
        """Update tool usage metrics."""
        if tool_name not in self.tool_metrics:
            self.tool_metrics[tool_name] = ToolCallMetrics(tool_name=tool_name)
        
        metrics = self.tool_metrics[tool_name]
        metrics.call_count += 1
        metrics.total_execution_time += execution_time
        metrics.average_execution_time = metrics.total_execution_time / metrics.call_count
        metrics.last_called = datetime.utcnow()
        
        if success:
            metrics.success_count += 1
        else:
            metrics.failure_count += 1
    
    def clear_history(self) -> None:
        """Clear conversation history."""
        self.conversation_history.clear()
    
    class Config:
        """Pydantic config."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
