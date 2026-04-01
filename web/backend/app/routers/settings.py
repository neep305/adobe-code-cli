"""User settings API router - AEP configuration management."""

import base64
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, SecretStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.database import get_db
from app.db.models import AEPConfig, User

router = APIRouter()


def _encrypt(value: str) -> str:
    """Simple base64 encoding for sensitive values.
    In production this should use a proper encryption library (e.g. cryptography.Fernet).
    """
    return base64.b64encode(value.encode()).decode()


def _decrypt(value: str) -> str:
    """Decode base64-encoded value."""
    try:
        return base64.b64decode(value.encode()).decode()
    except Exception:
        return value


class AEPConfigRequest(BaseModel):
    """Request schema for saving AEP credentials."""
    client_id: str = Field(..., min_length=1)
    client_secret: SecretStr = Field(..., min_length=1)
    org_id: str = Field(..., min_length=1)
    technical_account_id: str = Field(..., min_length=1)
    sandbox_name: str = Field(default="prod")
    tenant_id: Optional[str] = None
    is_default: bool = True


class AEPConfigResponse(BaseModel):
    """Response schema for AEP configuration (secrets masked)."""
    id: int
    client_id: str
    org_id: str
    technical_account_id: str
    sandbox_name: str
    tenant_id: Optional[str] = None
    is_default: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


@router.get("/aep", response_model=Optional[AEPConfigResponse])
async def get_aep_config(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Optional[AEPConfigResponse]:
    """Get the current user's default AEP configuration.

    Returns:
        AEP config with secrets masked, or null if not configured
    """
    result = await db.execute(
        select(AEPConfig).where(
            AEPConfig.user_id == current_user.id,
            AEPConfig.is_default == True,  # noqa: E712
        )
    )
    config = result.scalar_one_or_none()

    if not config:
        return None

    return AEPConfigResponse(
        id=config.id,
        client_id=config.client_id,
        org_id=config.org_id,
        technical_account_id=config.technical_account_id,
        sandbox_name=config.sandbox_name,
        tenant_id=config.tenant_id,
        is_default=config.is_default,
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


@router.put("/aep", response_model=AEPConfigResponse)
async def upsert_aep_config(
    request: AEPConfigRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AEPConfigResponse:
    """Create or update the current user's AEP configuration.

    Args:
        request: AEP credentials to save
        current_user: Current authenticated user
        db: Database session

    Returns:
        Saved AEP configuration (secrets masked)
    """
    # If is_default, clear existing default for this user
    if request.is_default:
        existing_defaults = await db.execute(
            select(AEPConfig).where(
                AEPConfig.user_id == current_user.id,
                AEPConfig.is_default == True,  # noqa: E712
            )
        )
        for existing in existing_defaults.scalars().all():
            existing.is_default = False

    # Check if a config already exists for this user (upsert by user)
    result = await db.execute(
        select(AEPConfig).where(AEPConfig.user_id == current_user.id)
        .order_by(AEPConfig.created_at.desc())
        .limit(1)
    )
    config = result.scalar_one_or_none()

    encrypted_secret = _encrypt(request.client_secret.get_secret_value())

    if config:
        config.client_id = request.client_id
        config.encrypted_client_secret = encrypted_secret
        config.org_id = request.org_id
        config.technical_account_id = request.technical_account_id
        config.sandbox_name = request.sandbox_name
        config.tenant_id = request.tenant_id
        config.is_default = request.is_default
    else:
        config = AEPConfig(
            user_id=current_user.id,
            client_id=request.client_id,
            encrypted_client_secret=encrypted_secret,
            org_id=request.org_id,
            technical_account_id=request.technical_account_id,
            sandbox_name=request.sandbox_name,
            tenant_id=request.tenant_id,
            is_default=request.is_default,
        )
        db.add(config)

    await db.commit()
    await db.refresh(config)

    return AEPConfigResponse(
        id=config.id,
        client_id=config.client_id,
        org_id=config.org_id,
        technical_account_id=config.technical_account_id,
        sandbox_name=config.sandbox_name,
        tenant_id=config.tenant_id,
        is_default=config.is_default,
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


@router.delete("/aep", status_code=status.HTTP_204_NO_CONTENT)
async def delete_aep_config(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete the current user's AEP configuration.

    Args:
        current_user: Current authenticated user
        db: Database session
    """
    result = await db.execute(
        select(AEPConfig).where(AEPConfig.user_id == current_user.id)
    )
    configs = result.scalars().all()

    if not configs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No AEP configuration found",
        )

    for config in configs:
        await db.delete(config)

    await db.commit()
