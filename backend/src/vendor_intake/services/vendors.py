from datetime import date, timedelta

from sqlalchemy.orm import Session

from vendor_intake.db import DocumentKind, DocumentStatus, User, Vendor, VendorStatus
from vendor_intake.errors import AppError, not_found
from vendor_intake.repositories.audit import AuditRepository
from vendor_intake.repositories.documents import DocumentRepository, ExtractionRepository
from vendor_intake.repositories.vendors import VendorRepository
from vendor_intake.schemas import VendorCreate, VendorOut, VendorUpdate
from vendor_intake.services.extraction import field_date

EDITABLE_STATUSES = {VendorStatus.DRAFT, VendorStatus.REJECTED}
EXPIRING_SOON_DAYS = 30


def get_vendor(session: Session, vendor_id: str, tenant_id: str) -> Vendor:
    vendor = VendorRepository(session).get(vendor_id, tenant_id)
    if vendor is None:
        raise not_found("vendor")
    return vendor


def ensure_editable(vendor: Vendor) -> None:
    if vendor.status not in EDITABLE_STATUSES:
        raise AppError(409, "vendor_locked", f"A vendor in status {vendor.status} cannot change")


def _ensure_name_free(session: Session, tenant_id: str, name: str, exclude: str | None) -> None:
    if VendorRepository(session).name_taken(tenant_id, name, exclude_id=exclude):
        raise AppError(409, "vendor_name_taken", f"A vendor named {name!r} already exists")


def create_vendor(session: Session, user: User, data: VendorCreate) -> Vendor:
    _ensure_name_free(session, user.tenant_id, data.name, exclude=None)
    vendor = Vendor(
        tenant_id=user.tenant_id,
        name=data.name,
        name_key=data.name.lower(),
        category=data.category,
        contact_email=str(data.contact_email).lower(),
        created_by=user.id,
    )
    VendorRepository(session).add(vendor)
    AuditRepository(session).record(
        tenant_id=user.tenant_id, vendor_id=vendor.id, actor_id=user.id, action="vendor.created"
    )
    session.commit()
    return vendor


def update_vendor(session: Session, user: User, vendor: Vendor, data: VendorUpdate) -> Vendor:
    ensure_editable(vendor)
    changes = data.model_dump(exclude_unset=True, exclude_none=True)
    if "name" in changes:
        _ensure_name_free(session, user.tenant_id, changes["name"], exclude=vendor.id)
        vendor.name_key = changes["name"].lower()
    if "contact_email" in changes:
        changes["contact_email"] = str(changes["contact_email"]).lower()
    for field, value in changes.items():
        setattr(vendor, field, value)
    if changes:
        AuditRepository(session).record(
            tenant_id=user.tenant_id,
            vendor_id=vendor.id,
            actor_id=user.id,
            action="vendor.updated",
            details={"fields": sorted(changes)},
        )
    session.commit()
    return vendor


def vendor_flags(session: Session, vendor: Vendor, today: date) -> list[str]:
    insurance = (
        DocumentRepository(session)
        .latest_by_kind(vendor.id, vendor.tenant_id)
        .get(DocumentKind.INSURANCE_CERTIFICATE)
    )
    if insurance is None or insurance.status != DocumentStatus.EXTRACTED:
        return []
    extraction = ExtractionRepository(session).for_document(insurance.id, vendor.tenant_id)
    expiry = field_date(extraction.fields, "expiry_date") if extraction else None
    if expiry is None:
        return []
    if expiry < today:
        return ["insurance_expired"]
    if expiry <= today + timedelta(days=EXPIRING_SOON_DAYS):
        return ["insurance_expiring_soon"]
    return []


def to_out(session: Session, vendor: Vendor, today: date) -> VendorOut:
    return VendorOut.model_validate(
        {
            **{c: getattr(vendor, c) for c in VendorOut.model_fields if c != "flags"},
            "flags": vendor_flags(session, vendor, today),
        }
    )
