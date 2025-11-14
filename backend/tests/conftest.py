"""
Pytest configuration and fixtures for the test suite.
"""
import asyncio
import os
import tempfile
import pytest
import pytest_asyncio
from pathlib import Path
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock
import aiosqlite

from core.config import Settings
from core.dependencies import ServiceContainer
from core.events import EventBus
from repositories.document_repository import DocumentRepository
from repositories.chat_repository import ChatSessionRepository, ChatMessageRepository
from services.rag_service import RAGService
from services.chat_service import ChatService
from services.document_service import DocumentService


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings() -> Settings:
    """Create test settings with temporary directories."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create test configuration
        test_config = {
            "ENVIRONMENT": "development",
            "DEBUG": True,
            "DATABASE_URL": f"sqlite:///{temp_path}/test.db",
            "CHROMA_PERSIST_DIRECTORY": str(temp_path / "chroma_test"),
            "UPLOAD_DIR": str(temp_path / "uploads"),
            "LOG_LEVEL": "DEBUG",
            "ENABLE_JSON_LOGGING": False,
            "SECRET_KEY": "test-secret-key-for-testing-only-32-chars",
            "OLLAMA_BASE_URL": "http://localhost:11434",
            "GPT_OSS_MODEL": "gpt-oss:20b",
            "MAX_TOKENS": 512,  # Smaller for tests
            "TEMPERATURE": 0.0,  # Deterministic for tests
        }
        
        # Create settings instance with test config
        settings = Settings(**test_config)
        yield settings


@pytest_asyncio.fixture
async def test_db_path() -> AsyncGenerator[str, None]:
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_file:
        db_path = temp_file.name
    
    try:
        # Initialize database
        async with aiosqlite.connect(db_path) as db:
            await db.execute("PRAGMA foreign_keys = ON")
            await db.commit()
        
        yield db_path
    finally:
        # Cleanup
        try:
            os.unlink(db_path)
        except OSError:
            pass


@pytest_asyncio.fixture
async def document_repository(test_db_path: str) -> AsyncGenerator[DocumentRepository, None]:
    """Create a test document repository."""
    repo = DocumentRepository(db_path=test_db_path)
    await repo.initialize()
    yield repo


@pytest_asyncio.fixture
async def chat_session_repository(test_db_path: str) -> AsyncGenerator[ChatSessionRepository, None]:
    """Create a test chat session repository."""
    repo = ChatSessionRepository(db_path=test_db_path)
    await repo.initialize()
    yield repo


@pytest_asyncio.fixture
async def chat_message_repository(test_db_path: str) -> AsyncGenerator[ChatMessageRepository, None]:
    """Create a test chat message repository."""
    repo = ChatMessageRepository(db_path=test_db_path)
    await repo.initialize()
    yield repo


@pytest_asyncio.fixture
async def event_bus() -> AsyncGenerator[EventBus, None]:
    """Create a test event bus."""
    bus = EventBus()
    await bus.start()
    yield bus
    await bus.stop()


@pytest_asyncio.fixture
async def mock_rag_service() -> AsyncGenerator[AsyncMock, None]:
    """Create a mock RAG service."""
    mock_service = AsyncMock(spec=RAGService)
    
    # Configure common mock responses
    mock_service.initialize.return_value = None
    mock_service.shutdown.return_value = None
    mock_service.process_query.return_value = {
        "response": "Test response",
        "sources": ["test_source.pdf"],
        "confidence": 0.85,
        "retrieved_chunks": 3
    }
    mock_service.add_documents.return_value = None
    mock_service.delete_documents.return_value = None
    mock_service.check_ollama_status.return_value = {
        "status": "success",
        "message": "GPT-OSS:20B model is available",
        "ollama_running": True,
        "model_available": True,
        "available_models": ["gpt-oss:20b"]
    }
    
    yield mock_service


@pytest_asyncio.fixture
async def chat_service(mock_rag_service: AsyncMock) -> AsyncGenerator[ChatService, None]:
    """Create a test chat service."""
    service = ChatService(rag_service=mock_rag_service)
    await service.initialize()
    yield service


@pytest_asyncio.fixture
async def document_service(
    mock_rag_service: AsyncMock,
    document_repository: DocumentRepository
) -> AsyncGenerator[DocumentService, None]:
    """Create a test document service."""
    service = DocumentService(
        rag_service=mock_rag_service,
        document_repository=document_repository
    )
    await service.initialize()
    yield service


@pytest_asyncio.fixture
async def test_service_container(
    test_settings: Settings,
    test_db_path: str
) -> AsyncGenerator[ServiceContainer, None]:
    """Create a test service container with all dependencies."""
    # Temporarily set the global settings
    import core.config
    original_settings = core.config.settings
    core.config.settings = test_settings
    
    try:
        container = ServiceContainer()
        await container.initialize()
        yield container
        await container.shutdown()
    finally:
        # Restore original settings
        core.config.settings = original_settings


@pytest.fixture
def sample_pdf_content() -> bytes:
    """Create sample PDF content for testing."""
    # This is a minimal PDF content for testing
    return b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj

4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Test PDF content) Tj
ET
endstream
endobj

xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000206 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
290
%%EOF"""


@pytest.fixture
def sample_text_content() -> str:
    """Create sample text content for testing."""
    return """
    This is a sample financial document for testing purposes.
    
    Company: Test Financial Corp
    Revenue: $1,000,000
    Profit: $200,000
    
    The company showed strong performance in Q1 2024.
    Key metrics include improved efficiency and cost reduction.
    """


class MockUploadFile:
    """Mock file upload for testing."""
    
    def __init__(self, filename: str, content: bytes, content_type: str = "application/octet-stream"):
        self.filename = filename
        self.content = content
        self.content_type = content_type
        self._position = 0
    
    async def read(self, size: int = -1) -> bytes:
        if size == -1:
            result = self.content[self._position:]
            self._position = len(self.content)
        else:
            result = self.content[self._position:self._position + size]
            self._position += len(result)
        return result
    
    async def seek(self, position: int) -> None:
        self._position = position


@pytest.fixture
def mock_pdf_upload(sample_pdf_content: bytes) -> MockUploadFile:
    """Create a mock PDF upload file."""
    return MockUploadFile("test_document.pdf", sample_pdf_content, "application/pdf")


@pytest.fixture
def mock_text_upload(sample_text_content: str) -> MockUploadFile:
    """Create a mock text upload file."""
    return MockUploadFile("test_document.txt", sample_text_content.encode(), "text/plain")


# Pytest markers for different test types
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "requires_ollama: mark test as requiring Ollama")
    config.addinivalue_line("markers", "requires_db: mark test as requiring database")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test location."""
    for item in items:
        # Add unit marker to unit tests
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        
        # Add integration marker to integration tests
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        
        # Mark async tests
        if "async" in item.name or item.get_closest_marker("asyncio"):
            item.add_marker(pytest.mark.asyncio)


@pytest.fixture(autouse=True)
def cleanup_temp_files():
    """Automatically cleanup temporary files after each test."""
    yield
    # Any cleanup code here
    pass