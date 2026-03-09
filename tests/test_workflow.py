"""Tests for WorkflowOrchestrator execution functionality."""

import asyncio
import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from adobe_experience.agent.models import (
    ExecutionPlan,
    ExecutionStep,
    PlanStatus,
    RetryPolicy,
    StepType,
)
from adobe_experience.agent.workflow import (
    ExecutionResult,
    StepResult,
    WorkflowExecutionError,
    WorkflowOrchestrator,
)


@pytest.fixture
def sample_plan():
    """Create a sample execution plan for testing."""
    steps = [
        ExecutionStep(
            step_id="step_1",
            step_number=1,
            step_type=StepType.VALIDATE_FILE,
            name="Validate file",
            description="Validate input file",
            action="validate_file",
            parameters={"file": "test.csv"},
            dependencies=[],
            estimated_duration=5
        ),
        ExecutionStep(
            step_id="step_2",
            step_number=2,
            step_type=StepType.GENERATE_SCHEMA,
            name="Generate schema",
            description="Generate XDM schema",
            action="generate_schema",
            parameters={"file": "test.csv", "entity": "test"},
            dependencies=["step_1"],
            estimated_duration=10,
            retry_policy=RetryPolicy(max_retries=2)
        ),
        ExecutionStep(
            step_id="step_3",
            step_number=3,
            step_type=StepType.UPLOAD_SCHEMA,
            name="Upload schema",
            description="Upload to registry",
            action="upload_schema",
            parameters={"entity": "test"},
            dependencies=["step_2"],
            estimated_duration=3
        ),
    ]
    
    return ExecutionPlan(
        plan_id="test-plan-123",
        name="Test Plan",
        description="Test execution plan",
        intent="Test ingestion",
        steps=steps,
        status=PlanStatus.READY
    )


@pytest.fixture
def test_csv_file(tmp_path):
    """Create a test CSV file."""
    csv_file = tmp_path / "test.csv"
    csv_content = """email,name,age
test@example.com,Test User,30
user@example.com,Another User,25
"""
    csv_file.write_text(csv_content)
    return str(csv_file)


