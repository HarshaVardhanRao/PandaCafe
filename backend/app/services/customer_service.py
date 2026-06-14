"""
Customer and Loyalty service layer.
"""

import logging
import re
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.models import Customer, Order, User
from app.schemas.customer import CustomerCreate, CustomerUpdate
from app.services.order_service import OrderService

logger = logging.getLogger(__name__)


class CustomerService:
    """Service for managing customers and loyalty points."""

    @staticmethod
    def create_customer(db: Session, request: CustomerCreate) -> Customer:
        """Create a new customer profile."""
        # Check if phone number already exists
        existing = db.query(Customer).filter(Customer.phone_number == request.phone_number).first()
        if existing:
            raise ValueError(f"Customer with phone number '{request.phone_number}' already exists")

        # Check if email exists if provided
        if request.email:
            existing_email = db.query(Customer).filter(Customer.email == request.email).first()
            if existing_email:
                raise ValueError(f"Customer with email '{request.email}' already exists")

        customer = Customer(
            id=uuid4(),
            name=request.name,
            phone_number=request.phone_number,
            email=request.email,
            loyalty_points=0,
            total_spent=Decimal("0.00"),
            visit_count=0,
            last_visit=None,
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)
        logger.info(f"Customer created: {customer.id}")
        return customer

    @staticmethod
    def get_customer(db: Session, customer_id: UUID) -> Optional[Customer]:
        """Get customer by ID."""
        return db.query(Customer).filter(Customer.id == customer_id, Customer.deleted_at.is_(None)).first()

    @staticmethod
    def get_customer_by_phone(db: Session, phone_number: str) -> Optional[Customer]:
        """Get customer by phone number."""
        return db.query(Customer).filter(
            Customer.phone_number == phone_number,
            Customer.deleted_at.is_(None)
        ).first()

    @staticmethod
    def list_customers(db: Session, skip: int = 0, limit: int = 100) -> List[Customer]:
        """List customers."""
        return db.query(Customer).filter(Customer.deleted_at.is_(None)).order_by(Customer.name).offset(skip).limit(limit).all()

    @staticmethod
    def update_customer(
        db: Session, customer_id: UUID, request: CustomerUpdate
    ) -> Optional[Customer]:
        """Update customer details."""
        customer = CustomerService.get_customer(db, customer_id)
        if not customer:
            return None

        # Validate unique phone if changing
        if request.phone_number and request.phone_number != customer.phone_number:
            existing = db.query(Customer).filter(
                Customer.phone_number == request.phone_number,
                Customer.id != customer_id
            ).first()
            if existing:
                raise ValueError(f"Customer with phone number '{request.phone_number}' already exists")

        # Validate unique email if changing
        if request.email and request.email != customer.email:
            existing_email = db.query(Customer).filter(
                Customer.email == request.email,
                Customer.id != customer_id
            ).first()
            if existing_email:
                raise ValueError(f"Customer with email '{request.email}' already exists")

        update_data = request.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(customer, field, value)

        db.commit()
        db.refresh(customer)
        logger.info(f"Customer updated: {customer_id}")
        return customer

    @staticmethod
    def get_purchase_history(db: Session, customer_id: UUID) -> dict:
        """Get purchase history for customer."""
        customer = CustomerService.get_customer(db, customer_id)
        if not customer:
            raise ValueError(f"Customer {customer_id} not found")

        orders = db.query(Order).filter(
            Order.customer_id == customer_id,
            Order.cancelled_at.is_(None)
        ).order_by(Order.created_at.desc()).all()

        return {
            "customer": customer,
            "orders": orders
        }

    @staticmethod
    def credit_loyalty_points(db: Session, order: Order) -> None:
        """Credit loyalty points based on order total spent."""
        if not order.customer_id:
            return

        customer = CustomerService.get_customer(db, order.customer_id)
        if not customer:
            return

        # 1 point per 10 currency units spent
        points_earned = int(order.total_amount / Decimal("10.00"))

        customer.loyalty_points += points_earned
        customer.total_spent += order.total_amount
        customer.visit_count += 1
        customer.last_visit = datetime.utcnow()

        db.add(customer)
        logger.info(f"Credited {points_earned} points to customer {customer.id} for order {order.order_number}")

    @staticmethod
    def revert_loyalty_points(db: Session, order: Order) -> None:
        """Deduct credited loyalty points if order is cancelled."""
        if not order.customer_id:
            return

        customer = CustomerService.get_customer(db, order.customer_id)
        if not customer:
            return

        points_to_revert = int(order.total_amount / Decimal("10.00"))

        customer.loyalty_points = max(0, customer.loyalty_points - points_to_revert)
        customer.total_spent = max(Decimal("0.00"), customer.total_spent - order.total_amount)
        customer.visit_count = max(0, customer.visit_count - 1)

        db.add(customer)
        logger.info(f"Reverted {points_to_revert} points from customer {customer.id} due to order {order.order_number} cancellation")

    @staticmethod
    def redeem_loyalty_points(db: Session, order_id: UUID, points_to_redeem: int) -> None:
        """Redeem points on a pending order as discount."""
        order = OrderService.get_order(db, str(order_id))
        if not order:
            raise ValueError(f"Order {order_id} not found")

        if order.status not in ["pending", "accepted", "preparing", "ready"]:
            raise ValueError("Can only redeem points on active/uncompleted orders")

        if not order.customer_id:
            raise ValueError("No customer linked to this order")

        customer = CustomerService.get_customer(db, order.customer_id)
        if not customer:
            raise ValueError("Customer not found")

        if customer.loyalty_points < points_to_redeem:
            raise ValueError(f"Insufficient points. Customer has {customer.loyalty_points}, requested {points_to_redeem}")

        # Check discount limit (points = discount in currency units)
        discount_value = Decimal(points_to_redeem)
        # Recalculate remaining balance
        # Current totals
        from app.services.billing_service import BillingService
        billing = BillingService.calculate_order_totals(db, str(order_id))
        remaining = billing["total_amount"] + order.discount_amount  # original total before current discount

        if discount_value > remaining:
            raise ValueError(f"Redemption discount ({discount_value}) exceeds order total ({remaining})")

        # Apply discount
        order.discount_amount = discount_value
        # Add metadata tag to notes to track redeemed points for refunds
        # Strip existing tag if present first
        clean_notes = re.sub(r"\s*\[REDEEMED_POINTS:\s*\d+\]", "", order.notes or "")
        order.notes = f"{clean_notes} [REDEEMED_POINTS: {points_to_redeem}]".strip()

        db.add(order)
        db.flush()

        # Update totals
        OrderService._update_order_totals(db, str(order_id))

        # Deduct from customer
        customer.loyalty_points -= points_to_redeem
        db.add(customer)
        db.commit()

        logger.info(f"Redeemed {points_to_redeem} points for customer {customer.id} on order {order.order_number}")

    @staticmethod
    def refund_redeemed_points(db: Session, order: Order) -> None:
        """Refund any loyalty points redeemed on a cancelled order."""
        if not order.customer_id or not order.notes:
            return

        customer = CustomerService.get_customer(db, order.customer_id)
        if not customer:
            return

        # Parse notes to extract redeemed points
        match = re.search(r"\[REDEEMED_POINTS:\s*(\d+)\]", order.notes)
        if match:
            points_to_refund = int(match.group(1))
            customer.loyalty_points += points_to_refund
            db.add(customer)
            logger.info(f"Refunded {points_to_refund} redeemed points to customer {customer.id} due to order cancellation")
