"""
Unit tests for product service.
"""

import pytest
from uuid import uuid4
from app.db.database import SessionLocal, Base, engine
from app.models import Category, Product
from app.schemas.product import (
    CategoryCreateRequest,
    ProductCreateRequest,
)
from app.services.product_service import CategoryService, ProductService


@pytest.fixture(scope="function")
def db():
    """Create test database."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)


class TestCategoryService:
    """Tests for CategoryService."""

    def test_create_category(self, db):
        """Test category creation."""
        request = CategoryCreateRequest(
            name="Coffee",
            description="Coffee beverages",
        )

        category = CategoryService.create_category(db, request)

        assert category is not None
        assert category.name == "Coffee"
        assert category.is_active is True

    def test_create_duplicate_category(self, db):
        """Test duplicate category creation."""
        request1 = CategoryCreateRequest(name="Coffee")
        CategoryService.create_category(db, request1)

        request2 = CategoryCreateRequest(name="Coffee")
        with pytest.raises(ValueError, match="already exists"):
            CategoryService.create_category(db, request2)

    def test_list_categories(self, db):
        """Test listing categories."""
        for i in range(3):
            request = CategoryCreateRequest(name=f"Category{i}")
            CategoryService.create_category(db, request)

        categories = CategoryService.list_categories(db)
        assert len(categories) == 3

    def test_soft_delete_category(self, db):
        """Test category soft delete."""
        request = CategoryCreateRequest(name="Coffee")
        category = CategoryService.create_category(db, request)

        success = CategoryService.soft_delete_category(db, category.id)
        assert success is True

        found = CategoryService.get_category(db, category.id)
        assert found is None  # Soft deleted categories are not returned


class TestProductService:
    """Tests for ProductService."""

    @pytest.fixture
    def category(self, db):
        """Create test category."""
        request = CategoryCreateRequest(name="Coffee")
        return CategoryService.create_category(db, request)

    def test_create_product(self, db, category):
        """Test product creation."""
        request = ProductCreateRequest(
            sku="COFFEE-001",
            name="Espresso",
            category_id=category.id,
            price=60.00,
            tax_percent=5.0,
            preparation_time_minutes=2,
        )

        product = ProductService.create_product(db, request)

        assert product is not None
        assert product.sku == "COFFEE-001"
        assert product.name == "Espresso"
        assert float(product.price) == 60.00

    def test_create_duplicate_product_sku(self, db, category):
        """Test duplicate SKU creation."""
        request1 = ProductCreateRequest(
            sku="COFFEE-001",
            name="Espresso",
            category_id=category.id,
            price=60.00,
        )
        ProductService.create_product(db, request1)

        request2 = ProductCreateRequest(
            sku="COFFEE-001",
            name="Double Espresso",
            category_id=category.id,
            price=80.00,
        )
        with pytest.raises(ValueError, match="already exists"):
            ProductService.create_product(db, request2)

    def test_list_products(self, db, category):
        """Test listing products."""
        for i in range(3):
            request = ProductCreateRequest(
                sku=f"COFFEE-{i:03d}",
                name=f"Coffee{i}",
                category_id=category.id,
                price=60.00 + i * 10,
            )
            ProductService.create_product(db, request)

        products = ProductService.list_products(db)
        assert len(products) == 3

    def test_list_products_by_category(self, db, category):
        """Test listing products by category."""
        # Create product in category
        request = ProductCreateRequest(
            sku="COFFEE-001",
            name="Espresso",
            category_id=category.id,
            price=60.00,
        )
        ProductService.create_product(db, request)

        # List by category
        products = ProductService.list_products(db, category_id=category.id)
        assert len(products) == 1

    def test_toggle_product_availability(self, db, category):
        """Test toggling product availability."""
        request = ProductCreateRequest(
            sku="COFFEE-001",
            name="Espresso",
            category_id=category.id,
            price=60.00,
        )
        product = ProductService.create_product(db, request)
        assert product.is_available is True

        # Toggle
        toggled = ProductService.toggle_product_availability(db, product.id)
        assert toggled.is_available is False

        # Toggle back
        toggled = ProductService.toggle_product_availability(db, product.id)
        assert toggled.is_available is True

    def test_soft_delete_product(self, db, category):
        """Test product soft delete."""
        request = ProductCreateRequest(
            sku="COFFEE-001",
            name="Espresso",
            category_id=category.id,
            price=60.00,
        )
        product = ProductService.create_product(db, request)

        success = ProductService.soft_delete_product(db, product.id)
        assert success is True

        found = ProductService.get_product(db, product.id)
        assert found is None
