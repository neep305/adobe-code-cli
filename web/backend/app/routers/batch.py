"""Batch management API router."""

import sys
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Add project root to path for importing CLI modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "src"))

from adobe_experience.aep.client import AEPClient
from adobe_experience.catalog.client import CatalogServiceClient
from adobe_experience.core.config import AEPConfig

from app.auth.dependencies import get_current_user
from app.db.database import get_db
from app.db.models import Batch, Dataset, User
from app.schemas.batch import (
    BatchCompleteRequest,
    BatchCreateRequest,
    BatchCreateResponse,
    BatchStatusResponse,
    FileUploadResponse,
)

router = APIRouter()


async def get_aep_client(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> AEPClient:
    """Get AEP client using user's saved credentials, falling back to environment variables."""
    from base64 import b64decode

    from sqlalchemy import select as sa_select

    from app.db.models import AEPConfig as AEPConfigModel

    # Try to load user's saved AEP config from DB first
    result = await db.execute(
        sa_select(AEPConfigModel).where(
            AEPConfigModel.user_id == current_user.id,
            AEPConfigModel.is_default == True,  # noqa: E712
        )
    )
    db_config = result.scalar_one_or_none()

    if db_config:
        try:
            client_secret = b64decode(db_config.encrypted_client_secret.encode()).decode()
        except Exception:
            client_secret = db_config.encrypted_client_secret

        config = AEPConfig(
            client_id=db_config.client_id,
            client_secret=client_secret,
            org_id=db_config.org_id,
            technical_account_id=db_config.technical_account_id,
            sandbox_name=db_config.sandbox_name,
            tenant_id=db_config.tenant_id or "",
        )
        return AEPClient(config)

    # Fallback to environment variables
    from app.config import get_settings
    settings = get_settings()

    if not settings.aep_client_id or not settings.aep_client_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Adobe Experience Platform credentials not configured. "
                   "Save your AEP credentials via PUT /api/settings/aep",
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


@router.post("/datasets/{dataset_id}/batches", response_model=BatchCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_batch(
    dataset_id: int,
    request: BatchCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    aep_client: AEPClient = Depends(get_aep_client)
) -> BatchCreateResponse:
    """Create a new batch for data ingestion.
    
    Args:
        dataset_id: Database dataset ID
        request: Batch creation request
        current_user: Current authenticated user
        db: Database session
        aep_client: AEP API client
        
    Returns:
        Created batch information
    """
    # Get dataset from database
    result = await db.execute(
        select(Dataset).where(
            Dataset.id == dataset_id,
            Dataset.user_id == current_user.id
        )
    )
    dataset = result.scalar_one_or_none()
    
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset {dataset_id} not found"
        )
    
    # Create batch in Adobe AEP
    async with aep_client:
        catalog = CatalogServiceClient(aep_client)
        aep_batch = await catalog.create_batch(
            dataset_id=dataset.aep_dataset_id,
            format=request.format
        )
    
    # Save batch to database
    batch = Batch(
        user_id=current_user.id,
        dataset_id=dataset_id,
        aep_batch_id=aep_batch.id,
        status="loading",
        files_count=0,
        files_uploaded=0,
    )
    
    db.add(batch)
    await db.commit()
    await db.refresh(batch)
    
    return BatchCreateResponse(
        id=batch.id,
        aep_batch_id=batch.aep_batch_id,
        dataset_id=batch.dataset_id,
        status=batch.status,
        created_at=batch.created_at,
    )


@router.get("/batches", response_model=List[BatchStatusResponse])
async def list_batches(
    limit: int = 20,
    offset: int = 0,
    status: Optional[str] = None,
    dataset_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> List[BatchStatusResponse]:
    """List all batches for the current user.
    
    Args:
        limit: Maximum number of batches to return (default: 20, max: 100)
        offset: Number of batches to skip for pagination (default: 0)
        status: Filter by batch status (loading, staged, processing, success, failed, aborted)
        dataset_id: Filter by dataset ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        List of batch status with metrics
    """
    # Limit max results
    limit = min(limit, 100)
    
    # Build query with JOIN to get dataset names
    query = (
        select(Batch, Dataset)
        .join(Dataset, Batch.dataset_id == Dataset.id)
        .where(Batch.user_id == current_user.id)
    )
    
    # Apply filters
    if status:
        query = query.where(Batch.status == status)
    if dataset_id:
        query = query.where(Batch.dataset_id == dataset_id)
    
    # Order by creation time (newest first) and apply pagination
    query = query.order_by(Batch.created_at.desc()).limit(limit).offset(offset)
    
    # Execute query
    result = await db.execute(query)
    rows = result.all()
    
    # Build response list
    batches = []
    for batch, dataset in rows:
        # Calculate progress
        progress_percent = 0.0
        if batch.files_count > 0:
            progress_percent = (batch.files_uploaded / batch.files_count) * 100
        elif batch.status == "success":
            progress_percent = 100.0
        
        # Calculate duration
        duration_seconds = None
        if batch.completed_at:
            duration = batch.completed_at - batch.created_at
            duration_seconds = duration.total_seconds()
        
        batches.append(BatchStatusResponse(
            id=batch.id,
            aep_batch_id=batch.aep_batch_id,
            dataset_id=batch.dataset_id,
            dataset_name=dataset.name,
            status=batch.status,
            files_count=batch.files_count,
            files_uploaded=batch.files_uploaded,
            progress_percent=progress_percent,
            records_processed=batch.records_processed,
            records_failed=batch.records_failed,
            error_message=batch.error_message,
            errors=[],  # No detailed errors for list view (performance optimization)
            created_at=batch.created_at,
            updated_at=batch.updated_at,
            completed_at=batch.completed_at,
            duration_seconds=duration_seconds,
        ))
    
    return batches


@router.get("/batches/{batch_id}", response_model=BatchStatusResponse)
async def get_batch_status(
    batch_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    aep_client: AEPClient = Depends(get_aep_client)
) -> BatchStatusResponse:
    """Get batch status and metrics.
    
    Args:
        batch_id: Database batch ID
        current_user: Current authenticated user
        db: Database session
        aep_client: AEP API client
        
    Returns:
        Batch status with metrics
    """
    # Get batch from database with dataset info
    result = await db.execute(
        select(Batch, Dataset).join(Dataset).where(
            Batch.id == batch_id,
            Batch.user_id == current_user.id
        )
    )
    row = result.one_or_none()
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch {batch_id} not found"
        )
    
    batch, dataset = row
    
    # Get latest status from Adobe AEP
    async with aep_client:
        catalog = CatalogServiceClient(aep_client)
        aep_batch = await catalog.get_batch(batch.aep_batch_id)
        
        # Update database with latest info
        batch.status = aep_batch.status.value
        if aep_batch.metrics:
            batch.records_processed = aep_batch.metrics.records_written
            batch.records_failed = aep_batch.metrics.records_failed
        if aep_batch.status.value in ["success", "failed", "aborted"]:
            batch.completed_at = batch.updated_at
        
        await db.commit()
        await db.refresh(batch)
    
    # Calculate progress
    progress_percent = 0.0
    if batch.files_count > 0:
        progress_percent = (batch.files_uploaded / batch.files_count) * 100
    elif batch.status == "success":
        progress_percent = 100.0
    
    # Calculate duration
    duration_seconds = None
    if batch.completed_at:
        duration = batch.completed_at - batch.created_at
        duration_seconds = duration.total_seconds()
    
    # Convert errors
    errors = []
    if aep_batch.errors:
        errors = [
            {"code": err.code, "message": err.description, "rows": err.rows}
            for err in aep_batch.errors
        ]
    
    return BatchStatusResponse(
        id=batch.id,
        aep_batch_id=batch.aep_batch_id,
        dataset_id=batch.dataset_id,
        dataset_name=dataset.name,
        status=batch.status,
        files_count=batch.files_count,
        files_uploaded=batch.files_uploaded,
        progress_percent=progress_percent,
        records_processed=batch.records_processed,
        records_failed=batch.records_failed,
        error_message=batch.error_message,
        errors=errors,
        created_at=batch.created_at,
        updated_at=batch.updated_at,
        completed_at=batch.completed_at,
        duration_seconds=duration_seconds,
    )


@router.post("/batches/{batch_id}/complete")
async def complete_batch(
    batch_id: int,
    request: BatchCompleteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    aep_client: AEPClient = Depends(get_aep_client)
) -> dict:
    """Complete or abort a batch.
    
    Args:
        batch_id: Database batch ID
        request: Complete request with action (COMPLETE or ABORT)
        current_user: Current authenticated user
        db: Database session
        aep_client: AEP API client
        
    Returns:
        Success message
    """
    # Get batch from database
    result = await db.execute(
        select(Batch).where(
            Batch.id == batch_id,
            Batch.user_id == current_user.id
        )
    )
    batch = result.scalar_one_or_none()
    
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch {batch_id} not found"
        )
    
    # Complete batch in Adobe AEP
    async with aep_client:
        catalog = CatalogServiceClient(aep_client)
        await catalog.complete_batch(batch.aep_batch_id)
        
        # Update database
        batch.status = "processing" if request.action == "COMPLETE" else "aborted"
        await db.commit()
    
    return {
        "message": f"Batch {request.action.lower()}d successfully",
        "batch_id": batch.aep_batch_id,
        "status": batch.status
    }


