"""
Unit tests for billing service (Phase 2).
Tests for billing calculations, discounts, and bill generation.
"""

import pytest
from decimal import Decimal
from sqlalchemy.orm import Session

from app.models import Order, User, Category, Product
from app.schemas.order import OrderCreateRequest, OrderItemAddRequest
from app.services.order_service import OrderService
from app.services.billing_service import BillingService


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
        price=Decimal("100.00"),
        tax_percent=Decimal("5.00"),
        is_available=True,
    )
    db.add(product)
    db.commit()
    return product


@pytest.fixture
def test_order_with_items(db: Session, test_user: User, test_product: Product):
    """Create order with items."""
    request = OrderCreateRequest(order_type="take_away")
    order = OrderService.create_order(db, request, str(test_user.id))

    # Add items
    for qty in [1, 2]:
        item_request = OrderItemAddRequest(
            product_id=str(test_product.id),
            quantity=qty,
        )
        OrderService.add_item_to_order(db, str(order.id), item_request)

    db.refresh(order)
    return order


class TestBillingCalculations:
    """Tests for billing calculations."""

    def test_calculate_order_totals(self, db: Session, test_order_with_items):
        """Test calculating order totals."""
        billing = BillingService.calculate_order_totals(db, str(test_order_with_items.id))

        assert billing["subtotal"] == Decimal("300.00")  # (1 + 2) * 100
        assert billing["tax_amount"] == Decimal("15.00")  # 300 * 5%
        assert billing["total_amount"] == Decimal("315.00")

    def test_effective_tax_rate(self, db: Session, test_order_with_items):
        """Test effective tax rate calculation."""
        billing = BillingService.calculate_order_totals(db, str(test_order_with_items.id))

        assert billing["tax_percentage"] == Decimal("5.00")

    def test_calculate_totals_with_mixed_tax_products(self, db: Session, test_user: User, test_category):
        """Test calculating totals with products having different tax rates."""
        # Create products with different tax rates
        product1 = Product(
            sku="ITEM-001",
            name="Item 1",
            category_id=test_category.id,
            price=Decimal("100.00"),
            tax_percent=Decimal("5.00"),
        )
        product2 = Product(
            sku="ITEM-002",
            name="Item 2",
            category_id=test_category.id,
            price=Decimal("100.00"),
            tax_percent=Decimal("10.00"),
        )
        db.add_all([product1, product2])
        db.commit()

        # Create order with both products
        request = OrderCreateRequest(order_type="take_away")
        order = OrderService.create_order(db, request, str(test_user.id))

        OrderService.add_item_to_order(
            db,
            str(order.id),
            OrderItemAddRequest(product_id=str(product1.id), quantity=1),
        )
        OrderService.add_item_to_order(
            db,
            str(order.id),
            OrderItemAddRequest(product_id=str(product2.id), quantity=1),
        )

        billing = BillingService.calculate_order_totals(db, str(order.id))

        assert billing["subtotal"] == Decimal("200.00")
        assert billing["tax_amount"] == Decimal("15.00")  # 5% on 100 + 10% on 100
        assert billing["total_amount"] == Decimal("215.00")

    def test_calculate_empty_order_totals(self, db: Session, test_user: User):
        """Test calculating totals for empty order."""
        request = OrderCreateRequest(order_type="take_away")
        order = OrderService.create_order(db, request, str(test_user.id))

        billing = BillingService.calculate_order_totals(db, str(order.id))

        assert billing["subtotal"] == Decimal("0.00")
        assert billing["tax_amount"] == Decimal("0.00")
        assert billing["total_amount"] == Decimal("0.00")


class TestDiscounts:
    """Tests for discount application."""

    def test_apply_fixed_discount(self, db: Session, test_order_with_items):
        """Test applying fixed discount."""
        billing = BillingService.apply_discount(
            db,
            str(test_order_with_items.id),
            discount_amount=Decimal("50.00"),
        )

        assert billing["discount_amount"] == Decimal("50.00")
        assert billing["total_amount"] == Decimal("265.00")

    def test_apply_percentage_discount(self, db: Session, test_order_with_items):
        """Test applying percentage discount."""
        billing = BillingService.apply_discount(
            db,
            str(test_order_with_items.id),
            discount_percentage=Decimal("10.00"),
        )

        # 10% of 300 = 30
        assert billing["discount_amount"] == Decimal("30.00")
        assert billing["total_amount"] == Decimal("285.00")

    def test_discount_cannot_exceed_total(self, db: Session, test_order_with_items):
        """Test that discount cannot exceed order total."""
        original_total = Decimal("315.00")

        # Try to apply discount larger than total
        billing = BillingService.apply_discount(
            db,
            str(test_order_with_items.id),
            discount_amount=Decimal("500.00"),
        )

        # Discount should be capped at order total
        assert billing["discount_amount"] == original_total
        assert billing["total_amount"] == Decimal("0.00")

    def test_remove_discount(self, db: Session, test_order_with_items):
        """Test removing discount."""
        # Apply discount
        BillingService.apply_discount(
            db,
            str(test_order_with_items.id),
            discount_amount=Decimal("50.00"),
        )

        # Remove discount
        billing = BillingService.remove_discount(db, str(test_order_with_items.id))

        assert billing["discount_amount"] == Decimal("0.00")
        assert billing["total_amount"] == Decimal("315.00")


class TestBillGeneration:
    """Tests for bill generation and summary."""

    def test_generate_bill_summary(self, db: Session, test_order_with_items):
        """Test generating bill summary."""
        summary = BillingService.generate_bill_summary(db, str(test_order_with_items.id))

        assert summary["order_number"] == test_order_with_items.order_number
        assert summary["order_type"] == "take_away"
        assert summary["items_count"] == 2
        assert len(summary["items"]) == 2
        assert summary["billing"]["subtotal"] == 300.00
        assert summary["billing"]["tax_amount"] == 15.00
        assert summary["billing"]["total_amount"] == 315.00

    def test_bill_summary_includes_product_names(self, db: Session, test_order_with_items, test_product):
        """Test that bill summary includes product names."""
        summary = BillingService.generate_bill_summary(db, str(test_order_with_items.id))

        product_names = [item["product_name"] for item in summary["items"]]
        assert test_product.name in product_names


class TestSplitBill:
    """Tests for split bill calculation."""

    def test_split_bill_equally(self, db: Session, test_order_with_items):
        """Test splitting bill equally."""
        split_bills = BillingService.split_bill(db, str(test_order_with_items.id), 3)

        assert len(split_bills) == 3
        total = sum(Decimal(str(b["amount"])) for b in split_bills)
        assert total == Decimal("315.00")

    def test_split_bill_two_ways(self, db: Session, test_order_with_items):
        """Test splitting bill two ways."""
        split_bills = BillingService.split_bill(db, str(test_order_with_items.id), 2)

        assert len(split_bills) == 2
        # Each person pays half
        assert Decimal(str(split_bills[0]["amount"])) == Decimal("157.50")

    def test_split_bill_invalid_count(self, db: Session, test_order_with_items):
        """Test split bill with invalid count."""
        with pytest.raises(ValueError, match="at least 2"):
            BillingService.split_bill(db, str(test_order_with_items.id), 1)


class TestItemTotalCalculation:
    """Tests for individual item total calculation."""

    def test_calculate_item_total_with_tax(self):
        """Test calculating single item total with tax."""
        total = BillingService.calculate_item_total(
            unit_price=Decimal("100.00"),
            quantity=2,
            tax_percent=Decimal("5.00"),
        )

        expected = Decimal("210.00")  # (100 * 2) + (100 * 2 * 0.05)
        assert total == expected
