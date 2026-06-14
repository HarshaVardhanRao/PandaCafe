"""
Unit tests for order service (Phase 2).
Tests for order creation, item management, and order lifecycle.
"""

import pytest
from decimal import Decimal
from sqlalchemy.orm import Session

from app.models import Order, User, Category, Product, Table, Customer
from app.schemas.order import OrderCreateRequest, OrderItemAddRequest
from app.services.order_service import OrderService


@pytest.fixture
def test_table(db: Session):
    """Create test table."""
    table = Table(
        table_number=1,
        capacity=4,
        location="Window",
        status="available",
    )
    db.add(table)
    db.commit()
    return table


@pytest.fixture
def test_customer(db: Session):
    """Create test customer."""
    customer = Customer(
        phone_number="9876543210",
        email="customer@test.com",
        name="John Doe",
    )
    db.add(customer)
    db.commit()
    return customer


@pytest.fixture
def test_category(db: Session):
    """Create test category."""
    category = Category(
        name="Beverages",
        description="Hot and Cold Beverages",
    )
    db.add(category)
    db.commit()
    return category


@pytest.fixture
def test_product(db: Session, test_category):
    """Create test product."""
    product = Product(
        sku="COFFEE-001",
        name="Espresso",
        description="Single shot espresso",
        category_id=test_category.id,
        price=Decimal("50.00"),
        tax_percent=Decimal("5.00"),
        is_available=True,
    )
    db.add(product)
    db.commit()
    return product


class TestOrderCreation:
    """Tests for order creation."""

    def test_create_dine_in_order(self, db: Session, test_user: User, test_table: Table):
        """Test creating dine-in order."""
        request = OrderCreateRequest(
            order_type="dine_in",
            table_id=str(test_table.id),
        )

        order = OrderService.create_order(db, request, str(test_user.id))

        assert order is not None
        assert order.order_type == "dine_in"
        assert order.table_id == test_table.id
        assert order.status == "pending"
        assert order.cashier_id == test_user.id
        assert order.order_number.startswith("ORD-")

    def test_create_takeaway_order(self, db: Session, test_user: User):
        """Test creating takeaway order."""
        request = OrderCreateRequest(
            order_type="take_away",
            notes="Extra hot",
        )

        order = OrderService.create_order(db, request, str(test_user.id))

        assert order.order_type == "take_away"
        assert order.table_id is None
        assert order.notes == "Extra hot"

    def test_create_order_with_customer(self, db: Session, test_user: User, test_customer: Customer):
        """Test creating order with customer."""
        request = OrderCreateRequest(
            order_type="dine_in",
            customer_id=str(test_customer.id),
        )

        order = OrderService.create_order(db, request, str(test_user.id))

        assert order.customer_id == test_customer.id

    def test_create_order_invalid_table(self, db: Session, test_user: User):
        """Test creating order with invalid table."""
        request = OrderCreateRequest(
            order_type="dine_in",
            table_id="invalid-id",
        )

        with pytest.raises(ValueError, match="not found"):
            OrderService.create_order(db, request, str(test_user.id))

    def test_create_order_invalid_cashier(self, db: Session, test_table: Table):
        """Test creating order with invalid cashier."""
        request = OrderCreateRequest(
            order_type="dine_in",
            table_id=str(test_table.id),
        )

        with pytest.raises(ValueError, match="Cashier"):
            OrderService.create_order(db, request, "invalid-id")


