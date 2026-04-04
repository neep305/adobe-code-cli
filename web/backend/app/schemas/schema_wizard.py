"""Schema Wizard API Pydantic models."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChecklistStatus(str, Enum):
    PENDING = "pending"
    ANALYZING = "analyzing"
    PASSED = "passed"
    WARNING = "warning"
    FAILED = "failed"


class ErdInputMode(str, Enum):
    FILE = "file"
    DOMAIN = "domain"
    MERMAID = "mermaid"


class ChecklistItem(BaseModel):
    id: str
    label: str
    status: ChecklistStatus = ChecklistStatus.PENDING
    detail: Optional[str] = None  # Agent reasoning / explanation


class StepState(BaseModel):
    phase: int
    status: str = "pending"  # pending | analyzing | completed | approved
    user_input: Dict[str, Any] = Field(default_factory=dict)
    agent_output: Dict[str, Any] = Field(default_factory=dict)
    checklist: List[ChecklistItem] = Field(default_factory=list)
    confidence: float = 0.0
    warnings: List[str] = Field(default_factory=list)
    recommendations: Dict[str, Any] = Field(default_factory=dict)


class WizardSession(BaseModel):
    session_id: str
    current_phase: int = 1
    total_phases: int = 6
    steps: Dict[int, StepState] = Field(default_factory=dict)
    erd_mermaid: Optional[str] = None
    entities: List[Dict[str, Any]] = Field(default_factory=list)
    schemas: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ── Step input bodies ──────────────────────────────────────────────────────────

class Step1Input(BaseModel):
    mode: ErdInputMode
    domain_description: Optional[str] = None
    mermaid_erd: Optional[str] = None


class Step2Input(BaseModel):
    """User overrides for entity → XDM class mapping."""
    entity_class_overrides: Dict[str, str] = Field(default_factory=dict)


class Step3Input(BaseModel):
    """User overrides for identity strategy."""
    primary_identity_overrides: Dict[str, Dict[str, str]] = Field(default_factory=dict)
    secondary_identity_overrides: Dict[str, List[Dict[str, str]]] = Field(default_factory=dict)
    graph_strategy_override: Optional[str] = None


class Step4Input(BaseModel):
    """Merge policy decisions."""
    merge_policy_overrides: Dict[str, str] = Field(default_factory=dict)
    source_priority: Optional[List[str]] = None


class Step5Input(BaseModel):
    """Field group assignments."""
    field_group_overrides: Dict[str, List[str]] = Field(default_factory=dict)


class Step6Input(BaseModel):
    """Type mapping and preprocessing decisions."""
    type_overrides: Dict[str, Dict[str, str]] = Field(default_factory=dict)
    preprocessing_notes: Optional[str] = None


class FinalizeInput(BaseModel):
    upload_to_aep: bool = False
    output_directory: Optional[str] = None


# ── Response bodies ────────────────────────────────────────────────────────────

class StepResult(BaseModel):
    session_id: str
    phase: int
    status: str
    confidence: float
    checklist: List[ChecklistItem]
    agent_output: Dict[str, Any]
    recommendations: Dict[str, Any]
    warnings: List[str]
    erd_mermaid: Optional[str] = None


class SessionResponse(BaseModel):
    session_id: str
    current_phase: int
    total_phases: int
    steps: Dict[int, StepState]
    erd_mermaid: Optional[str]
    entities: List[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime


class FinalizeResult(BaseModel):
    session_id: str
    schemas: List[Dict[str, Any]]
    output_files: List[str]
    uploaded_schema_ids: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
