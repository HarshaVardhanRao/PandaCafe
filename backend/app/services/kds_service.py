"""
Kitchen Display Service (KDS) - WebSocket connection manager and broadcaster.

Provides a simple in-memory connection manager and async broadcast helper
that other services can call (via asyncio.create_task) to push order
updates to connected KDS clients.
"""
import asyncio
from typing import Any, Dict, Set

from fastapi import WebSocket
from sqlalchemy.orm import Session
from app.models import Order


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

    @classmethod
    def format_kds_order(cls, db: Session, order: Order) -> Dict[str, Any]:
        """Format an order with full details for KDS display."""
        # Get table info
        table_number = None
        if order.table_id:
            from app.models import Table
            table = db.query(Table).filter(Table.id == order.table_id).first()
            if table:
                table_number = table.table_number

        # Get items
        from app.models import OrderItem, Product
        items = db.query(OrderItem).filter(
            OrderItem.order_id == order.id,
            OrderItem.is_cancelled == False
        ).all()

        formatted_items = []
        for item in items:
            product = db.query(Product).filter(Product.id == item.product_id).first()
            formatted_items.append({
                "id": str(item.id),
                "product_name": product.name if product else "Unknown Item",
                "quantity": item.quantity,
                "special_notes": item.special_notes or ""
            })

        return {
            "id": str(order.id),
            "order_number": order.order_number,
            "order_type": order.order_type,
            "table_number": table_number,
            "status": order.status,
            "notes": order.notes or "",
            "created_at": order.created_at.isoformat() if order.created_at else None,
            "items": formatted_items
        }