class TestOrderItems:
    """Tests for order items."""

    def test_add_item_to_order(self, db: Session, test_user: User, test_product: Product):
        """Test adding item to order."""
        # Create order
        request = OrderCreateRequest(order_type="take_away")
        order = OrderService.create_order(db, request, str(test_user.id))

        # Add item
        item_request = OrderItemAddRequest(
            product_id=str(test_product.id),
            quantity=2,
            special_notes="No foam",
        )
        item = OrderService.add_item_to_order(db, str(order.id), item_request)

        assert item.product_id == test_product.id
        assert item.quantity == 2
        assert item.special_notes == "No foam"
        assert item.unit_price == Decimal("50.00")
        assert item.is_cancelled == False

    def test_add_multiple_items(self, db: Session, test_user: User, test_product: Product):
        """Test adding multiple items to order."""
        # Create order
        request = OrderCreateRequest(order_type="take_away")
        order = OrderService.create_order(db, request, str(test_user.id))

        # Add first item
        item1_request = OrderItemAddRequest(
            product_id=str(test_product.id),
            quantity=1,
        )
        OrderService.add_item_to_order(db, str(order.id), item1_request)

        # Add second item
        item2_request = OrderItemAddRequest(
            product_id=str(test_product.id),
            quantity=2,
        )
        OrderService.add_item_to_order(db, str(order.id), item2_request)

        # Refresh and check
        db.refresh(order)
        assert len(order.items) == 2
        assert sum(item.quantity for item in order.items) == 3

    def test_add_unavailable_product(self, db: Session, test_user: User, test_product: Product):
        """Test adding unavailable product."""
        # Create order
        request = OrderCreateRequest(order_type="take_away")
        order = OrderService.create_order(db, request, str(test_user.id))

        # Mark product unavailable
        test_product.is_available = False
        db.add(test_product)
        db.commit()

        # Try to add item
        item_request = OrderItemAddRequest(
            product_id=str(test_product.id),
            quantity=1,
        )

        with pytest.raises(ValueError, match="not available"):
            OrderService.add_item_to_order(db, str(order.id), item_request)

    def test_remove_item_from_order(self, db: Session, test_user: User, test_product: Product):
        """Test removing item from order."""
        # Create order and add item
        request = OrderCreateRequest(order_type="take_away")
        order = OrderService.create_order(db, request, str(test_user.id))

        item_request = OrderItemAddRequest(
            product_id=str(test_product.id),
            quantity=2,
        )
        item = OrderService.add_item_to_order(db, str(order.id), item_request)

        # Remove item
        OrderService.remove_item_from_order(db, str(order.id), str(item.id))

        # Check item is marked as cancelled
        db.refresh(item)
        assert item.is_cancelled == True


class TestOrderStatus:
    """Tests for order status management."""

    def test_hold_order(self, db: Session, test_user: User):
        """Test holding order."""
        request = OrderCreateRequest(order_type="take_away")
        order = OrderService.create_order(db, request, str(test_user.id))

        held_order = OrderService.hold_order(db, str(order.id))

        assert held_order.is_hold == True

    def test_resume_order(self, db: Session, test_user: User):
        """Test resuming held order."""
        request = OrderCreateRequest(order_type="take_away")
        order = OrderService.create_order(db, request, str(test_user.id))

        # Hold and resume
        OrderService.hold_order(db, str(order.id))
        resumed_order = OrderService.resume_order(db, str(order.id))

        assert resumed_order.is_hold == False

    def test_update_order_status(self, db: Session, test_user: User):
        """Test updating order status."""
        request = OrderCreateRequest(order_type="take_away")
        order = OrderService.create_order(db, request, str(test_user.id))

        updated_order = OrderService.update_order_status(db, str(order.id), "preparing")

        assert updated_order.status == "preparing"

    def test_invalid_status(self, db: Session, test_user: User):
        """Test invalid status."""
        request = OrderCreateRequest(order_type="take_away")
        order = OrderService.create_order(db, request, str(test_user.id))

        with pytest.raises(ValueError, match="Invalid status"):
            OrderService.update_order_status(db, str(order.id), "invalid")


class TestOrderCalculations:
    """Tests for order total calculations."""

    def test_order_total_calculation(self, db: Session, test_user: User, test_product: Product):
        """Test order total calculation with items and tax."""
        request = OrderCreateRequest(order_type="take_away")
        order = OrderService.create_order(db, request, str(test_user.id))

        # Add item
        item_request = OrderItemAddRequest(
            product_id=str(test_product.id),
            quantity=2,
        )
        OrderService.add_item_to_order(db, str(order.id), item_request)

        # Check totals
        db.refresh(order)
        expected_subtotal = Decimal("100.00")  # 50 * 2
        expected_tax = Decimal("5.00")  # 100 * 5%
        expected_total = Decimal("105.00")

        assert order.subtotal == expected_subtotal
        assert order.tax_amount == expected_tax
        assert order.total_amount == expected_total
