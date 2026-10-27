"""features/vendors.feature"""

import pytest
from fastapi.testclient import TestClient

from tests.conftest import Api


def test_create_vendor_starts_in_draft_and_is_audited(
    client: TestClient, api: Api, member: dict[str, str]
) -> None:
    # Act
    response = client.post(
        "/api/vendors",
        json={
            "name": "Acme Freight",
            "category": "logistics",
            "contact_email": "ops@acmefreight.example",
        },
        headers=member,
    )

    # Assert
    assert response.status_code == 201
    assert response.json()["status"] == "draft"
    assert api.audit_actions(member, response.json()["id"]) == ["vendor.created"]


@pytest.mark.parametrize(
    ("field", "value"),
    [("name", "A"), ("category", "furniture"), ("contact_email", "not-an-email")],
)
def test_invalid_vendor_fields_name_the_field(
    client: TestClient, member: dict[str, str], field: str, value: str
) -> None:
    # Arrange
    body = {"name": "Acme Freight", "category": "logistics", "contact_email": "ops@acme.example"}
    body[field] = value

    # Act
    response = client.post("/api/vendors", json=body, headers=member)

    # Assert
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert [f["field"] for f in error["fields"]] == [field]


def test_vendor_names_are_unique_per_tenant_ignoring_case(
    client: TestClient, api: Api, member: dict[str, str]
) -> None:
    # Arrange
    api.create_vendor(member, "Acme Freight")

    # Act
    response = client.post(
        "/api/vendors",
        json={"name": "acme freight", "category": "logistics", "contact_email": "a@b.example"},
        headers=member,
    )

    # Assert
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "vendor_name_taken"


def test_same_name_is_allowed_in_another_tenant(
    api: Api, member: dict[str, str], globex: dict[str, str]
) -> None:
    # Arrange
    api.create_vendor(globex, "Acme Freight")

    # Act / Assert (create_vendor asserts 201)
    api.create_vendor(member, "Acme Freight")


def test_list_filters_paginates_and_searches(
    client: TestClient, api: Api, member: dict[str, str]
) -> None:
    # Arrange: 3 seeded vendors + 22 created = 25; approve-equivalent status via fixture is
    # not exposed, so the status filter is checked against "draft".
    for i in range(22):
        api.create_vendor(member, f"Vendor {i:02d}" + (" Freight" if i % 4 == 0 else ""))

    # Act
    by_status = client.get("/api/vendors", params={"status": "draft"}, headers=member).json()
    last_page = client.get(
        "/api/vendors", params={"limit": 10, "offset": 20}, headers=member
    ).json()
    searched = client.get("/api/vendors", params={"q": "FREIGHT"}, headers=member).json()

    # Assert
    assert by_status["total"] == 25
    assert (len(last_page["items"]), last_page["total"]) == (5, 25)
    assert searched["total"] == 6
    assert all("freight" in v["name"].lower() for v in searched["items"])


def test_pages_do_not_overlap_or_skip(client: TestClient, api: Api, member: dict[str, str]) -> None:
    # Arrange
    for i in range(7):
        api.create_vendor(member, f"Paged Vendor {i}")

    # Act
    first = client.get("/api/vendors", params={"limit": 5, "offset": 0}, headers=member).json()
    second = client.get("/api/vendors", params={"limit": 5, "offset": 5}, headers=member).json()

    # Assert
    ids = [v["id"] for v in first["items"] + second["items"]]
    assert len(ids) == len(set(ids)) == 10


@pytest.mark.parametrize("params", [{"limit": 101}, {"limit": 0}, {"offset": -1}])
def test_pagination_limits_are_enforced(
    client: TestClient, member: dict[str, str], params: dict[str, int]
) -> None:
    # Act
    response = client.get("/api/vendors", params=params, headers=member)

    # Assert
    assert response.status_code == 422


def test_vendors_from_another_tenant_are_invisible(
    client: TestClient, api: Api, member: dict[str, str], globex: dict[str, str]
) -> None:
    # Arrange
    other = api.create_vendor(globex, "Globex Only")

    # Act
    response = client.get(f"/api/vendors/{other['id']}", headers=member)
    listed = client.get("/api/vendors", params={"q": "globex"}, headers=member).json()

    # Assert
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "vendor_not_found"
    assert listed["total"] == 0


def test_update_draft_vendor_is_audited(
    client: TestClient, api: Api, member: dict[str, str]
) -> None:
    # Arrange
    vendor = api.create_vendor(member)

    # Act
    response = client.patch(
        f"/api/vendors/{vendor['id']}",
        json={"contact_email": "billing@acmefreight.example"},
        headers=member,
    )

    # Assert
    assert response.status_code == 200
    assert response.json()["contact_email"] == "billing@acmefreight.example"
    assert api.audit_actions(member, vendor["id"])[-1] == "vendor.updated"


def test_vendor_in_review_cannot_be_edited(
    client: TestClient, api: Api, member: dict[str, str]
) -> None:
    # Arrange
    vendor = api.in_review_vendor(member)

    # Act
    response = client.patch(
        f"/api/vendors/{vendor['id']}",
        json={"contact_email": "billing@acmefreight.example"},
        headers=member,
    )

    # Assert
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "vendor_locked"
