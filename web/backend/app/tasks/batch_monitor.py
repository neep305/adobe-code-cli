"""Background task for monitoring active batch statuses via AEP API polling."""

import asyncio
import logging
from base64 import b64decode
from datetime import datetime

from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.db.models import AEPConfig as AEPConfigModel, Batch, Dataset, User
from app.websockets.batch_status import broadcast_batch_update

logger = logging.getLogger(__name__)

# Statuses that require active polling
ACTIVE_STATUSES = {"loading", "processing", "queued", "staged"}
# Polling interval in seconds
POLL_INTERVAL = 30


async def _get_aep_client_for_user(user_id: int):
    """Build an AEP client for the given user from their stored credentials."""
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "src"))

    from adobe_experience.aep.client import AEPClient
    from adobe_experience.core.config import AEPConfig

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(AEPConfigModel).where(
                AEPConfigModel.user_id == user_id,
                AEPConfigModel.is_default == True,  # noqa: E712
            )
        )
        db_config = result.scalar_one_or_none()

    if not db_config:
        return None

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


async def _poll_once() -> None:
    """Single poll cycle: fetch active batches from DB and refresh their status from AEP."""
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Batch).where(Batch.status.in_(ACTIVE_STATUSES))
            )
            active_batches = result.scalars().all()

        if not active_batches:
            return

        logger.debug(f"Polling {len(active_batches)} active batch(es)")

        # Group by user to reuse AEP clients
        batches_by_user: dict[int, list[Batch]] = {}
        for batch in active_batches:
            batches_by_user.setdefault(batch.user_id, []).append(batch)

        for user_id, batches in batches_by_user.items():
            try:
                aep_client = await _get_aep_client_for_user(user_id)
                if not aep_client:
                    continue

                from adobe_experience.catalog.client import CatalogServiceClient

                async with aep_client:
                    catalog = CatalogServiceClient(aep_client)

                    for batch in batches:
                        try:
                            aep_batch = await catalog.get_batch(batch.aep_batch_id)
                            new_status = aep_batch.status.lower() if aep_batch.status else batch.status

                            updated = False
                            async with AsyncSessionLocal() as db:
                                result = await db.execute(
                                    select(Batch).where(Batch.id == batch.id)
                                )
                                db_batch = result.scalar_one_or_none()
                                if db_batch and db_batch.status != new_status:
                                    db_batch.status = new_status
                                    if hasattr(aep_batch, "records_loaded") and aep_batch.records_loaded:
                                        db_batch.records_processed = aep_batch.records_loaded
                                    if hasattr(aep_batch, "failed_records_count") and aep_batch.failed_records_count:
                                        db_batch.records_failed = aep_batch.failed_records_count
                                    if new_status in ("success", "failed"):
                                        db_batch.completed_at = datetime.utcnow()
                                    await db.commit()
                                    updated = True

                                    # Broadcast the update via WebSocket
                                    await broadcast_batch_update(
                                        batch_id=batch.id,
                                        status=new_status,
                                        files_uploaded=db_batch.files_uploaded,
                                        files_count=db_batch.files_count,
                                        records_processed=db_batch.records_processed,
                                        records_failed=db_batch.records_failed,
                                        error_message=db_batch.error_message,
                                    )

                            if updated:
                                logger.info(f"Batch {batch.id} status updated to {new_status}")

                        except Exception as e:
                            logger.warning(f"Failed to poll batch {batch.id}: {e}")

            except Exception as e:
                logger.warning(f"Failed to get AEP client for user {user_id}: {e}")

    except Exception as e:
        logger.error(f"Batch monitor poll error: {e}")


async def run_batch_monitor() -> None:
    """Continuously poll active batches until the application shuts down."""
    logger.info("Batch monitor background task started")
    while True:
        await _poll_once()
        await asyncio.sleep(POLL_INTERVAL)
