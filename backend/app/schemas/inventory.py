"""
Pydantic schemas for inventory management.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================================
# Supplier Schemas
# ============================================================================

class SupplierCreate(BaseModel):
    """Request schema for creating a supplier."""
    name: str = Field(..., min_length=1, max_length=100)
    contact_person: Optional[str] = Field(None, max_length=100)
    email: Optional[str] = Field(None, max_length=100)
    phone_number: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = None
    city: Optional[str] = Field(None, max_length=50)
    payment_terms: Optional[str] = Field(None, max_length=100)


class SupplierUpdate(BaseModel):
    """Request schema for updating a supplier."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    contact_person: Optional[str] = Field(None, max_length=100)
    email: Optional[str] = Field(None, max_length=100)
    phone_number: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = None
    city: Optional[str] = Field(None, max_length=50)
    payment_terms: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None


class SupplierResponse(BaseModel):
    """Response schema for a supplier."""
    id: UUID
    name: str
    contact_person: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    payment_terms: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Inventory Item Schemas
# ============================================================================

class InventoryItemCreate(BaseModel):
    """Request schema for creating an inventory item."""
    item_name: str = Field(..., min_length=1, max_length=100)
    unit: str = Field(..., min_length=1, max_length=20)
    current_quantity: Decimal = Field(default=Decimal("0.00"), ge=0)
    reorder_level: Decimal = Field(default=Decimal("0.00"), ge=0)
    reorder_quantity: Decimal = Field(default=Decimal("0.00"), ge=0)
    unit_cost: Optional[Decimal] = Field(None, ge=0)
    supplier_id: Optional[UUID] = None
    product_id: Optional[UUID] = None


class InventoryItemUpdate(BaseModel):
    """Request schema for updating an inventory item."""
    item_name: Optional[str] = Field(None, min_length=1, max_length=100)
    unit: Optional[str] = Field(None, min_length=1, max_length=20)
    current_quantity: Optional[Decimal] = Field(None, ge=0)
    reorder_level: Optional[Decimal] = Field(None, ge=0)
    reorder_quantity: Optional[Decimal] = Field(None, ge=0)
    unit_cost: Optional[Decimal] = Field(None, ge=0)
    supplier_id: Optional[UUID] = None
    product_id: Optional[UUID] = None


class InventoryItemResponse(BaseModel):
    """Response schema for an inventory item."""
    id: UUID
    product_id: Optional[UUID] = None
    item_name: str
    unit: str
    current_quantity: Decimal
    reorder_level: Decimal
    reorder_quantity: Decimal
    unit_cost: Optional[Decimal] = None
    supplier_id: Optional[UUID] = None
    last_stock_check: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Inventory Transaction Schemas
# ============================================================================

class InventoryTransactionCreate(BaseModel):
    """Request schema for creating an inventory transaction."""
    transaction_type: str = Field(..., description="stock_in, stock_out, purchase, waste, adjustment")
    quantity: Decimal = Field(...)
    reference_type: Optional[str] = Field(None, max_length=50)
    reference_id: Optional[UUID] = None
    notes: Optional[str] = None


class InventoryTransactionResponse(BaseModel):
    """Response schema for an inventory transaction."""
    id: UUID
    inventory_item_id: UUID
    transaction_type: str
    quantity: Decimal
    reference_type: Optional[str] = None
    reference_id: Optional[UUID] = None
    notes: Optional[str] = None
    created_by_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Recipe & Ingredient Schemas
# ============================================================================

class RecipeIngredientCreate(BaseModel):
    """Schema for adding an ingredient to a recipe."""
    inventory_item_id: UUID
    quantity_needed: Decimal = Field(..., gt=0)


class RecipeIngredientResponse(BaseModel):
    """Response schema for a recipe ingredient."""
    id: UUID
    recipe_id: UUID
    inventory_item_id: UUID
    quantity_needed: Decimal
    created_at: datetime
    updated_at: datetime
    item_name: Optional[str] = None
    unit: Optional[str] = None

    class Config:
        from_attributes = True


class RecipeCreate(BaseModel):
    """Request schema for creating a recipe."""
    product_id: UUID
    name: str = Field(..., min_length=1, max_length=100)
    ingredients: List[RecipeIngredientCreate] = []


class RecipeUpdate(BaseModel):
    """Request schema for updating a recipe."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    ingredients: Optional[List[RecipeIngredientCreate]] = None


class RecipeResponse(BaseModel):
    """Response schema for a recipe."""
    id: UUID
    product_id: UUID
    name: str
    created_at: datetime
    updated_at: datetime
    ingredients: List[RecipeIngredientResponse] = []

    class Config:
        from_attributes = True


# ============================================================================
# Forecasting & Alert Schemas
# ============================================================================

class StockForecastResponse(BaseModel):
    """Response schema for basic stock forecasting."""
    item_id: UUID
    item_name: str
    current_quantity: Decimal
    unit: str
    daily_rate: Decimal
    days_remaining: Decimal  # -1 or high value if burn rate is 0
    recommendation: str  # reorder_now, reorder_soon, sufficient_stock
