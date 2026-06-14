"""
Unit and integration tests for Reports & Analytics (Phase 6).
"""

import os
from datetime import date, datetime, timedelta
from decimal import Decimal
import uuid
import pytest
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.main import app
from app.models import (
    Category,
    Customer,
    Order,
    OrderItem,
    Payment,
    Product,
    Role,
    User,
    InventoryItem,
    InventoryTransaction,
    Shift,
)
from app.db.database import get_db
from app.api.v1.endpoints.inventory import get_current_user


@pytest.fixture
def manager_user(db: Session):
    """Create test manager user fixture."""
    role = db.query(Role).filter(Role.name == "manager").first()
    if not role:
        role = Role(
            id=uuid.uuid4(),
            name="manager",
            description="Manager Role",
            permissions=[]
        )
        db.add(role)
        db.commit()
        db.refresh(role)

    user = User(
        id=uuid.uuid4(),
        username="testmanager",
        email="manager@test.com",
        password_hash="hashed_password",
        full_name="Test Manager",
        role_id=role.id,
        status="active"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def sample_data(db: Session, test_user: User):
    """Seed sample catalog products and inventory items for report tests."""
    category = Category(id=uuid.uuid4(), name="Drinks")
    db.add(category)
    db.commit()

    p1 = Product(
        id=uuid.uuid4(),
        sku="TEST-COF-01",
        name="Latte",
        price=Decimal("100.00"),
        tax_percent=Decimal("5.00"),
        category_id=category.id,
        is_available=True,
    )
    p2 = Product(
        id=uuid.uuid4(),
        sku="TEST-COF-02",
        name="Mocha",
        price=Decimal("120.00"),
        tax_percent=Decimal("5.00"),
        category_id=category.id,
        is_available=True,
    )
    db.add_all([p1, p2])
    db.commit()

    inv1 = InventoryItem(
        id=uuid.uuid4(),
        product_id=p1.id,
        item_name="Coffee Beans",
        unit="g",
        current_quantity=Decimal("50.00"),  # Low stock
        reorder_level=Decimal("100.00"),
        reorder_quantity=Decimal("500.00"),
    )
    inv2 = InventoryItem(
        id=uuid.uuid4(),
        product_id=p2.id,
        item_name="Chocolate Powder",
        unit="g",
        current_quantity=Decimal("1000.00"),  # Sufficient stock
        reorder_level=Decimal("100.00"),
        reorder_quantity=Decimal("500.00"),
    )
    db.add_all([inv1, inv2])
    db.commit()

    return {"p1": p1, "p2": p2, "inv1": inv1, "inv2": inv2}


class TestReportAccessControls:
    """Verify that reports are restricted to owners and managers."""

    def test_cashier_access_forbidden(self, test_client: TestClient, db: Session, test_user: User):
        # test_user is a cashier by default
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_current_user] = lambda: test_user
        try:
            response = test_client.get("/api/v1/reports/daily")
            assert response.status_code == 403
            assert "Access denied" in response.json()["detail"]
        finally:
            app.dependency_overrides.pop(get_db, None)
            app.dependency_overrides.pop(get_current_user, None)

    def test_manager_access_allowed(self, test_client: TestClient, db: Session, manager_user: User):
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_current_user] = lambda: manager_user
        try:
            response = test_client.get("/api/v1/reports/daily")
            assert response.status_code == 200
        finally:
            app.dependency_overrides.pop(get_db, None)
            app.dependency_overrides.pop(get_current_user, None)


