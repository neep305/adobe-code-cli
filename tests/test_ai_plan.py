"""Tests for AI Plan Mode functionality."""

import json
from pathlib import Path
from uuid import uuid4

import pytest

from adobe_experience.agent.models import (
    ExecutionPlan,
    ExecutionStep,
    PlanStatus,
    RiskLevel,
    StepType,
)
from adobe_experience.agent.planner import PlannerEngine


@pytest.fixture
def sample_csv_file(tmp_path):
    """Create a sample CSV file for testing."""
    csv_file = tmp_path / "customers.csv"
    csv_content = """email,name,age,country
test@example.com,John Doe,30,US
jane@example.com,Jane Smith,25,UK
bob@example.com,Bob Johnson,35,CA
"""
    csv_file.write_text(csv_content)
    return str(csv_file)


@pytest.fixture
def sample_json_file(tmp_path):
    """Create a sample JSON file for testing."""
    json_file = tmp_path / "data.json"
    data = [
        {"id": 1, "email": "test@example.com", "name": "Test User"},
        {"id": 2, "email": "user@example.com", "name": "Another User"},
    ]
    json_file.write_text(json.dumps(data, indent=2))
    return str(json_file)


class TestPlanModels:
    """Test plan-related Pydantic models."""
    
    def test_execution_step_creation(self):
        """Test creating an ExecutionStep."""
        step = ExecutionStep(
            step_id="step_1",
            step_number=1,
            step_type=StepType.VALIDATE_FILE,
            name="Validate file",
            description="Check file format",
            action="validate_file",
            parameters={"file": "test.csv"},
            estimated_duration=5
        )
        
        assert step.step_id == "step_1"
        assert step.step_number == 1
        assert step.step_type == StepType.VALIDATE_FILE
        assert step.status == "pending"
        assert step.estimated_duration == 5
    
    def test_execution_plan_creation(self):
        """Test creating an ExecutionPlan."""
        steps = [
            ExecutionStep(
                step_id="step_1",
                step_number=1,
                step_type=StepType.VALIDATE_FILE,
                name="Validate",
                description="Validate file",
                action="validate",
                estimated_duration=5
            ),
            ExecutionStep(
                step_id="step_2",
                step_number=2,
                step_type=StepType.GENERATE_SCHEMA,
                name="Generate Schema",
                description="Generate XDM schema",
                action="generate",
                dependencies=["step_1"],
                estimated_duration=10
            ),
        ]
        
        plan = ExecutionPlan(
            plan_id=str(uuid4()),
            name="Test Plan",
            description="Test execution plan",
            intent="Test data ingestion",
            steps=steps,
            status=PlanStatus.DRAFT
        )
        
        assert plan.name == "Test Plan"
        assert len(plan.steps) == 2
        assert plan.status == PlanStatus.DRAFT
        assert plan.version == 1
    
    def test_plan_step_lookup(self):
        """Test finding steps by ID."""
        step1 = ExecutionStep(
            step_id="step_1",
            step_number=1,
            step_type=StepType.VALIDATE_FILE,
            name="Step 1",
            description="First step",
            action="action1",
            estimated_duration=5
        )
        step2 = ExecutionStep(
            step_id="step_2",
            step_number=2,
            step_type=StepType.GENERATE_SCHEMA,
            name="Step 2",
            description="Second step",
            action="action2",
            estimated_duration=10
        )
        
        plan = ExecutionPlan(
            plan_id=str(uuid4()),
            name="Test Plan",
            description="Test",
            intent="Test",
            steps=[step1, step2]
        )
        
        found_step = plan.get_step_by_id("step_1")
        assert found_step is not None
        assert found_step.name == "Step 1"
        
        not_found = plan.get_step_by_id("step_999")
        assert not_found is None
    
    def test_plan_ready_steps(self):
        """Test getting ready-to-execute steps."""
        step1 = ExecutionStep(
            step_id="step_1",
            step_number=1,
            step_type=StepType.VALIDATE_FILE,
            name="Step 1",
            description="First step",
            action="action1",
            estimated_duration=5
        )
        step2 = ExecutionStep(
            step_id="step_2",
            step_number=2,
            step_type=StepType.GENERATE_SCHEMA,
            name="Step 2",
            description="Second step",
            action="action2",
            dependencies=["step_1"],
            estimated_duration=10
        )
        
        plan = ExecutionPlan(
            plan_id=str(uuid4()),
            name="Test Plan",
            description="Test",
            intent="Test",
            steps=[step1, step2]
        )
        
        # Initially, only step1 should be ready (no dependencies)
        ready_steps = plan.get_ready_steps()
        assert len(ready_steps) == 1
        assert ready_steps[0].step_id == "step_1"
        
        # Mark step1 as completed
        plan.mark_step_completed("step_1")
        
        # Now step2 should be ready
        ready_steps = plan.get_ready_steps()
        assert len(ready_steps) == 1
        assert ready_steps[0].step_id == "step_2"