class TestWorkflowOrchestrator:
    """Test WorkflowOrchestrator functionality."""
    
    def test_orchestrator_initialization(self):
        """Test orchestrator initializes correctly."""
        orchestrator = WorkflowOrchestrator()
        
        assert orchestrator.config is None
        assert orchestrator.execution_context == {}
        assert orchestrator._aep_client is None
    
    @pytest.mark.asyncio
    async def test_execute_plan_dry_run(self, sample_plan, test_csv_file):
        """Test executing a plan in dry-run mode."""
        # Update plan to use test file
        for step in sample_plan.steps:
            if "file" in step.parameters:
                step.parameters["file"] = test_csv_file
        
        orchestrator = WorkflowOrchestrator()
        
        result = await orchestrator.execute_plan(sample_plan, dry_run=True)
        
        assert isinstance(result, ExecutionResult)
        assert result.plan_id == sample_plan.plan_id
        assert result.status == "completed"
        assert result.steps_completed == len(sample_plan.steps)
        assert result.steps_failed == 0
    
    @pytest.mark.asyncio
    async def test_execute_plan_with_progress_callback(self, sample_plan, test_csv_file):
        """Test execution with progress callback."""
        # Update plan to use test file
        for step in sample_plan.steps:
            if "file" in step.parameters:
                step.parameters["file"] = test_csv_file
        
        orchestrator = WorkflowOrchestrator()
        
        # Track progress
        progress_updates = []
        
        def progress_callback(step, step_result):
            progress_updates.append((step.step_id, step_result.status))
        
        result = await orchestrator.execute_plan(
            sample_plan,
            dry_run=True,
            progress_callback=progress_callback
        )
        
        assert len(progress_updates) == len(sample_plan.steps)
        assert all(status == "success" for _, status in progress_updates)
    
    @pytest.mark.asyncio
    async def test_validate_file_step(self, test_csv_file):
        """Test file validation step."""
        orchestrator = WorkflowOrchestrator()
        
        step = ExecutionStep(
            step_id="step_1",
            step_number=1,
            step_type=StepType.VALIDATE_FILE,
            name="Validate file",
            description="Validate CSV",
            action="validate_file",
            parameters={"file": test_csv_file},
            dependencies=[],
            estimated_duration=5
        )
        
        result = await orchestrator._validate_file(step, dry_run=False)
        
        assert result["status"] == "valid"
        assert result["row_count"] == 2
        assert "columns" in result
    
    @pytest.mark.asyncio
    async def test_validate_file_missing(self):
        """Test file validation with missing file."""
        orchestrator = WorkflowOrchestrator()
        
        step = ExecutionStep(
            step_id="step_1",
            step_number=1,
            step_type=StepType.VALIDATE_FILE,
            name="Validate file",
            description="Validate CSV",
            action="validate_file",
            parameters={"file": "/nonexistent/file.csv"},
            dependencies=[],
            estimated_duration=5
        )
        
        with pytest.raises(FileNotFoundError):
            await orchestrator._validate_file(step, dry_run=False)
    
    @pytest.mark.asyncio
    async def test_step_retry_logic(self, test_csv_file):
        """Test step execution with retry logic."""
        from datetime import datetime
        orchestrator = WorkflowOrchestrator()
        
        # Create a step that will succeed on second attempt
        step = ExecutionStep(
            step_id="step_1",
            step_number=1,
            step_type=StepType.VALIDATE_FILE,
            name="Validate file",
            description="Validate CSV",
            action="validate_file",
            parameters={"file": test_csv_file},
            dependencies=[],
            estimated_duration=5,
            retry_policy=RetryPolicy(max_retries=2, backoff_factor=1.5)
        )
        
        plan = ExecutionPlan(
            plan_id="test-plan",
            name="Test",
            description="Test",
            intent="Test",
            steps=[step],
            status=PlanStatus.READY
        )
        
        result = ExecutionResult(
            plan_id=plan.plan_id,
            status="executing",
            started_at=datetime.utcnow()
        )
        
        # Should succeed without retry since file exists
        step_result = await orchestrator._execute_step_with_retry(
            step, plan, result, dry_run=False, progress_callback=None
        )
        
        assert step_result.status == "success"
        assert step_result.retry_count == 0
    
    @pytest.mark.asyncio
    async def test_dependencies_check(self):
        """Test dependency checking logic."""
        orchestrator = WorkflowOrchestrator()
        
        step = ExecutionStep(
            step_id="step_2",
            step_number=2,
            step_type=StepType.GENERATE_SCHEMA,
            name="Generate schema",
            description="Generate XDM schema",
            action="generate_schema",
            parameters={},
            dependencies=["step_1"],
            estimated_duration=10
        )
        
        # No previous results
        results = {}
        assert not orchestrator._are_dependencies_met(step, results)
        
        # Dependency failed
        results["step_1"] = StepResult(
            step_id="step_1",
            step_number=1,
            status="failed",
            execution_time_seconds=1.0,
            error="Test error"
        )
        assert not orchestrator._are_dependencies_met(step, results)
        
        # Dependency succeeded
        results["step_1"] = StepResult(
            step_id="step_1",
            step_number=1,
            status="success",
            execution_time_seconds=1.0
        )
        assert orchestrator._are_dependencies_met(step, results)
    
    @pytest.mark.asyncio
    async def test_generate_schema_csv(self, test_csv_file):
        """Test schema generation from CSV."""
        orchestrator = WorkflowOrchestrator()
        
        step = ExecutionStep(
            step_id="step_2",
            step_number=2,
            step_type=StepType.GENERATE_SCHEMA,
            name="Generate schema",
            description="Generate XDM schema",
            action="generate_schema",
            parameters={"file": test_csv_file, "entity": "test"},
            dependencies=[],
            estimated_duration=10
        )
        
        previous_results = {}
        
        result = await orchestrator._generate_schema(step, previous_results, dry_run=False)
        
        assert result["status"] == "generated"
        assert "schema" in result
        assert "schema_title" in result
        assert result["field_count"] > 0
    
    @pytest.mark.asyncio
    async def test_create_batch_step(self):
        """Test batch creation step."""
        orchestrator = WorkflowOrchestrator()
        
        step = ExecutionStep(
            step_id="step_5",
            step_number=5,
            step_type=StepType.CREATE_BATCH,
            name="Create batch",
            description="Create batch",
            action="create_batch",
            parameters={"entity": "test"},
            dependencies=["step_4"],
            estimated_duration=2
        )
        
        previous_results = {
            "step_4": StepResult(
                step_id="step_4",
                step_number=4,
                status="success",
                execution_time_seconds=1.0,
                output={"dataset_id": "test-dataset-123"}
            )
        }
        
        result = await orchestrator._create_batch(step, previous_results, dry_run=True)
        
        assert "batch_id" in result
        assert result["dataset_id"] == "test-dataset-123"
    
    @pytest.mark.asyncio
    async def test_upload_file_step(self, test_csv_file):
        """Test file upload step."""
        orchestrator = WorkflowOrchestrator()
        
        step = ExecutionStep(
            step_id="step_6",
            step_number=6,
            step_type=StepType.UPLOAD_FILE,
            name="Upload file",
            description="Upload data",
            action="upload_file",
            parameters={"file": test_csv_file},
            dependencies=["step_5"],
            estimated_duration=15
        )
        
        previous_results = {
            "step_5": StepResult(
                step_id="step_5",
                step_number=5,
                status="success",
                execution_time_seconds=1.0,
                output={"batch_id": "test-batch-123", "dataset_id": "test-dataset-123"}
            )
        }
        
        result = await orchestrator._upload_file(step, previous_results, dry_run=True)
        
        assert result["batch_id"] == "test-batch-123"
        assert result["bytes_uploaded"] > 0
    
    @pytest.mark.asyncio
    async def test_plan_status_updates(self, sample_plan, test_csv_file):
        """Test plan status updates during execution."""
        # Update plan to use test file
        for step in sample_plan.steps:
            if "file" in step.parameters:
                step.parameters["file"] = test_csv_file
        
        orchestrator = WorkflowOrchestrator()
        
        assert sample_plan.status == PlanStatus.READY
        
        result = await orchestrator.execute_plan(sample_plan, dry_run=True)
        
        assert result.status == "completed"
        assert sample_plan.status == PlanStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_execution_result_serialization(self, sample_plan, test_csv_file):
        """Test ExecutionResult can be serialized."""
        # Update plan to use test file
        for step in sample_plan.steps:
            if "file" in step.parameters:
                step.parameters["file"] = test_csv_file
        
        orchestrator = WorkflowOrchestrator()
        
        result = await orchestrator.execute_plan(sample_plan, dry_run=True)
        
        # Should be serializable to dict
        result_dict = result.model_dump()
        
        assert "plan_id" in result_dict
        assert "status" in result_dict
        assert "steps_completed" in result_dict
        assert "results" in result_dict


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
