from datetime import datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine

from app.main import User, create_app


@pytest.fixture
def engine(tmp_path):
    engine = create_engine(f"sqlite:///{(tmp_path / 'test.db').as_posix()}")
    yield engine
    engine.dispose()


@pytest.fixture
def client(engine):
    with TestClient(create_app(engine)) as client:
        yield client


def test_create_edit_and_reopen_from_sqlite(client, engine):
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/documents").json() == []
    created = client.post("/documents", json={})
    assert created.status_code == 201
    document = created.json()
    assert document["title"] == "Untitled document"
    with Session(engine) as session:
        assert session.get(User, document["owner_id"]).name == "Alex Morgan"
    path = f"/documents/{document['id']}"
    content = {
        "type": "doc",
        "content": [{"type": "paragraph", "content": [
            {"type": "text", "text": "A draft", "marks": [{"type": "bold"}]},
        ]}],
    }

    renamed = client.patch(path, json={"title": "  Notes  "})
    assert renamed.status_code == 200
    assert renamed.json()["content"] == document["content"]
    saved = client.patch(path, json={"content": content})
    assert saved.status_code == 200
    assert saved.json()["title"] == "Notes"
    assert saved.json()["created_at"] == document["created_at"]
    assert datetime.fromisoformat(saved.json()["updated_at"]) > datetime.fromisoformat(document["updated_at"])

    with TestClient(create_app(engine)) as reopened:
        assert reopened.get(path).json() == saved.json()
        assert reopened.get(path).json()["content"] == content
        summary, = reopened.get("/documents").json()
        assert summary["id"] == document["id"]
        assert summary["title"] == "Notes"


def test_invalid_input_and_missing_documents(client):
    missing = f"/documents/{uuid4()}"
    assert client.get(missing).status_code == 404
    assert client.patch(missing, json={"title": "Notes"}).status_code == 404
    assert client.get("/documents/invalid").status_code == 422
    assert client.post("/documents", json={"title": "   "}).status_code == 422
    created = client.post("/documents", json={}).json()
    path = f"/documents/{created['id']}"
    for payload in (
        {},
        {"title": None},
        {"owner_id": 2},
        {"content": {"type": "paragraph"}},
        {"content": {"type": "doc", "content": [{"type": "unsupported"}]}},
        {"content": {"type": "doc", "content": [{"type": "text", "text": "Unwrapped"}]}},
    ):
        assert client.patch(path, json=payload).status_code == 422
    assert client.get(path).json() == created


def test_local_frontend_can_preflight_patch(client):
    response = client.options(
        f"/documents/{uuid4()}",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "PATCH",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