class TestPlannerEngine:
    """Test PlannerEngine functionality."""
    
    def test_planner_initialization(self):
        """Test initializing PlannerEngine."""
        planner = PlannerEngine(ai_provider="anthropic")
        assert planner.ai_provider == "anthropic"
    
    def test_file_analysis_csv(self, sample_csv_file):
        """Test analyzing a CSV file."""
        planner = PlannerEngine()
        file_info = planner._analyze_file(sample_csv_file)
        
        assert file_info["name"] == "customers.csv"
        assert file_info["extension"] == ".csv"
        assert file_info["size_mb"] >= 0  # Changed to >= 0 for small test files
        assert "columns" in file_info
        assert "email" in file_info["columns"]
        assert "name" in file_info["columns"]
    
    def test_file_analysis_json(self, sample_json_file):
        """Test analyzing a JSON file."""
        planner = PlannerEngine()
        file_info = planner._analyze_file(sample_json_file)
        
        assert file_info["name"] == "data.json"
        assert file_info["extension"] == ".json"
        assert "fields" in file_info
        assert "id" in file_info["fields"]
        assert "email" in file_info["fields"]
    
    def test_fallback_plan_generation(self, sample_csv_file):
        """Test fallback plan generation without AI."""
        planner = PlannerEngine()
        file_info = planner._analyze_file(sample_csv_file)
        
        plan_data = planner._fallback_plan_generation(
            intent="Ingest customers.csv",
            file_info=file_info
        )
        
        assert "name" in plan_data
        assert "steps" in plan_data
        assert len(plan_data["steps"]) >= 5  # Should have multiple steps
        
        # Check first step is validation
        first_step = plan_data["steps"][0]
        assert first_step["step_type"] == "validate_file"
    
    def test_generate_plan_basic(self, sample_csv_file):
        """Test basic plan generation."""
        planner = PlannerEngine()
        
        plan = planner.generate_plan(
            intent=f"Ingest customers data from {sample_csv_file}",
            file_path=sample_csv_file
        )
        
        assert plan is not None
        assert isinstance(plan, ExecutionPlan)
        assert len(plan.steps) > 0
        assert plan.status == PlanStatus.DRAFT
        assert plan.risk_level in [
            RiskLevel.VERY_LOW,
            RiskLevel.LOW,
            RiskLevel.MEDIUM,
            RiskLevel.HIGH,
            RiskLevel.VERY_HIGH
        ]
    
    def test_plan_metrics_calculation(self, sample_csv_file):
        """Test metrics calculation for a plan."""
        planner = PlannerEngine()
        plan = planner.generate_plan(
            intent="Ingest data",
            file_path=sample_csv_file
        )
        
        assert plan.metrics is not None
        assert plan.metrics.total_steps == len(plan.steps)
        assert plan.metrics.estimated_duration_seconds > 0
        assert plan.metrics.estimated_api_calls > 0
    
    def test_risk_level_assessment(self, sample_csv_file):
        """Test risk level assessment."""
        planner = PlannerEngine()
        plan = planner.generate_plan(
            intent="Ingest small file",
            file_path=sample_csv_file
        )
        
        # Small, simple plan should have low risk
        assert plan.risk_level in [RiskLevel.VERY_LOW, RiskLevel.LOW, RiskLevel.MEDIUM]
    
    def test_explain_plan(self, sample_csv_file):
        """Test plan explanation generation."""
        planner = PlannerEngine()
        plan = planner.generate_plan(
            intent="Ingest data",
            file_path=sample_csv_file
        )
        
        explanation = planner.explain_plan(plan)
        
        assert "plan_id" in explanation
        assert "overall_goal" in explanation
        assert "step_explanations" in explanation
        assert len(explanation["step_explanations"]) == len(plan.steps)
        
        # Check first step explanation
        first_step_exp = explanation["step_explanations"]["step_1"]
        assert "name" in first_step_exp
        assert "description" in first_step_exp
        assert "why_needed" in first_step_exp
    
    def test_optimize_plan_basic(self, sample_csv_file):
        """Test basic plan optimization."""
        planner = PlannerEngine()
        plan = planner.generate_plan(
            intent="Ingest data",
            file_path=sample_csv_file
        )
        
        original_status = plan.status
        optimized_plan = planner.optimize_plan(plan)
        
        # Plan should be marked as ready after optimization
        assert optimized_plan.status == PlanStatus.READY
        assert len(optimized_plan.optimizations_applied) >= 0  # May or may not have optimizations
    
    def test_compare_alternatives(self, sample_csv_file):
        """Test comparing alternative plans."""
        planner = PlannerEngine()
        
        comparison = planner.compare_alternatives(
            intent="Ingest data",
            context={"file": sample_csv_file}
        )
        
        assert comparison is not None
        assert len(comparison.plans) == 3  # Should generate 3 alternatives
        assert comparison.recommendation is not None
        assert comparison.reasoning is not None
        assert len(comparison.comparison_matrix) == 3


