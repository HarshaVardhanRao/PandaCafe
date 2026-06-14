"""
Unit tests for CustomerService, Loyalty systems, QR ordering, and Bill Sharing (Phase 5).
"""

import os
import pytest
from decimal import Decimal
from sqlalchemy.orm import Session
from uuid import uuid4

from app.models import Category, Customer, Order, OrderItem, Product, Table, User
from app.schemas.customer import CustomerCreate, CustomerUpdate, LoyaltyRedeemRequest, SelfOrderCreateRequest, BillShareRequest
from app.schemas.order import OrderCreateRequest, OrderItemAddRequest, PaymentRequest
from app.services.customer_service import CustomerService
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService
from fastapi.testclient import TestClient
from app.main import app
from app.db.database import get_db


@pytest.fixture
def test_table(db: Session):
    """Create test table."""
    table = Table(
        id=uuid4(),
        table_number=5,
        capacity=2,
        location="Terrace",
        status="available",
    )
    db.add(table)
    db.commit()
    return table


@pytest.fixture
def test_customer(db: Session):
    """Create test customer."""
    customer = Customer(
        id=uuid4(),
        name="Charlie Loyalty",
        phone_number="+91-8888888888",
        email="charlie@loyalty.com",
        loyalty_points=50,
        total_spent=Decimal("500.00"),
        visit_count=5,
    )
    db.add(customer)
    db.commit()
    return customer


@pytest.fixture
def test_category(db: Session):
    """Create test category."""
    category = Category(
        id=uuid4(),
        name="Coffee Category",
    )
    db.add(category)
    db.commit()
    return category


@pytest.fixture
def test_product(db: Session, test_category):
    """Create test product."""
    product = Product(
        id=uuid4(),
        sku="COFFEE-009",
        name="Cortado",
        description="Cortado espresso drink",
        category_id=test_category.id,
        price=Decimal("80.00"),
        tax_percent=Decimal("5.00"),
        is_available=True,
    )
    db.add(product)
    db.commit()
    return product


class TestCustomerCRUD:
    """Customer CRUD operations unit tests."""

    def test_create_and_lookup_customer(self, db: Session):
        request = CustomerCreate(
            name="John Customer",
            phone_number="1239874560",
            email="john@customer.com",
        )
        customer = CustomerService.create_customer(db, request)
        assert customer.name == "John Customer"
        assert customer.loyalty_points == 0

        # Lookup by phone
        retrieved = CustomerService.get_customer_by_phone(db, "1239874560")
        assert retrieved is not None
        assert retrieved.id == customer.id

    def test_purchase_history(self, db: Session, test_user: User, test_customer: Customer, test_product: Product):
        order_req = OrderCreateRequest(
            order_type="take_away",
            customer_id=str(test_customer.id),
        )
        order = OrderService.create_order(db, order_req, str(test_user.id))

        history = CustomerService.get_purchase_history(db, test_customer.id)
        assert history["customer"].id == test_customer.id
        assert len(history["orders"]) >= 1
        assert history["orders"][0].id == order.id


class TestLoyaltyPoints:
    """Loyalty points accumulation and redemption unit tests."""

    def test_loyalty_crediting_on_completion(self, db: Session, test_user: User, test_customer: Customer, test_product: Product):
        # 1. Create order
        order_req = OrderCreateRequest(
            order_type="take_away",
            customer_id=str(test_customer.id),
        )
        order = OrderService.create_order(db, order_req, str(test_user.id))

        # 2. Add item to order
        item_req = OrderItemAddRequest(product_id=str(test_product.id), quantity=3) # 3 * 80 + tax = 240 + 12 = 252 total
        OrderService.add_item_to_order(db, str(order.id), item_req)

        # 3. Pay for order
        pay_req = PaymentRequest(
            amount=order.total_amount,
            payment_method="cash",
        )
        PaymentService.process_payment(db, str(order.id), pay_req)

        # 4. Complete order
        OrderService.complete_order(db, str(order.id))

        # 5. Check points credited (original 50 points + 25 earned (from 252 total))
        db.refresh(test_customer)
        assert test_customer.loyalty_points == 50 + 25
        assert test_customer.visit_count == 6
        assert test_customer.total_spent == Decimal("500.00") + Decimal("252.00")

    def test_loyalty_point_redemption_and_refund(self, db: Session, test_user: User, test_customer: Customer, test_product: Product):
        # 1. Create order
        order_req = OrderCreateRequest(
            order_type="take_away",
            customer_id=str(test_customer.id),
        )
        order = OrderService.create_order(db, order_req, str(test_user.id))

        # 2. Add item to order
        item_req = OrderItemAddRequest(product_id=str(test_product.id), quantity=1) # 1 * 80 + tax = 84 total
        OrderService.add_item_to_order(db, str(order.id), item_req)

        # 3. Redeem points
        # 30 points = 30 currency units discount
        CustomerService.redeem_loyalty_points(db, order.id, 30)

        # 4. Verify discount applied and totals updated
        db.refresh(order)
        db.refresh(test_customer)
        assert order.discount_amount == Decimal("30.00")
        assert order.total_amount == Decimal("54.00") # 84 - 30 = 54
        assert test_customer.loyalty_points == 20 # 50 - 30 = 20

        # 5. Verify point refund on cancellation
        OrderService.cancel_order(db, str(order.id))
        db.refresh(test_customer)
        assert test_customer.loyalty_points == 50 # Refunded back to 50


