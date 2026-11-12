"""Provider verification: replays the web app's contract against the real API.

The contract comes from the frontend's consumer tests (frontend/pact), either from a local file
in ../pacts or, when PACT_BROKER_BASE_URL is set, from a Pact Broker, with the results published
back for can-i-deploy. With neither, the test is skipped.

The API runs in-process on a free port over an in-memory database seeded once. Each interaction's
provider states set it up: the signed-in state resets vendor data and sets the role of a dedicated
contract user, and the rest create the rows the interaction names, with the ids it names.
Requests carry that user's session cookie, injected here, since contracts don't carry credentials.
"""

import os
import socket
import threading
import time
from collections.abc import Iterator
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
import uvicorn
from pact import Verifier
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from vendor_intake.config import Settings
from vendor_intake.db import (
    AuditEvent,
    Document,
    DocumentKind,
    DocumentStatus,
    Extraction,
    Role,
    User,
    Vendor,
    VendorCategory,
    VendorStatus,
    utcnow,
)
from vendor_intake.main import create_app
from vendor_intake.security import hash_password, issue_token
from vendor_intake.seed import seed

PROVIDER = "vendor-intake-api"
PACTS = Path(__file__).resolve().parents[3] / "pacts"
# The contract user every verified request acts as; its role is set per interaction.
ACTOR_ID = "a0000000000000000000000000000001"
BROKER = os.environ.get("PACT_BROKER_BASE_URL")

pytestmark = pytest.mark.skipif(
    not BROKER and not list(PACTS.glob("*.json")),
    reason="no contract: run `npm run test:pact` in frontend/, or set PACT_BROKER_BASE_URL",
)


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port: int = sock.getsockname()[1]
        return port


