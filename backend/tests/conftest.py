"""
Test fixtures. Uses a file-based SQLite DB (not Postgres) purely so the
test suite has zero external dependencies and runs anywhere. Note: UUID
and Numeric types behave slightly differently under SQLite than Postgres
in production — the docker-compose stack should be used for integration
testing against real Postgres before deploying.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.main import app
from app.database import Base, get_db
from app.services.embeddings import get_embedding_service
from app.services.vector_store import get_persistent_vector_store, build_ephemeral_vector_store
from app.services.llm.factory import get_llm_client

from tests.fake_embeddings import FakeEmbeddingService
from tests.fake_llm import FakeLLMClient

SQLALCHEMY_TEST_URL = "sqlite:///./test.db"

engine = create_engine(SQLALCHEMY_TEST_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def fake_embedding_service():
    return FakeEmbeddingService()


@pytest.fixture(scope="function")
def ephemeral_vector_store():
    # Fresh in-memory Chroma client per test — no persistence, no network,
    # no leakage between tests.
    return build_ephemeral_vector_store()


@pytest.fixture(scope="function")
def fake_llm_client():
    return FakeLLMClient()


@pytest.fixture(scope="function")
def client(db_session, fake_embedding_service, ephemeral_vector_store, fake_llm_client):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_embedding_service] = lambda: fake_embedding_service
    app.dependency_overrides[get_persistent_vector_store] = lambda: ephemeral_vector_store
    app.dependency_overrides[get_llm_client] = lambda: fake_llm_client
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def auth_headers(client):
    """Registers a fresh user and returns Authorization headers for them."""
    resp = client.post(
        "/auth/register", json={"email": "tester@example.com", "password": "correcthorsebattery"}
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
