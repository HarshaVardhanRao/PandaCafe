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

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return str(value)

    def process_result_value(self, value, dialect):
        return value


# If the project imports UUID from postgresql dialect, override it for tests
try:
    _pg.UUID = GUID
except Exception:
    pass

from app.db.database import Base, get_db
from app.main import app
from fastapi.testclient import TestClient


# Use SQLite for testing
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


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
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def test_client():
    """Test client fixture."""
    return client
