import pytest
import os
import tempfile
import shutil
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from backend.database import Base, get_db
from backend.main import app
from backend.config import settings

# Test database
TEST_DATABASE_URL = "sqlite:///./test_chatbot.db"

@pytest.fixture(scope="session")
def test_engine():
    """Create test database engine."""
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    yield engine
    # Cleanup
    os.remove("./test_chatbot.db")

@pytest.fixture(scope="function")
def test_db(test_engine):
    """Create test database session."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()
    
    # Override the get_db dependency
    def override_get_db():
        try:
            yield session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    yield session
    
    # Cleanup
    session.rollback()
    session.close()
    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
def client(test_db):
    """Create test client."""
    return TestClient(app)

@pytest.fixture(scope="function")
def temp_upload_dir():
    """Create temporary upload directory."""
    temp_dir = tempfile.mkdtemp()
    original_upload_dir = settings.UPLOAD_DIR
    settings.UPLOAD_DIR = temp_dir
    
    yield temp_dir
    
    # Cleanup
    shutil.rmtree(temp_dir)
    settings.UPLOAD_DIR = original_upload_dir

@pytest.fixture
def sample_docx_content():
    """Sample Word document content for testing."""
    return b'PK\x03\x04\x14\x00\x00\x00\x08\x00'  # Minimal docx header

@pytest.fixture
def mock_hf_api_key():
    """Mock Hugging Face API key."""
    original_key = settings.HF_API_KEY
    settings.HF_API_KEY = "test_api_key"
    yield "test_api_key"
    settings.HF_API_KEY = original_key