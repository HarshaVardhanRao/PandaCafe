import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models import Setting, Role, User
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

class TestSettingsAPI:
    """Tests for settings endpoints."""

    def test_get_upi_id_default(self, test_client: TestClient, db: Session):
        """Test GET /api/v1/settings/upi_id when not explicitly in DB."""
        app.dependency_overrides[get_db] = lambda: db
        try:
            response = test_client.get("/api/v1/settings/upi_id")
            assert response.status_code == 200
            assert response.json() == {"upi_id": "pandacafe@upi"}
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_get_upi_id_stored(self, test_client: TestClient, db: Session):
        """Test GET /api/v1/settings/upi_id when setting exists in DB."""
        setting = Setting(
            setting_key="upi_id",
            setting_value="custom@upi",
            setting_type="string",
            description="UPI ID",
            is_system=True
        )
        db.add(setting)
        db.commit()

        app.dependency_overrides[get_db] = lambda: db
        try:
            response = test_client.get("/api/v1/settings/upi_id")
            assert response.status_code == 200
            assert response.json() == {"upi_id": "custom@upi"}
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_update_upi_id_as_manager(self, test_client: TestClient, db: Session, manager_user: User):
        """Test PUT /api/v1/settings/upi_id updates successfully when authorized."""
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_current_user] = lambda: manager_user
        try:
            payload = {"upi_id": "new_merchant@upi"}
            response = test_client.put("/api/v1/settings/upi_id", json=payload)
            assert response.status_code == 200
            assert response.json() == {"upi_id": "new_merchant@upi"}

            # Verify it's actually in DB
            db_setting = db.query(Setting).filter(Setting.setting_key == "upi_id").first()
            assert db_setting is not None
            assert db_setting.setting_value == "new_merchant@upi"
        finally:
            app.dependency_overrides.pop(get_db, None)
            app.dependency_overrides.pop(get_current_user, None)

    def test_update_upi_id_as_cashier_forbidden(self, test_client: TestClient, db: Session, test_user: User):
        """Test PUT /api/v1/settings/upi_id fails with 403 Forbidden when unauthorized."""
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_current_user] = lambda: test_user
        try:
            payload = {"upi_id": "malicious@upi"}
            response = test_client.put("/api/v1/settings/upi_id", json=payload)
            assert response.status_code == 403
            assert "Access denied" in response.json()["detail"]
        finally:
            app.dependency_overrides.pop(get_db, None)
            app.dependency_overrides.pop(get_current_user, None)
