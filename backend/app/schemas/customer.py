"""
Pydantic validation schemas for Customer, Loyalty, QR self-ordering, and Bill Sharing.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator

from app.schemas.order import OrderItemAddRequest


# ============================================================================
# Customer Schemas
# ============================================================================

class CustomerCreate(BaseModel):
    """Request schema for creating a customer profile."""
    name: str = Field(..., min_length=1, max_length=100)
    phone_number: str = Field(..., min_length=5, max_length=20, description="Unique phone number")
    email: Optional[str] = Field(None, max_length=100)


class CustomerUpdate(BaseModel):
    """Request schema for updating a customer profile."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone_number: Optional[str] = Field(None, min_length=5, max_length=20)
    email: Optional[str] = Field(None, max_length=100)
    loyalty_points: Optional[int] = Field(None, ge=0)
    total_spent: Optional[Decimal] = Field(None, ge=0)


class CustomerResponse(BaseModel):
    """Response schema for a customer profile."""
    id: UUID
    name: str
    phone_number: str
    email: Optional[str] = None
    loyalty_points: int
    total_spent: Decimal
    visit_count: int
    last_visit: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Customer Purchase History & Order Summaries
# ============================================================================

class CustomerOrderSummary(BaseModel):
    """Brief order summary for customer purchase history."""
    id: UUID
    order_number: str
    order_type: str
    status: str
    total_amount: Decimal
    created_at: datetime

    class Config:
        from_attributes = True


class CustomerPurchaseHistoryResponse(BaseModel):
    """Response containing customer details and order history."""
    customer: CustomerResponse
    orders: List[CustomerOrderSummary] = []


# ============================================================================
# Self-Ordering & Sharing Schemas
# ============================================================================

class SelfOrderCreateRequest(BaseModel):
    """Request schema for QR-based anonymous self-ordering."""
    table_id: UUID
    items: List[OrderItemAddRequest] = Field(..., min_items=1, description="List of items to order")
    customer_phone: Optional[str] = Field(None, description="Optional phone number for loyalty point tracking")
    notes: Optional[str] = None


class BillShareRequest(BaseModel):
    """Request schema for bill sharing."""
    method: str = Field(..., description="email, whatsapp, or sms")
    destination: str = Field(..., min_length=1, description="Email address or phone number")

    @validator("method")
    def validate_method(cls, v):
        valid_methods = ["email", "whatsapp", "sms"]
        if v.lower() not in valid_methods:
            raise ValueError(f"Method must be one of {valid_methods}")
        return v.lower()


class LoyaltyRedeemRequest(BaseModel):
    """Request schema for loyalty points redemption."""
    points_to_redeem: int = Field(..., gt=0, description="Number of points to redeem")
