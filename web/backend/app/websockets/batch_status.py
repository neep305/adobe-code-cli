"""WebSocket endpoint for batch status updates."""

import logging
from typing import Optional

from fastapi import Depends, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.database import get_db
from app.db.models import Batch, User
from app.websockets.manager import connection_manager

logger = logging.getLogger(__name__)


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
        token: Optional JWT token for authentication
    """
    subscription_key = f"batch:{batch_id}"
    
    # TODO: Implement proper authentication with token
    # For now, accept all connections
    
    await connection_manager.connect(websocket, subscription_key)
    
    try:
        # Send initial status
        # Note: This would normally query the database, but for now send a simple message
        await connection_manager.send_personal_message(
            {
                "event": "connected",
                "batch_id": batch_id,
                "message": f"Connected to batch {batch_id} status updates"
            },
            websocket
        )
        
        # Keep connection alive and listen for client messages
        while True:
            # Wait for client messages (e.g., pong responses, requests)
            data = await websocket.receive_json()
            
            # Handle pong responses
            if data.get("event") == "pong":
                logger.debug(f"Received pong from batch:{batch_id}")
                continue
            
            # Handle other client requests
            logger.debug(f"Received message from batch:{batch_id}: {data}")
            
    except WebSocketDisconnect:
        logger.info(f"Client disconnected from batch:{batch_id}")
    except Exception as e:
        logger.error(f"WebSocket error for batch:{batch_id}: {e}")
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
    
    # Calculate progress
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