class Provider:
    """The API under verification, and the state handlers that set it up."""

    def __init__(self) -> None:
        settings = Settings(database_url="sqlite://", extraction_delay_seconds=0)
        self.app = create_app(settings)
        self.sessions = self.app.state.session_factory
        with self.sessions() as session:
            seed(session)
            # The demo member's tenant, so the contract user shares its users and data.
            member = session.scalars(
                select(User).where(User.email == "member@northwind.test")
            ).one()
            actor = User(
                id=ACTOR_ID,
                tenant_id=member.tenant_id,
                email="contract@northwind.test",
                name="Contract Tester",
                role=Role.MEMBER,
                password_hash=hash_password("unused"),
            )
            session.add(actor)
            session.commit()
            self.tenant_id = member.tenant_id
            self.cookie = f"session={issue_token(actor, settings.jwt_secret, 24 * 60)}"
        self.port = _free_port()
        self.server = uvicorn.Server(
            uvicorn.Config(self.app, host="127.0.0.1", port=self.port, log_level="warning")
        )

    def start(self) -> None:
        self.thread = threading.Thread(target=self.server.run, daemon=True)
        self.thread.start()
        deadline = time.monotonic() + 15
        while not self.server.started:
            if time.monotonic() > deadline:
                raise RuntimeError("the API didn't start")
            time.sleep(0.05)

    # -- state handlers --------------------------------------------------------------------

    def _reset(self, session: Session) -> None:
        for model in (AuditEvent, Extraction, Document, Vendor):
            session.execute(delete(model))

    def signed_in(self, role: Role) -> Any:
        def handler(**_: Any) -> None:
            with self.sessions() as session:
                self._reset(session)
                session.get_one(User, ACTOR_ID).role = role
                session.commit()

        return handler

    def demo_member(self, **_: Any) -> None:
        with self.sessions() as session:
            self._reset(session)
            session.commit()

    def _vendor(self, session: Session, vendor_id: str, status: VendorStatus) -> Vendor:
        vendor = Vendor(
            id=vendor_id,
            tenant_id=self.tenant_id,
            name="Acme Freight",
            name_key="acme freight",
            category=VendorCategory.LOGISTICS,
            contact_email="ops@acmefreight.example",
            status=status,
            created_by=ACTOR_ID,
            submitted_at=None if status == VendorStatus.DRAFT else utcnow(),
        )
        session.add(vendor)
        return vendor

    def _extracted(
        self, session: Session, vendor_id: str, kind: DocumentKind, ids: tuple[str, str] | None
    ) -> None:
        document_id, extraction_id = ids or (None, None)
        document = Document(
            tenant_id=self.tenant_id,
            vendor_id=vendor_id,
            kind=kind,
            filename=f"{kind}.txt",
            content_type="text/plain",
            size_bytes=64,
            storage_path=f"/unused/{kind}.txt",
            status=DocumentStatus.EXTRACTED,
            uploaded_by=ACTOR_ID,
        )
        if document_id:
            document.id = document_id
        session.add(document)
        session.flush()
        fields = {
            DocumentKind.W9: {"legal_name": {"value": "Acme Freight LLC", "confidence": 0.95}},
            DocumentKind.INSURANCE_CERTIFICATE: {
                "expiry_date": {
                    "value": (utcnow() + timedelta(days=365)).date().isoformat(),
                    "confidence": 0.95,
                }
            },
            DocumentKind.CONTRACT: {
                "counterparty": {"value": "Acme Freight LLC", "confidence": 0.95}
            },
        }[kind]
        extraction = Extraction(tenant_id=self.tenant_id, document_id=document.id, fields=fields)
        if extraction_id:
            extraction.id = extraction_id
        session.add(extraction)

    def vendor(self, parameters: dict[str, Any] | None = None, **_: Any) -> None:
        params = parameters or {}
        with self.sessions() as session:
            self._vendor(session, params["id"], VendorStatus(params.get("status", "draft")))
            session.commit()

    def ready_vendor(self, parameters: dict[str, Any] | None = None, **_: Any) -> None:
        params = parameters or {}
        with self.sessions() as session:
            self._vendor(session, params["id"], VendorStatus.DRAFT)
            session.flush()
            for kind in DocumentKind:
                self._extracted(session, params["id"], kind, None)
            session.commit()

    def in_review(self, parameters: dict[str, Any] | None = None, **_: Any) -> None:
        params = parameters or {}
        with self.sessions() as session:
            self._vendor(session, params["vendor"], VendorStatus.IN_REVIEW)
            session.flush()
            self._extracted(
                session,
                params["vendor"],
                DocumentKind.W9,
                (params["document"], params["extraction"]),
            )
            session.add(
                AuditEvent(
                    tenant_id=self.tenant_id,
                    vendor_id=params["vendor"],
                    actor_id=ACTOR_ID,
                    action="vendor.submitted",
                )
            )
            session.commit()


@pytest.fixture(scope="module")
def provider() -> Iterator[Provider]:
    running = Provider()
    running.start()
    yield running
    running.server.should_exit = True
    running.thread.join(timeout=10)


def test_the_api_honors_the_web_apps_contract(provider: Provider) -> None:
    verifier = (
        Verifier(PROVIDER, host="127.0.0.1")
        .add_transport(url=f"http://127.0.0.1:{provider.port}")
        .state_handler(
            {
                "a member is signed in": provider.signed_in(Role.MEMBER),
                "a reviewer is signed in": provider.signed_in(Role.REVIEWER),
                "the demo member exists": provider.demo_member,
                "the member has a vendor": provider.vendor,
                "the member has a vendor ready to submit": provider.ready_vendor,
                "a vendor is in review with an extracted W-9": provider.in_review,
            },
            teardown=False,
        )
        .add_custom_header("Cookie", provider.cookie)
    )
    if BROKER:
        # Verify what the broker holds for the consumers, and publish the result so
        # can-i-deploy can answer for this commit.
        verifier.broker_source(BROKER)
        verifier.set_publish_options(
            version=os.environ["PACT_PROVIDER_VERSION"],
            branch=os.environ.get("PACT_PROVIDER_BRANCH"),
        )
    else:
        verifier.add_source(PACTS)
    verifier.verify()
