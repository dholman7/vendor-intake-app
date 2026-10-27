from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from vendor_intake.db import AuditEvent, User


class AuditRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def record(
        self,
        *,
        tenant_id: str,
        vendor_id: str,
        actor_id: str,
        action: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.session.add(
            AuditEvent(
                tenant_id=tenant_id,
                vendor_id=vendor_id,
                actor_id=actor_id,
                action=action,
                details=details or {},
            )
        )

    def for_vendor(self, vendor_id: str, tenant_id: str) -> list[tuple[AuditEvent, User]]:
        rows = self.session.execute(
            select(AuditEvent, User)
            .join(User, User.id == AuditEvent.actor_id)
            .where(AuditEvent.vendor_id == vendor_id, AuditEvent.tenant_id == tenant_id)
            .order_by(AuditEvent.id)
        )
        return [(event, user) for event, user in rows]
