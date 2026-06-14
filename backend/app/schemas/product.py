"""
Pydantic schemas for product management.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================================
# Category Schemas
# ============================================================================


class CategoryCreateRequest(BaseModel):
    """Category creation request."""

    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    image_url: Optional[str] = None
    display_order: int = Field(default=0, ge=0)


class CategoryUpdateRequest(BaseModel):
    """Category update request."""

    name: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None


class CategoryResponse(BaseModel):
    """Category response."""

    id: UUID
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    display_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Product Add-on Schemas
# ============================================================================


class ProductAddonCreateRequest(BaseModel):
    """Product add-on creation request."""

    addon_name: str = Field(..., min_length=1, max_length=100)
    addon_price: float = Field(..., gt=0)


class ProductAddonResponse(BaseModel):
    """Product add-on response."""

    id: UUID
    addon_name: str
    addon_price: float
    is_available: bool

    class Config:
        from_attributes = True


# ============================================================================
# Product Schemas
# ============================================================================


class ProductCreateRequest(BaseModel):
    """Product creation request."""

    sku: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=150)
    description: Optional[str] = None
    category_id: UUID
    price: float = Field(..., gt=0)
    tax_percent: float = Field(default=0, ge=0, le=100)
    image_url: Optional[str] = None
    preparation_time_minutes: int = Field(default=0, ge=0)


class ProductUpdateRequest(BaseModel):
    """Product update request."""

    name: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[UUID] = None
    price: Optional[float] = None
    tax_percent: Optional[float] = None
    image_url: Optional[str] = None
    preparation_time_minutes: Optional[int] = None
    is_available: Optional[bool] = None
    is_active: Optional[bool] = None


class ProductResponse(BaseModel):
    """Product response."""

    id: UUID
    sku: str
    name: str
    description: Optional[str] = None
    category_id: UUID
    price: float
    tax_percent: float
    image_url: Optional[str] = None
    preparation_time_minutes: int
    is_available: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProductDetailResponse(ProductResponse):
    """Product detail response with category and add-ons."""

    category: Optional[CategoryResponse] = None
    addons: list[ProductAddonResponse] = []


class ProductListResponse(BaseModel):
    """Product list response."""

    id: UUID
    sku: str
    name: str
    category_id: UUID
    price: float
    image_url: Optional[str] = None
    is_available: bool

    class Config:
        from_attributes = True


# ============================================================================
# Bulk Operations
# ============================================================================


class BulkProductUpdateRequest(BaseModel):
    """Bulk update products."""

    product_ids: list[UUID]
    is_available: Optional[bool] = None
    is_active: Optional[bool] = None


class BulkCategoryUpdateRequest(BaseModel):
    """Bulk update categories."""

    category_ids: list[UUID]
    is_active: Optional[bool] = None
