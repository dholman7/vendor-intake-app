from datetime import date

from sqlalchemy.orm import Session

from vendor_intake.db import (
    Document,
    DocumentKind,
    DocumentStatus,
    Extraction,
    ExtractionStatus,
    User,
    Vendor,
    VendorStatus,
    utcnow,
)
from vendor_intake.errors import AppError, not_found
from vendor_intake.repositories.audit import AuditRepository
from vendor_intake.repositories.documents import DocumentRepository, ExtractionRepository
from vendor_intake.repositories.vendors import VendorRepository
from vendor_intake.schemas import ExtractionOut, ReviewQueueItem
from vendor_intake.services.extraction import field_date, lowest_confidence
from vendor_intake.services.vendors import ensure_editable


def extraction_out(extraction: Extraction, kind: DocumentKind) -> ExtractionOut:
    return ExtractionOut.model_validate(
        {
            **{c: getattr(extraction, c) for c in ExtractionOut.model_fields if c != "kind"},
            "kind": kind,
        }
    )


def latest_extractions(session: Session, vendor: Vendor) -> list[tuple[Document, Extraction]]:
    extractions = ExtractionRepository(session)
    pairs = []
    for doc in DocumentRepository(session).latest_by_kind(vendor.id, vendor.tenant_id).values():
        extraction = extractions.for_document(doc.id, vendor.tenant_id)
        if doc.status == DocumentStatus.EXTRACTED and extraction is not None:
            pairs.append((doc, extraction))
    return pairs


def missing_kinds(session: Session, vendor: Vendor) -> list[str]:
    """Kinds lacking an extracted document; a rejected extraction needs a replacement upload."""
    ready = {
        DocumentKind(doc.kind)
        for doc, extraction in latest_extractions(session, vendor)
        if extraction.status != ExtractionStatus.REJECTED
    }
    return sorted(kind.value for kind in DocumentKind if kind not in ready)


def submit_vendor(session: Session, user: User, vendor: Vendor) -> Vendor:
    ensure_editable(vendor)
    missing = missing_kinds(session, vendor)
    if missing:
        raise AppError(
            409,
            "documents_incomplete",
            "Upload and process every required document before submitting",
            missing_kinds=missing,
        )
    vendor.status = VendorStatus.IN_REVIEW
    vendor.submitted_at = utcnow()
    AuditRepository(session).record(
        tenant_id=user.tenant_id, vendor_id=vendor.id, actor_id=user.id, action="vendor.submitted"
    )
    session.commit()
    return vendor


def review_queue(session: Session, tenant_id: str) -> list[ReviewQueueItem]:
    items = []
    for vendor in VendorRepository(session).in_review(tenant_id):
        pending = [
            (doc, ext)
            for doc, ext in latest_extractions(session, vendor)
            if ext.status == ExtractionStatus.PENDING_REVIEW
        ]
        if not pending:
            continue
        items.append(
            ReviewQueueItem(
                vendor_id=vendor.id,
                vendor_name=vendor.name,
                submitted_at=vendor.submitted_at,
                lowest_confidence=min(lowest_confidence(ext.fields) for _, ext in pending),
                extractions=[extraction_out(ext, DocumentKind(doc.kind)) for doc, ext in pending],
            )
        )
    return sorted(items, key=lambda i: (i.lowest_confidence, i.submitted_at or utcnow()))


def _check_insurance_approvable(extraction: Extraction, today: date) -> None:
    expiry = field_date(extraction.fields, "expiry_date")
    if expiry is None:
        raise AppError(409, "insurance_expiry_missing", "Confirm the expiry date before approving")
    if expiry < today:
        raise AppError(409, "insurance_expired", f"The insurance certificate expired on {expiry}")


def decide(
    session: Session,
    user: User,
    extraction_id: str,
    *,
    approve: bool,
    note: str | None,
    today: date,
) -> ExtractionOut:
    extraction = ExtractionRepository(session).get(extraction_id, user.tenant_id)
    if extraction is None:
        raise not_found("extraction")
    document = DocumentRepository(session).get(extraction.document_id, user.tenant_id)
    vendor = VendorRepository(session).get(document.vendor_id, user.tenant_id) if document else None
    if document is None or vendor is None:
        raise not_found("extraction")
    if vendor.status != VendorStatus.IN_REVIEW:
        raise AppError(409, "vendor_not_in_review", "Only vendors in review can be decided")
    if extraction.status != ExtractionStatus.PENDING_REVIEW:
        raise AppError(409, "already_decided", "This extraction has already been reviewed")
    kind = DocumentKind(document.kind)
    if approve and kind == DocumentKind.INSURANCE_CERTIFICATE:
        _check_insurance_approvable(extraction, today)

    extraction.status = ExtractionStatus.APPROVED if approve else ExtractionStatus.REJECTED
    extraction.review_note = note
    extraction.reviewed_by = user.id
    extraction.reviewed_at = utcnow()
    audit = AuditRepository(session)
    audit.record(
        tenant_id=user.tenant_id,
        vendor_id=vendor.id,
        actor_id=user.id,
        action=f"extraction.{extraction.status}",
        details={"extraction_id": extraction.id, "kind": kind, "note": note},
    )
    if not approve:
        vendor.status = VendorStatus.REJECTED
    elif all(
        ext.status == ExtractionStatus.APPROVED for _, ext in latest_extractions(session, vendor)
    ):
        vendor.status = VendorStatus.APPROVED
    if vendor.status != VendorStatus.IN_REVIEW:
        audit.record(
            tenant_id=user.tenant_id,
            vendor_id=vendor.id,
            actor_id=user.id,
            action=f"vendor.{vendor.status}",
        )
    session.commit()
    return extraction_out(extraction, kind)
