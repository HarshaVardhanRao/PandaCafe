"""
SQLAlchemy models for PandaCafe.
All tables with relationships, indexes, and constraints.
"""

import uuid
from datetime import datetime
from typing import List

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UUID,
    Index,
)
from sqlalchemy.orm import relationship

from app.db.database import Base


# ============================================================================
# User & Authentication Models
# ============================================================================


class Role(Base):
    """User roles with permission system."""

    __tablename__ = "roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50), unique=True, nullable=False)  # owner, manager, cashier, kitchen, waiter
    description = Column(Text)
    permissions = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    users = relationship("User", back_populates="role")

    __table_args__ = (
        Index("idx_roles_name", "name"),
    )


class User(Base):
    """System users with authentication and role-based access."""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    phone_number = Column(String(20))
    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id"), nullable=False)
    status = Column(String(20), default="active")  # active, inactive, suspended
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime(timezone=True))

    # Relationships
    role = relationship("Role", back_populates="users")
    orders = relationship("Order", back_populates="cashier")
    shifts = relationship("Shift", back_populates="cashier")
    audit_logs = relationship("AuditLog", back_populates="user")
    inventory_transactions = relationship("InventoryTransaction", back_populates="created_by")

    __table_args__ = (
        Index("idx_users_email", "email"),
        Index("idx_users_username", "username"),
    )


# ============================================================================
# Product & Category Models
# ============================================================================


class Category(Base):
    """Product categories."""

    __tablename__ = "categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    image_url = Column(String(500))
    display_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime(timezone=True))

    # Relationships
    products = relationship("Product", back_populates="category", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_categories_name", "name"),
    )


class Product(Base):
    """Menu products/items."""

    __tablename__ = "products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sku = Column(String(50), unique=True, nullable=False)
    name = Column(String(150), nullable=False)
    description = Column(Text)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    tax_percent = Column(Numeric(5, 2), default=0)
    image_url = Column(String(500))
    preparation_time_minutes = Column(Integer, default=0)
    is_available = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime(timezone=True))

    # Relationships
    category = relationship("Category", back_populates="products")
    addons = relationship("ProductAddon", back_populates="product", cascade="all, delete-orphan")
    order_items = relationship("OrderItem", back_populates="product")
    recipe = relationship("Recipe", back_populates="product", uselist=False, cascade="all, delete-orphan")
    inventory_item = relationship("InventoryItem", back_populates="product", uselist=False)

    __table_args__ = (
        Index("idx_products_category_id", "category_id"),
        Index("idx_products_is_available", "is_available"),
        Index("idx_products_sku", "sku"),
    )


class ProductAddon(Base):
    """Add-ons for products (e.g., extra shots, extra syrup)."""

    __tablename__ = "product_addons"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    addon_name = Column(String(100), nullable=False)
    addon_price = Column(Numeric(10, 2), nullable=False)
    is_available = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    product = relationship("Product", back_populates="addons")

    __table_args__ = (
        Index("idx_product_addons_product_id", "product_id"),
    )


# ============================================================================
# Table Management Models
# ============================================================================


class Table(Base):
    """Dine-in tables."""

    __tablename__ = "tables"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    table_number = Column(Integer, nullable=False)
    capacity = Column(Integer, nullable=False)
    location = Column(String(100))
    status = Column(String(20), default="available")  # available, occupied, reserved, cleaning
    current_order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime(timezone=True))

    # Relationships
    orders = relationship("Order", back_populates="table", foreign_keys="Order.table_id")

    __table_args__ = (
        Index("idx_tables_status", "status"),
        Index("idx_tables_table_number", "table_number"),
    )


# ============================================================================
# Customer Models
# ============================================================================


class Customer(Base):
    """Customer management with loyalty tracking."""

    __tablename__ = "customers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone_number = Column(String(20), unique=True, nullable=False)
    email = Column(String(100), unique=True)
    name = Column(String(100), nullable=False)
    loyalty_points = Column(Integer, default=0)
    total_spent = Column(Numeric(15, 2), default=0)
    visit_count = Column(Integer, default=0)
    last_visit = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime(timezone=True))

    # Relationships
    orders = relationship("Order", back_populates="customer")

    __table_args__ = (
        Index("idx_customers_phone", "phone_number"),
        Index("idx_customers_email", "email"),
    )


# ============================================================================
# Order Models
# ============================================================================


