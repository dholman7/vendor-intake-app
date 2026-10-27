from collections.abc import Iterator
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, ClassVar
from uuid import uuid4

from sqlalchemy import JSON, ForeignKey, String, create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool


def new_id() -> str:
    return uuid4().hex


def utcnow() -> datetime:
    return datetime.now(UTC)


class Role(StrEnum):
    MEMBER = "member"
    REVIEWER = "reviewer"
    ADMIN = "admin"


class VendorStatus(StrEnum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class VendorCategory(StrEnum):
    SOFTWARE = "software"
    SERVICES = "services"
    HARDWARE = "hardware"
    LOGISTICS = "logistics"
    OTHER = "other"


class DocumentKind(StrEnum):
    W9 = "w9"
    INSURANCE_CERTIFICATE = "insurance_certificate"
    CONTRACT = "contract"


class DocumentStatus(StrEnum):
    PROCESSING = "processing"
    EXTRACTED = "extracted"
    FAILED = "failed"


class ExtractionStatus(StrEnum):
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class Base(DeclarativeBase):
    type_annotation_map: ClassVar[dict[Any, Any]] = {dict[str, Any]: JSON}


class Tenant(Base):
    __tablename__ = "tenants"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(120), unique=True)


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[Role] = mapped_column(String(16))
    password_hash: Mapped[str] = mapped_column(String(200))


class Vendor(Base):
    __tablename__ = "vendors"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    # Lowercased name backs the per-tenant uniqueness check.
    name_key: Mapped[str] = mapped_column(String(120), index=True)
    category: Mapped[VendorCategory] = mapped_column(String(16))
    contact_email: Mapped[str] = mapped_column(String(254))
    status: Mapped[VendorStatus] = mapped_column(String(16), default=VendorStatus.DRAFT)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    submitted_at: Mapped[datetime | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    vendor_id: Mapped[str] = mapped_column(ForeignKey("vendors.id"), index=True)
    kind: Mapped[DocumentKind] = mapped_column(String(32))
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int]
    storage_path: Mapped[str] = mapped_column(String(500))
    status: Mapped[DocumentStatus] = mapped_column(String(16), default=DocumentStatus.PROCESSING)
    uploaded_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class Extraction(Base):
    __tablename__ = "extractions"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), unique=True)
    # {field_name: {"value": str | None, "confidence": float}}
    fields: Mapped[dict[str, Any]]
    status: Mapped[ExtractionStatus] = mapped_column(
        String(16), default=ExtractionStatus.PENDING_REVIEW
    )
    review_note: Mapped[str | None] = mapped_column(String(1000), default=None)
    reviewed_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), default=None)
    reviewed_at: Mapped[datetime | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    # Integer key gives a stable insertion order even when timestamps collide.
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    vendor_id: Mapped[str] = mapped_column(ForeignKey("vendors.id"), index=True)
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(64))
    details: Mapped[dict[str, Any]] = mapped_column(default=dict)
    at: Mapped[datetime] = mapped_column(default=utcnow)


def make_engine(url: str) -> Engine:
    if url.startswith("sqlite"):
        in_memory = url in ("sqlite://", "sqlite:///:memory:")
        engine = create_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool if in_memory else None,
        )

        @event.listens_for(engine, "connect")
        def _enable_fks(dbapi_conn: Any, _: Any) -> None:
            dbapi_conn.execute("PRAGMA foreign_keys=ON")

        return engine
    return create_engine(url)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(engine, expire_on_commit=False)


def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    with factory() as session:
        yield session
