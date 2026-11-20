from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.dialects import postgresql
from sqlmodel import SQLModel, create_engine

from app.config import LOCAL_DATABASE, database_url
from app.main import create_app


def test_local_database_fallback(monkeypatch):
    monkeypatch.delenv("RENDER", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    url = database_url()
    assert url.get_backend_name() == "sqlite"
    assert url.database == str(LOCAL_DATABASE)


@pytest.mark.parametrize("scheme", ["postgres", "postgresql", "postgresql+psycopg"])
def test_postgres_urls_keep_credentials_and_provider_options(monkeypatch, scheme):
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("DATABASE_URL", f"{scheme}://demo:fake%40password@db.example/draftly?sslmode=require")
    url = database_url()
    assert url.drivername == "postgresql+psycopg"
    assert url.password == "fake@password"
    assert url.database == "draftly"
    assert url.query["sslmode"] == "require"


def test_app_can_construct_the_psycopg_engine(monkeypatch):
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("DATABASE_URL", "postgresql://demo@db.example/draftly")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://draftly.example")
    assert create_app().title == "Draftly"


@pytest.mark.parametrize("value", [None, "", "sqlite:///draftly.db", "malformed"])
def test_render_requires_postgres(monkeypatch, value):
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://draftly.example")
    if value is None:
        monkeypatch.delenv("DATABASE_URL", raising=False)
    else:
        monkeypatch.setenv("DATABASE_URL", value)
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        create_app()


@pytest.mark.parametrize("origins", ["", "*", "https://*.vercel.app", "https://draftly.example/path"])
def test_render_requires_explicit_cors_origins(monkeypatch, origins):
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", origins)
    with pytest.raises(RuntimeError, match="CORS_ALLOWED_ORIGINS"):
        create_app()


def test_configured_cors_and_public_health(monkeypatch, tmp_path):
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", " https://draftly.example/ , https://preview.example ")
    engine = create_engine(f"sqlite:///{(tmp_path / 'cors.db').as_posix()}")
    with TestClient(create_app(engine)) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json() == {"status": "ok"}
        for origin, expected in [
            ("https://draftly.example", 200),
            ("https://preview.example", 200),
            ("https://draftly.example.other", 400),
            ("http://localhost:5173", 400),
        ]:
            preflight = client.options("/documents/test/shares/2", headers={
                "Origin": origin,
                "Access-Control-Request-Method": "DELETE",
                "Access-Control-Request-Headers": "X-Demo-User-Id, Content-Type",
            })
            assert preflight.status_code == expected
            assert preflight.headers.get("access-control-allow-origin") == (origin if expected == 200 else None)
    engine.dispose()


def test_postgres_bootstrap_locks_and_seeds_in_one_transaction(monkeypatch):
    engine = MagicMock()
    engine.dialect = postgresql.dialect()
    connection = engine.begin.return_value.__enter__.return_value
    create_tables = MagicMock()
    monkeypatch.setattr(SQLModel.metadata, "create_all", create_tables)
    with TestClient(create_app(engine)) as client:
        assert client.get("/health").json() == {"status": "ok"}
    create_tables.assert_called_once_with(connection)
    lock, seed = [call.args[0] for call in connection.execute.call_args_list]
    assert "pg_advisory_xact_lock" in str(lock)
    statement = seed.compile(dialect=engine.dialect)
    assert 'INSERT INTO "user"' in str(statement)
    assert "ON CONFLICT (id) DO NOTHING" in str(statement)
    assert statement.params == {"id_m0": 1, "name_m0": "Alex Morgan", "id_m1": 2, "name_m1": "Jordan Lee"}