class TestReportCalculations:
    """Verify core math calculations of report services."""

    def test_daily_report_calculation(self, test_client: TestClient, db: Session, manager_user: User, sample_data: dict):
        p1 = sample_data["p1"]
        # Create completed order today
        order = Order(
            id=uuid.uuid4(),
            order_number="ORD-REP-01",
            order_type="dine_in",
            cashier_id=manager_user.id,
            status="completed",
            subtotal=Decimal("100.00"),
            tax_amount=Decimal("5.00"),
            discount_amount=Decimal("10.00"),
            total_amount=Decimal("95.00"),
            created_at=datetime.utcnow() - timedelta(minutes=5),
            completed_at=datetime.utcnow(),
        )
        db.add(order)
        db.commit()

        # Add OrderItem
        item = OrderItem(
            id=uuid.uuid4(),
            order_id=order.id,
            product_id=p1.id,
            quantity=1,
            unit_price=Decimal("100.00"),
            tax_percent=Decimal("5.00"),
            item_total=Decimal("105.00"),
            is_cancelled=False,
        )
        db.add(item)

        # Add Payment
        payment = Payment(
            id=uuid.uuid4(),
            order_id=order.id,
            amount=Decimal("95.00"),
            payment_method="cash",
            payment_status="completed",
            created_at=datetime.utcnow(),
        )
        db.add(payment)
        db.commit()

        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_current_user] = lambda: manager_user
        try:
            response = test_client.get(f"/api/v1/reports/daily?target_date={date.today()}")
            assert response.status_code == 200
            data = response.json()
            assert float(data["total_sales"]) == 95.00
            assert float(data["net_revenue"]) == 95.00
            assert data["order_count"] == 1
            assert float(data["average_order_value"]) == 95.00
            assert float(data["tax_collected"]) == 5.00
            assert float(data["discounts_given"]) == 10.00
            assert data["orders_by_status"]["completed"] == 1
            assert data["payments_by_method"]["cash"]["count"] == 1
            assert float(data["payments_by_method"]["cash"]["total"]) == 95.00
        finally:
            app.dependency_overrides.pop(get_db, None)
            app.dependency_overrides.pop(get_current_user, None)

    def test_trends_report_calculation(self, test_client: TestClient, db: Session, manager_user: User):
        # Create orders completed today and yesterday
        today = datetime.utcnow()
        yesterday = today - timedelta(days=1)

        o1 = Order(
            id=uuid.uuid4(),
            order_number="ORD-REP-10",
            order_type="take_away",
            cashier_id=manager_user.id,
            status="completed",
            total_amount=Decimal("150.00"),
            created_at=today,
            completed_at=today,
        )
        o2 = Order(
            id=uuid.uuid4(),
            order_number="ORD-REP-11",
            order_type="take_away",
            cashier_id=manager_user.id,
            status="completed",
            total_amount=Decimal("250.00"),
            created_at=yesterday,
            completed_at=yesterday,
        )
        db.add_all([o1, o2])
        db.commit()

        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_current_user] = lambda: manager_user
        try:
            start_str = (date.today() - timedelta(days=2)).strftime("%Y-%m-%d")
            end_str = date.today().strftime("%Y-%m-%d")
            response = test_client.get(f"/api/v1/reports/trends?start_date={start_str}&end_date={end_str}")
            assert response.status_code == 200
            data = response.json()
            trends = data["trends"]
            assert len(trends) >= 3

            # Verify today and yesterday totals
            today_trend = next(t for t in trends if t["date"] == date.today().strftime("%Y-%m-%d"))
            yesterday_trend = next(t for t in trends if t["date"] == (date.today() - timedelta(days=1)).strftime("%Y-%m-%d"))

            assert float(today_trend["sales_amount"]) == 150.00
            assert today_trend["order_count"] == 1
            assert float(yesterday_trend["sales_amount"]) == 250.00
            assert yesterday_trend["order_count"] == 1
        finally:
            app.dependency_overrides.pop(get_db, None)
            app.dependency_overrides.pop(get_current_user, None)

    def test_products_report_calculation(self, test_client: TestClient, db: Session, manager_user: User, sample_data: dict):
        p1 = sample_data["p1"]  # Latte
        p2 = sample_data["p2"]  # Mocha

        # Sell p1
        order = Order(
            id=uuid.uuid4(),
            order_number="ORD-REP-12",
            order_type="take_away",
            cashier_id=manager_user.id,
            status="completed",
            total_amount=Decimal("200.00"),
            created_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )
        db.add(order)
        db.commit()

        item = OrderItem(
            id=uuid.uuid4(),
            order_id=order.id,
            product_id=p1.id,
            quantity=2,
            unit_price=Decimal("100.00"),
            tax_percent=Decimal("0.00"),
            item_total=Decimal("200.00"),
            is_cancelled=False,
        )
        db.add(item)
        db.commit()

        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_current_user] = lambda: manager_user
        try:
            response = test_client.get("/api/v1/reports/products")
            assert response.status_code == 200
            data = response.json()

            # p1 (Latte) must be top seller
            top_p1 = next((p for p in data["top_products"] if str(p["product_id"]) == str(p1.id)), None)
            assert top_p1 is not None
            assert top_p1["quantity_sold"] == 2
            assert float(top_p1["total_revenue"]) == 200.00

            # p2 (Mocha) must be unsold
            unsold_p2 = next((p for p in data["least_selling_products"] if str(p["product_id"]) == str(p2.id)), None)
            assert unsold_p2 is not None
            assert unsold_p2["quantity_sold"] == 0
            assert unsold_p2["is_unsold"] is True
        finally:
            app.dependency_overrides.pop(get_db, None)
            app.dependency_overrides.pop(get_current_user, None)

    def test_inventory_report_calculation(self, test_client: TestClient, db: Session, manager_user: User, sample_data: dict):
        inv1 = sample_data["inv1"]  # low stock
        inv2 = sample_data["inv2"]  # normal stock

        # Log a stock transaction
        tx = InventoryTransaction(
            id=uuid.uuid4(),
            inventory_item_id=inv1.id,
            transaction_type="adjustment",
            quantity=Decimal("-10.00"),
            reference_type="manual",
            created_by_id=manager_user.id,
            created_at=datetime.utcnow()
        )
        db.add(tx)
        db.commit()

        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_current_user] = lambda: manager_user
        try:
            start_str = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
            end_str = date.today().strftime("%Y-%m-%d")
            response = test_client.get(f"/api/v1/reports/inventory?start_date={start_str}&end_date={end_str}")
            assert response.status_code == 200
            data = response.json()

            # Low stock item checked
            item_c = next(i for i in data["stock_levels"] if str(i["item_id"]) == str(inv1.id))
            assert item_c["is_low_stock"] is True

            item_p = next(i for i in data["stock_levels"] if str(i["item_id"]) == str(inv2.id))
            assert item_p["is_low_stock"] is False

            # Movements logged
            mov = next(m for m in data["movements"] if str(m["item_id"]) == str(inv1.id))
            assert mov["transaction_type"] == "adjustment"
            assert float(mov["total_quantity"]) == -10.00
            assert mov["transaction_count"] == 1
        finally:
            app.dependency_overrides.pop(get_db, None)
            app.dependency_overrides.pop(get_current_user, None)

    def test_employee_report_calculation(self, test_client: TestClient, db: Session, manager_user: User):
        # Create a shift for manager user
        shift = Shift(
            id=uuid.uuid4(),
            cashier_id=manager_user.id,
            shift_date=datetime.utcnow(),
            start_time=datetime.utcnow() - timedelta(hours=8),
            opening_cash=Decimal("500.00"),
            expected_cash=Decimal("1500.00"),
            actual_cash=Decimal("1490.00"),  # Shortage of 10
            cash_difference=Decimal("-10.00"),
            total_sales=Decimal("1000.00"),
            status="closed",
        )
        db.add(shift)

        # Create a completed order today
        order = Order(
            id=uuid.uuid4(),
            order_number="ORD-REP-13",
            order_type="take_away",
            cashier_id=manager_user.id,
            status="completed",
            total_amount=Decimal("1000.00"),
            created_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )
        db.add(order)
        db.commit()

        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_current_user] = lambda: manager_user
        try:
            response = test_client.get("/api/v1/reports/employees")
            assert response.status_code == 200
            data = response.json()

            # Cashier sales details
            cashier = next(c for c in data["cashier_performance"] if str(c["cashier_id"]) == str(manager_user.id))
            assert cashier["username"] == manager_user.username
            assert float(cashier["total_sales"]) == 1000.00
            assert cashier["orders_processed"] == 1

            # Shift reconciliations
            shift_res = next(s for s in data["shift_summaries"] if str(s["shift_id"]) == str(shift.id))
            assert shift_res["cashier_name"] == manager_user.full_name
            assert float(shift_res["opening_cash"]) == 500.00
            assert float(shift_res["cash_difference"]) == -10.00
            assert shift_res["status"] == "closed"
        finally:
            app.dependency_overrides.pop(get_db, None)
            app.dependency_overrides.pop(get_current_user, None)


