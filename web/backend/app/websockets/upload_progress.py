"""WebSocket endpoint for file upload progress tracking."""

import asyncio
import logging
import uuid
from typing import Dict, Optional

from fastapi import WebSocket, WebSocketDisconnect

from app.auth.security import verify_token
from app.db.database import AsyncSessionLocal
from app.db.models import User
from sqlalchemy import select

logger = logging.getLogger(__name__)


class UploadProgressManager:
    """Track and broadcast upload progress to connected WebSocket clients."""

    def __init__(self):
        # upload_id -> set of WebSocket connections
        self._connections: Dict[str, set] = {}
        # upload_id -> latest progress dict
        self._progress: Dict[str, dict] = {}

    async def connect(self, websocket: WebSocket, upload_id: str) -> None:
        await websocket.accept()
        self._connections.setdefault(upload_id, set()).add(websocket)
        logger.info(f"Upload progress client connected for upload:{upload_id}")

        # Send current state if available
        if upload_id in self._progress:
            await self._safe_send(websocket, self._progress[upload_id])

    def disconnect(self, websocket: WebSocket, upload_id: str) -> None:
        self._connections.get(upload_id, set()).discard(websocket)
        if not self._connections.get(upload_id):
            self._connections.pop(upload_id, None)
        logger.info(f"Upload progress client disconnected from upload:{upload_id}")

    async def update(self, upload_id: str, progress: dict) -> None:
        """Store the latest progress and broadcast to all listeners."""
        self._progress[upload_id] = progress
        connections = list(self._connections.get(upload_id, set()))
        if connections:
            await asyncio.gather(
                *[self._safe_send(ws, progress) for ws in connections],
                return_exceptions=True,
            )

    def finish(self, upload_id: str) -> None:
        """Clean up state for a completed upload."""
        self._progress.pop(upload_id, None)

    async def _safe_send(self, websocket: WebSocket, message: dict) -> None:
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.debug(f"Upload progress send error: {e}")


# Singleton
upload_progress_manager = UploadProgressManager()


async def _authenticate_token(token: Optional[str]) -> Optional[User]:
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
    upload_id: str,
    token: Optional[str] = None,
) -> None:
    """WebSocket endpoint that streams upload progress to the client.

    The client connects here to receive real-time progress updates while
    a file is being uploaded via the REST API.  Progress is pushed by the
    upload router via ``upload_progress_manager.update()``.

    Args:
        websocket: Incoming WebSocket connection.
        upload_id: Unique identifier for the upload session.
        token: JWT bearer token for authentication.
    """
    user = await _authenticate_token(token)
    if not user:
        await websocket.close(code=4001, reason="Unauthorized: invalid or missing token")
        logger.warning(f"Rejected unauthenticated upload-progress WS for upload:{upload_id}")
        return

    await upload_progress_manager.connect(websocket, upload_id)

    try:
        while True:
            # Keep connection alive; client may send pings
            data = await websocket.receive_json()
            if data.get("event") == "ping":
                await websocket.send_json({"event": "pong"})
    except WebSocketDisconnect:
        logger.info(f"Upload progress WS disconnected: upload:{upload_id}")
    except Exception as e:
        logger.error(f"Upload progress WS error for upload:{upload_id}: {e}")
    finally:
        upload_progress_manager.disconnect(websocket, upload_id)


def generate_upload_id() -> str:
    """Generate a unique upload session ID."""
    return str(uuid.uuid4())
