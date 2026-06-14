"""
Product API endpoints.
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.product import (
    CategoryCreateRequest,
    CategoryResponse,
    CategoryUpdateRequest,
    ProductCreateRequest,
    ProductDetailResponse,
    ProductListResponse,
    ProductResponse,
    ProductUpdateRequest,
)
from app.services.product_service import CategoryService, ProductService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/products", tags=["Products"])


# ============================================================================
# Category Endpoints
# ============================================================================


@router.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(request: CategoryCreateRequest, db: Session = Depends(get_db)):
    """
    Create a new product category.

    - **name**: Category name (required, unique)
    - **description**: Optional description
    - **image_url**: Optional image URL
    - **display_order**: Order for display (default: 0)
    """
    try:
        category = CategoryService.create_category(db, request)
        return category
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error creating category: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating category",
        )


@router.get("/categories", response_model=list[CategoryResponse])
def list_categories(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
):
    """
    List all product categories.

    - **skip**: Number of records to skip
    - **limit**: Number of records to return
    - **active_only**: Filter by active status
    """
    try:
        categories = CategoryService.list_categories(db, skip=skip, limit=limit, active_only=active_only)
        return categories
    except Exception as e:
        logger.error(f"Error listing categories: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error listing categories",
        )


@router.get("/categories/{category_id}", response_model=CategoryResponse)
def get_category(category_id: UUID, db: Session = Depends(get_db)):
    """Get a specific category by ID."""
    category = CategoryService.get_category(db, category_id)

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    return category


@router.put("/categories/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: UUID,
    request: CategoryUpdateRequest,
    db: Session = Depends(get_db),
):
    """Update a category."""
    category = CategoryService.update_category(db, category_id, request)

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    return category


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: UUID, db: Session = Depends(get_db)):
    """Soft delete a category."""
    success = CategoryService.soft_delete_category(db, category_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )


# ============================================================================
# Product Endpoints
# ============================================================================


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(request: ProductCreateRequest, db: Session = Depends(get_db)):
    """
    Create a new product.

    - **sku**: Stock keeping unit (unique, required)
    - **name**: Product name (required)
    - **category_id**: Category ID (required)
    - **price**: Product price (required, > 0)
    - **tax_percent**: Tax percentage (0-100, optional)
    - **preparation_time_minutes**: Cooking time in minutes (optional)
    """
    try:
        product = ProductService.create_product(db, request)
        return product
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error creating product: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating product",
        )


@router.get("", response_model=list[ProductListResponse])
def list_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    category_id: Optional[UUID] = Query(None),
    available_only: bool = Query(False),
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
):
    """
    List products with optional filters.

    - **skip**: Number of records to skip
    - **limit**: Number of records to return
    - **category_id**: Filter by category
    - **available_only**: Only return available products
    - **active_only**: Filter by active status
    """
    try:
        products = ProductService.list_products(
            db,
            skip=skip,
            limit=limit,
            category_id=category_id,
            available_only=available_only,
            active_only=active_only,
        )
        return products
    except Exception as e:
        logger.error(f"Error listing products: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error listing products",
        )


@router.get("/{product_id}", response_model=ProductDetailResponse)
def get_product(product_id: UUID, db: Session = Depends(get_db)):
    """Get a specific product with details (category, add-ons)."""
    product = ProductService.get_product(db, product_id)

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    return product


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: UUID,
    request: ProductUpdateRequest,
    db: Session = Depends(get_db),
):
    """Update a product."""
    try:
        product = ProductService.update_product(db, product_id, request)

        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found",
            )

        return product
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.patch("/{product_id}/toggle-availability", response_model=ProductResponse)
def toggle_product_availability(product_id: UUID, db: Session = Depends(get_db)):
    """Toggle product availability."""
    product = ProductService.toggle_product_availability(db, product_id)

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: UUID, db: Session = Depends(get_db)):
    """Soft delete a product."""
    success = ProductService.soft_delete_product(db, product_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )


@router.post("/{product_id}/addons", status_code=status.HTTP_201_CREATED)
def add_product_addon(
    product_id: UUID,
    addon_name: str = Query(..., min_length=1),
    addon_price: float = Query(..., gt=0),
    db: Session = Depends(get_db),
):
    """Add an add-on to a product."""
    addon = ProductService.add_addon(db, product_id, addon_name, addon_price)

    if not addon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    return {
        "id": addon.id,
        "addon_name": addon.addon_name,
        "addon_price": addon.addon_price,
        "is_available": addon.is_available,
    }
