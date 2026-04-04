"""WebSocket endpoint for Schema Wizard real-time agent progress."""

import logging
from typing import Optional

from fastapi import WebSocket, WebSocketDisconnect

from app.websockets.manager import connection_manager

logger = logging.getLogger(__name__)


async def websocket_endpoint(websocket: WebSocket, session_id: str) -> None:
    """WebSocket endpoint for schema wizard agent progress updates.

    Clients connect here after creating a wizard session to receive
    real-time events: analyzing_start, checklist_update, agent_result, step_complete.

    Args:
        websocket: WebSocket connection
        session_id: Wizard session ID (from POST /api/schema-wizard/sessions)
    """
    subscription_key = f"wizard:{session_id}"
    await connection_manager.connect(websocket, subscription_key)
    logger.info(f"Client connected to wizard:{session_id}")

    try:
        await connection_manager.send_personal_message(
            {
                "event": "connected",
                "session_id": session_id,
                "message": f"Connected to schema wizard session {session_id}",
            },
            websocket,
        )

        while True:
            data = await websocket.receive_json()
            if data.get("event") == "pong":
                continue
            logger.debug(f"wizard:{session_id} received: {data}")

    except WebSocketDisconnect:
        logger.info(f"Client disconnected from wizard:{session_id}")
    except Exception as exc:
        logger.error(f"WebSocket error wizard:{session_id}: {exc}")
    finally:
        connection_manager.disconnect(websocket, subscription_key)


async def broadcast_wizard_event(session_id: str, event: dict) -> None:
    """Broadcast an event to all clients watching this wizard session.

    Called by SchemaWizardOrchestrator during agent analysis.

    Args:
        session_id: Wizard session ID
        event: Event dict (must include "event" key)
    """
    subscription_key = f"wizard:{session_id}"
    await connection_manager.broadcast(event, subscription_key)
