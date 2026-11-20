from datetime import datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine

from app.main import Document, User, create_app

ALEX = {"X-Demo-User-Id": "1"}
JORDAN = {"X-Demo-User-Id": "2"}


@pytest.fixture
def engine(tmp_path):
    engine = create_engine(f"sqlite:///{(tmp_path / 'test.db').as_posix()}")
    yield engine
    engine.dispose()


@pytest.fixture
def client(engine):
    with TestClient(create_app(engine), headers=ALEX) as client:
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

    with TestClient(create_app(engine), headers=ALEX) as reopened:
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
            "Access-Control-Request-Headers": "Content-Type, X-Demo-User-Id",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_startup_preserves_phase_one_documents(engine):
    User.__table__.create(engine)
    Document.__table__.create(engine)
    legacy_id = uuid4()
    content = {"type": "doc", "content": [{"type": "paragraph"}]}
    with Session(engine) as session:
        session.add(User(id=1, name="Alex Morgan"))
        session.add(Document(id=legacy_id, owner_id=1, title="Phase One", content=content))
        session.commit()

    with TestClient(create_app(engine), headers=ALEX) as client:
        assert client.get("/demo-users").json() == [
            {"id": 1, "name": "Alex Morgan"}, {"id": 2, "name": "Jordan Lee"},
        ]
        assert client.get(f"/documents/{legacy_id}").json()["content"] == content
        assert client.get("/documents").json()[0]["id"] == str(legacy_id)
        assert client.get("/documents", headers=JORDAN).json() == []
        assert client.post(f"/documents/{legacy_id}/shares", json={"user_id": 2}).status_code == 204


def test_demo_identity_is_required_and_controls_ownership(client, engine):
    with TestClient(create_app(engine)) as no_identity:
        assert no_identity.get("/documents").status_code == 422
    with Session(engine) as session:
        session.add(User(id=99, name="Non-demo user"))
        session.commit()
    assert client.get("/documents", headers={"X-Demo-User-Id": "99"}).status_code == 400
    assert client.post("/documents", headers=JORDAN, json={"owner_id": 1}).status_code == 422
    created = client.post("/documents", headers=JORDAN, json={})
    assert created.status_code == 201
    assert created.json()["owner_id"] == 2
    assert client.get("/documents").json() == []


def test_sharing_grants_read_only_access_and_revoke_removes_it(client):
    document = client.post("/documents", json={}).json()
    private = client.post("/documents", json={"title": "Private"}).json()
    path = f"/documents/{document['id']}"
    shares = f"{path}/shares"
    assert client.get(path, headers=JORDAN).status_code == 404
    assert client.get("/documents", headers=JORDAN).json() == []
    assert client.post(shares, json={"user_id": 1}).status_code == 400
    assert client.post(shares, json={"user_id": 999}).status_code == 400
    for _ in range(2):
        assert client.post(shares, json={"user_id": 2}).status_code == 204
    share, = client.get(shares).json()
    assert share["user_id"] == 2
    assert share["document_id"] == document["id"]
    assert client.get(path, headers=JORDAN).json() == document
    summary, = client.get("/documents", headers=JORDAN).json()
    assert summary["id"] == document["id"]
    assert summary["owner_name"] == "Alex Morgan"
    assert client.get(f"/documents/{private['id']}", headers=JORDAN).status_code == 404
    assert client.patch(path, headers=JORDAN, json={"title": "Changed"}).status_code == 404
    assert client.patch(path, headers=JORDAN, json={"content": document["content"]}).status_code == 404
    assert client.delete(path, headers=JORDAN).status_code in (404, 405)
    assert client.get(shares, headers=JORDAN).status_code == 404
    assert client.post(shares, headers=JORDAN, json={"user_id": 1}).status_code == 404
    assert client.delete(f"{shares}/2", headers=JORDAN).status_code == 404
    assert client.get(path).json() == document
    assert client.delete(f"{shares}/2").status_code == 204
    assert client.get(shares).json() == []
    assert client.get(path, headers=JORDAN).status_code == 404
    assert client.get("/documents", headers=JORDAN).json() == []
