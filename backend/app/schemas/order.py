"""
Pydantic schemas for order management, billing, and payments.
Request/response models for Phase 2 endpoints.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field, validator


# ============================================================================
# Order Item Schemas
# ============================================================================


class OrderItemAddRequest(BaseModel):
    """Request to add item to order."""

    product_id: str = Field(..., description="Product UUID")
    quantity: int = Field(..., gt=0, description="Quantity must be > 0")
    special_notes: Optional[str] = Field(None, description="Special instructions for item")

    class Config:
        json_schema_extra = {
            "example": {
                "product_id": "550e8400-e29b-41d4-a716-446655440000",
                "quantity": 2,
                "special_notes": "Extra hot",
            }
        }


class OrderItemResponse(BaseModel):
    """Response model for order item."""

    id: str
    order_id: str
    product_id: str
    product_name: Optional[str] = None
    quantity: int
    unit_price: Decimal
    tax_percent: Decimal
    item_total: Decimal
    special_notes: Optional[str]
    is_cancelled: bool
    created_at: datetime

    class Config:
        from_attributes = True


class OrderItemDetailResponse(OrderItemResponse):
    """Extended order item response with product details."""

    product_sku: Optional[str] = None
    product_category: Optional[str] = None


# ============================================================================
# Order Creation & Management Schemas
# ============================================================================


class OrderCreateRequest(BaseModel):
    """Request to create new order."""

    order_type: str = Field(..., description="dine_in, take_away, or delivery")
    table_id: Optional[str] = Field(None, description="Table UUID for dine-in orders")
    customer_id: Optional[str] = Field(None, description="Customer UUID")
    notes: Optional[str] = Field(None, description="Order notes/special instructions")

    @validator("order_type")
    def validate_order_type(cls, v):
        if v not in ["dine_in", "take_away", "delivery"]:
            raise ValueError("order_type must be dine_in, take_away, or delivery")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "order_type": "dine_in",
                "table_id": "550e8400-e29b-41d4-a716-446655440000",
                "notes": "No onions",
            }
        }


class OrderUpdateRequest(BaseModel):
    """Request to update order details."""

    table_id: Optional[str] = None
    customer_id: Optional[str] = None
    notes: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "notes": "Updated special instructions",
            }
        }


class OrderHoldRequest(BaseModel):
    """Request to hold/resume order."""

    reason: Optional[str] = Field(None, description="Reason for hold/resume")

    class Config:
        json_schema_extra = {
            "example": {
                "reason": "Waiting for customer",
            }
        }


# ============================================================================
# Billing & Calculation Schemas
# ============================================================================


class BillingCalculation(BaseModel):
    """Billing calculation details."""

    subtotal: Decimal
    tax_amount: Decimal
    tax_percentage: Decimal
    discount_amount: Decimal = Decimal("0.00")
    discount_reason: Optional[str] = None
    total_amount: Decimal

    class Config:
        json_schema_extra = {
            "example": {
                "subtotal": Decimal("500.00"),
                "tax_amount": Decimal("50.00"),
                "tax_percentage": Decimal("10.00"),
                "discount_amount": Decimal("25.00"),
                "total_amount": Decimal("525.00"),
            }
        }


class BillingResponse(BaseModel):
    """Complete billing summary for order."""

    order_id: str
    order_number: str
    items_count: int
    item_details: List[OrderItemResponse]
    billing: BillingCalculation
    created_at: datetime
    customer_name: Optional[str] = None
    table_number: Optional[int] = None

    class Config:
        from_attributes = True


# ============================================================================
# Payment Schemas
# ============================================================================


class PaymentRequest(BaseModel):
    """Request to process payment."""

    amount: Decimal = Field(..., gt=0, description="Payment amount")
    payment_method: str = Field(..., description="cash, upi, card, or split")
    transaction_id: Optional[str] = Field(None, description="External transaction ID")
    reference_number: Optional[str] = Field(None, description="Reference/receipt number")

    @validator("payment_method")
    def validate_payment_method(cls, v):
        if v not in ["cash", "upi", "card", "split"]:
            raise ValueError("payment_method must be cash, upi, card, or split")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "amount": Decimal("525.00"),
                "payment_method": "cash",
                "reference_number": "INV-001",
            }
        }


class SplitPaymentRequest(BaseModel):
    """Request for split payment."""

    payments: List[PaymentRequest] = Field(..., description="List of payment methods")

    @validator("payments")
    def validate_split_payments(cls, v):
        if len(v) < 2:
            raise ValueError("Split payment must have at least 2 payment methods")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "payments": [
                    {
                        "amount": Decimal("300.00"),
                        "payment_method": "cash",
                    },
                    {
                        "amount": Decimal("225.00"),
                        "payment_method": "upi",
                        "transaction_id": "UPI123456",
                    },
                ]
            }
        }


class PaymentResponse(BaseModel):
    """Response for payment transaction."""

    id: str
    order_id: str
    amount: Decimal
    payment_method: str
    transaction_id: Optional[str]
    payment_status: str
    reference_number: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class PaymentListResponse(BaseModel):
    """Response for payment list."""

    order_id: str
    total_paid: Decimal
    remaining_amount: Decimal
    payments: List[PaymentResponse]

    class Config:
        from_attributes = True


# ============================================================================
# Order Response Schemas
# ============================================================================


class OrderResponse(BaseModel):
    """Basic order response."""

    id: str
    order_number: str
    order_type: str
    status: str
    table_id: Optional[str]
    customer_id: Optional[str]
    cashier_id: str
    subtotal: Decimal
    tax_amount: Decimal
    discount_amount: Decimal
    total_amount: Decimal
    is_hold: bool
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
    cancelled_at: Optional[datetime]

    class Config:
        from_attributes = True


class OrderDetailResponse(OrderResponse):
    """Extended order response with items and payments."""

    items: List[OrderItemResponse]
    payments: List[PaymentResponse]
    table_number: Optional[int] = None
    customer_name: Optional[str] = None
    cashier_name: Optional[str] = None

    class Config:
        from_attributes = True


class OrderListResponse(BaseModel):
    """Paginated list of orders."""

    total: int
    limit: int
    offset: int
    orders: List[OrderResponse]

    class Config:
        from_attributes = True


# ============================================================================
# Table Management Schemas
# ============================================================================


class TableStatusUpdateRequest(BaseModel):
    """Request to update table status."""

    status: str = Field(..., description="available, occupied, reserved, or cleaning")
    notes: Optional[str] = None

    @validator("status")
    def validate_status(cls, v):
        if v not in ["available", "occupied", "reserved", "cleaning"]:
            raise ValueError("status must be available, occupied, reserved, or cleaning")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "status": "occupied",
                "notes": "Customers seated",
            }
        }


class TableResponse(BaseModel):
    """Response model for table."""

    id: str
    table_number: int
    capacity: int
    location: Optional[str]
    status: str
    current_order_id: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TableMergeRequest(BaseModel):
    """Request to merge tables."""

    table_ids: List[str] = Field(..., min_items=2, description="List of table IDs to merge")

    class Config:
        json_schema_extra = {
            "example": {
                "table_ids": [
                    "550e8400-e29b-41d4-a716-446655440000",
                    "550e8400-e29b-41d4-a716-446655440001",
                ]
            }
        }
