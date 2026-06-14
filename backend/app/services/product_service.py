"""
Product service for managing products and categories.
"""

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import Category, Product, ProductAddon
from app.schemas.product import (
    CategoryCreateRequest,
    CategoryUpdateRequest,
    ProductCreateRequest,
    ProductUpdateRequest,
)

logger = logging.getLogger(__name__)


class CategoryService:
    """Category management service."""

    @staticmethod
    def create_category(db: Session, request: CategoryCreateRequest) -> Category:
        """Create a new category."""
        # Check if category already exists
        existing = (
            db.query(Category)
            .filter(Category.name == request.name, Category.deleted_at.is_(None))
            .first()
        )
        if existing:
            raise ValueError(f"Category '{request.name}' already exists")

        category = Category(
            name=request.name,
            description=request.description,
            image_url=request.image_url,
            display_order=request.display_order,
            is_active=True,
        )

        db.add(category)
        db.commit()
        db.refresh(category)

        logger.info(f"Category created: {category.id}")
        return category

    @staticmethod
    def get_category(db: Session, category_id: UUID) -> Optional[Category]:
        """Get category by ID."""
        return (
            db.query(Category)
            .filter(Category.id == category_id, Category.deleted_at.is_(None))
            .first()
        )

    @staticmethod
    def list_categories(
        db: Session, skip: int = 0, limit: int = 100, active_only: bool = True
    ) -> list[Category]:
        """List all categories."""
        query = db.query(Category).filter(Category.deleted_at.is_(None))

        if active_only:
            query = query.filter(Category.is_active == True)

        return query.order_by(Category.display_order).offset(skip).limit(limit).all()

    @staticmethod
    def update_category(
        db: Session, category_id: UUID, request: CategoryUpdateRequest
    ) -> Optional[Category]:
        """Update category."""
        category = CategoryService.get_category(db, category_id)

        if not category:
            return None

        update_data = request.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(category, field, value)

        db.commit()
        db.refresh(category)

        logger.info(f"Category updated: {category_id}")
        return category

    @staticmethod
    def soft_delete_category(db: Session, category_id: UUID) -> bool:
        """Soft delete a category."""
        category = CategoryService.get_category(db, category_id)

        if not category:
            return False

        from datetime import datetime

        category.deleted_at = datetime.utcnow()
        db.commit()

        logger.info(f"Category soft deleted: {category_id}")
        return True


class ProductService:
    """Product management service."""

    @staticmethod
    def create_product(db: Session, request: ProductCreateRequest) -> Product:
        """Create a new product."""
        # Check if SKU already exists
        existing = db.query(Product).filter(Product.sku == request.sku, Product.deleted_at.is_(None)).first()
        if existing:
            raise ValueError(f"SKU '{request.sku}' already exists")

        # Verify category exists
        category = CategoryService.get_category(db, request.category_id)
        if not category:
            raise ValueError(f"Category '{request.category_id}' not found")

        product = Product(
            sku=request.sku,
            name=request.name,
            description=request.description,
            category_id=request.category_id,
            price=request.price,
            tax_percent=request.tax_percent,
            image_url=request.image_url,
            preparation_time_minutes=request.preparation_time_minutes,
            is_available=True,
            is_active=True,
        )

        db.add(product)
        db.commit()
        db.refresh(product)

        logger.info(f"Product created: {product.id}")
        return product

    @staticmethod
    def get_product(db: Session, product_id: UUID) -> Optional[Product]:
        """Get product by ID."""
        return (
            db.query(Product).filter(Product.id == product_id, Product.deleted_at.is_(None)).first()
        )

    @staticmethod
    def get_product_by_sku(db: Session, sku: str) -> Optional[Product]:
        """Get product by SKU."""
        return db.query(Product).filter(Product.sku == sku, Product.deleted_at.is_(None)).first()

    @staticmethod
    def list_products(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        category_id: Optional[UUID] = None,
        available_only: bool = False,
        active_only: bool = True,
    ) -> list[Product]:
        """List products with optional filters."""
        query = db.query(Product).filter(Product.deleted_at.is_(None))

        if category_id:
            query = query.filter(Product.category_id == category_id)

        if available_only:
            query = query.filter(Product.is_available == True)

        if active_only:
            query = query.filter(Product.is_active == True)

        return query.order_by(Product.name).offset(skip).limit(limit).all()

    @staticmethod
    def update_product(db: Session, product_id: UUID, request: ProductUpdateRequest) -> Optional[Product]:
        """Update product."""
        product = ProductService.get_product(db, product_id)

        if not product:
            return None

        # If category is being updated, verify it exists
        if request.category_id:
            category = CategoryService.get_category(db, request.category_id)
            if not category:
                raise ValueError(f"Category '{request.category_id}' not found")

        update_data = request.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(product, field, value)

        db.commit()
        db.refresh(product)

        logger.info(f"Product updated: {product_id}")
        return product

    @staticmethod
    def toggle_product_availability(db: Session, product_id: UUID) -> Optional[Product]:
        """Toggle product availability."""
        product = ProductService.get_product(db, product_id)

        if not product:
            return None

        product.is_available = not product.is_available
        db.commit()
        db.refresh(product)

        logger.info(f"Product availability toggled: {product_id} -> {product.is_available}")
        return product

    @staticmethod
    def soft_delete_product(db: Session, product_id: UUID) -> bool:
        """Soft delete a product."""
        product = ProductService.get_product(db, product_id)

        if not product:
            return False

        from datetime import datetime

        product.deleted_at = datetime.utcnow()
        db.commit()

        logger.info(f"Product soft deleted: {product_id}")
        return True

    @staticmethod
    def add_addon(db: Session, product_id: UUID, addon_name: str, addon_price: float) -> Optional[ProductAddon]:
        """Add an add-on to a product."""
        product = ProductService.get_product(db, product_id)

        if not product:
            return None

        addon = ProductAddon(
            product_id=product_id,
            addon_name=addon_name,
            addon_price=addon_price,
            is_available=True,
        )

        db.add(addon)
        db.commit()
        db.refresh(addon)

        logger.info(f"Add-on created for product {product_id}: {addon.id}")
        return addon

    @staticmethod
    def get_product_with_details(db: Session, product_id: UUID) -> Optional[Product]:
        """Get product with category and add-ons loaded."""
        return db.query(Product).filter(Product.id == product_id, Product.deleted_at.is_(None)).first()
