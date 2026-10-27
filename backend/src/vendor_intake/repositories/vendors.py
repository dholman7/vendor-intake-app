from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vendor_intake.db import Vendor, VendorStatus


class VendorRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, vendor: Vendor) -> None:
        self.session.add(vendor)
        self.session.flush()

    def get(self, vendor_id: str, tenant_id: str) -> Vendor | None:
        return self.session.scalar(
            select(Vendor).where(Vendor.id == vendor_id, Vendor.tenant_id == tenant_id)
        )

    def name_taken(self, tenant_id: str, name: str, exclude_id: str | None = None) -> bool:
        query = select(Vendor.id).where(
            Vendor.tenant_id == tenant_id, Vendor.name_key == name.lower()
        )
        if exclude_id:
            query = query.where(Vendor.id != exclude_id)
        return self.session.scalar(query) is not None

    def search(
        self,
        tenant_id: str,
        *,
        q: str | None,
        status: VendorStatus | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Vendor], int]:
        query = select(Vendor).where(Vendor.tenant_id == tenant_id)
        if q:
            query = query.where(Vendor.name_key.contains(q.lower()))
        if status:
            query = query.where(Vendor.status == status)
        total = self.session.scalar(select(func.count()).select_from(query.subquery())) or 0
        rows = self.session.scalars(
            query.order_by(Vendor.created_at.desc(), Vendor.id).limit(limit).offset(offset)
        )
        return list(rows), total

    def in_review(self, tenant_id: str) -> list[Vendor]:
        return list(
            self.session.scalars(
                select(Vendor).where(
                    Vendor.tenant_id == tenant_id, Vendor.status == VendorStatus.IN_REVIEW
                )
            )
        )
