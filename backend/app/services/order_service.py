"""
Order management service layer.
Handles order creation, item management, and order lifecycle.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models import Order, OrderItem, Product, Table, Customer, User
from app.schemas.order import OrderCreateRequest, OrderItemAddRequest


class OrderService:
    """Service for managing orders."""

    @staticmethod
    def create_order(
        db: Session,
        request: OrderCreateRequest,
        cashier_id: str,
    ) -> Order:
        """
        Create a new order.

        Args:
            db: Database session
            request: Order creation request
            cashier_id: ID of cashier creating order

        Returns:
            Created Order object

        Raises:
            ValueError: If table or customer not found
        """
        # Validate table exists if dine_in
        if request.order_type == "dine_in" and request.table_id:
            table = db.query(Table).filter(Table.id == request.table_id).first()
            if not table:
                raise ValueError(f"Table {request.table_id} not found")
            # Update table status to occupied
            table.status = "occupied"

        # Validate customer exists if provided
        if request.customer_id:
            customer = db.query(Customer).filter(Customer.id == request.customer_id).first()
            if not customer:
                raise ValueError(f"Customer {request.customer_id} not found")

        # Validate cashier exists
        cashier = db.query(User).filter(User.id == cashier_id).first()
        if not cashier:
            raise ValueError(f"Cashier {cashier_id} not found")

        # Generate unique order number
        order_number = OrderService._generate_order_number(db)

        # Create order
        order = Order(
            id=uuid.uuid4(),
            order_number=order_number,
            order_type=request.order_type,
            table_id=request.table_id,
            customer_id=request.customer_id,
            cashier_id=cashier_id,
            status="pending",
            subtotal=Decimal("0.00"),
            tax_amount=Decimal("0.00"),
            discount_amount=Decimal("0.00"),
            total_amount=Decimal("0.00"),
            notes=request.notes,
            is_hold=False,
        )

        db.add(order)
        db.commit()
        db.refresh(order)
        return order

    @staticmethod
    def get_order(db: Session, order_id: str) -> Optional[Order]:
        """Get order by ID."""
        return db.query(Order).filter(Order.id == order_id).first()

    @staticmethod
    def list_orders(
        db: Session,
        status: Optional[str] = None,
        order_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[List[Order], int]:
        """
        List orders with optional filters.

        Returns:
            Tuple of (orders list, total count)
        """
        query = db.query(Order)

        if status:
            query = query.filter(Order.status == status)
        if order_type:
            query = query.filter(Order.order_type == order_type)

        # Exclude deleted orders
        query = query.filter(Order.cancelled_at.is_(None))

        total = query.count()
        orders = query.order_by(Order.created_at.desc()).limit(limit).offset(offset).all()

        return orders, total

    @staticmethod
    def add_item_to_order(
        db: Session,
        order_id: str,
        request: OrderItemAddRequest,
    ) -> OrderItem:
        """
        Add item to order and update totals.

        Args:
            db: Database session
            order_id: Order ID
            request: Item addition request

        Returns:
            Created OrderItem

        Raises:
            ValueError: If order or product not found
        """
        order = OrderService.get_order(db, order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")

        # Get product
        product = db.query(Product).filter(Product.id == request.product_id).first()
        if not product:
            raise ValueError(f"Product {request.product_id} not found")

        if not product.is_available:
            raise ValueError(f"Product {product.name} is not available")

        # Create order item
        item_subtotal = product.price * Decimal(request.quantity)
        item_tax = item_subtotal * (product.tax_percent / Decimal("100"))

        item = OrderItem(
            id=uuid.uuid4(),
            order_id=order_id,
            product_id=request.product_id,
            quantity=request.quantity,
            unit_price=product.price,
            tax_percent=product.tax_percent,
            item_total=item_subtotal + item_tax,
            special_notes=request.special_notes,
            is_cancelled=False,
        )

        db.add(item)

        # Update order totals
        OrderService._update_order_totals(db, order_id)

        db.commit()
        db.refresh(item)
        return item

    @staticmethod
    def remove_item_from_order(db: Session, order_id: str, item_id: str) -> None:
        """Remove item from order and update totals."""
        item = db.query(OrderItem).filter(
            OrderItem.id == item_id, OrderItem.order_id == order_id
        ).first()

        if not item:
            raise ValueError(f"Item {item_id} not found in order")

        item.is_cancelled = True
        db.add(item)

        # Update order totals
        OrderService._update_order_totals(db, order_id)

        db.commit()

    @staticmethod
    def update_order(db: Session, order_id: str, updates: dict) -> Order:
        """Update order details."""
        order = OrderService.get_order(db, order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")

        if "table_id" in updates:
            table = db.query(Table).filter(Table.id == updates["table_id"]).first()
            if not table:
                raise ValueError(f"Table {updates['table_id']} not found")
            order.table_id = updates["table_id"]

        if "customer_id" in updates:
            customer = db.query(Customer).filter(Customer.id == updates["customer_id"]).first()
            if not customer:
                raise ValueError(f"Customer {updates['customer_id']} not found")
            order.customer_id = updates["customer_id"]

        if "notes" in updates:
            order.notes = updates["notes"]

        order.updated_at = datetime.utcnow()
        db.add(order)
        db.commit()
        db.refresh(order)
        return order

    @staticmethod
    def hold_order(db: Session, order_id: str) -> Order:
        """Mark order as on hold."""
        order = OrderService.get_order(db, order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")

        order.is_hold = True
        order.updated_at = datetime.utcnow()
        db.add(order)
        db.commit()
        db.refresh(order)
        return order

    @staticmethod
    def resume_order(db: Session, order_id: str) -> Order:
        """Resume order from hold."""
        order = OrderService.get_order(db, order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")

        order.is_hold = False
        order.updated_at = datetime.utcnow()
        db.add(order)
        db.commit()
        db.refresh(order)
        return order

    @staticmethod
    def complete_order(db: Session, order_id: str) -> Order:
        """Mark order as completed."""
        order = OrderService.get_order(db, order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")

        if order.total_amount > Decimal("0.00"):
            # Check if order is fully paid
            total_paid = sum(payment.amount for payment in order.payments if payment.payment_status == "completed")
            if total_paid < order.total_amount:
                raise ValueError("Order not fully paid")

        order.status = "completed"
        order.completed_at = datetime.utcnow()
        order.updated_at = datetime.utcnow()

        # Update table status if dine_in
        if order.table_id:
            table = db.query(Table).filter(Table.id == order.table_id).first()
            if table:
                table.status = "available"
                db.add(table)

        db.add(order)
        db.commit()
        db.refresh(order)
        return order

    @staticmethod
    def cancel_order(db: Session, order_id: str) -> Order:
        """Cancel order."""
        order = OrderService.get_order(db, order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")

        if order.status == "completed":
            raise ValueError("Cannot cancel completed order")

        order.status = "cancelled"
        order.cancelled_at = datetime.utcnow()
        order.updated_at = datetime.utcnow()

        # Update table status if dine_in
        if order.table_id:
            table = db.query(Table).filter(Table.id == order.table_id).first()
            if table:
                table.status = "available"
                db.add(table)

        db.add(order)
        db.commit()
        db.refresh(order)
        return order

    @staticmethod
    def update_order_status(db: Session, order_id: str, status: str) -> Order:
        """Update order status."""
        valid_statuses = ["pending", "accepted", "preparing", "ready", "served", "completed", "cancelled"]
        if status not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of {valid_statuses}")

        order = OrderService.get_order(db, order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")

        order.status = status
        order.updated_at = datetime.utcnow()
        db.add(order)
        db.commit()
        db.refresh(order)
        return order

    @staticmethod
    def _update_order_totals(db: Session, order_id: str) -> None:
        """
        Recalculate and update order totals based on items.
        Called after adding/removing items.
        """
        order = OrderService.get_order(db, order_id)
        if not order:
            return

        items = db.query(OrderItem).filter(
            OrderItem.order_id == order_id,
            OrderItem.is_cancelled == False,
        ).all()

        subtotal = sum(item.unit_price * Decimal(item.quantity) for item in items)
        tax_amount = sum(item.item_total - (item.unit_price * Decimal(item.quantity)) for item in items)

        order.subtotal = subtotal
        order.tax_amount = tax_amount
        order.total_amount = subtotal + tax_amount - order.discount_amount

        db.add(order)
        db.commit()

    @staticmethod
    def _generate_order_number(db: Session) -> str:
        """Generate unique order number."""
        today_count = db.query(Order).filter(
            Order.created_at >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        ).count()
        return f"ORD-{datetime.utcnow().strftime('%Y%m%d')}-{today_count + 1:04d}"