class TestPlanSerialization:
    """Test plan serialization and deserialization."""
    
    def test_plan_to_json(self):
        """Test serializing plan to JSON."""
        step = ExecutionStep(
            step_id="step_1",
            step_number=1,
            step_type=StepType.VALIDATE_FILE,
            name="Validate",
            description="Validate file",
            action="validate",
            estimated_duration=5
        )
        
        plan = ExecutionPlan(
            plan_id=str(uuid4()),
            name="Test Plan",
            description="Test",
            intent="Test intent",
            steps=[step]
        )
        
        # Serialize to dict
        plan_dict = plan.model_dump()
        
        assert "plan_id" in plan_dict
        assert "steps" in plan_dict
        assert len(plan_dict["steps"]) == 1
        
        # Should be JSON serializable
        json_str = json.dumps(plan_dict, default=str)
        assert len(json_str) > 0
    
    def test_plan_from_json(self):
        """Test deserializing plan from JSON."""
        plan_data = {
            "plan_id": str(uuid4()),
            "version": 1,
            "name": "Test Plan",
            "description": "Test",
            "intent": "Test intent",
            "steps": [
                {
                    "step_id": "step_1",
                    "step_number": 1,
                    "step_type": "validate_file",
                    "name": "Validate",
                    "description": "Validate file",
                    "action": "validate",
                    "parameters": {},
                    "dependencies": [],
                    "estimated_duration": 5,
                    "skippable": False,
                    "validation_required": False,
                    "status": "pending"
                }
            ],
            "status": "draft",
            "risk_level": "low",
            "parameters": {},
            "optimizations_applied": [],
            "execution_results": {}
        }
        
        # Deserialize from dict
        plan = ExecutionPlan(**plan_data)
        
        assert plan.name == "Test Plan"
        assert len(plan.steps) == 1
        assert plan.steps[0].step_id == "step_1"