class TestReportExports:
    """Verify exports (CSV & PDF formats) render correctly."""

    def test_export_csv(self, test_client: TestClient, db: Session, manager_user: User):
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_current_user] = lambda: manager_user
        try:
            response = test_client.get("/api/v1/reports/daily/export?format=csv")
            assert response.status_code == 200
            assert response.headers["Content-Disposition"].startswith("attachment; filename=daily_report")
            assert response.headers["content-type"] == "text/csv; charset=utf-8"
            
            content = response.content.decode("utf-8")
            assert "Daily Operational Report" in content
            assert "Total Completed Sales" in content
        finally:
            app.dependency_overrides.pop(get_db, None)
            app.dependency_overrides.pop(get_current_user, None)

    def test_export_pdf(self, test_client: TestClient, db: Session, manager_user: User):
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_current_user] = lambda: manager_user
        try:
            response = test_client.get("/api/v1/reports/inventory/export?format=pdf")
            assert response.status_code == 200
            assert response.headers["Content-Disposition"].startswith("attachment; filename=inventory_report")
            assert response.headers["content-type"] == "application/pdf"
            
            # Simple PDF signature check (%PDF-1.4)
            assert response.content.startswith(b"%PDF")
        finally:
            app.dependency_overrides.pop(get_db, None)
            app.dependency_overrides.pop(get_current_user, None)
