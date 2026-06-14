"""
Customer API endpoints.
"""

import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models import User
from app.api.v1.endpoints.inventory import get_current_user
from app.schemas.customer import (
    CustomerCreate,
    CustomerResponse,
    CustomerUpdate,
    CustomerPurchaseHistoryResponse,
    LoyaltyRedeemRequest,
)
from app.services.customer_service import CustomerService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/customers", tags=["Customers"])


@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
def create_customer(
    request: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new customer profile."""
    try:
        return CustomerService.create_customer(db, request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating customer: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("", response_model=List[CustomerResponse])
def list_customers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List customer profiles."""
    return CustomerService.list_customers(db, skip=skip, limit=limit)


@router.get("/lookup/{phone_number}", response_model=CustomerResponse)
def lookup_customer(
    phone_number: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Look up customer by phone number."""
    customer = CustomerService.get_customer_by_phone(db, phone_number)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(
    customer_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a customer by ID."""
    customer = CustomerService.get_customer(db, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.put("/{customer_id}", response_model=CustomerResponse)
def update_customer(
    customer_id: UUID,
    request: CustomerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update customer details."""
    try:
        customer = CustomerService.update_customer(db, customer_id, request)
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        return customer
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{customer_id}/history", response_model=CustomerPurchaseHistoryResponse)
def get_purchase_history(
    customer_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get customer profile along with purchase history."""
    try:
        return CustomerService.get_purchase_history(db, customer_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/orders/{order_id}/redeem", response_model=dict)
def redeem_loyalty_points(
    order_id: UUID,
    request: LoyaltyRedeemRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Redeem loyalty points for a discount on an active order (1 point = 1 currency unit)."""
    try:
        CustomerService.redeem_loyalty_points(db, order_id, request.points_to_redeem)
        return {"message": f"Successfully redeemed {request.points_to_redeem} points on order {order_id}"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error redeeming loyalty points: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
