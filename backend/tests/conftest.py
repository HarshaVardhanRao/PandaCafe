"""
Test configuration and fixtures.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Provide a lightweight UUID fallback for SQLite when models use UUID types
from sqlalchemy import types as sa_types
import sqlalchemy.dialects.postgresql as _pg


class GUID(sa_types.TypeDecorator):
    """Platform-independent GUID type.

    Uses String for SQLite (and other dialects without native UUID).
    """
    impl = sa_types.String
    cache_ok = True

    def __init__(self, *args, **kwargs):
        kwargs.pop('as_uuid', None)
        super().__init__(*args, **kwargs)

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return str(value)

    def process_result_value(self, value, dialect):
        return value


# If the project imports UUID from postgresql dialect or sqlalchemy, override it for tests
try:
    _pg.UUID = GUID
    import sqlalchemy
    sqlalchemy.types.UUID = GUID
    sqlalchemy.UUID = GUID
except Exception:
    pass


# Use SQLite for testing (placed in temp dir to avoid Docker mount locking issues and support Windows)
import tempfile
from pathlib import Path
db_path = Path(tempfile.gettempdir()) / "pandacafe_test.db"
SQLALCHEMY_TEST_DATABASE_URL = f"sqlite:///{db_path.as_posix()}"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override database module properties to use SQLite for tests
import app.db.database
app.db.database.engine = engine
app.db.database.SessionLocal = TestingSessionLocal

from app.db.database import Base, get_db
from app.main import app
from fastapi.testclient import TestClient



def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


Base.metadata.create_all(bind=engine)

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture
def db():
    """Database session fixture."""
    Base.metadata.create_all(bind=engine)
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_client():
    """Test client fixture."""
    return client


@pytest.fixture
def test_user(db):
    """Create test user fixture."""
    import uuid
    from app.models import Role, User
    role = db.query(Role).filter(Role.name == "cashier").first()
    if not role:
        role = Role(
            id=uuid.uuid4(),
            name="cashier",
            description="Cashier Role",
            permissions=[]
        )
        db.add(role)
        db.commit()
        db.refresh(role)

    user = User(
        id=uuid.uuid4(),
        username="testcashier",
        email="cashier@test.com",
        password_hash="hashed_password",
        full_name="Test Cashier",
        role_id=role.id,
        status="active"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
