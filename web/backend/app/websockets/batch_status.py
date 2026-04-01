"""WebSocket endpoint for batch status updates."""

import logging
from typing import Optional

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.auth.security import verify_token
from app.db.database import AsyncSessionLocal
from app.db.models import User
from app.websockets.manager import connection_manager

logger = logging.getLogger(__name__)


async def _authenticate_token(token: Optional[str]) -> Optional[User]:
    """Validate a JWT token and return the corresponding user.

    Args:
        token: JWT bearer token string

    Returns:
        User object if valid, None otherwise
    """
    if not token:
        return None

    payload = verify_token(token)
    if not payload:
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.id == int(user_id)))
        user = result.scalar_one_or_none()
        if user and user.is_active:
            return user
    return None


async def websocket_endpoint(
    websocket: WebSocket,
    batch_id: int,
    token: Optional[str] = None,
) -> None:
    """WebSocket endpoint for real-time batch status updates.

    Clients connect to this endpoint to receive real-time updates
    about batch ingestion status, progress, and completion.

    Args:
        websocket: WebSocket connection
        batch_id: Database batch ID to monitor
        token: JWT token for authentication (passed as query parameter)
    """
    # Authenticate the connecting client
    user = await _authenticate_token(token)
    if not user:
        await websocket.close(code=4001, reason="Unauthorized: invalid or missing token")
        logger.warning(f"Rejected unauthenticated WebSocket connection for batch:{batch_id}")
        return

    subscription_key = f"batch:{batch_id}"
    await connection_manager.connect(websocket, subscription_key)
    logger.info(f"User {user.id} connected to batch:{batch_id} status updates")

    try:
        # Send initial connected confirmation
        await connection_manager.send_personal_message(
            {
                "event": "connected",
                "batch_id": batch_id,
                "user_id": user.id,
                "message": f"Connected to batch {batch_id} status updates",
            },
            websocket,
        )

        # Keep connection alive and listen for client messages
        while True:
            data = await websocket.receive_json()

            if data.get("event") == "pong":
                logger.debug(f"Received pong from user:{user.id} batch:{batch_id}")
                continue

            logger.debug(f"Received message from user:{user.id} batch:{batch_id}: {data}")

    except WebSocketDisconnect:
        logger.info(f"User {user.id} disconnected from batch:{batch_id}")
    except Exception as e:
        logger.error(f"WebSocket error for user:{user.id} batch:{batch_id}: {e}")
    finally:
        connection_manager.disconnect(websocket, subscription_key)


async def broadcast_batch_update(
    batch_id: int,
    status: str,
    files_uploaded: int,
    files_count: int,
    records_processed: Optional[int] = None,
    records_failed: Optional[int] = None,
    error_message: Optional[str] = None,
) -> None:
    """Broadcast batch status update to all connected clients.

    This function is called by background tasks when batch status changes.

    Args:
        batch_id: Database batch ID
        status: Current batch status
        files_uploaded: Number of files uploaded
        files_count: Total number of files
        records_processed: Number of records processed
        records_failed: Number of records failed
        error_message: Error message if failed
    """
    subscription_key = f"batch:{batch_id}"

    progress_percent = 0.0
    if files_count > 0:
        progress_percent = (files_uploaded / files_count) * 100
    elif status == "success":
        progress_percent = 100.0

    message = {
        "event": "status_update",
        "batch_id": batch_id,
        "status": status,
        "files_uploaded": files_uploaded,
        "files_count": files_count,
        "progress_percent": progress_percent,
        "records_processed": records_processed,
        "records_failed": records_failed,
        "error_message": error_message,
    }

    await connection_manager.broadcast(message, subscription_key)
    logger.info(f"Broadcasted status update for batch:{batch_id} - {status}")
