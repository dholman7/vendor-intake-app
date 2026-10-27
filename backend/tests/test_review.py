"""features/review.feature"""

import pytest
from fastapi.testclient import TestClient
from httpx import Response

from tests.conftest import Api, days_from_today, insurance_text


def _decide(
    client: TestClient, headers: dict[str, str], extraction_id: str, decision: str, note: str = ""
) -> Response:
    body = {"decision": decision} | ({"note": note} if note else {})
    response: Response = client.post(
        f"/api/extractions/{extraction_id}/decision", json=body, headers=headers
    )
    return response


def _status(client: TestClient, headers: dict[str, str], vendor_id: str) -> str:
    status: str = client.get(f"/api/vendors/{vendor_id}", headers=headers).json()["status"]
    return status


def test_submit_vendor_with_all_documents(
    client: TestClient, api: Api, member: dict[str, str]
) -> None:
    # Arrange
    vendor = api.ready_vendor(member)

    # Act
    response = client.post(f"/api/vendors/{vendor['id']}/submit", headers=member)

    # Assert
    assert response.status_code == 200
    assert response.json()["status"] == "in_review"
    assert response.json()["submitted_at"] is not None
    assert api.audit_actions(member, vendor["id"])[-1] == "vendor.submitted"


def test_submit_with_missing_documents_lists_them(
    client: TestClient, api: Api, member: dict[str, str]
) -> None:
    # Arrange
    vendor = api.create_vendor(member)
    api.upload(member, vendor["id"], "w9", "Legal Name: Acme\nTax ID: 123456789\n")

    # Act
    response = client.post(f"/api/vendors/{vendor['id']}/submit", headers=member)

    # Assert
    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "documents_incomplete"
    assert error["missing_kinds"] == ["contract", "insurance_certificate"]


def test_queue_orders_lowest_confidence_first(
    client: TestClient, api: Api, member: dict[str, str], reviewer: dict[str, str]
) -> None:
    # Arrange: "next spring" makes the expiry date unparseable (confidence 0.3).
    confident = api.in_review_vendor(member, "Confident Co")
    shaky = api.in_review_vendor(member, "Shaky Co", insurance_text("next spring"))

    # Act
    queue = client.get("/api/review-queue", headers=reviewer).json()

    # Assert
    assert [item["vendor_id"] for item in queue] == [shaky["id"], confident["id"]]
    assert queue[0]["lowest_confidence"] == 0.3
    assert len(queue[0]["extractions"]) == 3


def test_members_cannot_see_review_queue(client: TestClient, member: dict[str, str]) -> None:
    # Act
    response = client.get("/api/review-queue", headers=member)

    # Assert
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_members_cannot_decide_extractions(
    client: TestClient, api: Api, member: dict[str, str]
) -> None:
    # Arrange
    vendor = api.in_review_vendor(member)
    w9 = api.extractions(member, vendor["id"])["w9"]

    # Act
    response = _decide(client, member, w9["id"], "approve")

    # Assert
    assert response.status_code == 403


def test_approving_every_extraction_approves_vendor(
    client: TestClient, api: Api, member: dict[str, str], reviewer: dict[str, str]
) -> None:
    # Arrange
    vendor = api.in_review_vendor(member)
    extractions = api.extractions(member, vendor["id"]).values()

    # Act
    statuses = [_decide(client, reviewer, e["id"], "approve").status_code for e in extractions]

    # Assert
    assert statuses == [200, 200, 200]
    assert _status(client, member, vendor["id"]) == "approved"
    assert api.audit_actions(member, vendor["id"])[-2:] == [
        "extraction.approved",
        "vendor.approved",
    ]


def test_vendor_stays_in_review_until_every_extraction_is_approved(
    client: TestClient, api: Api, member: dict[str, str], reviewer: dict[str, str]
) -> None:
    # Arrange
    vendor = api.in_review_vendor(member)
    w9 = api.extractions(member, vendor["id"])["w9"]

    # Act
    _decide(client, reviewer, w9["id"], "approve")

    # Assert
    assert _status(client, member, vendor["id"]) == "in_review"


def test_reject_requires_note_and_returns_vendor_to_member(
    client: TestClient, api: Api, member: dict[str, str], reviewer: dict[str, str]
) -> None:
    # Arrange
    vendor = api.in_review_vendor(member)
    w9 = api.extractions(member, vendor["id"])["w9"]

    # Act
    without_note = _decide(client, reviewer, w9["id"], "reject")
    with_note = _decide(client, reviewer, w9["id"], "reject", "Tax ID does not match")

    # Assert
    assert without_note.status_code == 422
    assert without_note.json()["error"]["fields"][0]["field"] == "note"
    assert with_note.status_code == 200
    assert _status(client, member, vendor["id"]) == "rejected"
    assert api.audit_actions(member, vendor["id"])[-2:] == [
        "extraction.rejected",
        "vendor.rejected",
    ]


def test_rejected_document_must_be_replaced_before_resubmitting(
    client: TestClient, api: Api, member: dict[str, str], reviewer: dict[str, str]
) -> None:
    # Arrange
    vendor = api.in_review_vendor(member)
    w9 = api.extractions(member, vendor["id"])["w9"]
    _decide(client, reviewer, w9["id"], "reject", "Tax ID does not match")

    # Act
    blocked = client.post(f"/api/vendors/{vendor['id']}/submit", headers=member)
    api.upload(member, vendor["id"], "w9", "Legal Name: Acme\nTax ID: 987654321\n")
    resubmitted = client.post(f"/api/vendors/{vendor['id']}/submit", headers=member)

    # Assert
    assert blocked.json()["error"]["missing_kinds"] == ["w9"]
    assert resubmitted.status_code == 200


def test_extraction_cannot_be_decided_twice(
    client: TestClient, api: Api, member: dict[str, str], reviewer: dict[str, str]
) -> None:
    # Arrange
    vendor = api.in_review_vendor(member)
    w9 = api.extractions(member, vendor["id"])["w9"]
    _decide(client, reviewer, w9["id"], "approve")

    # Act
    response = _decide(client, reviewer, w9["id"], "approve")

    # Assert
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "already_decided"


@pytest.mark.parametrize(
    ("insurance", "code"),
    [
        (insurance_text(days_from_today(-1)), "insurance_expired"),
        (insurance_text("next spring"), "insurance_expiry_missing"),
    ],
)
def test_insurance_without_a_valid_future_expiry_cannot_be_approved(
    client: TestClient,
    api: Api,
    member: dict[str, str],
    reviewer: dict[str, str],
    insurance: str,
    code: str,
) -> None:
    # Arrange
    vendor = api.in_review_vendor(member, insurance=insurance)
    certificate = api.extractions(member, vendor["id"])["insurance_certificate"]

    # Act
    response = _decide(client, reviewer, certificate["id"], "approve")

    # Assert
    assert response.status_code == 409
    assert response.json()["error"]["code"] == code


@pytest.mark.parametrize(
    ("days", "flags"),
    [
        (-1, ["insurance_expired"]),
        (0, ["insurance_expiring_soon"]),
        (30, ["insurance_expiring_soon"]),
        (31, []),
    ],
)
def test_insurance_expiry_flags(
    client: TestClient, api: Api, member: dict[str, str], days: int, flags: list[str]
) -> None:
    # Arrange
    vendor = api.create_vendor(member)
    api.upload(member, vendor["id"], "insurance_certificate", insurance_text(days_from_today(days)))

    # Act
    response = client.get(f"/api/vendors/{vendor['id']}", headers=member)

    # Assert
    assert response.json()["flags"] == flags
