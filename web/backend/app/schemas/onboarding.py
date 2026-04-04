"""Pydantic schemas for onboarding status API."""

from typing import List, Optional
from pydantic import BaseModel


class OnboardingPhaseSummary(BaseModel):
    """Aggregated progress for one onboarding phase (module)."""

    id: str
    title: str
    description: str
    order: int
    depends_on: List[str]
    completed_count: int
    total_count: int
    progress: float  # 0.0 ~ 1.0


class OnboardingStepStatus(BaseModel):
    """Status of a single onboarding step."""

    key: str
    phase_id: str
    label: str
    description: str
    completed: bool
    cli_only: bool = False
    node_hint: str = ""
    allow_manual_complete: bool = False
    manual_marked: bool = False
    resource_id: Optional[str] = None
    resource_name: Optional[str] = None
    action_url: str
    action_label: str


class OnboardingStatusResponse(BaseModel):
    """Full onboarding status for the current user."""

    steps: List[OnboardingStepStatus]
    phases: List[OnboardingPhaseSummary]
    completed_count: int
    total_count: int
    overall_progress: float  # 0.0 ~ 1.0


class OnboardingProgressUpdate(BaseModel):
    """Request body to manually mark a step as complete."""

    step_key: str
    completed: bool = True


class OnboardingPlanMessage(BaseModel):
    """Single chat message for Plan-mode onboarding."""

    role: str  # "user" | "assistant"
    content: str


class OnboardingPlanRequest(BaseModel):
    """Chat request for conversational onboarding guidance."""

    messages: List[OnboardingPlanMessage]


class OnboardingPlanResponse(BaseModel):
    """Assistant reply with optional step routing."""

    reply: str
    suggested_step_key: Optional[str] = None
    action_url: Optional[str] = None
    action_label: Optional[str] = None
    follow_up_questions: List[str] = []
    used_llm: bool = False
