"""
Kitchen Display Service (KDS) - WebSocket connection manager and broadcaster.

Provides a simple in-memory connection manager and async broadcast helper
that other services can call (via asyncio.create_task) to push order
updates to connected KDS clients.
"""
import asyncio
from typing import Any, Dict, Set

from fastapi import WebSocket


class KDSService:
    """Simple KDS WebSocket manager."""

    _connections: Set[WebSocket] = set()
    _lock = asyncio.Lock()

    @classmethod
    async def connect(cls, websocket: WebSocket) -> None:
        await websocket.accept()
        async with cls._lock:
            cls._connections.add(websocket)

    @classmethod
    async def disconnect(cls, websocket: WebSocket) -> None:
        async with cls._lock:
            if websocket in cls._connections:
                cls._connections.remove(websocket)

    @classmethod
    async def broadcast_order_update(cls, data: Dict[str, Any]) -> None:
        """Broadcast an order update dictionary to all connected clients."""
        async with cls._lock:
            conns = list(cls._connections)

        if not conns:
            return

        # Send concurrently
        await asyncio.gather(*[conn.send_json({"type": "order_update", "data": data}) for conn in conns], return_exceptions=True)
