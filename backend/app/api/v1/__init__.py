"""
API v1 routes.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, product, order

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(product.router)
api_router.include_router(order.router)

__all__ = ["api_router"]
