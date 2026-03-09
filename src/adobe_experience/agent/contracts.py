"""Common contracts for supervisor-managed agents."""

from enum import Enum
from typing import Any, Dict, List, Protocol, runtime_checkable

from pydantic import BaseModel, Field


CONTRACT_VERSION = "1.0"


class Capability(str, Enum):
    """Capability tags used for routing in the supervisor."""

    ANALYSIS = "analysis"
    SCHEMA = "schema"
    INGESTION = "ingestion"
    SEGMENTATION = "segmentation"


class SafetyMode(str, Enum):
    """Execution safety policy for agent runs."""

    READ_ONLY = "read_only"
    WRITE_ALLOWED = "write_allowed"


class AgentResultStatus(str, Enum):
    """Normalized result status returned by each agent."""

    SUCCESS = "success"
    WARNING = "warning"
    FAILED = "failed"
    UNSUPPORTED = "unsupported"


class ExecutionContext(BaseModel):
    """Shared execution context for supervisor and agents."""

    contract_version: str = CONTRACT_VERSION
    request_id: str
    trace_id: str
    intent: str
    input_source: str = Field(description="file|dataset|directory|llm")
    payload: Dict[str, Any] = Field(default_factory=dict)
    capability_hints: List[Capability] = Field(default_factory=list)
    safety_mode: SafetyMode = SafetyMode.READ_ONLY
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentResult(BaseModel):
    """Standardized output shape from any agent implementation."""

    contract_version: str = CONTRACT_VERSION
    agent_name: str
    status: AgentResultStatus
    summary: str
    structured_output: Dict[str, Any] = Field(default_factory=dict)
    artifacts: List[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    warnings: List[str] = Field(default_factory=list)
    next_actions: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


@runtime_checkable
class AgentContract(Protocol):
    """Protocol every routed agent must implement."""

    name: str
    capabilities: List[Capability]
    priority: int

    def can_handle(self, context: ExecutionContext) -> bool:
        """Return True if this agent can handle the provided context."""

    def plan(self, context: ExecutionContext) -> Dict[str, Any]:
        """Return execution plan metadata for this run."""

    def execute(self, context: ExecutionContext) -> AgentResult:
        """Execute agent logic and return standardized result."""

    def summarize(self, result: AgentResult) -> str:
        """Return a short summary suitable for supervisor aggregation."""
