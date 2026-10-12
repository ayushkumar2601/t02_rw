"""Pytest test configuration, fixtures, and database isolation."""

import os
import tempfile
import pytest
import pytest_asyncio
import httpx

from app.config import settings
from app.main import app
from app.repositories.database import DatabaseManager
from app.repositories.lead_repository import LeadRepository
from app.repositories.session_repository import SessionRepository
from app.services.conversation_manager import ConversationManager
from app.services.extraction_service import ExtractionService
from app.services.validation_service import ValidationService


@pytest_asyncio.fixture
async def test_db():
    """Create a temporary SQLite database for test isolation."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    db_mgr = DatabaseManager(db_path=db_path)
    await db_mgr.init_db()

    yield db_mgr

    # Cleanup after test
    try:
        if os.path.exists(db_path):
            os.remove(db_path)
    except OSError:
        pass


@pytest_asyncio.fixture
async def session_repo(test_db):
    """SessionRepository connected to test database."""
    return SessionRepository(manager=test_db)


@pytest_asyncio.fixture
async def lead_repo(test_db):
    """LeadRepository connected to test database."""
    return LeadRepository(manager=test_db)


@pytest_asyncio.fixture
async def conv_manager(session_repo, lead_repo):
    """ConversationManager wired to test database."""
    extraction_svc = ExtractionService()
    validation_svc = ValidationService()
    return ConversationManager(
        session_repo=session_repo,
        lead_repo=lead_repo,
        extraction_svc=extraction_svc,
        validation_svc=validation_svc,
    )


@pytest_asyncio.fixture
async def async_client(test_db, monkeypatch):
    """Async HTTP test client pointing to the FastAPI app with test DB."""
    # Monkeypatch the global db_manager to point to our test DB
    import app.repositories.database
    import app.repositories.lead_repository
    import app.repositories.session_repository
    import app.services.conversation_manager
    import app.main

    monkeypatch.setattr(app.repositories.database, "db_manager", test_db)
    monkeypatch.setattr(app.repositories.lead_repository, "db_manager", test_db)
    monkeypatch.setattr(app.repositories.session_repository, "db_manager", test_db)
    
    app.repositories.lead_repository.lead_repository.manager = test_db
    app.repositories.session_repository.session_repository.manager = test_db
    app.services.conversation_manager.conversation_manager.session_repo.manager = test_db
    transport = httpx.ASGITransport(app=app.main.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
