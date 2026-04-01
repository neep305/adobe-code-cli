"""State model shared by LangGraph supervisor nodes."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from adobe_experience.agent.contracts import AgentResult, ExecutionContext


class GraphState(BaseModel):
    """Graph-level state for deterministic supervisor routing."""

    request_id: str
    trace_id: str
    raw_request: Dict[str, Any] = Field(default_factory=dict)
    normalized_intent: Optional[str] = None
    route: Optional[str] = None
    context: Optional[ExecutionContext] = None
    selected_agents: List[str] = Field(default_factory=list)
    results: Dict[str, AgentResult] = Field(default_factory=dict)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    artifacts: Dict[str, str] = Field(default_factory=dict)
    next_actions: List[str] = Field(default_factory=list)
    final_summary: Optional[str] = None
