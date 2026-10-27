"""features/documents.feature"""

import pytest
from fastapi.testclient import TestClient

from tests.conftest import Api, insurance_text

TEN_MIB = 10 * 1024 * 1024


def test_upload_returns_processing_then_extracts_in_background(
    client: TestClient, api: Api, member: dict[str, str]
) -> None:
    # Arrange
    vendor = api.create_vendor(member)

    # Act
    response = api.upload(member, vendor["id"], "insurance_certificate", insurance_text())

    # Assert
    assert response.status_code == 201
    assert response.json()["status"] == "processing"
    document = client.get(f"/api/documents/{response.json()['id']}", headers=member).json()
    assert document["status"] == "extracted"
    extraction = api.extractions(member, vendor["id"])["insurance_certificate"]
    assert set(extraction["fields"]) == {
        "insurer",
        "policy_number",
        "coverage_amount",
        "expiry_date",
    }
    assert all(0 <= f["confidence"] <= 1 for f in extraction["fields"].values())
    assert api.audit_actions(member, vendor["id"])[-2:] == [
        "document.uploaded",
        "document.extracted",
    ]


def test_unparseable_field_gets_null_value_and_low_confidence(
    api: Api, member: dict[str, str]
) -> None:
    # Arrange
    vendor = api.create_vendor(member)

    # Act
    api.upload(member, vendor["id"], "insurance_certificate", insurance_text("next spring"))

    # Assert
    expiry = api.extractions(member, vendor["id"])["insurance_certificate"]["fields"]["expiry_date"]
    assert expiry["value"] is None
    assert expiry["confidence"] < 0.5


@pytest.mark.parametrize(
    ("filename", "content", "content_type", "kind", "status", "code"),
    [
        ("empty.txt", b"", "text/plain", "w9", 422, "empty_file"),
        ("big.txt", b"x" * (TEN_MIB + 1), "text/plain", "w9", 413, "file_too_large"),
        ("tool.exe", b"MZ", "application/octet-stream", "w9", 415, "unsupported_type"),
        ("w9.txt", b"text", "application/pdf", "w9", 415, "unsupported_type"),
        ("w9.txt", b"text", "text/plain", "passport", 422, "validation_error"),
    ],
    ids=["empty", "over-limit", "exe", "type-mismatch", "unknown-kind"],
)
def test_invalid_uploads_are_rejected(
    api: Api,
    member: dict[str, str],
    filename: str,
    content: bytes,
    content_type: str,
    kind: str,
    status: int,
    code: str,
) -> None:
    # Arrange
    vendor = api.create_vendor(member)

    # Act
    response = api.upload(member, vendor["id"], kind, content, filename, content_type)

    # Assert
    assert response.status_code == status
    assert response.json()["error"]["code"] == code


def test_file_of_exactly_ten_mib_is_accepted(api: Api, member: dict[str, str]) -> None:
    # Arrange
    vendor = api.create_vendor(member)

    # Act
    response = api.upload(member, vendor["id"], "contract", b"x" * TEN_MIB)

    # Assert
    assert response.status_code == 201


def test_generic_content_type_is_inferred_from_extension(api: Api, member: dict[str, str]) -> None:
    # Arrange
    vendor = api.create_vendor(member)

    # Act
    response = api.upload(
        member, vendor["id"], "w9", b"Legal Name: Acme", "w9.txt", "application/octet-stream"
    )

    # Assert
    assert response.status_code == 201
    assert response.json()["content_type"] == "text/plain"


def test_documents_cannot_be_added_to_vendor_in_review(api: Api, member: dict[str, str]) -> None:
    # Arrange
    vendor = api.in_review_vendor(member)

    # Act
    response = api.upload(member, vendor["id"], "w9", "Legal Name: Acme")

    # Assert
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "vendor_locked"


def test_documents_from_another_tenant_are_invisible(
    client: TestClient, api: Api, member: dict[str, str], globex: dict[str, str]
) -> None:
    # Arrange
    vendor = api.create_vendor(globex, "Globex Only")
    document_id = api.upload(globex, vendor["id"], "w9", "Legal Name: Globex").json()["id"]

    # Act
    document = client.get(f"/api/documents/{document_id}", headers=member)
    extraction = client.get(f"/api/documents/{document_id}/extraction", headers=member)
    upload = api.upload(member, vendor["id"], "w9", "Legal Name: Intruder")

    # Assert
    assert document.status_code == 404
    assert document.json()["error"]["code"] == "document_not_found"
    assert extraction.status_code == 404
    assert upload.status_code == 404
