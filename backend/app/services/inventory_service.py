"""
Inventory, supplier, transaction, and recipe service layer.
"""

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.models import (
    Customer,
    InventoryItem,
    InventoryTransaction,
    Notification,
    Order,
    OrderItem,
    Product,
    Recipe,
    RecipeIngredient,
    Supplier,
)
from app.schemas.inventory import (
    InventoryItemCreate,
    InventoryItemUpdate,
    InventoryTransactionCreate,
    RecipeCreate,
    RecipeUpdate,
    SupplierCreate,
    SupplierUpdate,
)

logger = logging.getLogger(__name__)


class SupplierService:
    """Service for managing suppliers."""

    @staticmethod
    def create_supplier(db: Session, request: SupplierCreate) -> Supplier:
        """Create a new supplier."""
        # Check if supplier already exists by name
        existing = db.query(Supplier).filter(Supplier.name == request.name).first()
        if existing:
            raise ValueError(f"Supplier '{request.name}' already exists")

        supplier = Supplier(
            id=uuid4(),
            name=request.name,
            contact_person=request.contact_person,
            email=request.email,
            phone_number=request.phone_number,
            address=request.address,
            city=request.city,
            payment_terms=request.payment_terms,
            is_active=True,
        )
        db.add(supplier)
        db.commit()
        db.refresh(supplier)
        logger.info(f"Supplier created: {supplier.id}")
        return supplier

    @staticmethod
    def get_supplier(db: Session, supplier_id: UUID) -> Optional[Supplier]:
        """Get supplier by ID."""
        return db.query(Supplier).filter(Supplier.id == supplier_id).first()

    @staticmethod
    def list_suppliers(
        db: Session, skip: int = 0, limit: int = 100, active_only: bool = True
    ) -> List[Supplier]:
        """List suppliers."""
        query = db.query(Supplier)
        if active_only:
            query = query.filter(Supplier.is_active == True)
        return query.order_by(Supplier.name).offset(skip).limit(limit).all()

    @staticmethod
    def update_supplier(
        db: Session, supplier_id: UUID, request: SupplierUpdate
    ) -> Optional[Supplier]:
        """Update supplier details."""
        supplier = SupplierService.get_supplier(db, supplier_id)
        if not supplier:
            return None

        update_data = request.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(supplier, field, value)

        db.commit()
        db.refresh(supplier)
        logger.info(f"Supplier updated: {supplier_id}")
        return supplier


