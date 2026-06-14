"""
Order API endpoints for Phase 2.
REST endpoints for order management, billing, and payments.
"""

from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Header
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models import User
from app.schemas.order import (
    OrderCreateRequest,
    OrderResponse,
    OrderDetailResponse,
    OrderListResponse,
    OrderItemAddRequest,
    OrderItemResponse,
    OrderUpdateRequest,
    OrderHoldRequest,
    BillingResponse,
    PaymentRequest,
    PaymentResponse,
    PaymentListResponse,
    TableResponse,
    TableStatusUpdateRequest,
    TableMergeRequest,
)
from app.services.order_service import OrderService
from app.services.billing_service import BillingService
from app.services.payment_service import PaymentService
from app.services.table_service import TableService
from app.core.security import verify_token

router = APIRouter(prefix="", tags=["orders"])


def get_current_user(db: Session = Depends(get_db), authorization: str = Header(None)) -> User:
    """Dependency to get current user from JWT token."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")

    try:
        token = authorization.replace("Bearer ", "")
        token_data = verify_token(token)
        if not token_data:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = db.query(User).filter(User.id == token_data.user_id).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


# ============================================================================
# Order Endpoints
# ============================================================================


@router.post("/orders", response_model=OrderResponse, status_code=201)
def create_order(
    request: OrderCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create new order."""
    try:
        order = OrderService.create_order(db, request, str(current_user.id))
        return order
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orders", response_model=OrderListResponse)
def list_orders(
    status: Optional[str] = Query(None),
    order_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List orders with optional filters."""
    try:
        orders, total = OrderService.list_orders(
            db,
            status=status,
            order_type=order_type,
            limit=limit,
            offset=offset,
        )
        return OrderListResponse(
            total=total,
            limit=limit,
            offset=offset,
            orders=orders,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orders/{order_id}", response_model=OrderDetailResponse)
def get_order_detail(
    order_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get order details with items and payments."""
    try:
        order = OrderService.get_order(db, order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        return order
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/orders/{order_id}", response_model=OrderResponse)
def update_order(
    order_id: str,
    request: OrderUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update order details."""
    try:
        updates = request.dict(exclude_unset=True)
        order = OrderService.update_order(db, order_id, updates)
        return order
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Order Item Endpoints
# ============================================================================


@router.post("/orders/{order_id}/items", response_model=OrderItemResponse, status_code=201)
def add_item_to_order(
    order_id: str,
    request: OrderItemAddRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add item to order."""
    try:
        item = OrderService.add_item_to_order(db, order_id, request)
        return item
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/orders/{order_id}/items/{item_id}", status_code=204)
def remove_item_from_order(
    order_id: str,
    item_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove item from order."""
    try:
        OrderService.remove_item_from_order(db, order_id, item_id)
        return None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Order Status Endpoints
# ============================================================================


@router.patch("/orders/{order_id}/hold", response_model=OrderResponse)
def hold_order(
    order_id: str,
    request: OrderHoldRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Put order on hold."""
    try:
        order = OrderService.hold_order(db, order_id)
        return order
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/orders/{order_id}/resume", response_model=OrderResponse)
def resume_order(
    order_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Resume order from hold."""
    try:
        order = OrderService.resume_order(db, order_id)
        return order
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/orders/{order_id}/complete", response_model=OrderResponse)
def complete_order(
    order_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark order as completed."""
    try:
        order = OrderService.complete_order(db, order_id)
        return order
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/orders/{order_id}/cancel", response_model=OrderResponse)
def cancel_order(
    order_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancel order."""
    try:
        order = OrderService.cancel_order(db, order_id)
        return order
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Billing Endpoints
# ============================================================================


@router.get("/orders/{order_id}/billing", response_model=BillingResponse)
def get_order_billing(
    order_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get billing summary for order."""
    try:
        bill_data = BillingService.generate_bill_summary(db, order_id)
        return bill_data
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/orders/{order_id}/discount")
def apply_discount(
    order_id: str,
    discount_amount: Optional[Decimal] = Query(None),
    discount_percentage: Optional[Decimal] = Query(None),
    discount_code: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Apply discount to order."""
    try:
        billing = BillingService.apply_discount(
            db,
            order_id,
            discount_amount=discount_amount,
            discount_percentage=discount_percentage,
            discount_code=discount_code,
        )
        return billing
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/orders/{order_id}/discount")
def remove_discount(
    order_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove discount from order."""
    try:
        billing = BillingService.remove_discount(db, order_id)
        return billing
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Payment Endpoints
# ============================================================================


@router.post("/orders/{order_id}/payments", response_model=PaymentResponse, status_code=201)
def process_payment(
    order_id: str,
    request: PaymentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Process payment for order."""
    try:
        payment = PaymentService.process_payment(db, order_id, request)
        return payment
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orders/{order_id}/payments", response_model=PaymentListResponse)
def get_order_payments(
    order_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all payments for order."""
    try:
        summary = PaymentService.get_payment_summary(db, order_id)
        return summary
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/orders/{order_id}/split-payment")
def process_split_payment(
    order_id: str,
    payments: list[PaymentRequest],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Process split payment for order."""
    try:
        payment_list = PaymentService.process_split_payment(db, order_id, payments)
        return [p for p in payment_list]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Table Endpoints
# ============================================================================


@router.get("/tables", response_model=list[TableResponse])
def list_tables(
    status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List tables with optional status filter."""
    try:
        tables, total = TableService.list_tables(db, status=status, limit=limit, offset=offset)
        return tables
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tables/{table_id}", response_model=TableResponse)
def get_table(
    table_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get table details."""
    try:
        table = TableService.get_table(db, table_id)
        if not table:
            raise HTTPException(status_code=404, detail="Table not found")
        return table
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tables/{table_id}/qr")
def get_table_qr(table_id: str, db: Session = Depends(get_db)):
    """Generate table self-ordering QR code image."""
    import qrcode
    import io
    from fastapi.responses import Response
    from app.models import Table

    try:
        table = db.query(Table).filter(Table.id == table_id).first()
        if not table:
            raise HTTPException(status_code=404, detail="Table not found")

        menu_url = f"http://localhost:3000/menu?table_id={table_id}"
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(menu_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        qr_bytes = buf.getvalue()

        return Response(content=qr_bytes, media_type="image/png")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/tables/{table_id}/status", response_model=TableResponse)
def update_table_status(
    table_id: str,
    request: TableStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update table status."""
    try:
        table = TableService.update_table_status(db, table_id, request.status)
        return table
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tables/merge", response_model=TableResponse)
def merge_tables(
    request: TableMergeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Merge multiple tables."""
    try:
        table = TableService.merge_tables(db, request.table_ids)
        return table
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tables/status/occupancy")
def get_table_occupancy(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get table occupancy report."""
    try:
        report = TableService.get_table_occupancy_report(db)
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
