import logging
import time
from pathlib import Path

from sqlalchemy.orm import Session, sessionmaker

from vendor_intake.db import (
    Document,
    DocumentKind,
    DocumentStatus,
    Extraction,
    User,
    Vendor,
    new_id,
)
from vendor_intake.errors import AppError
from vendor_intake.repositories.audit import AuditRepository
from vendor_intake.repositories.documents import DocumentRepository, ExtractionRepository
from vendor_intake.services.extraction import extract_fields, lowest_confidence
from vendor_intake.services.storage import LocalStorage
from vendor_intake.services.vendors import ensure_editable

logger = logging.getLogger(__name__)

CONTENT_TYPES = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".txt": "text/plain",
}
GENERIC_TYPE = "application/octet-stream"


def validate_upload(filename: str, declared_type: str | None, size: int, max_bytes: int) -> str:
    """Returns the canonical content type, inferred from the extension."""
    if size > max_bytes:
        raise AppError(413, "file_too_large", f"Files must be {max_bytes} bytes or smaller")
    expected = CONTENT_TYPES.get(Path(filename).suffix.lower())
    declared = (declared_type or GENERIC_TYPE).split(";")[0].strip().lower()
    if expected is None or declared not in (expected, GENERIC_TYPE):
        allowed = ", ".join(sorted(CONTENT_TYPES))
        raise AppError(415, "unsupported_type", f"Upload a file with one of: {allowed}")
    if size == 0:
        raise AppError(422, "empty_file", "The uploaded file is empty")
    return expected


def upload_document(
    session: Session,
    storage: LocalStorage,
    user: User,
    vendor: Vendor,
    *,
    kind: DocumentKind,
    filename: str,
    content_type: str,
    data: bytes,
) -> Document:
    ensure_editable(vendor)
    document_id = new_id()
    document = Document(
        id=document_id,
        tenant_id=user.tenant_id,
        vendor_id=vendor.id,
        kind=kind,
        filename=Path(filename).name,
        content_type=content_type,
        size_bytes=len(data),
        storage_path=storage.save(user.tenant_id, document_id, data),
        uploaded_by=user.id,
    )
    DocumentRepository(session).add(document)
    AuditRepository(session).record(
        tenant_id=user.tenant_id,
        vendor_id=vendor.id,
        actor_id=user.id,
        action="document.uploaded",
        details={"document_id": document_id, "kind": kind, "filename": document.filename},
    )
    session.commit()
    return document


def process_document(
    session_factory: sessionmaker[Session],
    storage: LocalStorage,
    document_id: str,
    tenant_id: str,
    delay_seconds: float,
) -> None:
    """Background job: extract fields and record the outcome on the document."""
    if delay_seconds:
        time.sleep(delay_seconds)
    with session_factory() as session:
        document = DocumentRepository(session).get(document_id, tenant_id)
        if document is None:
            logger.warning("Document %s vanished before processing", document_id)
            return
        audit = AuditRepository(session)
        try:
            fields = extract_fields(
                DocumentKind(document.kind),
                storage.read(document.storage_path),
                document.content_type,
            )
            ExtractionRepository(session).add(
                Extraction(tenant_id=tenant_id, document_id=document.id, fields=fields)
            )
            document.status = DocumentStatus.EXTRACTED
            action, details = "document.extracted", {"lowest_confidence": lowest_confidence(fields)}
        except Exception:
            logger.exception("Extraction failed for document %s", document_id)
            session.rollback()
            document.status = DocumentStatus.FAILED
            action, details = "document.failed", {}
        audit.record(
            tenant_id=tenant_id,
            vendor_id=document.vendor_id,
            actor_id=document.uploaded_by,
            action=action,
            details={"document_id": document.id, "kind": document.kind, **details},
        )
        session.commit()