class InventoryService:
    """Service for managing inventory items and transactions."""

    @staticmethod
    def create_inventory_item(db: Session, request: InventoryItemCreate) -> InventoryItem:
        """Create a new inventory item."""
        # Validate supplier exists if provided
        if request.supplier_id:
            supplier = SupplierService.get_supplier(db, request.supplier_id)
            if not supplier:
                raise ValueError(f"Supplier '{request.supplier_id}' not found")

        # Validate product exists if provided
        if request.product_id:
            product = db.query(Product).filter(Product.id == request.product_id).first()
            if not product:
                raise ValueError(f"Product '{request.product_id}' not found")

        # Check if item name is unique
        existing = db.query(InventoryItem).filter(InventoryItem.item_name == request.item_name).first()
        if existing:
            raise ValueError(f"Inventory item '{request.item_name}' already exists")

        # Check if product is already mapped
        if request.product_id:
            existing_product_map = db.query(InventoryItem).filter(InventoryItem.product_id == request.product_id).first()
            if existing_product_map:
                raise ValueError(f"Product '{request.product_id}' is already mapped to inventory item '{existing_product_map.item_name}'")

        item = InventoryItem(
            id=uuid4(),
            product_id=request.product_id,
            item_name=request.item_name,
            unit=request.unit,
            current_quantity=request.current_quantity,
            reorder_level=request.reorder_level,
            reorder_quantity=request.reorder_quantity,
            unit_cost=request.unit_cost,
            supplier_id=request.supplier_id,
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        logger.info(f"Inventory item created: {item.id}")
        return item

    @staticmethod
    def get_inventory_item(db: Session, item_id: UUID) -> Optional[InventoryItem]:
        """Get inventory item by ID."""
        return db.query(InventoryItem).filter(InventoryItem.id == item_id).first()

    @staticmethod
    def list_inventory_items(
        db: Session, skip: int = 0, limit: int = 100
    ) -> List[InventoryItem]:
        """List all inventory items."""
        return db.query(InventoryItem).order_by(InventoryItem.item_name).offset(skip).limit(limit).all()

    @staticmethod
    def update_inventory_item(
        db: Session, item_id: UUID, request: InventoryItemUpdate
    ) -> Optional[InventoryItem]:
        """Update inventory item."""
        item = InventoryService.get_inventory_item(db, item_id)
        if not item:
            return None

        # Validate supplier if updated
        if request.supplier_id:
            supplier = SupplierService.get_supplier(db, request.supplier_id)
            if not supplier:
                raise ValueError(f"Supplier '{request.supplier_id}' not found")

        # Validate product if updated
        if request.product_id:
            product = db.query(Product).filter(Product.id == request.product_id).first()
            if not product:
                raise ValueError(f"Product '{request.product_id}' not found")
            # Ensure it is not mapped to another item
            existing_product_map = db.query(InventoryItem).filter(
                InventoryItem.product_id == request.product_id, InventoryItem.id != item_id
            ).first()
            if existing_product_map:
                raise ValueError(f"Product '{request.product_id}' is already mapped to inventory item '{existing_product_map.item_name}'")

        update_data = request.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(item, field, value)

        db.commit()
        db.refresh(item)
        logger.info(f"Inventory item updated: {item_id}")
        return item

    @staticmethod
    def track_transaction(
        db: Session,
        item_id: UUID,
        request: InventoryTransactionCreate,
        user_id: UUID,
    ) -> InventoryTransaction:
        """
        Record an inventory movement and update the item's current quantity.
        Also triggers low-stock alerts if needed.
        """
        item = InventoryService.get_inventory_item(db, item_id)
        if not item:
            raise ValueError(f"Inventory item {item_id} not found")

        valid_types = ["stock_in", "stock_out", "purchase", "waste", "adjustment"]
        if request.transaction_type not in valid_types:
            raise ValueError(f"Invalid transaction type. Must be one of {valid_types}")

        # Update inventory item current quantity
        qty = request.quantity
        if request.transaction_type in ["stock_in", "purchase"]:
            item.current_quantity += abs(qty)
        elif request.transaction_type in ["stock_out", "waste"]:
            item.current_quantity -= abs(qty)
        elif request.transaction_type == "adjustment":
            item.current_quantity += qty

        # Ensure quantity does not fall below zero
        if item.current_quantity < 0:
            item.current_quantity = Decimal("0.00")

        # Log transaction
        txn = InventoryTransaction(
            id=uuid4(),
            inventory_item_id=item_id,
            transaction_type=request.transaction_type,
            quantity=qty,
            reference_type=request.reference_type,
            reference_id=request.reference_id,
            notes=request.notes,
            created_by_id=user_id,
        )
        db.add(txn)
        db.add(item)
        db.flush()

        # Check reorder level alert
        InventoryService._check_and_trigger_low_stock_alert(db, item)

        db.commit()
        db.refresh(txn)
        return txn

    @staticmethod
    def deduct_stock_for_order(db: Session, order: Order) -> None:
        """
        Deduct recipe ingredients for all items in an order.
        Idempotent: skips if stock has already been deducted for this order.
        """
        # Check if already deducted
        existing_txn = db.query(InventoryTransaction).filter(
            InventoryTransaction.reference_type == "order_id",
            InventoryTransaction.reference_id == order.id,
        ).first()

        if existing_txn:
            logger.info(f"Stock already deducted for order {order.id}")
            return

        for item in order.items:
            if item.is_cancelled:
                continue

            # Check if product has a recipe
            recipe = db.query(Recipe).filter(Recipe.product_id == item.product_id).first()
            if not recipe:
                # If product itself is mapped to an inventory item directly
                # (e.g., packaged beverage or raw retail item)
                inv_item = db.query(InventoryItem).filter(InventoryItem.product_id == item.product_id).first()
                if inv_item:
                    # Deduct directly
                    deduct_qty = Decimal(item.quantity)
                    inv_item.current_quantity -= deduct_qty
                    if inv_item.current_quantity < 0:
                        inv_item.current_quantity = Decimal("0.00")

                    txn = InventoryTransaction(
                        id=uuid4(),
                        inventory_item_id=inv_item.id,
                        transaction_type="stock_out",
                        quantity=deduct_qty,
                        reference_type="order_id",
                        reference_id=order.id,
                        notes=f"Auto-deducted directly for product in order {order.order_number}",
                        created_by_id=order.cashier_id,
                    )
                    db.add(txn)
                    db.add(inv_item)
                    db.flush()
                    InventoryService._check_and_trigger_low_stock_alert(db, inv_item)
                continue

            # Map through recipe ingredients
            for ingredient in recipe.ingredients:
                total_needed = ingredient.quantity_needed * Decimal(item.quantity)
                inv_item = ingredient.inventory_item

                inv_item.current_quantity -= total_needed
                if inv_item.current_quantity < 0:
                    inv_item.current_quantity = Decimal("0.00")

                txn = InventoryTransaction(
                    id=uuid4(),
                    inventory_item_id=inv_item.id,
                    transaction_type="stock_out",
                    quantity=total_needed,
                    reference_type="order_id",
                    reference_id=order.id,
                    notes=f"Auto-deducted for recipe {recipe.name} in order {order.order_number}",
                    created_by_id=order.cashier_id,
                )
                db.add(txn)
                db.add(inv_item)
                db.flush()
                InventoryService._check_and_trigger_low_stock_alert(db, inv_item)

        db.flush()

    @staticmethod
    def get_stock_forecast(db: Session, item_id: UUID, days: int = 7) -> dict:
        """
        Calculate daily rate of consumption and forecast days of stock remaining.
        Uses stock deductions over the last N days.
        """
        item = InventoryService.get_inventory_item(db, item_id)
        if not item:
            raise ValueError(f"Inventory item {item_id} not found")

        since_date = datetime.utcnow() - timedelta(days=days)
        txns = db.query(InventoryTransaction).filter(
            InventoryTransaction.inventory_item_id == item_id,
            InventoryTransaction.created_at >= since_date,
        ).all()

        # Sum up all deductions (stock_out, waste, negative adjustments)
        total_used = Decimal("0.00")
        for txn in txns:
            if txn.transaction_type in ["stock_out", "waste"]:
                total_used += abs(txn.quantity)
            elif txn.transaction_type == "adjustment" and txn.quantity < 0:
                total_used += abs(txn.quantity)

        daily_rate = total_used / Decimal(days) if days > 0 else Decimal("0.00")
        if daily_rate > 0:
            days_remaining = item.current_quantity / daily_rate
        else:
            days_remaining = Decimal("-1.00")

        # Recommendation logic
        if days_remaining >= 0 and days_remaining <= 3:
            recommendation = "reorder_now"
        elif days_remaining > 3 and days_remaining <= 7:
            recommendation = "reorder_soon"
        else:
            recommendation = "sufficient_stock"

        return {
            "item_id": item_id,
            "item_name": item.item_name,
            "current_quantity": item.current_quantity,
            "unit": item.unit,
            "daily_rate": daily_rate,
            "days_remaining": days_remaining,
            "recommendation": recommendation,
        }

    @staticmethod
    def _check_and_trigger_low_stock_alert(db: Session, item: InventoryItem) -> None:
        """Helper to create low stock alerts when quantity reaches reorder level."""
        if item.current_quantity <= item.reorder_level:
            # Check if there's already an active (unread) low_stock notification for this item/product
            # To handle items without product_id, check message contains item_name
            existing = db.query(Notification).filter(
                Notification.notification_type == "low_stock",
                Notification.is_read == False,
            )
            if item.product_id:
                existing = existing.filter(Notification.related_product_id == item.product_id)
            else:
                existing = existing.filter(Notification.message.like(f"%{item.item_name}%"))

            existing_notif = existing.first()
            if not existing_notif:
                # Get first admin/manager to link to user_id or keep None
                logger.warning(f"Low Stock warning: {item.item_name} has {item.current_quantity} {item.unit}")
                notification = Notification(
                    id=uuid4(),
                    notification_type="low_stock",
                    title=f"Low Stock Alert: {item.item_name}",
                    message=f"Inventory item '{item.item_name}' is low. Current: {item.current_quantity} {item.unit} (Reorder level: {item.reorder_level} {item.unit})",
                    related_product_id=item.product_id,
                    is_read=False,
                )
                db.add(notification)


class RecipeService:
    """Service for managing recipes and ingredient mappings."""

    @staticmethod
    def create_recipe(db: Session, request: RecipeCreate) -> Recipe:
        """Create a recipe for a product."""
        # Ensure product exists
        product = db.query(Product).filter(Product.id == request.product_id).first()
        if not product:
            raise ValueError(f"Product {request.product_id} not found")

        # Check if recipe already exists
        existing = db.query(Recipe).filter(Recipe.product_id == request.product_id).first()
        if existing:
            raise ValueError(f"Recipe for product {request.product_id} already exists")

        recipe = Recipe(
            id=uuid4(),
            product_id=request.product_id,
            name=request.name,
        )
        db.add(recipe)
        db.flush()

        # Add ingredients
        for ingredient in request.ingredients:
            # Ensure inventory item exists
            item = InventoryService.get_inventory_item(db, ingredient.inventory_item_id)
            if not item:
                raise ValueError(f"Inventory item {ingredient.inventory_item_id} not found")

            recipe_ingredient = RecipeIngredient(
                id=uuid4(),
                recipe_id=recipe.id,
                inventory_item_id=ingredient.inventory_item_id,
                quantity_needed=ingredient.quantity_needed,
            )
            db.add(recipe_ingredient)

        db.commit()
        db.refresh(recipe)
        logger.info(f"Recipe created: {recipe.id}")
        return recipe

    @staticmethod
    def get_recipe(db: Session, recipe_id: UUID) -> Optional[Recipe]:
        """Get recipe by ID."""
        return db.query(Recipe).filter(Recipe.id == recipe_id).first()

    @staticmethod
    def get_recipe_by_product(db: Session, product_id: UUID) -> Optional[Recipe]:
        """Get recipe by Product ID."""
        return db.query(Recipe).filter(Recipe.product_id == product_id).first()

    @staticmethod
    def update_recipe(db: Session, recipe_id: UUID, request: RecipeUpdate) -> Optional[Recipe]:
        """Update recipe details and ingredient mappings."""
        recipe = RecipeService.get_recipe(db, recipe_id)
        if not recipe:
            return None

        if request.name:
            recipe.name = request.name

        if request.ingredients is not None:
            # Delete old ingredients
            db.query(RecipeIngredient).filter(RecipeIngredient.recipe_id == recipe_id).delete()

            # Add new ingredients
            for ingredient in request.ingredients:
                item = InventoryService.get_inventory_item(db, ingredient.inventory_item_id)
                if not item:
                    raise ValueError(f"Inventory item {ingredient.inventory_item_id} not found")

                recipe_ingredient = RecipeIngredient(
                    id=uuid4(),
                    recipe_id=recipe_id,
                    inventory_item_id=ingredient.inventory_item_id,
                    quantity_needed=ingredient.quantity_needed,
                )
                db.add(recipe_ingredient)

        db.commit()
        db.refresh(recipe)
        logger.info(f"Recipe updated: {recipe_id}")
        return recipe

    @staticmethod
    def delete_recipe(db: Session, recipe_id: UUID) -> bool:
        """Delete a recipe and its ingredient mappings."""
        recipe = RecipeService.get_recipe(db, recipe_id)
        if not recipe:
            return False

        db.delete(recipe)
        db.commit()
        logger.info(f"Recipe deleted: {recipe_id}")
        return True
