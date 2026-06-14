"""
Unit tests for authentication service.
"""

import pytest
from uuid import uuid4
from app.db.database import SessionLocal, Base, engine
from app.models import Role, User
from app.schemas.auth import UserRegisterRequest
from app.services.auth_service import AuthService
from app.core.security import verify_password, get_password_hash


@pytest.fixture(scope="function")
def db():
    """Create test database."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Create test role
    role = Role(name="test_role", description="Test Role")
    db.add(role)
    db.commit()

    yield db

    db.close()
    Base.metadata.drop_all(bind=engine)


class TestAuthService:
    """Tests for AuthService."""

    def test_register_user_success(self, db):
        """Test successful user registration."""
        request = UserRegisterRequest(
            username="testuser",
            email="test@example.com",
            password="TestPassword123",
            full_name="Test User",
            phone_number="+91-9999999999",
            role="test_role",
        )

        # Create default role first
        role = Role(name="cashier", description="Cashier")
        db.add(role)
        db.commit()

        result = AuthService.register_user(db, request)

        assert result is not None
        assert result["user"].username == "testuser"
        assert result["user"].email == "test@example.com"
        assert result["access_token"] is not None
        assert result["refresh_token"] is not None

    def test_register_user_duplicate_username(self, db):
        """Test registration with duplicate username."""
        # Create first user
        role = Role(name="cashier", description="Cashier")
        db.add(role)
        db.commit()

        first_request = UserRegisterRequest(
            username="testuser",
            email="test1@example.com",
            password="TestPassword123",
            full_name="Test User 1",
            role="cashier",
        )
        AuthService.register_user(db, first_request)

        # Try to create another with same username
        second_request = UserRegisterRequest(
            username="testuser",
            email="test2@example.com",
            password="TestPassword123",
            full_name="Test User 2",
            role="cashier",
        )

        with pytest.raises(ValueError, match="already exists"):
            AuthService.register_user(db, second_request)

    def test_authenticate_user_success(self, db):
        """Test successful authentication."""
        # Create user
        role = Role(name="cashier", description="Cashier")
        db.add(role)
        db.commit()

        user = User(
            username="testuser",
            email="test@example.com",
            password_hash=get_password_hash("TestPassword123"),
            full_name="Test User",
            role_id=role.id,
            status="active",
        )
        db.add(user)
        db.commit()

        # Authenticate
        result = AuthService.authenticate_user(db, "testuser", "TestPassword123")

        assert result is not None
        assert result["user"].id == user.id
        assert result["access_token"] is not None

    def test_authenticate_user_invalid_password(self, db):
        """Test authentication with invalid password."""
        role = Role(name="cashier", description="Cashier")
        db.add(role)
        db.commit()

        user = User(
            username="testuser",
            email="test@example.com",
            password_hash=get_password_hash("TestPassword123"),
            full_name="Test User",
            role_id=role.id,
            status="active",
        )
        db.add(user)
        db.commit()

        result = AuthService.authenticate_user(db, "testuser", "WrongPassword")
        assert result is None

    def test_change_password(self, db):
        """Test password change."""
        role = Role(name="cashier", description="Cashier")
        db.add(role)
        db.commit()

        user = User(
            username="testuser",
            email="test@example.com",
            password_hash=get_password_hash("OldPassword123"),
            full_name="Test User",
            role_id=role.id,
            status="active",
        )
        db.add(user)
        db.commit()

        # Change password
        success = AuthService.change_password(
            db, user.id, "OldPassword123", "NewPassword123"
        )

        assert success is True

        # Verify old password no longer works
        result = AuthService.authenticate_user(db, "testuser", "OldPassword123")
        assert result is None

        # Verify new password works
        result = AuthService.authenticate_user(db, "testuser", "NewPassword123")
        assert result is not None

    def test_get_user_by_username(self, db):
        """Test getting user by username."""
        role = Role(name="cashier", description="Cashier")
        db.add(role)
        db.commit()

        user = User(
            username="testuser",
            email="test@example.com",
            password_hash=get_password_hash("Password123"),
            full_name="Test User",
            role_id=role.id,
            status="active",
        )
        db.add(user)
        db.commit()

        found_user = AuthService.get_user_by_username(db, "testuser")
        assert found_user is not None
        assert found_user.id == user.id

    def test_soft_delete_user(self, db):
        """Test soft delete of user."""
        role = Role(name="cashier", description="Cashier")
        db.add(role)
        db.commit()

        user = User(
            username="testuser",
            email="test@example.com",
            password_hash=get_password_hash("Password123"),
            full_name="Test User",
            role_id=role.id,
            status="active",
        )
        db.add(user)
        db.commit()

        # Soft delete
        success = AuthService.soft_delete_user(db, user.id)
        assert success is True

        # Verify soft delete
        found_user = AuthService.get_user(db, user.id)
        assert found_user is not None
        assert found_user.deleted_at is not None
