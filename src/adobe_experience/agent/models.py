"""Pydantic models for AI workflow planning and execution."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PlanStatus(str, Enum):
    """Status of an execution plan."""
    
    DRAFT = "draft"
    VALIDATED = "validated"
    READY = "ready"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RiskLevel(str, Enum):
    """Risk level assessment for execution plan."""
    
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class StepType(str, Enum):
    """Type of execution step."""
    
    VALIDATE_FILE = "validate_file"
    ANALYZE_DATA = "analyze_data"
    GENERATE_SCHEMA = "generate_schema"
    UPLOAD_SCHEMA = "upload_schema"
    CREATE_DATASET = "create_dataset"
    CREATE_BATCH = "create_batch"
    UPLOAD_FILE = "upload_file"
    COMPLETE_BATCH = "complete_batch"
    VALIDATE_INGESTION = "validate_ingestion"
    TRANSFORM_DATA = "transform_data"
    CHECK_QUOTA = "check_quota"
    WAIT_FOR_COMPLETION = "wait_for_completion"


class RetryPolicy(BaseModel):
    """Retry policy for execution steps."""
    
    max_retries: int = Field(default=3, ge=0, le=10)
    backoff_factor: float = Field(default=2.0, ge=1.0, le=10.0)
    retry_on_errors: List[str] = Field(default_factory=lambda: ["network", "timeout", "503", "429"])
    max_retry_delay: int = Field(default=60, description="Maximum delay in seconds")


class ExecutionStep(BaseModel):
    """Single step in an execution plan."""
    
    step_id: str = Field(description="Unique identifier for this step")
    step_number: int = Field(ge=1, description="Sequential step number")
    step_type: StepType
    name: str = Field(description="Human-readable step name")
    description: str = Field(description="Detailed description of what this step does")
    action: str = Field(description="Action to perform (e.g., 'create_schema', 'upload_file')")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parameters for this step")
    dependencies: List[str] = Field(default_factory=list, description="List of step_ids that must complete first")
    estimated_duration: int = Field(default=0, description="Estimated duration in seconds")
    retry_policy: Optional[RetryPolicy] = None
    skippable: bool = Field(default=False, description="Whether this step can be skipped on error")
    validation_required: bool = Field(default=False, description="Whether user validation is needed")
    
    # Execution tracking
    status: str = Field(default="pending", description="pending, running, completed, failed, skipped")
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None


class OptimizationSuggestion(BaseModel):
    """AI-generated optimization suggestion for a plan."""
    
    suggestion_id: str
    category: str = Field(description="performance, cost, reliability, security")
    title: str
    description: str
    impact: str = Field(description="Expected impact description")
    effort: str = Field(description="low, medium, high")
    estimated_improvement: Optional[str] = None
    auto_applicable: bool = Field(default=False, description="Can be applied automatically")
    applied: bool = Field(default=False)


class PlanValidationResult(BaseModel):
    """Result of plan validation."""
    
    is_valid: bool
    blockers: List[str] = Field(default_factory=list, description="Critical issues that block execution")
    warnings: List[str] = Field(default_factory=list, description="Non-critical issues")
    suggestions: List[str] = Field(default_factory=list, description="Improvement suggestions")
    checks_passed: int = 0
    checks_failed: int = 0
    validation_details: Dict[str, Any] = Field(default_factory=dict)


class PlanMetrics(BaseModel):
    """Metrics for execution plan."""
    
    total_steps: int
    estimated_duration_seconds: int
    estimated_api_calls: int
    estimated_data_transfer_mb: float = 0.0
    estimated_storage_mb: float = 0.0
    parallelizable_steps: int = 0
    critical_path_duration: int = 0


class ExecutionPlan(BaseModel):
    """Complete execution plan for AEP workflow."""
    
    plan_id: str = Field(description="Unique identifier for this plan")
    version: int = Field(default=1, ge=1)
    name: str
    description: str
    intent: str = Field(description="Original user intent/goal")
    
    # Plan configuration
    steps: List[ExecutionStep]
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Global plan parameters")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    modified_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    
    # Status and assessment
    status: PlanStatus = PlanStatus.DRAFT
    risk_level: RiskLevel = RiskLevel.MEDIUM
    
    # Metrics and estimates
    metrics: Optional[PlanMetrics] = None
    
    # Optimization and validation
    optimizations_applied: List[str] = Field(default_factory=list)
    validation_result: Optional[PlanValidationResult] = None
    
    # Template information
    template_id: Optional[str] = None
    template_version: Optional[str] = None
    
    # Execution tracking
    execution_started_at: Optional[datetime] = None
    execution_completed_at: Optional[datetime] = None
    execution_error: Optional[str] = None
    execution_results: Dict[str, Any] = Field(default_factory=dict)
    
    def get_step_by_id(self, step_id: str) -> Optional[ExecutionStep]:
        """Get a step by its ID."""
        for step in self.steps:
            if step.step_id == step_id:
                return step
        return None
    
    def get_pending_steps(self) -> List[ExecutionStep]:
        """Get all steps that haven't been executed yet."""
        return [s for s in self.steps if s.status == "pending"]
    
    def get_ready_steps(self) -> List[ExecutionStep]:
        """Get steps that are ready to execute (dependencies met)."""
        completed_ids = {s.step_id for s in self.steps if s.status == "completed"}
        ready = []
        
        for step in self.steps:
            if step.status == "pending":
                if all(dep in completed_ids for dep in step.dependencies):
                    ready.append(step)
        
        return ready
    
    def mark_step_completed(self, step_id: str, result: Optional[Dict[str, Any]] = None) -> None:
        """Mark a step as completed."""
        step = self.get_step_by_id(step_id)
        if step:
            step.status = "completed"
            step.completed_at = datetime.utcnow()
            if result:
                step.result = result
    
    def mark_step_failed(self, step_id: str, error: str) -> None:
        """Mark a step as failed."""
        step = self.get_step_by_id(step_id)
        if step:
            step.status = "failed"
            step.completed_at = datetime.utcnow()
            step.error_message = error


