"""
WebSocket endpoint for Kitchen Display System (KDS).
Clients connect and receive real-time order updates pushed from backend services.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends

from app.services.kds_service import KDSService
from app.db.database import get_db
from app.core.security import verify_token

router = APIRouter(prefix="/api/v1", tags=["kds"])


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
