"""
Unit tests for payment service (Phase 2).
Tests for payment processing, split payments, and refunds.
"""

import pytest
from decimal import Decimal
from sqlalchemy.orm import Session

from app.models import User, Category, Product
from app.schemas.order import OrderCreateRequest, OrderItemAddRequest, PaymentRequest
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService


@pytest.fixture
def test_category(db: Session):
    """Create test category."""
    category = Category(
        name="Beverages",
    )
    db.add(category)
    db.commit()
    return category


@pytest.fixture
def test_product(db: Session, test_category):
    """Create test product."""
    product = Product(
        sku="TEST-001",
        name="Test Item",
        category_id=test_category.id,
        price=Decimal("100.00"),
        tax_percent=Decimal("5.00"),
    )
    db.add(product)
    db.commit()
    return product


@pytest.fixture
def test_order_with_balance(db: Session, test_user: User, test_product: Product):
    """Create order with items and balance due."""
    request = OrderCreateRequest(order_type="take_away")
    order = OrderService.create_order(db, request, str(test_user.id))

    # Add item
    item_request = OrderItemAddRequest(
        product_id=str(test_product.id),
        quantity=2,
    )
    OrderService.add_item_to_order(db, str(order.id), item_request)

    db.refresh(order)
    return order


class TestPaymentProcessing:
    """Tests for payment processing."""

    def test_process_cash_payment(self, db: Session, test_order_with_balance):
        """Test processing cash payment."""
        payment_request = PaymentRequest(
            amount=Decimal("210.00"),
            payment_method="cash",
        )

        payment = PaymentService.process_payment(db, str(test_order_with_balance.id), payment_request)

        assert payment.amount == Decimal("210.00")
        assert payment.payment_method == "cash"
        assert payment.payment_status == "completed"

    def test_process_upi_payment(self, db: Session, test_order_with_balance):
        """Test processing UPI payment."""
        payment_request = PaymentRequest(
            amount=Decimal("210.00"),
            payment_method="upi",
            transaction_id="UPI123456",
            reference_number="REF001",
        )

        payment = PaymentService.process_payment(db, str(test_order_with_balance.id), payment_request)

        assert payment.payment_method == "upi"
        assert payment.transaction_id == "UPI123456"
        assert payment.reference_number == "REF001"

    def test_process_partial_payment(self, db: Session, test_order_with_balance):
        """Test processing partial payment."""
        payment_request = PaymentRequest(
            amount=Decimal("100.00"),
            payment_method="cash",
        )

        payment = PaymentService.process_payment(db, str(test_order_with_balance.id), payment_request)

        assert payment.amount == Decimal("100.00")
        assert payment.payment_status == "completed"

    def test_payment_exceeds_balance(self, db: Session, test_order_with_balance):
        """Test payment exceeding order balance."""
        payment_request = PaymentRequest(
            amount=Decimal("500.00"),
            payment_method="cash",
        )

        with pytest.raises(ValueError, match="exceeds remaining balance"):
            PaymentService.process_payment(db, str(test_order_with_balance.id), payment_request)

    def test_invalid_payment_amount(self, db: Session, test_order_with_balance):
        """Test invalid payment amount."""
        payment_request = PaymentRequest.model_construct(
            amount=Decimal("-10.00"),
            payment_method="cash",
        )

        with pytest.raises(ValueError, match="greater than 0"):
            PaymentService.process_payment(db, str(test_order_with_balance.id), payment_request)

    def test_full_payment_marks_order_served(self, db: Session, test_order_with_balance):
        """Test that full payment marks order as served."""
        payment_request = PaymentRequest(
            amount=Decimal("210.00"),
            payment_method="cash",
        )

        PaymentService.process_payment(db, str(test_order_with_balance.id), payment_request)

        db.refresh(test_order_with_balance)
        assert test_order_with_balance.status == "served"


class TestSplitPayment:
    """Tests for split payment processing."""

    def test_split_payment_two_methods(self, db: Session, test_order_with_balance):
        """Test split payment with two methods."""
        payments = [
            PaymentRequest(
                amount=Decimal("100.00"),
                payment_method="cash",
            ),
            PaymentRequest(
                amount=Decimal("110.00"),
                payment_method="upi",
                transaction_id="UPI123",
            ),
        ]

        payment_list = PaymentService.process_split_payment(db, str(test_order_with_balance.id), payments)

        assert len(payment_list) == 2
        assert payment_list[0].amount == Decimal("100.00")
        assert payment_list[1].amount == Decimal("110.00")

    def test_split_payment_unequal_total(self, db: Session, test_order_with_balance):
        """Test split payment with unequal total."""
        payments = [
            PaymentRequest(
                amount=Decimal("100.00"),
                payment_method="cash",
            ),
            PaymentRequest(
                amount=Decimal("50.00"),
                payment_method="upi",
            ),
        ]

        with pytest.raises(ValueError, match="must equal order total"):
            PaymentService.process_split_payment(db, str(test_order_with_balance.id), payments)


