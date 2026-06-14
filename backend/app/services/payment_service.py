"""
Payment processing service layer.
Handles payment transactions, reconciliation, and payment status tracking.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models import Payment, Order
from app.schemas.order import PaymentRequest
from app.services.order_service import OrderService
from app.services.billing_service import BillingService


class PaymentService:
    """Service for processing payments."""

    @staticmethod
    def process_payment(
        db: Session,
        order_id: str,
        request: PaymentRequest,
    ) -> Payment:
        """
        Process payment for order.

        Args:
            db: Database session
            order_id: Order ID
            request: Payment request

        Returns:
            Created Payment object

        Raises:
            ValueError: If order not found or payment invalid
        """
        order = OrderService.get_order(db, order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")

        # Validate payment amount
        if request.amount <= 0:
            raise ValueError("Payment amount must be greater than 0")

        # Get current billing
        billing = BillingService.calculate_order_totals(db, order_id)
        remaining_amount = billing["total_amount"] - PaymentService.get_total_paid(db, order_id)

        if request.amount > remaining_amount:
            raise ValueError(
                f"Payment amount ({request.amount}) exceeds remaining balance ({remaining_amount})"
            )

        # Create payment
        payment = Payment(
            id=uuid.uuid4(),
            order_id=order_id,
            amount=request.amount,
            payment_method=request.payment_method,
            transaction_id=request.transaction_id,
            reference_number=request.reference_number,
            payment_status="completed",
        )

        db.add(payment)

        # Update order status if fully paid
        total_paid = PaymentService.get_total_paid(db, order_id) + request.amount
        if total_paid >= billing["total_amount"]:
            order.status = "served"
            db.add(order)

        db.commit()
        db.refresh(payment)

        return payment

    @staticmethod
    def process_split_payment(
        db: Session,
        order_id: str,
        payments: List[PaymentRequest],
    ) -> List[Payment]:
        """
        Process split payment with multiple payment methods.

        Args:
            db: Database session
            order_id: Order ID
            payments: List of payment requests

        Returns:
            List of created Payment objects
        """
        order = OrderService.get_order(db, order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")

        # Get billing
        billing = BillingService.calculate_order_totals(db, order_id)
        remaining_amount = billing["total_amount"]

        # Validate total payment amount
        total_payment = sum(p.amount for p in payments)
        if total_payment != remaining_amount:
            raise ValueError(
                f"Total split payment ({total_payment}) must equal order total ({remaining_amount})"
            )

        # Process each payment
        created_payments = []
        for payment_request in payments:
            payment = Payment(
                id=uuid.uuid4(),
                order_id=order_id,
                amount=payment_request.amount,
                payment_method=payment_request.payment_method,
                transaction_id=payment_request.transaction_id,
                reference_number=payment_request.reference_number,
                payment_status="completed",
            )
            db.add(payment)
            created_payments.append(payment)

        # Mark order as served (fully paid)
        order.status = "served"
        db.add(order)

        db.commit()

        for payment in created_payments:
            db.refresh(payment)

        return created_payments

    @staticmethod
    def refund_payment(db: Session, payment_id: str, amount: Optional[Decimal] = None) -> Payment:
        """
        Refund payment (full or partial).

        Args:
            db: Database session
            payment_id: Payment ID
            amount: Refund amount (None for full refund)

        Returns:
            Updated Payment object
        """
        payment = db.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            raise ValueError(f"Payment {payment_id} not found")

        if payment.payment_status == "refunded":
            raise ValueError("Payment already refunded")

        refund_amount = amount or payment.amount

        if refund_amount > payment.amount:
            raise ValueError("Refund amount cannot exceed payment amount")

        # Create refund payment record
        refund = Payment(
            id=uuid.uuid4(),
            order_id=payment.order_id,
            amount=-refund_amount,  # Negative for refund
            payment_method=payment.payment_method,
            transaction_id=payment.transaction_id,
            reference_number=f"REFUND-{payment.reference_number}" if payment.reference_number else "REFUND",
            payment_status="refunded",
        )

        db.add(refund)

        # Update original payment status
        if refund_amount == payment.amount:
            payment.payment_status = "refunded"
        else:
            payment.payment_status = "partially_refunded"

        db.add(payment)
        db.commit()
        db.refresh(refund)

        return refund

    @staticmethod
    def get_payment(db: Session, payment_id: str) -> Optional[Payment]:
        """Get payment by ID."""
        return db.query(Payment).filter(Payment.id == payment_id).first()

    @staticmethod
    def get_order_payments(db: Session, order_id: str) -> List[Payment]:
        """Get all payments for an order."""
        return (
            db.query(Payment)
            .filter(Payment.order_id == order_id)
            .order_by(Payment.created_at.desc())
            .all()
        )

    @staticmethod
    def get_total_paid(db: Session, order_id: str) -> Decimal:
        """Get total paid amount for order."""
        payments = PaymentService.get_order_payments(db, order_id)
        return sum(
            (p.amount for p in payments if p.payment_status in ["completed", "partially_refunded"]),
            Decimal("0.00"),
        )

    @staticmethod
    def get_remaining_balance(db: Session, order_id: str) -> Decimal:
        """Get remaining payment balance for order."""
        billing = BillingService.calculate_order_totals(db, order_id)
        paid = PaymentService.get_total_paid(db, order_id)
        return billing["total_amount"] - paid

    @staticmethod
    def validate_payment_amount(
        db: Session,
        order_id: str,
        amount: Decimal,
    ) -> bool:
        """Validate payment amount is acceptable."""
        remaining = PaymentService.get_remaining_balance(db, order_id)
        return amount > 0 and amount <= remaining

    @staticmethod
    def get_payment_summary(db: Session, order_id: str) -> dict:
        """Get complete payment summary for order."""
        order = OrderService.get_order(db, order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")

        billing = BillingService.calculate_order_totals(db, order_id)
        payments = PaymentService.get_order_payments(db, order_id)
        total_paid = PaymentService.get_total_paid(db, order_id)
        remaining = billing["total_amount"] - total_paid

        return {
            "order_id": order_id,
            "order_number": order.order_number,
            "total_amount": float(billing["total_amount"]),
            "total_paid": float(total_paid),
            "remaining_amount": float(remaining),
            "is_fully_paid": remaining <= 0,
            "payments": [
                {
                    "id": p.id,
                    "amount": float(p.amount),
                    "method": p.payment_method,
                    "status": p.payment_status,
                    "reference": p.reference_number,
                    "created_at": p.created_at.isoformat(),
                }
                for p in payments
            ],
        }
