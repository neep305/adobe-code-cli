"""Dataflow monitoring API router."""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

# Add project root to path for importing CLI modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "src"))

from adobe_experience.aep.client import AEPClient
from adobe_experience.flow.client import FlowServiceClient
from adobe_experience.core.config import AEPConfig

from app.auth.dependencies import get_current_user
from app.db.database import get_db
from app.db.models import User
from app.schemas.dataflow import (
    DataflowHealthError,
    DataflowHealthResponse,
    DataflowListResponse,
    DataflowResponse,
    DataflowRunError,
    DataflowRunMetrics,
    DataflowRunResponse,
)

router = APIRouter()


async def get_aep_client(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> AEPClient:
    """Get AEP client with user's credentials."""
    from app.config import get_settings
    settings = get_settings()
    
    if not settings.aep_client_id or not settings.aep_client_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Adobe Experience Platform credentials not configured"
        )
    
    config = AEPConfig(
        client_id=settings.aep_client_id,
        client_secret=settings.aep_client_secret.get_secret_value() if settings.aep_client_secret else None,
        org_id=settings.aep_org_id or "",
        technical_account_id=settings.aep_technical_account_id or "",
        sandbox_name=settings.aep_sandbox_name,
        tenant_id=settings.aep_tenant_id or "",
    )
    
    return AEPClient(config)


@router.get("", response_model=DataflowListResponse)
async def list_dataflows(
    limit: int = Query(default=50, ge=1, le=100),
    state: Optional[str] = Query(default=None, regex="^(enabled|disabled)$"),
    current_user: User = Depends(get_current_user),
    aep_client: AEPClient = Depends(get_aep_client)
) -> DataflowListResponse:
    """List dataflows with optional filtering.
    
    Args:
        limit: Maximum number of dataflows to return
        state: Filter by state (enabled/disabled)
        current_user: Current authenticated user
        aep_client: AEP API client
        
    Returns:
        List of dataflows
    """
    async with aep_client:
        flow_client = FlowServiceClient(aep_client)
        
        # Build filter
        property_filter = None
        if state:
            property_filter = f"state=={state}"
        
        dataflows = await flow_client.list_dataflows(
            limit=limit,
            property_filter=property_filter
        )
        
        # Convert to response schema
        dataflow_responses = [
            DataflowResponse(
                id=df.id,
                name=df.name,
                state=df.state,
                source_connection_ids=df.source_connection_ids,
                target_connection_ids=df.target_connection_ids,
                created_at=datetime.fromtimestamp(df.created_at / 1000) if df.created_at else datetime.now(),
                updated_at=datetime.fromtimestamp(df.updated_at / 1000) if df.updated_at else datetime.now(),
                description=df.description,
            )
            for df in dataflows
        ]
        
        return DataflowListResponse(
            dataflows=dataflow_responses,
            total=len(dataflow_responses)
        )


@router.get("/{flow_id}", response_model=DataflowResponse)
async def get_dataflow(
    flow_id: str,
    current_user: User = Depends(get_current_user),
    aep_client: AEPClient = Depends(get_aep_client)
) -> DataflowResponse:
    """Get dataflow details.
    
    Args:
        flow_id: Dataflow ID
        current_user: Current authenticated user
        aep_client: AEP API client
        
    Returns:
        Dataflow details
    """
    async with aep_client:
        flow_client = FlowServiceClient(aep_client)
        dataflow = await flow_client.get_dataflow(flow_id)
        
        return DataflowResponse(
            id=dataflow.id,
            name=dataflow.name,
            state=dataflow.state,
            source_connection_ids=dataflow.source_connection_ids,
            target_connection_ids=dataflow.target_connection_ids,
            created_at=datetime.fromtimestamp(dataflow.created_at / 1000) if dataflow.created_at else datetime.now(),
            updated_at=datetime.fromtimestamp(dataflow.updated_at / 1000) if dataflow.updated_at else datetime.now(),
            description=dataflow.description,
        )


