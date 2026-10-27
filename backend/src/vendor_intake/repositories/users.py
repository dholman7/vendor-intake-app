from sqlalchemy import select
from sqlalchemy.orm import Session

from vendor_intake.db import Tenant, User


class UserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def by_email(self, email: str) -> User | None:
        return self.session.scalar(select(User).where(User.email == email.lower()))

    def get(self, user_id: str, tenant_id: str) -> User | None:
        return self.session.scalar(
            select(User).where(User.id == user_id, User.tenant_id == tenant_id)
        )

    def tenant(self, tenant_id: str) -> Tenant:
        tenant = self.session.get(Tenant, tenant_id)
        if tenant is None:
            raise LookupError(f"Tenant {tenant_id} missing for an authenticated user")
        return tenant
