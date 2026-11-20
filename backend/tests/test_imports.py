import pytest
from fastapi.testclient import TestClient
from sqlmodel import create_engine

from app.imports import MAX_FILE_BYTES
from app.main import EditorContent, create_app


@pytest.fixture
def client(tmp_path):
    engine = create_engine(f"sqlite:///{(tmp_path / 'imports.db').as_posix()}")
    with TestClient(create_app(engine), headers={"X-Demo-User-Id": "2"}) as client:
        yield client
    engine.dispose()


def upload(client, filename, content):
    return client.post(
        "/documents/import", params={"filename": filename}, content=content,
        headers={"Content-Type": "application/octet-stream"},
    )


def test_import_text_is_editable_and_belongs_to_active_user(client):
    response = upload(client, "Meeting.notes.TXT", "Café\r\n**plain**".encode())
    assert response.status_code == 201
    document = response.json()
    assert document["title"] == "Meeting.notes"
    assert document["owner_id"] == 2
    assert document["content"] == {"type": "doc", "content": [
        {"type": "paragraph", "content": [{"type": "text", "text": "Café"}]},
        {"type": "paragraph", "content": [{"type": "text", "text": "**plain**"}]},
    ]}
    path = f"/documents/{document['id']}"
    assert client.get(path, headers={"X-Demo-User-Id": "1"}).status_code == 404
    assert client.patch(path, json={"title": "Revised", "content": document["content"]}).status_code == 200


def test_markdown_import_creates_supported_nodes_and_keeps_html_as_text(client):
    response = upload(client, "notes.md", b"# Notes\n- **Bold**\n- *Italic*\n3. Item\n<script>alert(1)</script>")
    assert response.status_code == 201
    content = response.json()["content"]
    EditorContent.model_validate(content)
    heading, bullets, numbered, html = content["content"]
    assert heading["type"] == "heading"
    assert bullets["type"] == "bulletList"
    assert [item["content"][0]["content"][0]["marks"][0]["type"] for item in bullets["content"]] == [
        "bold", "italic",
    ]
    assert numbered["type"] == "orderedList"
    assert numbered["attrs"]["start"] == 3
    assert html["content"] == [{"type": "text", "text": "<script>alert(1)</script>"}]


@pytest.mark.parametrize(("filename", "content", "status_code", "detail"), [
    ("notes.pdf", b"anything", 415, ".txt or .md"),
    ("notes.txt", b"a" * (MAX_FILE_BYTES + 1), 413, "1 MB"),
    ("notes.txt", b"\xff", 400, "UTF-8"),
    ("../notes.txt", b"text", 400, "without a directory"),
])
def test_reject_invalid_uploads(client, filename, content, status_code, detail):
    response = upload(client, filename, content)
    assert response.status_code == status_code
    assert detail in response.json()["detail"]
    assert client.get("/documents").json() == []


def test_import_requires_filename_and_file_content_type(client):
    assert client.post("/documents/import", content=b"text").status_code == 422
    response = client.post("/documents/import", params={"filename": "notes.txt"}, json={"file": "text"})
    assert response.status_code == 415
    assert client.get("/documents").json() == []