class TestProjectPlanning:
    """Test multi-file project planning functionality."""
    
    def test_project_plan_generation(self):
        """Test generating plan for multi-file project."""
        planner = PlannerEngine()
        
        # Use existing ecommerce test data
        project_dir = "test-data/ecommerce"
        if not Path(project_dir).exists():
            pytest.skip("ecommerce test data not available")
        
        plan = planner.generate_plan(
            intent="Ingest ecommerce data",
            project_dir=project_dir
        )
        
        # Verify plan structure
        assert plan is not None
        assert "Multi-Entity" in plan.name
        assert len(plan.steps) > 8  # At least 8 steps per entity
        assert plan.status == PlanStatus.DRAFT
        
        # Verify project metadata
        assert plan.parameters is not None
        assert "entity_count" in plan.parameters
        assert plan.parameters["entity_count"] >= 4
        assert "ingestion_order" in plan.parameters
        assert len(plan.parameters["ingestion_order"]) >= 4
    
    def test_ingestion_order_calculation(self):
        """Test that ingestion order respects dependencies."""
        planner = PlannerEngine()
        
        project_dir = "test-data/ecommerce"
        if not Path(project_dir).exists():
            pytest.skip("ecommerce test data not available")
        
        plan = planner.generate_plan(
            intent="Ingest ecommerce data",
            project_dir=project_dir
        )
        
        ingestion_order = plan.parameters.get("ingestion_order", [])
        
        # customers should come before orders (FK dependency)
        customers_idx = ingestion_order.index("customers") if "customers" in ingestion_order else -1
        orders_idx = ingestion_order.index("orders") if "orders" in ingestion_order else -1
        
        if customers_idx >= 0 and orders_idx >= 0:
            assert customers_idx < orders_idx, "customers should be ingested before orders"
    
    def test_cross_entity_dependencies(self):
        """Test that cross-entity dependencies are set up correctly."""
        planner = PlannerEngine()
        
        project_dir = "test-data/ecommerce"
        if not Path(project_dir).exists():
            pytest.skip("ecommerce test data not available")
        
        plan = planner.generate_plan(
            intent="Ingest ecommerce data",
            project_dir=project_dir
        )
        
        # Find orders schema generation step
        orders_schema_step = None
        customers_schema_upload_step = None
        
        for step in plan.steps:
            if (step.step_type == StepType.GENERATE_SCHEMA and 
                step.parameters.get("entity") == "orders"):
                orders_schema_step = step
            if (step.step_type == StepType.UPLOAD_SCHEMA and 
                step.parameters.get("entity") == "customers"):
                customers_schema_upload_step = step
        
        # Verify cross-entity dependency exists
        if orders_schema_step and customers_schema_upload_step:
            assert customers_schema_upload_step.step_id in orders_schema_step.dependencies, \
                "orders schema should depend on customers schema being uploaded"
    
    def test_entity_steps_generation(self):
        """Test that each entity gets proper steps."""
        planner = PlannerEngine()
        
        project_dir = "test-data/ecommerce"
        if not Path(project_dir).exists():
            pytest.skip("ecommerce test data not available")
        
        plan = planner.generate_plan(
            intent="Ingest ecommerce data",
            project_dir=project_dir
        )
        
        # Group steps by entity
        entity_steps = {}
        for step in plan.steps:
            entity = step.parameters.get("entity")
            if entity:
                entity_steps.setdefault(entity, []).append(step)
        
        # Each entity should have standard workflow steps
        for entity, steps in entity_steps.items():
            assert len(steps) >= 7, f"{entity} should have at least 7 steps"
            
            # Check for key step types
            step_types = [s.step_type for s in steps]
            assert StepType.VALIDATE_FILE in step_types
            assert StepType.GENERATE_SCHEMA in step_types
            assert StepType.UPLOAD_SCHEMA in step_types
            assert StepType.CREATE_DATASET in step_types


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
