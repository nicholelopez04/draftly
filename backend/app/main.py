from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, StringConstraints, field_serializer, model_validator
from sqlalchemy import JSON, Engine
from sqlmodel import Field, Session, SQLModel, create_engine, select

DEFAULT_TITLE = "Untitled document"
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

    demo_owner_id = 1

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        SQLModel.metadata.create_all(engine)
        with Session(engine) as session:
            if session.get(User, demo_owner_id) is None:
                session.add(User(id=demo_owner_id, name="Alex Morgan"))
                session.commit()
        yield

    app = FastAPI(title="Draftly", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["Content-Type"],
    )

    def get_session():
        with Session(engine) as session:
            yield session

    def get_owned_document(document_id: UUID, session: Session) -> Document:
        document = session.get(Document, document_id)
        if document is None or document.owner_id != demo_owner_id:
            raise HTTPException(status_code=404, detail="Document not found.")
        return document

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/documents", response_model=list[DocumentSummary])
    def list_documents(session: Session = Depends(get_session)):
        return session.exec(
            select(Document)
            .where(Document.owner_id == demo_owner_id)
            .order_by(Document.updated_at.desc(), Document.id)
        ).all()

    @app.post("/documents", response_model=DocumentDetail, status_code=status.HTTP_201_CREATED)
    def create_document(payload: CreateDocument, session: Session = Depends(get_session)):
        document = Document(
            owner_id=demo_owner_id,
            title=payload.title,
            content={"type": "doc", "content": [{"type": "paragraph"}]},
        )
        session.add(document)
        session.commit()
        session.refresh(document)
        return document

    @app.get("/documents/{document_id}", response_model=DocumentDetail)
    def read_document(document_id: UUID, session: Session = Depends(get_session)):
        return get_owned_document(document_id, session)

    @app.patch("/documents/{document_id}", response_model=DocumentDetail)
    def update_document(document_id: UUID, payload: UpdateDocument, session: Session = Depends(get_session)):
        document = get_owned_document(document_id, session)
        if payload.title is not None:
            document.title = payload.title
        if payload.content is not None:
            document.content = payload.content.model_dump(exclude_unset=True)
        document.updated_at = utc_now()
        session.commit()
        session.refresh(document)
        return document

    return app


app = create_app()
