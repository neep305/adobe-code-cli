"""WebSocket connection manager."""

import asyncio
import json
import logging
from collections import defaultdict
from typing import Dict, List, Set

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manage WebSocket connections and broadcasting."""
    
    def __init__(self):
        """Initialize connection manager."""
        # Store active connections by subscription key
        self.active_connections: Dict[str, Set[WebSocket]] = defaultdict(set)
        # Store heartbeat tasks by websocket id
        self.heartbeat_tasks: Dict[int, asyncio.Task] = {}
    
    async def connect(self, websocket: WebSocket, subscription_key: str) -> None:
        """Accept and register a WebSocket connection.
        
        Args:
            websocket: WebSocket connection
            subscription_key: Key for grouping connections (e.g., "batch:abc123")
        """
        await websocket.accept()
        self.active_connections[subscription_key].add(websocket)
        
        # Start heartbeat task
        task = asyncio.create_task(self._heartbeat(websocket))
        self.heartbeat_tasks[id(websocket)] = task
        
        logger.info(f"WebSocket connected to {subscription_key}. Total: {len(self.active_connections[subscription_key])}")
    
    def disconnect(self, websocket: WebSocket, subscription_key: str) -> None:
        """Remove a WebSocket connection.
        
        Args:
            websocket: WebSocket connection
            subscription_key: Subscription key
        """
        self.active_connections[subscription_key].discard(websocket)
        
        # Cancel heartbeat task
        task = self.heartbeat_tasks.pop(id(websocket), None)
        if task:
            task.cancel()
        
        # Clean up empty subscription keys
        if not self.active_connections[subscription_key]:
            del self.active_connections[subscription_key]
        
        logger.info(f"WebSocket disconnected from {subscription_key}. Remaining: {len(self.active_connections.get(subscription_key, set()))}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket) -> None:
        """Send a message to a specific WebSocket.
        
        Args:
            message: Message data to send
            websocket: Target WebSocket
        """
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
    
    async def broadcast(self, message: dict, subscription_key: str) -> None:
        """Broadcast a message to all connections in a subscription.
        
        Args:
            message: Message data to broadcast
            subscription_key: Subscription key
        """
        if subscription_key not in self.active_connections:
            logger.debug(f"No active connections for {subscription_key}")
            return
        
        connections = list(self.active_connections[subscription_key])
        logger.debug(f"Broadcasting to {len(connections)} connections for {subscription_key}")
        
        # Send to all connections concurrently
        tasks = [
            self._safe_send(websocket, message)
            for websocket in connections
        ]
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def broadcast_all(self, message: dict) -> None:
        """Broadcast a message to all active connections.
        
        Args:
            message: Message data to broadcast
        """
        all_connections = []
        for connections in self.active_connections.values():
            all_connections.extend(connections)
        
        logger.debug(f"Broadcasting to {len(all_connections)} total connections")
        
        tasks = [
            self._safe_send(websocket, message)
            for websocket in all_connections
        ]
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _safe_send(self, websocket: WebSocket, message: dict) -> None:
        """Safely send a message to a WebSocket.
        
        Args:
            websocket: Target WebSocket
            message: Message data
        """
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            # Note: Don't disconnect here as it might be handled elsewhere
    
    async def _heartbeat(self, websocket: WebSocket, interval: int = 30) -> None:
        """Send periodic ping messages to keep connection alive.
        
        Args:
            websocket: WebSocket connection
            interval: Ping interval in seconds
        """
        try:
            while True:
                await asyncio.sleep(interval)
                try:
                    await websocket.send_json({"event": "ping", "timestamp": asyncio.get_event_loop().time()})
                except Exception:
                    # Connection closed
                    break
        except asyncio.CancelledError:
            # Task cancelled, normal shutdown
            pass
    
    def get_connection_count(self, subscription_key: str) -> int:
        """Get number of active connections for a subscription.
        
        Args:
            subscription_key: Subscription key
            
        Returns:
            Number of active connections
        """
        return len(self.active_connections.get(subscription_key, set()))
    
    def get_total_connections(self) -> int:
        """Get total number of active connections.
        
        Returns:
            Total connection count
        """
        return sum(len(connections) for connections in self.active_connections.values())
    
    def get_subscription_keys(self) -> List[str]:
        """Get all active subscription keys.
        
        Returns:
            List of subscription keys
        """
        return list(self.active_connections.keys())


# Global connection manager instance
connection_manager = ConnectionManager()