class PlanTemplate(BaseModel):
    """Reusable plan template."""
    
    template_id: str
    name: str
    description: str
    version: str
    category: str = Field(description="ingestion, analysis, migration, etc.")
    tags: List[str] = Field(default_factory=list)
    
    # Template parameters (to be filled when applying)
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Parameter definitions with types and defaults"
    )
    
    # Template steps (can use {{parameter}} placeholders)
    steps: List[Dict[str, Any]]
    
    # Metadata
    author: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_used: Optional[datetime] = None
    usage_count: int = 0
    
    # Optimization hints
    optimization_hints: List[str] = Field(default_factory=list)
    estimated_metrics: Optional[Dict[str, Any]] = None


class PlanComparison(BaseModel):
    """Comparison between multiple plan alternatives."""
    
    comparison_id: str
    plans: List[ExecutionPlan]
    comparison_criteria: List[str] = Field(
        default=["duration", "cost", "reliability", "complexity"]
    )
    recommendation: Optional[str] = None
    reasoning: str
    comparison_matrix: Dict[str, Dict[str, Any]] = Field(default_factory=dict)


class WorkflowContext(BaseModel):
    """Persistent context for multi-step workflows."""
    
    session_id: str
    workspace_dir: str = Field(description="Directory for session files")
    
    # Resources created during workflow
    created_resources: Dict[str, str] = Field(
        default_factory=dict,
        description="Map of resource type to ID (e.g., schema_id, dataset_id)"
    )
    uploaded_files: List[str] = Field(default_factory=list)
    
    # Conversation and state
    conversation_history: List[Dict[str, str]] = Field(default_factory=list)
    current_step: int = 0
    total_steps: int = 0
    
    # Error tracking
    error_history: List[Dict[str, Any]] = Field(default_factory=list)
    retry_count: int = 0
    
    # Checkpoints
    last_checkpoint: Optional[datetime] = None
    checkpoint_data: Dict[str, Any] = Field(default_factory=dict)
    
    # Associated plan
    current_plan_id: Optional[str] = None
    
    def add_resource(self, resource_type: str, resource_id: str) -> None:
        """Track a created resource."""
        self.created_resources[resource_type] = resource_id
    
    def get_resource(self, resource_type: str) -> Optional[str]:
        """Get a created resource ID."""
        return self.created_resources.get(resource_type)
    
    def add_conversation(self, role: str, message: str) -> None:
        """Add a conversation message."""
        self.conversation_history.append({
            "role": role,
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def add_error(self, error: str, step: str, recoverable: bool = False) -> None:
        """Track an error."""
        self.error_history.append({
            "error": error,
            "step": step,
            "recoverable": recoverable,
            "timestamp": datetime.utcnow().isoformat(),
            "retry_count": self.retry_count
        })
    
    def save_checkpoint(self) -> None:
        """Update checkpoint timestamp."""
        self.last_checkpoint = datetime.utcnow()
