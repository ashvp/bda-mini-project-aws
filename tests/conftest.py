import os
import shutil
import tempfile
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Force local mock for testing
os.environ["USE_LOCAL_S3_MOCK"] = "True"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.config import get_settings
from app.database import Base, get_db
from app.main import app, seed_admin_user

settings = get_settings()
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Create all tables in the in-memory test database and isolate test uploads."""
    # Set up isolated temporary directory for test uploads
    test_upload_dir = tempfile.mkdtemp(prefix="test_uploads_")
    original_upload_dir = settings.LOCAL_UPLOAD_DIR
    settings.LOCAL_UPLOAD_DIR = test_upload_dir

    Base.metadata.create_all(bind=engine)
    # Seed admin user in test db
    db = TestingSessionLocal()
    try:
        from app.models.user import User
        from app.services.auth import hash_password
        admin = User(
            username="admin",
            pw_hashed=hash_password("AdminSecurePassword123!"),
            houseid=None,
            isAdmin=True
        )
        db.add(admin)
        db.commit()
    finally:
        db.close()

    yield

    Base.metadata.drop_all(bind=engine)
    # Clean up isolated test uploads
    settings.LOCAL_UPLOAD_DIR = original_upload_dir
    shutil.rmtree(test_upload_dir, ignore_errors=True)


@pytest.fixture()
def db_session():
    """Yield a database session for test operations."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client():
    """FastAPI TestClient with overridden get_db dependency."""
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
