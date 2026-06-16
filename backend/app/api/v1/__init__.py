"""
API v1 routes.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, product, order, kds, inventory, customer, self_order, sharing, report, settings

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(product.router)
api_router.include_router(order.router)
api_router.include_router(kds.router)
api_router.include_router(inventory.router)
api_router.include_router(customer.router)
api_router.include_router(self_order.router)
api_router.include_router(sharing.router)
api_router.include_router(report.router)
api_router.include_router(settings.router)

__all__ = ["api_router"]
