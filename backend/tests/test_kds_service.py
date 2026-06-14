"""
Unit tests for Kitchen Display System (KDS) service and endpoints.
"""
import os
import pytest
from decimal import Decimal
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.models import Order, User, Category, Product, Table
from app.schemas.order import OrderCreateRequest, OrderItemAddRequest
from app.services.order_service import OrderService
from app.services.kds_service import KDSService

@pytest.fixture
def test_table(db: Session):
    table = Table(
        table_number=2,
        capacity=4,
        location="Main Hall",
        status="available",
    )
    db.add(table)
    db.commit()
    return table

@pytest.fixture
def test_category(db: Session):
    category = Category(
        name="Main Course",
        description="Main course dishes",
    )
    db.add(category)
    db.commit()
    return category

@pytest.fixture
def test_product(db: Session, test_category):
    product = Product(
        sku="BURGER-001",
        name="Panda Burger",
        category_id=test_category.id,
        price=Decimal("150.00"),
        tax_percent=Decimal("5.00"),
        is_available=True,
    )
    db.add(product)
    db.commit()
    return product

def test_get_kds_orders_empty(db: Session, test_client: TestClient):
    """Test getting KDS orders when there are none."""
    from app.main import app
    from app.db.database import get_db
    app.dependency_overrides[get_db] = lambda: db
    try:
        response = test_client.get("/api/v1/kds/orders")
        assert response.status_code == 200
        assert response.json() == []
    finally:
        app.dependency_overrides.pop(get_db, None)

def test_get_kds_orders_with_active_orders(db: Session, test_client: TestClient, test_user: User, test_table: Table, test_product: Product):
    """Test retrieving active KDS orders."""
    from app.main import app
    from app.db.database import get_db
    app.dependency_overrides[get_db] = lambda: db
    try:
        # Create order
        request = OrderCreateRequest(order_type="dine_in", table_id=str(test_table.id))
        order = OrderService.create_order(db, request, str(test_user.id))
        
        # Add item
        item_request = OrderItemAddRequest(product_id=str(test_product.id), quantity=2, special_notes="No onions")
        OrderService.add_item_to_order(db, str(order.id), item_request)
        
        # Check KDS active orders
        response = test_client.get("/api/v1/kds/orders")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["order_number"] == order.order_number
        assert data[0]["table_number"] == 2
        assert len(data[0]["items"]) == 1
        assert data[0]["items"][0]["product_name"] == "Panda Burger"
        assert data[0]["items"][0]["quantity"] == 2
        assert data[0]["items"][0]["special_notes"] == "No onions"
    finally:
        app.dependency_overrides.pop(get_db, None)

def test_update_kds_order_status(db: Session, test_client: TestClient, test_user: User, test_table: Table, test_product: Product):
    """Test updating order status via KDS endpoint and verify printer simulation."""
    from app.main import app
    from app.db.database import get_db
    app.dependency_overrides[get_db] = lambda: db
    try:
        # Create order
        request = OrderCreateRequest(order_type="dine_in", table_id=str(test_table.id))
        order = OrderService.create_order(db, request, str(test_user.id))
        
        # Add item
        item_request = OrderItemAddRequest(product_id=str(test_product.id), quantity=1)
        OrderService.add_item_to_order(db, str(order.id), item_request)
        
        # Clear printer simulation file if it exists
        sim_file = os.path.join(os.getcwd(), "printer_simulation.txt")
        if os.path.exists(sim_file):
            os.remove(sim_file)
            
        # Update status to preparing
        response = test_client.patch(
            f"/api/v1/kds/orders/{order.id}/status",
            json={"status": "preparing"}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "preparing"
        
        # Verify printer simulation file contains KOT ticket details
        assert os.path.exists(sim_file)
        with open(sim_file, "r", encoding="utf-8") as f:
            content = f.read()
            assert "PANDA CAFE" in content
            assert order.order_number in content
            assert "Panda Burger" in content
    finally:
        app.dependency_overrides.pop(get_db, None)