class Order(Base):
    """Orders with status tracking."""

    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_number = Column(String(20), unique=True, nullable=False)
    order_type = Column(String(20), nullable=False)  # dine_in, take_away, delivery
    table_id = Column(UUID(as_uuid=True), ForeignKey("tables.id", ondelete="SET NULL"))
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"))
    cashier_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    status = Column(
        String(20),
        default="pending",
    )  # pending, accepted, preparing, ready, served, completed, cancelled
    subtotal = Column(Numeric(15, 2), default=0)
    tax_amount = Column(Numeric(15, 2), default=0)
    discount_amount = Column(Numeric(15, 2), default=0)
    total_amount = Column(Numeric(15, 2), default=0)
    notes = Column(Text)
    is_hold = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime(timezone=True))
    cancelled_at = Column(DateTime(timezone=True))

    # Relationships
    table = relationship("Table", back_populates="orders", foreign_keys=[table_id])
    customer = relationship("Customer", back_populates="orders")
    cashier = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="order", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_orders_status", "status"),
        Index("idx_orders_table_id", "table_id"),
        Index("idx_orders_cashier_id", "cashier_id"),
        Index("idx_orders_created_at", "created_at"),
        Index("idx_orders_order_number", "order_number"),
    )


class OrderItem(Base):
    """Line items in an order."""

    __tablename__ = "order_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    tax_percent = Column(Numeric(5, 2), default=0)
    item_total = Column(Numeric(15, 2), nullable=False)
    special_notes = Column(Text)
    is_cancelled = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")

    __table_args__ = (
        Index("idx_order_items_order_id", "order_id"),
        Index("idx_order_items_product_id", "product_id"),
    )


# ============================================================================
# Payment Models
# ============================================================================


class Payment(Base):
    """Payment transactions."""

    __tablename__ = "payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    payment_method = Column(String(20), nullable=False)  # cash, upi, card, split
    transaction_id = Column(String(100))
    payment_status = Column(String(20), default="completed")  # pending, completed, failed, refunded
    reference_number = Column(String(100))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    order = relationship("Order", back_populates="payments")

    __table_args__ = (
        Index("idx_payments_order_id", "order_id"),
        Index("idx_payments_created_at", "created_at"),
    )


# ============================================================================
# Inventory Models
# ============================================================================


class InventoryItem(Base):
    """Inventory tracking for ingredients and supplies."""

    __tablename__ = "inventory_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), unique=True)
    item_name = Column(String(100), nullable=False)
    unit = Column(String(20), nullable=False)  # ml, g, pieces, etc.
    current_quantity = Column(Numeric(10, 2), default=0)
    reorder_level = Column(Numeric(10, 2), default=0)
    reorder_quantity = Column(Numeric(10, 2), default=0)
    unit_cost = Column(Numeric(10, 2))
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="SET NULL"))
    last_stock_check = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    product = relationship("Product", back_populates="inventory_item")
    transactions = relationship("InventoryTransaction", back_populates="inventory_item", cascade="all, delete-orphan")
    recipe_ingredients = relationship("RecipeIngredient", back_populates="inventory_item")
    supplier = relationship("Supplier", back_populates="inventory_items")

    __table_args__ = (
        Index("idx_inventory_product_id", "product_id"),
    )


class InventoryTransaction(Base):
    """Track inventory movements (stock in/out)."""

    __tablename__ = "inventory_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    inventory_item_id = Column(
        UUID(as_uuid=True), ForeignKey("inventory_items.id", ondelete="CASCADE"), nullable=False
    )
    transaction_type = Column(String(20), nullable=False)  # stock_in, stock_out, purchase, waste, adjustment
    quantity = Column(Numeric(10, 2), nullable=False)
    reference_type = Column(String(50))  # order_id, purchase_id, manual
    reference_id = Column(UUID(as_uuid=True))
    notes = Column(Text)
    created_by_id = Column(
        "created_by",
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False
    )

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    inventory_item = relationship(
        "InventoryItem",
        back_populates="transactions"
    )

    created_by = relationship(
        "User",
        back_populates="inventory_transactions",
        foreign_keys=[created_by_id]
    )

    __table_args__ = (
        Index("idx_inventory_transactions_item_id", "inventory_item_id"),
        Index("idx_inventory_transactions_created_at", "created_at"),
    )


# ============================================================================
# Recipe Models
# ============================================================================


class Recipe(Base):
    """Recipe definitions for products."""

    __tablename__ = "recipes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    product = relationship("Product", back_populates="recipe")
    ingredients = relationship("RecipeIngredient", back_populates="recipe", cascade="all, delete-orphan")


