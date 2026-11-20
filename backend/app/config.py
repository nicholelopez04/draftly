from os import environ
from pathlib import Path
from urllib.parse import urlsplit

from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError

LOCAL_DATABASE = Path(__file__).resolve().parents[1] / "draftly.db"
LOCAL_ORIGIN = "http://localhost:5173"


def on_render() -> bool:
    return environ.get("RENDER") == "true"


def database_url() -> URL:
    value = environ.get("DATABASE_URL")
    if value is None and not on_render():
        return URL.create("sqlite", database=str(LOCAL_DATABASE))
    if not value or not value.strip():
        raise RuntimeError("Set DATABASE_URL to a PostgreSQL connection URL.")

    try:
        url = make_url(value.strip())
    except (ArgumentError, ValueError):
        raise RuntimeError("DATABASE_URL is not a valid connection URL.") from None

    if url.drivername in {"postgres", "postgresql", "postgresql+psycopg"}:
        return url.set(drivername="postgresql+psycopg")
    if not on_render() and url.drivername in {"sqlite", "sqlite+pysqlite"}:
        return url
    raise RuntimeError("DATABASE_URL must use PostgreSQL on Render, or PostgreSQL or SQLite locally.")


def cors_origins() -> list[str]:
    configured = environ.get("CORS_ALLOWED_ORIGINS")
    origins = [
        entry.strip().rstrip("/") for entry in (configured or "").split(",") if entry.strip()
    ]
    for origin in origins:
        try:
            url = urlsplit(origin)
            port = url.port
            valid = (
                url.scheme in {"http", "https"} and url.hostname and url.username is None
                and not url.path and not any(char.isspace() or char in "*?#\\" for char in origin)
                and (port is not None or not origin.endswith(":"))
            )
        except ValueError:
            valid = False
        if not valid:
            raise RuntimeError("CORS_ALLOWED_ORIGINS must contain exact HTTP or HTTPS origins.")
    if on_render() and not origins:
        raise RuntimeError("Set CORS_ALLOWED_ORIGINS to the deployed frontend origin.")
    return origins or [LOCAL_ORIGIN]
