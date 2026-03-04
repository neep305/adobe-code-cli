"""Workflow orchestrator for executing AI-generated plans."""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from adobe_experience.agent.models import (
    ExecutionPlan,
    ExecutionStep,
    PlanStatus,
    StepType,
)


logger = logging.getLogger(__name__)


# ============================================================================
# Exceptions
# ============================================================================


class WorkflowExecutionError(Exception):
    """Base exception for workflow execution errors."""
    
    def __init__(self, message: str, step_id: Optional[str] = None):
        super().__init__(message)
        self.step_id = step_id


class StepExecutionError(WorkflowExecutionError):
    """Exception raised when a step fails."""
    pass


class IngestionError(WorkflowExecutionError):
    """Exception raised during data ingestion."""
    pass


class ValidationError(WorkflowExecutionError):
    """Exception raised during validation."""
    pass


# ============================================================================
# Result Models
# ============================================================================


class StepResult(BaseModel):
    """Result of executing a single step."""
    
    step_id: str
    step_number: int
    status: str  # success, failed, skipped
    execution_time_seconds: float
    output: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    retry_count: int = 0


class ExecutionResult(BaseModel):
    """Result of executing an entire plan."""
    
    plan_id: str
    status: str  # completed, failed, partial
    started_at: datetime
    completed_at: Optional[datetime] = None
    execution_time_seconds: float = 0.0
    steps_completed: int = 0
    steps_failed: int = 0
    steps_skipped: int = 0
    results: Dict[str, StepResult] = Field(default_factory=dict)
    artifacts: Dict[str, Any] = Field(default_factory=dict)  # schema_ids, dataset_ids, etc.


# ============================================================================
# Workflow Orchestrator
# ============================================================================