@router.get("/{flow_id}/runs", response_model=List[DataflowRunResponse])
async def list_dataflow_runs(
    flow_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    days: Optional[int] = Query(default=None, ge=1, le=90, description="Filter runs from last N days"),
    current_user: User = Depends(get_current_user),
    aep_client: AEPClient = Depends(get_aep_client)
) -> List[DataflowRunResponse]:
    """List dataflow execution runs.
    
    Args:
        flow_id: Dataflow ID
        limit: Maximum number of runs to return
        days: Filter runs from last N days
        current_user: Current authenticated user
        aep_client: AEP API client
        
    Returns:
        List of dataflow runs
    """
    async with aep_client:
        flow_client = FlowServiceClient(aep_client)
        
        # Get runs with optional date filtering
        if days:
            start_date = datetime.now() - timedelta(days=days)
            runs = await flow_client.list_runs_by_date_range(
                flow_id=flow_id,
                start_date=start_date,
                limit=limit
            )
        else:
            runs = await flow_client.list_runs(flow_id=flow_id, limit=limit)
        
        # Convert to response schema
        run_responses = []
        for run in runs:
            metrics = None
            if run.metrics and run.metrics.record_summary:
                rs = run.metrics.record_summary
                duration_ms = None
                if run.metrics.duration_summary:
                    ds = run.metrics.duration_summary
                    if ds.started_at_utc and ds.completed_at_utc:
                        duration_ms = ds.completed_at_utc - ds.started_at_utc
                
                metrics = DataflowRunMetrics(
                    input_record_count=rs.input_record_count,
                    output_record_count=rs.output_record_count,
                    failed_record_count=rs.failed_record_count,
                    duration_ms=duration_ms
                )
            
            errors = []
            if run.status.errors:
                errors = [
                    DataflowRunError(code=err.code, message=err.message)
                    for err in run.status.errors
                ]
            
            run_responses.append(
                DataflowRunResponse(
                    id=run.id,
                    flow_id=flow_id,
                    status=run.status.value,
                    created_at=datetime.fromtimestamp(run.created_at / 1000) if run.created_at else datetime.now(),
                    updated_at=datetime.fromtimestamp(run.updated_at / 1000) if run.updated_at else datetime.now(),
                    metrics=metrics,
                    errors=errors
                )
            )
        
        return run_responses


@router.get("/{flow_id}/health", response_model=DataflowHealthResponse)
async def get_dataflow_health(
    flow_id: str,
    window_days: int = Query(default=7, ge=1, le=90, description="Analysis window in days"),
    current_user: User = Depends(get_current_user),
    aep_client: AEPClient = Depends(get_aep_client)
) -> DataflowHealthResponse:
    """Analyze dataflow health and performance.
    
    Args:
        flow_id: Dataflow ID
        window_days: Number of days to analyze
        current_user: Current authenticated user
        aep_client: AEP API client
        
    Returns:
        Health analysis with metrics and recommendations
    """
    async with aep_client:
        flow_client = FlowServiceClient(aep_client)
        
        # Get dataflow info
        dataflow = await flow_client.get_dataflow(flow_id)
        
        # Get health analysis
        health = await flow_client.analyze_dataflow_health(
            flow_id=flow_id,
            lookback_days=window_days
        )
        
        # Determine health status
        success_rate = health["success_rate"]
        if success_rate >= 95:
            health_status = "excellent"
        elif success_rate >= 80:
            health_status = "good"
        elif success_rate >= 50:
            health_status = "poor"
        else:
            health_status = "critical"
        
        # Aggregate errors
        error_map = {}
        for err in health["errors"]:
            key = f"{err['code']}:{err['message']}"
            if key not in error_map:
                error_map[key] = {
                    "code": err["code"],
                    "message": err["message"],
                    "run_ids": [err["run_id"]]
                }
            else:
                error_map[key]["run_ids"].append(err["run_id"])
        
        aggregated_errors = [
            DataflowHealthError(
                code=err["code"],
                message=err["message"],
                count=len(err["run_ids"]),
                run_ids=err["run_ids"]
            )
            for err in error_map.values()
        ]
        
        # Generate recommendations
        recommendations = []
        if success_rate < 80:
            recommendations.append(f"Success rate is below 80%. Review error logs for common issues.")
        if health["failed_runs"] > 0:
            recommendations.append(f"{health['failed_runs']} failed runs detected. Check source data quality.")
        if health["pending_runs"] > health["total_runs"] * 0.3:
            recommendations.append("High number of pending runs. Check dataflow schedule and source availability.")
        if health["average_duration_seconds"] > 3600:
            recommendations.append("Average run duration exceeds 1 hour. Consider optimizing data volume or transformation logic.")
        
        return DataflowHealthResponse(
            flow_id=flow_id,
            flow_name=dataflow.name,
            lookback_days=window_days,
            total_runs=health["total_runs"],
            success_runs=health["success_runs"],
            failed_runs=health["failed_runs"],
            pending_runs=health["pending_runs"],
            success_rate=success_rate,
            avg_duration_seconds=health["average_duration_seconds"],
            health_status=health_status,
            errors=aggregated_errors,
            recommendations=recommendations
        )