class TestPaymentRetrieval:
    """Tests for retrieving payment information."""

    def test_get_total_paid(self, db: Session, test_order_with_balance):
        """Test getting total paid for order."""
        # Process payment
        payment_request = PaymentRequest(
            amount=Decimal("100.00"),
            payment_method="cash",
        )
        PaymentService.process_payment(db, str(test_order_with_balance.id), payment_request)

        total_paid = PaymentService.get_total_paid(db, str(test_order_with_balance.id))

        assert total_paid == Decimal("100.00")

    def test_get_multiple_payment_total(self, db: Session, test_order_with_balance):
        """Test getting total from multiple payments."""
        # First payment
        PaymentService.process_payment(
            db,
            str(test_order_with_balance.id),
            PaymentRequest(amount=Decimal("100.00"), payment_method="cash"),
        )

        # Second payment
        PaymentService.process_payment(
            db,
            str(test_order_with_balance.id),
            PaymentRequest(amount=Decimal("110.00"), payment_method="upi"),
        )

        total_paid = PaymentService.get_total_paid(db, str(test_order_with_balance.id))

        assert total_paid == Decimal("210.00")

    def test_get_remaining_balance(self, db: Session, test_order_with_balance):
        """Test getting remaining balance."""
        # Process partial payment
        PaymentService.process_payment(
            db,
            str(test_order_with_balance.id),
            PaymentRequest(amount=Decimal("100.00"), payment_method="cash"),
        )

        remaining = PaymentService.get_remaining_balance(db, str(test_order_with_balance.id))

        assert remaining == Decimal("110.00")

    def test_validate_payment_amount(self, db: Session, test_order_with_balance):
        """Test validating payment amount."""
        # Valid amount
        assert PaymentService.validate_payment_amount(
            db,
            str(test_order_with_balance.id),
            Decimal("100.00"),
        )

        # Invalid amount (exceeds balance)
        assert not PaymentService.validate_payment_amount(
            db,
            str(test_order_with_balance.id),
            Decimal("500.00"),
        )

        # Invalid amount (negative)
        assert not PaymentService.validate_payment_amount(
            db,
            str(test_order_with_balance.id),
            Decimal("-50.00"),
        )

    def test_get_payment_summary(self, db: Session, test_order_with_balance):
        """Test getting payment summary."""
        # Process payment
        PaymentService.process_payment(
            db,
            str(test_order_with_balance.id),
            PaymentRequest(amount=Decimal("100.00"), payment_method="cash"),
        )

        summary = PaymentService.get_payment_summary(db, str(test_order_with_balance.id))

        assert summary["order_number"] == test_order_with_balance.order_number
        assert summary["total_amount"] == 210.00
        assert summary["total_paid"] == 100.00
        assert summary["remaining_amount"] == 110.00
        assert summary["is_fully_paid"] == False
        assert len(summary["payments"]) == 1


class TestRefunds:
    """Tests for refund processing."""

    def test_full_refund(self, db: Session, test_order_with_balance):
        """Test full refund."""
        # Process payment
        payment_request = PaymentRequest(
            amount=Decimal("210.00"),
            payment_method="cash",
            reference_number="PAY001",
        )
        payment = PaymentService.process_payment(db, str(test_order_with_balance.id), payment_request)

        # Process refund
        refund = PaymentService.refund_payment(db, str(payment.id))

        assert refund.amount == Decimal("-210.00")
        assert refund.payment_status == "refunded"

    def test_partial_refund(self, db: Session, test_order_with_balance):
        """Test partial refund."""
        # Process payment
        payment_request = PaymentRequest(
            amount=Decimal("210.00"),
            payment_method="cash",
        )
        payment = PaymentService.process_payment(db, str(test_order_with_balance.id), payment_request)

        # Process partial refund
        refund = PaymentService.refund_payment(
            db,
            str(payment.id),
            amount=Decimal("50.00"),
        )

        assert refund.amount == Decimal("-50.00")
        assert refund.payment_status == "refunded"

    def test_refund_exceeds_payment(self, db: Session, test_order_with_balance):
        """Test refund exceeding payment amount."""
        # Process payment
        payment_request = PaymentRequest(
            amount=Decimal("100.00"),
            payment_method="cash",
        )
        payment = PaymentService.process_payment(db, str(test_order_with_balance.id), payment_request)

        # Try to refund more
        with pytest.raises(ValueError, match="cannot exceed payment"):
            PaymentService.refund_payment(
                db,
                str(payment.id),
                amount=Decimal("200.00"),
            )

    def test_cannot_refund_already_refunded(self, db: Session, test_order_with_balance):
        """Test refunding already refunded payment."""
        # Process payment and refund
        payment_request = PaymentRequest(
            amount=Decimal("100.00"),
            payment_method="cash",
        )
        payment = PaymentService.process_payment(db, str(test_order_with_balance.id), payment_request)
        PaymentService.refund_payment(db, str(payment.id))

        # Try to refund again
        with pytest.raises(ValueError, match="already refunded"):
            PaymentService.refund_payment(db, str(payment.id))
