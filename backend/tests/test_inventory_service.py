"""
Unit tests for SupplierService, InventoryService, and RecipeService (Phase 4).
"""

import pytest
from decimal import Decimal
from sqlalchemy.orm import Session
from uuid import uuid4

from app.models import (
    Category,
    Customer,
    InventoryItem,
    InventoryTransaction,
    Notification,
    Order,
    OrderItem,
    Product,
    Recipe,
    RecipeIngredient,
    Role,
    Supplier,
    User,
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
from app.schemas.order import OrderCreateRequest, OrderItemAddRequest, PaymentRequest
from app.services.inventory_service import (
    InventoryService,
    RecipeService,
    SupplierService,
)
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService


@pytest.fixture
def test_supplier(db: Session):
    """Create test supplier."""
    supplier = Supplier(
        id=uuid4(),
        name="Global Coffee Co",
        contact_person="Alice Smith",
        email="alice@globalcoffee.com",
        phone_number="+1-555-0199",
        address="123 Coffee Lane",
        city="Seattle",
        payment_terms="Net 30",
        is_active=True,
    )
    db.add(supplier)
    db.commit()
    return supplier


@pytest.fixture
def test_category(db: Session):
    """Create test category."""
    category = Category(
        id=uuid4(),
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
        id=uuid4(),
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


class TestSupplierService:
    """Supplier service unit tests."""

    def test_create_supplier(self, db: Session):
        request = SupplierCreate(
            name="Sugar Ltd",
            contact_person="Bob Sugar",
            email="bob@sugar.com",
            phone_number="1234567890",
        )
        supplier = SupplierService.create_supplier(db, request)
        assert supplier.name == "Sugar Ltd"
        assert supplier.is_active is True

        # Unique name constraint check
        with pytest.raises(ValueError):
            SupplierService.create_supplier(db, request)

    def test_get_supplier(self, db: Session, test_supplier: Supplier):
        retrieved = SupplierService.get_supplier(db, test_supplier.id)
        assert retrieved is not None
        assert retrieved.name == "Global Coffee Co"

    def test_list_suppliers(self, db: Session, test_supplier: Supplier):
        suppliers = SupplierService.list_suppliers(db)
        assert len(suppliers) >= 1
        assert any(s.name == "Global Coffee Co" for s in suppliers)

    def test_update_supplier(self, db: Session, test_supplier: Supplier):
        request = SupplierUpdate(contact_person="Alice Updated", is_active=False)
        updated = SupplierService.update_supplier(db, test_supplier.id, request)
        assert updated.contact_person == "Alice Updated"
        assert updated.is_active is False


class TestInventoryService:
    """Inventory service unit tests."""

    def test_create_inventory_item(self, db: Session, test_supplier: Supplier):
        request = InventoryItemCreate(
            item_name="Coffee Beans",
            unit="g",
            current_quantity=Decimal("1000.00"),
            reorder_level=Decimal("200.00"),
            reorder_quantity=Decimal("500.00"),
            unit_cost=Decimal("1.50"),
            supplier_id=test_supplier.id,
        )
        item = InventoryService.create_inventory_item(db, request)
        assert item.item_name == "Coffee Beans"
        assert item.current_quantity == Decimal("1000.00")

    def test_track_transaction_stock_in(self, db: Session, test_user: User):
        item_req = InventoryItemCreate(
            item_name="Milk",
            unit="ml",
            current_quantity=Decimal("500.00"),
            reorder_level=Decimal("100.00"),
        )
        item = InventoryService.create_inventory_item(db, item_req)

        txn_req = InventoryTransactionCreate(
            transaction_type="stock_in",
            quantity=Decimal("200.00"),
            notes="Manual restock",
        )
        txn = InventoryService.track_transaction(db, item.id, txn_req, test_user.id)
        assert txn.quantity == Decimal("200.00")
        assert item.current_quantity == Decimal("700.00")

    def test_track_transaction_stock_out_trigger_alert(self, db: Session, test_user: User):
        item_req = InventoryItemCreate(
            item_name="Cups",
            unit="pieces",
            current_quantity=Decimal("50.00"),
            reorder_level=Decimal("20.00"),
        )
        item = InventoryService.create_inventory_item(db, item_req)

        # Triggers low stock alert (50 - 35 = 15 <= 20)
        txn_req = InventoryTransactionCreate(
            transaction_type="stock_out",
            quantity=Decimal("35.00"),
            notes="Event usage",
        )
        txn = InventoryService.track_transaction(db, item.id, txn_req, test_user.id)
        assert item.current_quantity == Decimal("15.00")

        # Verify low stock alert notification was triggered
        notification = db.query(Notification).filter(
            Notification.notification_type == "low_stock",
            Notification.is_read == False,
        ).first()
        assert notification is not None
        assert "Cups" in notification.title


class TestRecipeService:
    """Recipe service unit tests."""

    def test_create_and_delete_recipe(self, db: Session, test_product: Product):
        # Create inventory items
        bean_req = InventoryItemCreate(item_name="Espresso Beans", unit="g", current_quantity=Decimal("1000.00"))
        beans = InventoryService.create_inventory_item(db, bean_req)

        milk_req = InventoryItemCreate(item_name="Fresh Milk", unit="ml", current_quantity=Decimal("2000.00"))
        milk = InventoryService.create_inventory_item(db, milk_req)

        # Create recipe
        request = RecipeCreate(
            product_id=test_product.id,
            name="Espresso Double",
            ingredients=[
                {"inventory_item_id": beans.id, "quantity_needed": Decimal("18.00")},
                {"inventory_item_id": milk.id, "quantity_needed": Decimal("150.00")},
            ],
        )
        recipe = RecipeService.create_recipe(db, request)
        assert recipe.name == "Espresso Double"
        assert len(recipe.ingredients) == 2

        # Retrieve recipe
        recipe_id = recipe.id
        retrieved = RecipeService.get_recipe_by_product(db, test_product.id)
        assert retrieved is not None
        assert retrieved.id == recipe_id

        # Update recipe name
        update_req = RecipeUpdate(name="Espresso Double Shot")
        RecipeService.update_recipe(db, recipe_id, update_req)
        assert recipe.name == "Espresso Double Shot"

        # Delete recipe
        deleted = RecipeService.delete_recipe(db, recipe_id)
        assert deleted is True
        assert RecipeService.get_recipe(db, recipe_id) is None


class TestStockDeductionIntegration:
    """Integration tests verifying automated stock deduction on sales."""

    def test_automated_stock_deduction_on_payment(
        self, db: Session, test_user: User, test_product: Product
    ):
        # 1. Setup ingredients & recipe
        bean_req = InventoryItemCreate(
            item_name="Organic Beans",
            unit="g",
            current_quantity=Decimal("1000.00"),
            reorder_level=Decimal("200.00"),
        )
        beans = InventoryService.create_inventory_item(db, bean_req)

        recipe_req = RecipeCreate(
            product_id=test_product.id,
            name="Single Espresso Recipe",
            ingredients=[{"inventory_item_id": beans.id, "quantity_needed": Decimal("10.00")}],
        )
        RecipeService.create_recipe(db, recipe_req)

        # 2. Create POS order for 2 Espressos
        order_req = OrderCreateRequest(order_type="take_away", notes="Test auto deduct")
        order = OrderService.create_order(db, order_req, str(test_user.id))

        item_req = OrderItemAddRequest(product_id=str(test_product.id), quantity=2)
        OrderService.add_item_to_order(db, str(order.id), item_req)

        # 3. Pay for order to transition to "served"
        pay_req = PaymentRequest(
            amount=order.total_amount,
            payment_method="cash",
            transaction_id="TXN-100",
        )
        PaymentService.process_payment(db, str(order.id), pay_req)

        # 4. Verify stock deducted: 1000 - (10g * 2 qty) = 980g
        db.refresh(beans)
        assert beans.current_quantity == Decimal("980.00")

        # Verify transaction log created referencing this order
        txn = db.query(InventoryTransaction).filter(
            InventoryTransaction.inventory_item_id == beans.id,
            InventoryTransaction.reference_type == "order_id",
            InventoryTransaction.reference_id == order.id,
        ).first()
        assert txn is not None
        assert txn.transaction_type == "stock_out"
        assert txn.quantity == Decimal("20.00")

        # 5. Verify idempotence: transitioning status again does not double-deduct
        OrderService.update_order_status(db, str(order.id), "completed")
        db.refresh(beans)
        assert beans.current_quantity == Decimal("980.00")  # Still 980


class TestStockForecasting:
    """Unit tests for consumption forecasting."""

    def test_forecast_calculation(self, db: Session, test_user: User):
        item_req = InventoryItemCreate(
            item_name="Chocolate Powder",
            unit="g",
            current_quantity=Decimal("700.00"),
            reorder_level=Decimal("100.00"),
        )
        item = InventoryService.create_inventory_item(db, item_req)

        # Create two stock out transactions totaling 140g over the last 7 days
        txn1 = InventoryTransactionCreate(transaction_type="stock_out", quantity=Decimal("80.00"))
        txn2 = InventoryTransactionCreate(transaction_type="stock_out", quantity=Decimal("60.00"))
        InventoryService.track_transaction(db, item.id, txn1, test_user.id)
        InventoryService.track_transaction(db, item.id, txn2, test_user.id)

        # Forecast over 7 days: Burn rate = 140g / 7 days = 20g/day
        # Days remaining = 560g (current) / 20g/day = 28 days
        forecast = InventoryService.get_stock_forecast(db, item.id, days=7)
        assert forecast["daily_rate"] == Decimal("20.00")
        assert forecast["days_remaining"] == Decimal("28.00")
        assert forecast["recommendation"] == "sufficient_stock"
