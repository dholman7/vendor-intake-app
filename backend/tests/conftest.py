from collections.abc import Callable, Iterator
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from vendor_intake.config import Settings
from vendor_intake.main import create_app
from vendor_intake.seed import DEMO_PASSWORD, seed

TODAY = date(2026, 10, 27)

W9 = "Legal Name: Acme Freight LLC\nTax ID: 12-3456789\nBusiness Type: LLC\n"
CONTRACT = "Counterparty: Acme Freight LLC\nEffective Date: 2026-01-01\nExpiry Date: 2027-12-31\n"


def insurance_text(expiry: str = "2027-03-31") -> str:
    return (
        "Insurer: Harbor Mutual\nPolicy Number: HM-55-1290\n"
        f"Coverage Amount: $2,000,000\nExpiry Date: {expiry}\n"
    )


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    settings = Settings(
        database_url="sqlite://",
        storage_dir=tmp_path / "uploads",
        extraction_delay_seconds=0,
    )
    app = create_app(settings, today=lambda: TODAY)
    with app.state.session_factory() as session:
        seed(session)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth(client: TestClient) -> Callable[[str], dict[str, str]]:
    """Returns bearer headers for a seeded user, e.g. auth("member@northwind.test")."""

    def _auth(email: str) -> dict[str, str]:
        response = client.post("/api/auth/login", json={"email": email, "password": DEMO_PASSWORD})
        assert response.status_code == 200, response.text
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    return _auth


@pytest.fixture
def member(auth: Callable[[str], dict[str, str]]) -> dict[str, str]:
    return auth("member@northwind.test")


@pytest.fixture
def reviewer(auth: Callable[[str], dict[str, str]]) -> dict[str, str]:
    return auth("reviewer@northwind.test")


@pytest.fixture
def globex(auth: Callable[[str], dict[str, str]]) -> dict[str, str]:
    return auth("member@globex.test")


class Api:
    """Thin helpers for arranging state through the public API."""

    def __init__(self, client: TestClient) -> None:
        self.client = client

    def create_vendor(self, headers: dict[str, str], name: str = "Acme Freight") -> dict[str, Any]:
        response = self.client.post(
            "/api/vendors",
            json={"name": name, "category": "logistics", "contact_email": "ops@acme.example"},
            headers=headers,
        )
        assert response.status_code == 201, response.text
        body: dict[str, Any] = response.json()
        return body

    def upload(
        self,
        headers: dict[str, str],
        vendor_id: str,
        kind: str,
        content: str | bytes,
        filename: str = "doc.txt",
        content_type: str = "text/plain",
    ) -> Any:
        data = content.encode() if isinstance(content, str) else content
        return self.client.post(
            f"/api/vendors/{vendor_id}/documents",
            data={"kind": kind},
            files={"file": (filename, data, content_type)},
            headers=headers,
        )

    def ready_vendor(
        self, headers: dict[str, str], name: str = "Acme Freight", insurance: str | None = None
    ) -> dict[str, Any]:
        """Draft vendor with all three documents uploaded and extracted."""
        vendor = self.create_vendor(headers, name)
        for kind, text in (
            ("w9", W9),
            ("insurance_certificate", insurance or insurance_text()),
            ("contract", CONTRACT),
        ):
            assert self.upload(headers, vendor["id"], kind, text).status_code == 201
        return vendor

    def in_review_vendor(
        self, headers: dict[str, str], name: str = "Acme Freight", insurance: str | None = None
    ) -> dict[str, Any]:
        vendor = self.ready_vendor(headers, name, insurance)
        response = self.client.post(f"/api/vendors/{vendor['id']}/submit", headers=headers)
        assert response.status_code == 200, response.text
        body: dict[str, Any] = response.json()
        return body

    def extractions(self, headers: dict[str, str], vendor_id: str) -> dict[str, dict[str, Any]]:
        docs = self.client.get(f"/api/vendors/{vendor_id}/documents", headers=headers).json()
        return {
            d["kind"]: self.client.get(
                f"/api/documents/{d['id']}/extraction", headers=headers
            ).json()
            for d in docs
        }

    def audit_actions(self, headers: dict[str, str], vendor_id: str) -> list[str]:
        trail = self.client.get(f"/api/vendors/{vendor_id}/audit", headers=headers).json()
        return [event["action"] for event in trail["items"]]


@pytest.fixture
def api(client: TestClient) -> Api:
    return Api(client)


def days_from_today(days: int) -> str:
    return (TODAY + timedelta(days=days)).isoformat()
