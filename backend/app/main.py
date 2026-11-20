from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, StringConstraints, field_serializer, model_validator
from sqlalchemy import JSON, Engine, delete
from sqlalchemy.dialects.sqlite import insert
from sqlmodel import Field, Session, SQLModel, create_engine, select

from .imports import read_import

DEFAULT_TITLE = "Untitled document"
DEMO_USERS = {1: "Alex Morgan", 2: "Jordan Lee"}
DATABASE = Path(__file__).resolve().parents[1] / "draftly.db"
Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


def utc_now() -> datetime:
    return datetime.now(UTC)


class User(SQLModel, table=True):
    id: int = Field(primary_key=True)
    name: str


class Document(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    owner_id: int = Field(foreign_key="user.id", index=True)
    title: str
    content: dict = Field(sa_type=JSON)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class DocumentShare(SQLModel, table=True):
    document_id: UUID = Field(foreign_key="document.id", primary_key=True)
    user_id: int = Field(foreign_key="user.id", primary_key=True, index=True)
    created_at: datetime = Field(default_factory=utc_now)


class ShareRequest(BaseModel):
    user_id: int


class DemoUser(BaseModel):
    id: int
    name: str


class ContentMark(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["bold", "italic", "underline", "strike", "code", "link"]
    attrs: dict | None = None


class ContentNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal[
        "doc", "paragraph", "heading", "text", "hardBreak", "horizontalRule",
        "blockquote", "codeBlock", "bulletList", "orderedList", "listItem",
    ]
    attrs: dict | None = None
    content: list["ContentNode"] | None = None
    marks: list[ContentMark] | None = None
    text: str | None = None

    @model_validator(mode="after")
    def validate_children(self):
        children = [child.type for child in self.content or []]
        blocks = {"paragraph", "heading", "horizontalRule", "blockquote",
                  "codeBlock", "bulletList", "orderedList"}

        match self.type:
            case "doc" | "blockquote":
                valid = bool(children) and all(child in blocks for child in children)
            case "listItem":
                valid = children[:1] == ["paragraph"] and all(child in blocks for child in children)
            case "bulletList" | "orderedList":
                valid = bool(children) and all(child == "listItem" for child in children)
            case "paragraph" | "heading":
                valid = all(child in {"text", "hardBreak"} for child in children)
            case "codeBlock":
                valid = all(child.type == "text" and not child.marks for child in self.content or [])
            case _:
                valid = not children

        if not valid:
            raise ValueError(f"Invalid children for {self.type}.")
        if (self.type == "text" and not self.text) or (self.type != "text" and self.text is not None):
            raise ValueError("Only text nodes can contain text, and it must be nonempty.")
        if self.marks and self.type not in {"text", "hardBreak"}:
            raise ValueError("Marks must be applied to inline content.")
        return self


class EditorContent(ContentNode):
    type: Literal["doc"]
    content: list[ContentNode] = Field(min_length=1)
    text: None = None
    marks: None = None


class CreateDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Title = DEFAULT_TITLE


class UpdateDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Title | None = None
    content: EditorContent | None = None

    @model_validator(mode="after")
    def require_changes(self):
        if not self.model_fields_set or any(
            getattr(self, name) is None for name in self.model_fields_set
        ):
            raise ValueError("Provide a title or content. Fields cannot be null.")
        return self


class DocumentSummary(BaseModel):
    id: UUID
    owner_id: int
    owner_name: str
    title: str
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at")
    def serialize_utc(self, value: datetime) -> str:
        # SQLite returns stored UTC timestamps without timezone information.
        return value.replace(tzinfo=UTC).isoformat()


class DocumentDetail(DocumentSummary):
    content: dict


def create_app(engine: Engine | None = None) -> FastAPI:
    if engine is None:
        engine = create_engine(f"sqlite:///{DATABASE.as_posix()}", connect_args={"check_same_thread": False})

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        SQLModel.metadata.create_all(engine)
        with Session(engine) as session:
            session.execute(
                insert(User).values([{"id": user_id, "name": name} for user_id, name in DEMO_USERS.items()])
                .on_conflict_do_nothing(index_elements=["id"])
            )
            session.commit()
        yield

    app = FastAPI(title="Draftly", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "X-Demo-User-Id"],
    )

    def get_session():
        with Session(engine) as session:
            yield session

    def require_demo_user(
        user_id: Annotated[int, Header(alias="X-Demo-User-Id")],
        session: Session = Depends(get_session),
    ) -> int:
        if user_id not in DEMO_USERS or session.get(User, user_id) is None:
            raise HTTPException(status_code=400, detail="Unknown demo user.")
        return user_id

    def get_accessible_document(
        document_id: UUID, session: Session, user_id: int, *, owner_only: bool = False,
    ) -> Document:
        document = session.get(Document, document_id)
        if document is not None:
            if document.owner_id == user_id:
                return document
            if not owner_only and session.get(DocumentShare, (document_id, user_id)):
                return document
        raise HTTPException(status_code=404, detail="Document not found.")

    def document_response(document: Document, session: Session) -> dict:
        return {**document.model_dump(), "owner_name": session.get(User, document.owner_id).name}

    def store_document(session: Session, user_id: int, title: str, content: dict) -> dict:
        document = Document(owner_id=user_id, title=title, content=content)
        session.add(document)
        session.commit()
        session.refresh(document)
        return document_response(document, session)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/demo-users", response_model=list[DemoUser])
    def list_demo_users(
        session: Session = Depends(get_session), _user_id: int = Depends(require_demo_user),
    ):
        return session.exec(select(User).where(User.id.in_(DEMO_USERS)).order_by(User.id)).all()

    @app.get("/documents", response_model=list[DocumentSummary])
    def list_documents(session: Session = Depends(get_session), user_id: int = Depends(require_demo_user)):
        shared_ids = select(DocumentShare.document_id).where(DocumentShare.user_id == user_id)
        rows = session.exec(
            select(Document.id, Document.owner_id, User.name, Document.title, Document.created_at, Document.updated_at)
            .join(User, User.id == Document.owner_id)
            .where((Document.owner_id == user_id) | Document.id.in_(shared_ids))
            .order_by(Document.updated_at.desc(), Document.id)
        )
        return [
            DocumentSummary(id=id_, owner_id=owner_id, owner_name=owner_name, title=title,
                            created_at=created_at, updated_at=updated_at)
            for id_, owner_id, owner_name, title, created_at, updated_at in rows
        ]

    @app.post("/documents", response_model=DocumentDetail, status_code=status.HTTP_201_CREATED)
    def create_document(
        payload: CreateDocument, session: Session = Depends(get_session),
        user_id: int = Depends(require_demo_user),
    ):
        return store_document(session, user_id, payload.title, {"type": "doc", "content": [{"type": "paragraph"}]})

    @app.post("/documents/import", response_model=DocumentDetail, status_code=status.HTTP_201_CREATED)
    async def import_document(
        request: Request, filename: str, session: Session = Depends(get_session),
        user_id: int = Depends(require_demo_user),
    ):
        title, content = await read_import(request, filename)
        return store_document(session, user_id, title, content)

    @app.get("/documents/{document_id}", response_model=DocumentDetail)
    def read_document(
        document_id: UUID, session: Session = Depends(get_session), user_id: int = Depends(require_demo_user),
    ):
        return document_response(get_accessible_document(document_id, session, user_id), session)

    @app.patch("/documents/{document_id}", response_model=DocumentDetail)
    def update_document(
        document_id: UUID, payload: UpdateDocument, session: Session = Depends(get_session),
        user_id: int = Depends(require_demo_user),
    ):
        document = get_accessible_document(document_id, session, user_id, owner_only=True)
        if payload.title is not None:
            document.title = payload.title
        if payload.content is not None:
            document.content = payload.content.model_dump(exclude_unset=True)
        document.updated_at = utc_now()
        session.commit()
        session.refresh(document)
        return document_response(document, session)

    @app.get("/documents/{document_id}/shares", response_model=list[DocumentShare])
    def list_shares(
        document_id: UUID, session: Session = Depends(get_session), user_id: int = Depends(require_demo_user),
    ):
        get_accessible_document(document_id, session, user_id, owner_only=True)
        return session.exec(select(DocumentShare).where(DocumentShare.document_id == document_id)).all()

    @app.post("/documents/{document_id}/shares", status_code=204)
    def grant_share(
        document_id: UUID, payload: ShareRequest, session: Session = Depends(get_session),
        user_id: int = Depends(require_demo_user),
    ):
        get_accessible_document(document_id, session, user_id, owner_only=True)
        if payload.user_id == user_id:
            raise HTTPException(status_code=400, detail="You already own this document.")
        if payload.user_id not in DEMO_USERS or session.get(User, payload.user_id) is None:
            raise HTTPException(status_code=400, detail="Unknown demo user.")
        session.execute(
            insert(DocumentShare).values(document_id=document_id, user_id=payload.user_id, created_at=utc_now())
            .on_conflict_do_nothing(index_elements=["document_id", "user_id"])
        )
        session.commit()
        return Response(status_code=204)

    @app.delete("/documents/{document_id}/shares/{recipient_id}", status_code=204)
    def revoke_share(
        document_id: UUID, recipient_id: int, session: Session = Depends(get_session),
        user_id: int = Depends(require_demo_user),
    ):
        get_accessible_document(document_id, session, user_id, owner_only=True)
        session.execute(delete(DocumentShare).where(
            DocumentShare.document_id == document_id, DocumentShare.user_id == recipient_id,
        ))
        session.commit()
        return Response(status_code=204)

    return app


app = create_app()
