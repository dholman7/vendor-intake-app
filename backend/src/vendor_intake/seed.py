"""Demo data. Run with `python -m vendor_intake.seed`; skips when tenants already exist.

Every seeded account uses the password `demo-password`. Demo use only.
"""

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from vendor_intake.config import get_settings
from vendor_intake.db import (
    Base,
    Role,
    Tenant,
    User,
    Vendor,
    VendorCategory,
    VendorStatus,
    make_engine,
    make_session_factory,
)
from vendor_intake.security import hash_password

logger = logging.getLogger(__name__)

DEMO_PASSWORD = "demo-password"  # noqa: S105 - documented demo credential

USERS = [
    ("Northwind Supply", "admin@northwind.test", "Avery Admin", Role.ADMIN),
    ("Northwind Supply", "reviewer@northwind.test", "Riley Reviewer", Role.REVIEWER),
    ("Northwind Supply", "member@northwind.test", "Morgan Member", Role.MEMBER),
    ("Globex Procurement", "member@globex.test", "Gale Globex", Role.MEMBER),
]

VENDORS = [
    ("Harborline Logistics", VendorCategory.LOGISTICS, "ops@harborline.example"),
    ("Brightwire Software", VendorCategory.SOFTWARE, "legal@brightwire.example"),
    ("Cobalt Facilities", VendorCategory.SERVICES, "accounts@cobalt.example"),
]


def seed(session: Session) -> bool:
    if session.scalar(select(Tenant.id)) is not None:
        return False
    tenants: dict[str, Tenant] = {}
    users: dict[str, User] = {}
    password_hash = hash_password(DEMO_PASSWORD)
    for tenant_name, email, name, role in USERS:
        tenant = tenants.setdefault(tenant_name, Tenant(name=tenant_name))
        session.add(tenant)
        session.flush()
        users[email] = User(
            tenant_id=tenant.id, email=email, name=name, role=role, password_hash=password_hash
        )
        session.add(users[email])
    session.flush()
    member = users["member@northwind.test"]
    for name, category, contact in VENDORS:
        session.add(
            Vendor(
                tenant_id=member.tenant_id,
                name=name,
                name_key=name.lower(),
                category=category,
                contact_email=contact,
                status=VendorStatus.DRAFT,
                created_by=member.id,
            )
        )
    session.commit()
    return True


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    settings.prepare_paths()
    engine = make_engine(settings.database_url)
    Base.metadata.create_all(engine)
    with make_session_factory(engine)() as session:
        logger.info("Seeded demo data" if seed(session) else "Demo data already present")


if __name__ == "__main__":
    main()
