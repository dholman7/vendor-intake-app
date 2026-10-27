from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from vendor_intake.db import User, VendorStatus
from vendor_intake.deps import current_user, get_session, get_today
from vendor_intake.repositories.audit import AuditRepository
from vendor_intake.repositories.vendors import VendorRepository
from vendor_intake.schemas import (
    ActorOut,
    AuditEventOut,
    AuditTrail,
    VendorCreate,
    VendorOut,
    VendorPage,
    VendorUpdate,
)
from vendor_intake.services import review, vendors

router = APIRouter(prefix="/vendors", tags=["vendors"])


@router.get("")
def list_vendors(
    q: str | None = Query(default=None, max_length=120),
    status: VendorStatus | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
    today: date = Depends(get_today),
) -> VendorPage:
    rows, total = VendorRepository(session).search(
        user.tenant_id, q=q, status=status, limit=limit, offset=offset
    )
    return VendorPage(
        items=[vendors.to_out(session, v, today) for v in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", status_code=201)
def create_vendor(
    body: VendorCreate,
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
    today: date = Depends(get_today),
) -> VendorOut:
    return vendors.to_out(session, vendors.create_vendor(session, user, body), today)


@router.get("/{vendor_id}")
def get_vendor(
    vendor_id: str,
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
    today: date = Depends(get_today),
) -> VendorOut:
    return vendors.to_out(session, vendors.get_vendor(session, vendor_id, user.tenant_id), today)


@router.patch("/{vendor_id}")
def update_vendor(
    vendor_id: str,
    body: VendorUpdate,
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
    today: date = Depends(get_today),
) -> VendorOut:
    vendor = vendors.get_vendor(session, vendor_id, user.tenant_id)
    return vendors.to_out(session, vendors.update_vendor(session, user, vendor, body), today)


@router.post("/{vendor_id}/submit")
def submit_vendor(
    vendor_id: str,
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
    today: date = Depends(get_today),
) -> VendorOut:
    vendor = vendors.get_vendor(session, vendor_id, user.tenant_id)
    return vendors.to_out(session, review.submit_vendor(session, user, vendor), today)


@router.get("/{vendor_id}/audit")
def audit_trail(
    vendor_id: str,
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
) -> AuditTrail:
    vendor = vendors.get_vendor(session, vendor_id, user.tenant_id)
    return AuditTrail(
        items=[
            AuditEventOut(
                id=event.id,
                action=event.action,
                actor=ActorOut.model_validate(actor),
                at=event.at,
                details=event.details,
            )
            for event, actor in AuditRepository(session).for_vendor(vendor.id, user.tenant_id)
        ]
    )