@router.post("/batches/{batch_id}/files", response_model=FileUploadResponse)
async def upload_file(
    batch_id: int,
    file: UploadFile = File(...),
    upload_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    aep_client: AEPClient = Depends(get_aep_client)
) -> FileUploadResponse:
    """Upload a file to a batch.
    
    Args:
        batch_id: Database batch ID
        file: File to upload
        current_user: Current authenticated user
        db: Database session
        aep_client: AEP API client
        
    Returns:
        Upload result
    """
    # Get batch and dataset from database
    result = await db.execute(
        select(Batch, Dataset).join(Dataset).where(
            Batch.id == batch_id,
            Batch.user_id == current_user.id
        )
    )
    row = result.one_or_none()
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch {batch_id} not found"
        )
    
    batch, dataset = row
    
    if batch.status not in ["loading", "staged"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot upload to batch in status: {batch.status}"
        )
    
    from app.websockets.upload_progress import upload_progress_manager

    effective_upload_id = upload_id or f"{batch.aep_batch_id}:{file.filename}"

    try:
        # Read file content
        file_content = await file.read()
        file_size = len(file_content)

        # Notify: upload started
        await upload_progress_manager.update(effective_upload_id, {
            "event": "progress",
            "upload_id": effective_upload_id,
            "batch_id": batch_id,
            "file_name": file.filename,
            "bytes_total": file_size,
            "bytes_sent": 0,
            "status": "uploading",
        })

        # Upload to Adobe AEP
        async with aep_client:
            catalog = CatalogServiceClient(aep_client)
            await catalog.upload_file_to_batch(
                batch_id=batch.aep_batch_id,
                dataset_id=dataset.aep_dataset_id,
                file_name=file.filename or "data.parquet",
                file_content=file_content
            )

        # Update database
        batch.files_uploaded += 1
        if batch.files_count == 0:
            batch.files_count = 1
        await db.commit()

        # Notify: upload complete
        await upload_progress_manager.update(effective_upload_id, {
            "event": "progress",
            "upload_id": effective_upload_id,
            "batch_id": batch_id,
            "file_name": file.filename,
            "bytes_total": file_size,
            "bytes_sent": file_size,
            "status": "done",
        })
        upload_progress_manager.finish(effective_upload_id)

        return FileUploadResponse(
            file_name=file.filename or "data.parquet",
            file_size=file_size,
            upload_id=effective_upload_id,
            status="completed",
            message="File uploaded successfully"
        )

    except Exception as e:
        # Notify: upload failed
        await upload_progress_manager.update(effective_upload_id, {
            "event": "progress",
            "upload_id": effective_upload_id,
            "batch_id": batch_id,
            "file_name": file.filename,
            "status": "error",
            "error": str(e),
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )
