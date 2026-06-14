"""
WebSocket endpoint for Kitchen Display System (KDS).
Clients connect and receive real-time order updates pushed from backend services.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.services.kds_service import KDSService
from app.db.database import get_db
from app.core.security import verify_token

router = APIRouter(prefix="", tags=["kds"])


async def get_current_user_from_ws(token: str = None):
    # For KDS we optionally allow unauthenticated connections; implement token check if provided
    if not token:
        return None
    try:
        user_id = verify_token(token)
        return user_id
    except Exception:
        return None


@router.websocket("/ws/kds")
async def websocket_kds(websocket: WebSocket):
    """WebSocket endpoint for KDS clients."""
    await KDSService.connect(websocket)
    try:
        while True:
            # Keep connection alive, receive pings from client
            await websocket.receive_text()
    except WebSocketDisconnect:
        await KDSService.disconnect(websocket)
    except Exception:
        # Ensure we remove connection on any error
        await KDSService.disconnect(websocket)


class KDSStatusUpdateRequest(BaseModel):
    status: str = Field(..., description="New status (e.g. accepted, preparing, ready, served)")


@router.get("/kds/orders", response_model=list[dict])
def get_kds_orders(db: Session = Depends(get_db)):
    """Retrieve active kitchen orders."""
    from app.models import Order
    # Active statuses in kitchen are pending, accepted, preparing, ready
    active_statuses = ["pending", "accepted", "preparing", "ready"]
    orders = db.query(Order).filter(
        Order.status.in_(active_statuses),
        Order.cancelled_at.is_(None)
    ).order_by(Order.created_at.asc()).all()
    
    return [KDSService.format_kds_order(db, order) for order in orders]


@router.patch("/kds/orders/{order_id}/status", response_model=dict)
def update_kds_order_status(
    order_id: str,
    request: KDSStatusUpdateRequest,
    db: Session = Depends(get_db)
):
    """Update active kitchen order status."""
    from app.services.order_service import OrderService
    # Validate the status
    valid_kds_statuses = ["pending", "accepted", "preparing", "ready", "served", "completed", "cancelled"]
    if request.status not in valid_kds_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of {valid_kds_statuses}")
    
    try:
        order = OrderService.update_order_status(db, order_id, request.status)
        return KDSService.format_kds_order(db, order)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
