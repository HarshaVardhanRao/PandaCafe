"""
Public self-ordering API endpoint for customer QR codes.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models import User, Customer, Table
from app.schemas.customer import SelfOrderCreateRequest
from app.schemas.order import OrderCreateRequest, OrderResponse
from app.services.order_service import OrderService
from app.services.customer_service import CustomerService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/self-order", tags=["Self Ordering"])


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def self_order(request: SelfOrderCreateRequest, db: Session = Depends(get_db)):
    """
    Public self-ordering endpoint for customers scanning a table QR code.
    No cashier token/auth is required.
    """
    try:
        # 1. Validate table
        table = db.query(Table).filter(Table.id == request.table_id).first()
        if not table:
            raise HTTPException(status_code=404, detail=f"Table {request.table_id} not found")

        # 2. Get default cashier (admin)
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            # Fallback to any user to prevent database failure in custom tests
            admin = db.query(User).first()
            if not admin:
                raise HTTPException(
                    status_code=500,
                    detail="Default operational staff user not seeded"
                )
        cashier_id = str(admin.id)

        # 3. Resolve customer if phone number provided
        customer_id = None
        if request.customer_phone:
            customer = CustomerService.get_customer_by_phone(db, request.customer_phone)
            if not customer:
                # Create a placeholder customer profile
                from app.schemas.customer import CustomerCreate
                create_req = CustomerCreate(
                    name="QR Customer",
                    phone_number=request.customer_phone,
                )
                customer = CustomerService.create_customer(db, create_req)
            customer_id = str(customer.id)

        # 4. Create Order
        notes = f"[QR Self-Order] {request.notes or ''}".strip()
        order_create = OrderCreateRequest(
            order_type="dine_in",
            table_id=str(request.table_id),
            customer_id=customer_id,
            notes=notes,
        )
        order = OrderService.create_order(db, order_create, cashier_id)

        # 5. Add Items
        for item in request.items:
            OrderService.add_item_to_order(db, str(order.id), item)

        logger.info(f"Self-order {order.order_number} created for table {table.table_number}")
        return order

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in self-order API: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
