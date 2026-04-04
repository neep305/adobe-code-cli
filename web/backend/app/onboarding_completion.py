"""Per-step onboarding completion detection (modular detectors composed into one map)."""

from __future__ import annotations

import base64
import sys
from pathlib import Path
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AEPConfig, Batch, Dataset, Schema, User


async def detect_schema(user: User, db: AsyncSession) -> tuple[bool, Optional[str], Optional[str]]:
    result = await db.execute(
        select(Schema).where(Schema.user_id == user.id).order_by(Schema.created_at.desc()).limit(1)
    )
    schema = result.scalar_one_or_none()
    return (
        schema is not None,
        schema.aep_schema_id if schema else None,
        schema.title if schema else None,
    )


async def detect_source(_user: User, _db: AsyncSession) -> tuple[bool, Optional[str], Optional[str]]:
    """Source account is created in AEP UI — no auto-detect yet."""
    return (False, None, None)


async def detect_dataflow(
    config: Optional[AEPConfig],
) -> tuple[bool, Optional[str], Optional[str]]:
    if config is None:
        return (False, None, None)
    try:
        src_path = Path(__file__).resolve().parent.parent.parent.parent / "src"
        if str(src_path) not in sys.path:
            sys.path.insert(0, str(src_path))

        from adobe_experience.aep.client import AEPClient
        from adobe_experience.core.config import AEPConfig as CLIAEPConfig
        from adobe_experience.flow.client import FlowServiceClient

        cli_config = CLIAEPConfig(
            aep_client_id=config.client_id,
            aep_client_secret=base64.b64decode(config.encrypted_client_secret).decode(),
            aep_org_id=config.org_id,
            aep_technical_account_id=config.technical_account_id,
            aep_sandbox_name=config.sandbox_name,
            aep_tenant_id=config.tenant_id,
        )
        async with AEPClient(cli_config) as aep_client:
            flow_client = FlowServiceClient(aep_client)
            flows = await flow_client.list_flows(limit=1)
            if flows and flows.get("items"):
                first = flows["items"][0]
                return (True, first.get("id"), first.get("name"))
    except Exception:
        pass
    return (False, None, None)


async def detect_dataset(
    user: User,
    db: AsyncSession,
    dataflow_completed: bool,
    dataflow_id: Optional[str],
    dataflow_name: Optional[str],
) -> tuple[bool, Optional[str], Optional[str]]:
    result = await db.execute(
        select(Dataset).where(Dataset.user_id == user.id).order_by(Dataset.created_at.desc()).limit(1)
    )
    dataset = result.scalar_one_or_none()
    if dataset is not None:
        return (
            True,
            dataset.aep_dataset_id if dataset else None,
            dataset.name if dataset else None,
        )
    if dataflow_completed:
        return (
            True,
            dataflow_id,
            dataflow_name or "Target dataset (ingestion dataflow)",
        )
    return (False, None, None)


async def detect_ingest(user: User, db: AsyncSession) -> tuple[bool, Optional[str], Optional[str]]:
    result = await db.execute(
        select(Batch)
        .where(Batch.user_id == user.id, Batch.status == "success")
        .order_by(Batch.completed_at.desc())
        .limit(1)
    )
    batch = result.scalar_one_or_none()
    return (
        batch is not None,
        str(batch.id) if batch else None,
        f"Batch #{batch.id}" if batch else None,
    )


async def detect_profile_ready(_user: User, _db: AsyncSession) -> tuple[bool, Optional[str], Optional[str]]:
    """Merge policy / identity graph — manual or future Profile API."""
    return (False, None, None)


async def detect_segment(_user: User, _db: AsyncSession) -> tuple[bool, Optional[str], Optional[str]]:
    """Segment creation — manual until Segmentation API sync exists."""
    return (False, None, None)


async def detect_destination(_user: User, _db: AsyncSession) -> tuple[bool, Optional[str], Optional[str]]:
    """Destination activation — manual until Destination API sync exists."""
    return (False, None, None)


async def detect_all_step_completion(
    user: User,
    db: AsyncSession,
) -> dict[str, tuple[bool, Optional[str], Optional[str]]]:
    """Run all detectors and return a map step_key -> (completed, resource_id, resource_name)."""
    cfg_result = await db.execute(select(AEPConfig).where(AEPConfig.user_id == user.id).limit(1))
    config = cfg_result.scalar_one_or_none()
    auth_tuple: tuple[bool, Optional[str], Optional[str]] = (
        config is not None,
        str(config.id) if config else None,
        config.sandbox_name if config else None,
    )

    schema_t = await detect_schema(user, db)
    source_t = await detect_source(user, db)
    dataflow_t = await detect_dataflow(config)
    dataset_t = await detect_dataset(user, db, dataflow_t[0], dataflow_t[1], dataflow_t[2])
    ingest_t = await detect_ingest(user, db)
    profile_t = await detect_profile_ready(user, db)
    segment_t = await detect_segment(user, db)
    destination_t = await detect_destination(user, db)

    return {
        "auth": auth_tuple,
        "schema": schema_t,
        "source": source_t,
        "dataflow": dataflow_t,
        "dataset": dataset_t,
        "ingest": ingest_t,
        "profile_ready": profile_t,
        "segment": segment_t,
        "destination": destination_t,
    }