class RecipeIngredient(Base):
    """Ingredients required for a recipe."""

    __tablename__ = "recipe_ingredients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipe_id = Column(UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)
    inventory_item_id = Column(UUID(as_uuid=True), ForeignKey("inventory_items.id"), nullable=False)
    quantity_needed = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    recipe = relationship("Recipe", back_populates="ingredients")
    inventory_item = relationship("InventoryItem", back_populates="recipe_ingredients")


# ============================================================================
# Discount Models
# ============================================================================


class Discount(Base):
    """Discount and coupon management."""

    __tablename__ = "discounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(50), unique=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    discount_type = Column(String(20), nullable=False)  # percentage, fixed_amount, bogo
    discount_value = Column(Numeric(10, 2), nullable=False)
    max_discount_amount = Column(Numeric(15, 2))
    min_order_amount = Column(Numeric(15, 2), default=0)
    max_usage = Column(Integer)
    usage_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    starts_at = Column(DateTime(timezone=True))
    expires_at = Column(DateTime(timezone=True))
    requires_approval = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime(timezone=True))


# ============================================================================
# Printer & Device Models
# ============================================================================


class Printer(Base):
    """Thermal printer management."""

    __tablename__ = "printers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    printer_type = Column(String(50), nullable=False)  # usb, network, bluetooth
    model = Column(String(100))
    connection_string = Column(String(500))  # COM port or IP address
    is_active = Column(Boolean, default=True)
    printer_location = Column(String(100))  # bill, kitchen, etc.
    status = Column(String(20), default="offline")  # online, offline, error
    last_test_time = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_printers_location", "printer_location"),
    )


# ============================================================================
# Shift Management
# ============================================================================


class Shift(Base):
    """Cashier shift tracking with cash reconciliation."""

    __tablename__ = "shifts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cashier_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    shift_date = Column(DateTime(timezone=True), nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True))
    opening_cash = Column(Numeric(15, 2))
    expected_cash = Column(Numeric(15, 2))
    actual_cash = Column(Numeric(15, 2))
    cash_difference = Column(Numeric(15, 2))
    total_sales = Column(Numeric(15, 2), default=0)
    notes = Column(Text)
    status = Column(String(20), default="open")  # open, closed
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    cashier = relationship("User", back_populates="shifts")

    __table_args__ = (
        Index("idx_shifts_cashier_id", "cashier_id"),
        Index("idx_shifts_shift_date", "shift_date"),
    )


# ============================================================================
# Notification Models
# ============================================================================


class Notification(Base):
    """Real-time notifications."""

    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    notification_type = Column(
        String(50), nullable=False
    )  # order_ready, low_stock, printer_offline, payment_failed
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    related_order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id", ondelete="SET NULL"))
    related_product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"))
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    read_at = Column(DateTime(timezone=True))

    # Relationships
    user = relationship("User")
    order = relationship("Order")
    product = relationship("Product")

    __table_args__ = (
        Index("idx_notifications_user_id", "user_id"),
        Index("idx_notifications_is_read", "is_read"),
    )


# ============================================================================
# Audit Models
# ============================================================================


class AuditLog(Base):
    """Complete audit trail of all changes."""

    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    entity_type = Column(String(50), nullable=False)  # users, products, orders, etc.
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    action = Column(String(20), nullable=False)  # create, update, delete
    changes = Column(JSON)  # field_name: {old_value, new_value}
    ip_address = Column(String(45))
    user_agent = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="audit_logs")

    __table_args__ = (
        Index("idx_audit_logs_user_id", "user_id"),
        Index("idx_audit_logs_entity", "entity_type", "entity_id"),
        Index("idx_audit_logs_created_at", "created_at"),
    )


# ============================================================================
# Settings & Configuration
# ============================================================================


class Setting(Base):
    """Application settings."""

    __tablename__ = "settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    setting_key = Column(String(100), unique=True, nullable=False)
    setting_value = Column(Text)
    setting_type = Column(String(20))  # string, number, boolean, json
    description = Column(Text)
    is_system = Column(Boolean, default=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))


# ============================================================================
# Supplier Model (for inventory)
# ============================================================================


class Supplier(Base):
    """Supplier management."""

    __tablename__ = "suppliers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    contact_person = Column(String(100))
    email = Column(String(100))
    phone_number = Column(String(20))
    address = Column(Text)
    city = Column(String(50))
    payment_terms = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    inventory_items = relationship("InventoryItem", back_populates="supplier")