class TestQROrdering:
    """QR code table ordering unit tests."""

    def test_self_order_public_api(self, db: Session, test_table: Table, test_product: Product, test_client: TestClient):
        admin = User(
            id=uuid4(),
            username="admin",
            email="admin@test.com",
            password_hash="pw",
            full_name="Admin",
            role_id=test_table.id, # just mock role ID
        )
        db.add(admin)
        db.commit()

        # Place a self order
        payload = {
            "table_id": str(test_table.id),
            "items": [
                {"product_id": str(test_product.id), "quantity": 2}
            ],
            "customer_phone": "+91-7777777777",
            "notes": "No ice",
        }

        app.dependency_overrides[get_db] = lambda: db
        try:
            response = test_client.post("/api/v1/self-order", json=payload)
            assert response.status_code == 201
            data = response.json()
            assert data["status"] == "pending"
            assert data["order_type"] == "dine_in"
            assert "[QR Self-Order]" in data["notes"]

            # Verify table status updated
            db.refresh(test_table)
            assert test_table.status == "occupied"
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_get_table_qr(self, db: Session, test_table: Table, test_client: TestClient):
        app.dependency_overrides[get_db] = lambda: db
        try:
            response = test_client.get(f"/api/v1/tables/{test_table.id}/qr")
            assert response.status_code == 200
            assert response.headers["content-type"] == "image/png"
            assert len(response.content) > 0
        finally:
            app.dependency_overrides.pop(get_db, None)


class TestBillSharing:
    """Bill sharing simulation unit tests."""

    def test_share_bill_simulation(self, db: Session, test_user: User, test_customer: Customer, test_product: Product, test_client: TestClient):
        order_req = OrderCreateRequest(order_type="take_away", customer_id=str(test_customer.id))
        order = OrderService.create_order(db, order_req, str(test_user.id))
        item_req = OrderItemAddRequest(product_id=str(test_product.id), quantity=1)
        OrderService.add_item_to_order(db, str(order.id), item_req)

        import os
        base_path = ""
        if os.path.basename(os.getcwd()) != "backend" and os.path.exists("backend"):
            base_path = "backend"

        email_sim = os.path.join(base_path, "email_simulation.txt")
        wa_sim = os.path.join(base_path, "whatsapp_simulation.txt")
        sms_sim = os.path.join(base_path, "sms_simulation.txt")

        # Clear existing simulated files
        for f in [email_sim, wa_sim, sms_sim]:
            if os.path.exists(f):
                os.remove(f)

        app.dependency_overrides[get_db] = lambda: db
        try:
            # Share via Email
            response = test_client.post(
                f"/api/v1/orders/{order.id}/share",
                json={"method": "email", "destination": "customer@test.com"},
            )
            assert response.status_code == 200
            assert os.path.exists(email_sim)

            # Share via WhatsApp
            response = test_client.post(
                f"/api/v1/orders/{order.id}/share",
                json={"method": "whatsapp", "destination": "+91-9999988888"},
            )
            assert response.status_code == 200
            assert "whatsapp_link" in response.json()
            assert os.path.exists(wa_sim)

            # Share via SMS
            response = test_client.post(
                f"/api/v1/orders/{order.id}/share",
                json={"method": "sms", "destination": "+91-9999988888"},
            )
            assert response.status_code == 200
            assert os.path.exists(sms_sim)
        finally:
            app.dependency_overrides.pop(get_db, None)
