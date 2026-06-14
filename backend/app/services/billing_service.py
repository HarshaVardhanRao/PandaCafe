"""
Billing calculation service layer.
Handles order billing calculations, tax, discounts, and bill generation.
"""

from decimal import Decimal
from typing import Dict, Optional

from sqlalchemy.orm import Session

from app.models import Order, OrderItem, Discount
from app.services.order_service import OrderService


class BillingService:
    """Service for billing calculations."""

    @staticmethod
    def calculate_order_totals(db: Session, order_id: str) -> Dict:
        """
        Calculate complete billing for an order.

        Returns dict with:
        - subtotal: Sum of all item prices
        - tax_amount: Total tax
        - discount_amount: Total discount
        - total_amount: Final amount due
        """
        order = OrderService.get_order(db, order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")

        # Get active items
        items = db.query(OrderItem).filter(
            OrderItem.order_id == order_id,
            OrderItem.is_cancelled == False,
        ).all()

        # Calculate subtotal and tax
        subtotal = Decimal("0.00")
        tax_amount = Decimal("0.00")

        for item in items:
            item_subtotal = item.unit_price * Decimal(item.quantity)
            item_tax = item_subtotal * (item.tax_percent / Decimal("100"))

            subtotal += item_subtotal
            tax_amount += item_tax

        # Get discount amount from order
        discount_amount = order.discount_amount

        # Final total
        total_amount = subtotal + tax_amount - discount_amount

        return {
            "subtotal": subtotal,
            "tax_amount": tax_amount,
            "tax_percentage": BillingService._calculate_effective_tax_rate(items),
            "discount_amount": discount_amount,
            "total_amount": max(total_amount, Decimal("0.00")),  # Ensure non-negative
        }

    @staticmethod
    def apply_discount(
        db: Session,
        order_id: str,
        discount_amount: Optional[Decimal] = None,
        discount_percentage: Optional[Decimal] = None,
        discount_code: Optional[str] = None,
    ) -> Dict:
        """
        Apply discount to order.

        Args:
            db: Database session
            order_id: Order ID
            discount_amount: Fixed discount amount
            discount_percentage: Discount percentage
            discount_code: Discount code for lookup

        Returns:
            Updated billing calculation
        """
        order = OrderService.get_order(db, order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")

        # Calculate discount amount
        calculated_discount = Decimal("0.00")

        if discount_code:
            # Lookup discount code
            discount = db.query(Discount).filter(
                Discount.code == discount_code,
                Discount.is_active == True,
            ).first()

            if not discount:
                raise ValueError(f"Invalid discount code: {discount_code}")

            if discount_percentage:
                calculated_discount = order.subtotal * (discount.percentage / Decimal("100"))
            else:
                calculated_discount = Decimal(discount.fixed_amount or 0)

        elif discount_amount:
            calculated_discount = discount_amount

        elif discount_percentage:
            calculated_discount = order.subtotal * (discount_percentage / Decimal("100"))

        # Ensure discount doesn't exceed order total
        calculated_discount = min(calculated_discount, order.subtotal + order.tax_amount)

        # Apply discount
        order.discount_amount = calculated_discount
        db.add(order)
        db.commit()

        # Return updated billing
        return BillingService.calculate_order_totals(db, order_id)

    @staticmethod
    def remove_discount(db: Session, order_id: str) -> Dict:
        """Remove discount from order."""
        order = OrderService.get_order(db, order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")

        order.discount_amount = Decimal("0.00")
        db.add(order)
        db.commit()

        return BillingService.calculate_order_totals(db, order_id)

    @staticmethod
    def calculate_item_total(unit_price: Decimal, quantity: int, tax_percent: Decimal) -> Decimal:
        """Calculate total for a single item including tax."""
        subtotal = unit_price * Decimal(quantity)
        tax = subtotal * (tax_percent / Decimal("100"))
        return subtotal + tax

    @staticmethod
    def generate_bill_summary(db: Session, order_id: str) -> Dict:
        """
        Generate complete bill summary for printing/display.

        Returns formatted bill data with items and totals.
        """
        order = OrderService.get_order(db, order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")

        items = db.query(OrderItem).filter(
            OrderItem.order_id == order_id,
            OrderItem.is_cancelled == False,
        ).all()

        billing = BillingService.calculate_order_totals(db, order_id)

        # Get related data
        table_number = None
        if order.table_id:
            from app.models import Table
            table = db.query(Table).filter(Table.id == order.table_id).first()
            table_number = table.table_number if table else None

        customer_name = None
        if order.customer_id:
            from app.models import Customer
            customer = db.query(Customer).filter(Customer.id == order.customer_id).first()
            customer_name = customer.name if customer else None

        # Format items
        formatted_items = []
        for item in items:
            from app.models import Product
            product = db.query(Product).filter(Product.id == item.product_id).first()

            formatted_items.append({
                "product_name": product.name if product else "Unknown",
                "quantity": item.quantity,
                "unit_price": float(item.unit_price),
                "item_total": float(item.item_total),
                "special_notes": item.special_notes,
            })

        return {
            "order_number": order.order_number,
            "order_type": order.order_type,
            "status": order.status,
            "table_number": table_number,
            "customer_name": customer_name,
            "items": formatted_items,
            "items_count": len(formatted_items),
            "billing": {
                "subtotal": float(billing["subtotal"]),
                "tax_amount": float(billing["tax_amount"]),
                "tax_percentage": float(billing["tax_percentage"]),
                "discount_amount": float(billing["discount_amount"]),
                "total_amount": float(billing["total_amount"]),
            },
            "created_at": order.created_at.isoformat(),
            "notes": order.notes,
        }

    @staticmethod
    def split_bill(db: Session, order_id: str, split_count: int) -> list[Dict]:
        """
        Calculate split bill for multiple payers.

        Args:
            order_id: Order ID
            split_count: Number of ways to split

        Returns:
            List of bill calculations, one per person
        """
        if split_count < 2:
            raise ValueError("Split count must be at least 2")

        billing = BillingService.calculate_order_totals(db, order_id)
        total_amount = billing["total_amount"]

        # Divide equally
        per_person = total_amount / Decimal(split_count)

        bills = []
        for i in range(split_count):
            bills.append({
                "person": i + 1,
                "amount": float(per_person),
                "percentage": float(Decimal("100") / Decimal(split_count)),
            })

        # Adjust last person to account for rounding
        if split_count > 1:
            amount_covered = sum(Decimal(str(b["amount"])) for b in bills[:-1])
            bills[-1]["amount"] = float(total_amount - amount_covered)

        return bills

    @staticmethod
    def _calculate_effective_tax_rate(items: list) -> Decimal:
        """Calculate effective tax rate across all items."""
        if not items:
            return Decimal("0.00")

        total_tax = Decimal("0.00")
        total_subtotal = Decimal("0.00")

        for item in items:
            item_subtotal = item.unit_price * Decimal(item.quantity)
            item_tax = item_subtotal * (item.tax_percent / Decimal("100"))

            total_tax += item_tax
            total_subtotal += item_subtotal

        if total_subtotal == 0:
            return Decimal("0.00")

        return (total_tax / total_subtotal) * Decimal("100")