class WorkflowOrchestrator:
    """Executes AI-generated plans against Adobe Experience Platform."""
    
    def __init__(self, config=None):
        """Initialize workflow orchestrator.
        
        Args:
            config: AEP configuration object
        """
        self.config = config
        self.execution_context = {}
        
        # Initialize clients (lazy loading)
        self._aep_client = None
        self._schema_client = None
        self._catalog_client = None
        self._flow_client = None
    
    @property
    def aep_client(self):
        """Lazy load AEP client."""
        if self._aep_client is None:
            from adobe_experience.aep.client import AEPClient
            self._aep_client = AEPClient(self.config)
        return self._aep_client
    
    @property
    def schema_client(self):
        """Lazy load schema client."""
        if self._schema_client is None:
            from adobe_experience.schema.xdm import XDMSchemaAnalyzer
            self._schema_client = XDMSchemaAnalyzer
        return self._schema_client
    
    @property
    def catalog_client(self):
        """Lazy load catalog client."""
        if self._catalog_client is None:
            from adobe_experience.catalog.client import CatalogClient
            self._catalog_client = CatalogClient(self.config)
        return self._catalog_client
    
    @property
    def flow_client(self):
        """Lazy load flow client."""
        if self._flow_client is None:
            from adobe_experience.flow.client import FlowClient
            self._flow_client = FlowClient(self.config)
        return self._flow_client
    
    async def execute_plan(
        self,
        plan: ExecutionPlan,
        dry_run: bool = False,
        progress_callback: Optional[callable] = None
    ) -> ExecutionResult:
        """Execute a plan step by step.
        
        Args:
            plan: ExecutionPlan to execute
            dry_run: If True, simulate execution without actual API calls
            progress_callback: Optional callback for progress updates
            
        Returns:
            ExecutionResult with outcomes of all steps
        """
        logger.info(f"Starting execution of plan {plan.plan_id} (dry_run={dry_run})")
        
        started_at = datetime.utcnow()
        plan.status = PlanStatus.EXECUTING
        
        result = ExecutionResult(
            plan_id=plan.plan_id,
            status="executing",
            started_at=started_at
        )
        
        # Execute steps in order
        for step in plan.steps:
            # Check if dependencies are met
            if not self._are_dependencies_met(step, result.results):
                logger.warning(f"Dependencies not met for step {step.step_id}, skipping")
                result.results[step.step_id] = StepResult(
                    step_id=step.step_id,
                    step_number=step.step_number,
                    status="skipped",
                    execution_time_seconds=0.0,
                    error="Dependencies not met"
                )
                result.steps_skipped += 1
                continue
            
            # Execute step with retry logic
            step_result = await self._execute_step_with_retry(
                step, plan, result, dry_run, progress_callback
            )
            
            result.results[step.step_id] = step_result
            
            if step_result.status == "success":
                result.steps_completed += 1
                plan.mark_step_completed(step.step_id)
            elif step_result.status == "failed":
                result.steps_failed += 1
                plan.mark_step_failed(step.step_id, step_result.error or "Unknown error")
                
                # Stop execution on critical step failure
                if not step.skippable:
                    logger.error(f"Critical step {step.step_id} failed, stopping execution")
                    break
            else:
                result.steps_skipped += 1
            
            # Progress callback
            if progress_callback:
                progress_callback(step, step_result)
        
        # Finalize result
        result.completed_at = datetime.utcnow()
        result.execution_time_seconds = (result.completed_at - started_at).total_seconds()
        
        if result.steps_failed == 0:
            result.status = "completed"
            plan.status = PlanStatus.COMPLETED
        elif result.steps_completed > 0:
            result.status = "partial"
            plan.status = PlanStatus.FAILED
        else:
            result.status = "failed"
            plan.status = PlanStatus.FAILED
        
        logger.info(
            f"Plan execution finished: {result.steps_completed} completed, "
            f"{result.steps_failed} failed, {result.steps_skipped} skipped"
        )
        
        return result
    
    async def _execute_step_with_retry(
        self,
        step: ExecutionStep,
        plan: ExecutionPlan,
        result: ExecutionResult,
        dry_run: bool,
        progress_callback: Optional[callable]
    ) -> StepResult:
        """Execute a step with retry logic."""
        
        retry_policy = step.retry_policy
        max_retries = retry_policy.max_retries if retry_policy else 0
        base_delay = 5  # Base retry delay in seconds
        
        for attempt in range(max_retries + 1):
            try:
                step_result = await self._execute_step(step, result.results, dry_run)
                step_result.retry_count = attempt
                return step_result
                
            except Exception as e:
                logger.warning(f"Step {step.step_id} attempt {attempt + 1} failed: {e}")
                
                if attempt < max_retries:
                    # Calculate backoff delay
                    if retry_policy:
                        delay = min(
                            base_delay * (retry_policy.backoff_factor ** attempt),
                            retry_policy.max_retry_delay
                        )
                    else:
                        delay = base_delay
                    
                    logger.info(f"Retrying step {step.step_id} in {delay:.1f}s...")
                    await asyncio.sleep(delay)
                else:
                    # All retries exhausted
                    return StepResult(
                        step_id=step.step_id,
                        step_number=step.step_number,
                        status="failed",
                        execution_time_seconds=0.0,
                        error=str(e),
                        retry_count=attempt
                    )
    
    async def _execute_step(
        self,
        step: ExecutionStep,
        previous_results: Dict[str, StepResult],
        dry_run: bool
    ) -> StepResult:
        """Execute a single step.
        
        Args:
            step: ExecutionStep to execute
            previous_results: Results from previous steps
            dry_run: If True, simulate without actual API calls
            
        Returns:
            StepResult with execution outcome
        """
        logger.info(f"Executing step {step.step_number}: {step.name}")
        started_at = datetime.utcnow()
        
        try:
            # Route to appropriate executor based on step type
            if step.step_type == StepType.VALIDATE_FILE:
                output = await self._validate_file(step, dry_run)
            
            elif step.step_type == StepType.GENERATE_SCHEMA:
                output = await self._generate_schema(step, previous_results, dry_run)
            
            elif step.step_type == StepType.UPLOAD_SCHEMA:
                output = await self._upload_schema(step, previous_results, dry_run)
            
            elif step.step_type == StepType.CREATE_DATASET:
                output = await self._create_dataset(step, previous_results, dry_run)
            
            elif step.step_type == StepType.CREATE_BATCH:
                output = await self._create_batch(step, previous_results, dry_run)
            
            elif step.step_type == StepType.UPLOAD_FILE:
                output = await self._upload_file(step, previous_results, dry_run)
            
            elif step.step_type == StepType.COMPLETE_BATCH:
                output = await self._complete_batch(step, previous_results, dry_run)
            
            elif step.step_type == StepType.VALIDATE_INGESTION:
                output = await self._validate_ingestion(step, previous_results, dry_run)
            
            else:
                raise ValueError(f"Unsupported step type: {step.step_type}")
            
            completed_at = datetime.utcnow()
            execution_time = (completed_at - started_at).total_seconds()
            
            return StepResult(
                step_id=step.step_id,
                step_number=step.step_number,
                status="success",
                execution_time_seconds=execution_time,
                output=output
            )
            
        except Exception as e:
            logger.error(f"Step {step.step_id} failed: {e}")
            completed_at = datetime.utcnow()
            execution_time = (completed_at - started_at).total_seconds()
            
            return StepResult(
                step_id=step.step_id,
                step_number=step.step_number,
                status="failed",
                execution_time_seconds=execution_time,
                error=str(e)
            )
    
    def _are_dependencies_met(
        self,
        step: ExecutionStep,
        results: Dict[str, StepResult]
    ) -> bool:
        """Check if all dependencies for a step are met."""
        for dep_id in step.dependencies:
            if dep_id not in results:
                return False
            if results[dep_id].status != "success":
                return False
        return True
    
    # ========================================================================
    # Step Executors
    # ========================================================================
    
    async def _validate_file(self, step: ExecutionStep, dry_run: bool) -> Dict[str, Any]:
        """Validate file exists and is readable."""
        file_path = Path(step.parameters["file"])
        
        if dry_run:
            return {
                "file_path": str(file_path),
                "status": "valid (dry-run)",
                "row_count": 100
            }
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Check format and count rows
        if file_path.suffix.lower() == ".csv":
            import csv
            with open(file_path, encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                row_count = len(rows)
                columns = list(rows[0].keys()) if rows else []
        
        elif file_path.suffix.lower() == ".json":
            with open(file_path, encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    row_count = len(data)
                    columns = list(data[0].keys()) if data else []
                else:
                    row_count = 1
                    columns = list(data.keys())
        
        else:
            raise ValueError(f"Unsupported file format: {file_path.suffix}")
        
        logger.info(f"Validated {file_path.name}: {row_count} records, {len(columns)} columns")
        
        return {
            "file_path": str(file_path),
            "status": "valid",
            "row_count": row_count,
            "column_count": len(columns),
            "columns": columns[:10]  # First 10 columns
        }
    
    async def _generate_schema(
        self,
        step: ExecutionStep,
        previous_results: Dict[str, StepResult],
        dry_run: bool
    ) -> Dict[str, Any]:
        """Generate XDM schema from file."""
        
        if dry_run:
            entity = step.parameters.get('entity', 'data')
            # Return mock schema data that matches real schema structure
            return {
                "schema": {
                    "title": f"{entity}_schema",
                    "type": "object",
                    "properties": {}
                },
                "schema_title": f"{entity}_schema",
                "schema_id": f"https://ns.adobe.com/{entity}_schema",
                "status": "generated (dry-run)",
                "field_count": 10
            }
        
        file_path = step.parameters["file"]
        entity = step.parameters.get("entity", "data")
        
        # Use XDM analyzer to generate schema
        path = Path(file_path)
        
        if path.suffix.lower() == ".json":
            schema = self.schema_client.from_json_file(
                file_path,
                schema_name=f"{entity}_schema",
                schema_description=f"Auto-generated schema for {entity}"
            )
        elif path.suffix.lower() == ".csv":
            # For CSV, read and convert to sample data first
            import csv
            with open(file_path, encoding='utf-8') as f:
                reader = csv.DictReader(f)
                sample_data = [row for row in reader][:100]  # Sample first 100 rows
            
            schema = self.schema_client.from_sample_data(
                sample_data,
                schema_name=f"{entity}_schema",
                schema_description=f"Auto-generated schema for {entity}"
            )
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")
        
        logger.info(f"Generated schema: {schema.title} with {len(schema.properties or {})} fields")
        
        return {
            "schema": schema.model_dump(),
            "schema_title": schema.title,
            "schema_id": schema.schema_id,
            "field_count": len(schema.properties or {}),
            "status": "generated"
        }
    
    async def _upload_schema(
        self,
        step: ExecutionStep,
        previous_results: Dict[str, StepResult],
        dry_run: bool
    ) -> Dict[str, Any]:
        """Upload schema to AEP Schema Registry."""
        
        # Get schema from previous step
        schema_step_id = step.dependencies[0]
        if schema_step_id not in previous_results:
            raise StepExecutionError("Schema generation step not found", step.step_id)
        
        schema_data = previous_results[schema_step_id].output.get("schema")
        if not schema_data:
            raise StepExecutionError("No schema data from previous step", step.step_id)
        
        if dry_run:
            return {
                "schema_id": "https://ns.adobe.com/tenant/schemas/mock-schema-id",
                "status": "uploaded (dry-run)"
            }
        
        # Upload schema using Schema Registry API
        try:
            from adobe_experience.schema.models import XDMSchema
            from adobe_experience.schema.xdm import XDMSchemaAnalyzer
            from adobe_experience.aep.client import AEPClient
            
            # Reconstruct XDMSchema from dict
            schema = XDMSchema(**schema_data)
            
            # Create clients
            async with AEPClient(self.config) as aep_client:
                schema_analyzer = XDMSchemaAnalyzer(aep_client)
                response = await schema_analyzer.create_schema(schema)
            
            schema_id = response.get("$id") or response.get("meta:altId")
            logger.info(f"Schema uploaded successfully: {schema_id}")
            
            return {
                "schema_id": schema_id,
                "schema_title": response.get("title"),
                "status": "uploaded"
            }
            
        except Exception as e:
            logger.error(f"Schema upload failed: {e}")
            raise StepExecutionError(f"Failed to upload schema: {e}", step.step_id)
    
    async def _create_dataset(
        self,
        step: ExecutionStep,
        previous_results: Dict[str, StepResult],
        dry_run: bool
    ) -> Dict[str, Any]:
        """Create dataset in AEP."""
        
        # Get schema ID from previous step
        schema_upload_step = None
        for dep_id in step.dependencies:
            if dep_id in previous_results:
                result = previous_results[dep_id]
                if "schema_id" in result.output:
                    schema_upload_step = result
                    break
        
        if not schema_upload_step:
            raise StepExecutionError("Schema upload step not found", step.step_id)
        
        schema_id = schema_upload_step.output["schema_id"]
        entity = step.parameters.get("entity", "data")
        enable_profile = step.parameters.get("enable_profile", False)
        
        if dry_run:
            return {
                "dataset_id": "mock-dataset-id-12345",
                "dataset_name": f"{entity}_dataset",
                "status": "created (dry-run)"
            }
        
        # Create dataset using Catalog Service API
        try:
            from adobe_experience.aep.client import AEPClient
            from adobe_experience.catalog.client import CatalogServiceClient
            
            dataset_name = step.parameters.get("name") or f"{entity.title()} Dataset"
            description = step.parameters.get("description") or f"Auto-generated dataset for {entity}"
            
            async with AEPClient(self.config) as aep_client:
                catalog = CatalogServiceClient(aep_client)
                dataset_id = await catalog.create_dataset(
                    name=dataset_name,
                    schema_id=schema_id,
                    description=description,
                    enable_profile=enable_profile
                )
            
            logger.info(f"Dataset created successfully: {dataset_id}")
            
            return {
                "dataset_id": dataset_id,
                "dataset_name": dataset_name,
                "schema_id": schema_id,
                "enable_profile": enable_profile,
                "status": "created"
            }
            
        except Exception as e:
            logger.error(f"Dataset creation failed: {e}")
            raise StepExecutionError(f"Failed to create dataset: {e}", step.step_id)
    
    async def _create_batch(
        self,
        step: ExecutionStep,
        previous_results: Dict[str, StepResult],
        dry_run: bool
    ) -> Dict[str, Any]:
        """Create batch for data ingestion."""
        
        # Get dataset ID from previous step
        dataset_step = None
        for dep_id in step.dependencies:
            if dep_id in previous_results:
                result = previous_results[dep_id]
                if "dataset_id" in result.output:
                    dataset_step = result
                    break
        
        if not dataset_step:
            raise StepExecutionError("Dataset creation step not found", step.step_id)
        
        dataset_id = dataset_step.output["dataset_id"]
        
        if dry_run:
            return {
                "batch_id": "mock-batch-id-67890",
                "dataset_id": dataset_id,
                "status": "initialized (dry-run)"
            }
        
        # Create batch using Catalog Service API
        try:
            from adobe_experience.aep.client import AEPClient
            from adobe_experience.catalog.client import CatalogServiceClient
            
            format_type = step.parameters.get("format", "parquet")
            
            async with AEPClient(self.config) as aep_client:
                catalog = CatalogServiceClient(aep_client)
                batch_id = await catalog.create_batch(
                    dataset_id=dataset_id,
                    format=format_type
                )
            
            logger.info(f"Batch created successfully: {batch_id}")
            
            return {
                "batch_id": batch_id,
                "dataset_id": dataset_id,
                "status": "initialized"
            }
            
        except Exception as e:
            logger.error(f"Batch creation failed: {e}")
            raise StepExecutionError(f"Failed to create batch: {e}", step.step_id)
    
    async def _upload_file(
        self,
        step: ExecutionStep,
        previous_results: Dict[str, StepResult],
        dry_run: bool
    ) -> Dict[str, Any]:
        """Upload file data to batch."""
        
        # Get batch ID
        batch_step = None
        for dep_id in step.dependencies:
            if dep_id in previous_results:
                result = previous_results[dep_id]
                if "batch_id" in result.output:
                    batch_step = result
                    break
        
        if not batch_step:
            raise StepExecutionError("Batch creation step not found", step.step_id)
        
        batch_id = batch_step.output["batch_id"]
        dataset_id = batch_step.output["dataset_id"]
        file_path = Path(step.parameters["file"])
        
        if dry_run:
            return {
                "batch_id": batch_id,
                "bytes_uploaded": 1024000,
                "status": "uploaded (dry-run)"
            }
        
        # Upload file using Bulk Ingest API
        try:
            from adobe_experience.aep.client import AEPClient
            from adobe_experience.ingestion.bulk_upload import BulkIngestClient
            
            async with AEPClient(self.config) as aep_client:
                bulk = BulkIngestClient(aep_client)
                result = await bulk.upload_file(
                    batch_id=batch_id,
                    dataset_id=dataset_id,
                    file_path=str(file_path)
                )
            
            logger.info(f"File uploaded successfully: {result['size_bytes']} bytes")
            
            return {
                "batch_id": batch_id,
                "file_path": str(file_path),
                "bytes_uploaded": result["size_bytes"],
                "file_name": result["file_name"],
                "status": "uploaded"
            }
            
        except Exception as e:
            logger.error(f"File upload failed: {e}")
            raise StepExecutionError(f"Failed to upload file: {e}", step.step_id)
    
    async def _complete_batch(
        self,
        step: ExecutionStep,
        previous_results: Dict[str, StepResult],
        dry_run: bool
    ) -> Dict[str, Any]:
        """Complete batch ingestion."""
        
        # Get batch ID
        batch_id = None
        for dep_id in step.dependencies:
            if dep_id in previous_results:
                result = previous_results[dep_id]
                if "batch_id" in result.output:
                    batch_id = result.output["batch_id"]
                    break
        
        if not batch_id:
            raise StepExecutionError("Batch ID not found", step.step_id)
        
        if dry_run:
            return {
                "batch_id": batch_id,
                "status": "completed (dry-run)"
            }
        
        # Complete batch using Catalog Service API
        try:
            from adobe_experience.aep.client import AEPClient
            from adobe_experience.catalog.client import CatalogServiceClient
            
            async with AEPClient(self.config) as aep_client:
                catalog = CatalogServiceClient(aep_client)
                await catalog.complete_batch(batch_id)
            
            logger.info(f"Batch completed successfully: {batch_id}")
            
            return {
                "batch_id": batch_id,
                "status": "completed"
            }
            
        except Exception as e:
            logger.error(f"Batch completion failed: {e}")
            raise StepExecutionError(f"Failed to complete batch: {e}", step.step_id)
    
    async def _validate_ingestion(
        self,
        step: ExecutionStep,
        previous_results: Dict[str, StepResult],
        dry_run: bool
    ) -> Dict[str, Any]:
        """Validate batch ingestion was successful."""
        
        # Get batch ID
        batch_id = None
        for dep_id in step.dependencies:
            if dep_id in previous_results:
                result = previous_results[dep_id]
                if "batch_id" in result.output:
                    batch_id = result.output["batch_id"]
                    break
        
        if not batch_id:
            raise StepExecutionError("Batch ID not found", step.step_id)
        
        expected_records = step.parameters.get("expected_records", 0)
        
        if dry_run:
            return {
                "batch_id": batch_id,
                "records_ingested": expected_records,
                "status": "validated (dry-run)"
            }
        
        # Wait for batch completion and validate
        try:
            from adobe_experience.aep.client import AEPClient
            from adobe_experience.catalog.client import CatalogServiceClient
            
            timeout = step.parameters.get("timeout", 300)
            poll_interval = step.parameters.get("poll_interval", 5)
            
            async with AEPClient(self.config) as aep_client:
                catalog = CatalogServiceClient(aep_client)
                batch = await catalog.wait_for_batch_completion(
                    batch_id=batch_id,
                    timeout=timeout,
                    poll_interval=poll_interval
                )
            
            if batch.status == "success":
                records_ingested = batch.metrics.get("recordsIngested", 0) if batch.metrics else 0
                records_failed = batch.metrics.get("recordsFailed", 0) if batch.metrics else 0
                logger.info(f"Batch ingestion successful: {records_ingested} records")
                
                return {
                    "batch_id": batch_id,
                    "records_ingested": records_ingested,
                    "records_failed": records_failed,
                    "status": "validated",
                    "batch_status": batch.status
                }
            else:
                error_msg = f"Batch ingestion failed with status: {batch.status}"
                if batch.errors:
                    error_msg += f" - Errors: {batch.errors}"
                raise IngestionError(error_msg)
                
        except asyncio.TimeoutError:
            raise StepExecutionError(f"Batch validation timed out after {timeout}s", step.step_id)
        except Exception as e:
            logger.error(f"Ingestion validation failed: {e}")
            raise StepExecutionError(f"Failed to validate ingestion: {e}", step.step_id)
