"""features/audit.feature"""

from fastapi.testclient import TestClient

from tests.conftest import W9, Api


def test_audit_trail_lists_events_oldest_first_with_actor(
    client: TestClient, api: Api, member: dict[str, str]
) -> None:
    # Arrange
    vendor = api.create_vendor(member)
    api.upload(member, vendor["id"], "w9", W9)

    # Act
    response = client.get(f"/api/vendors/{vendor['id']}/audit", headers=member)

    # Assert
    assert response.status_code == 200
    items = response.json()["items"]
    assert [e["action"] for e in items] == [
        "vendor.created",
        "document.uploaded",
        "document.extracted",
    ]
    assert all(e["actor"]["email"] == "member@northwind.test" and e["at"] for e in items)


def test_audit_trail_from_another_tenant_is_invisible(
    client: TestClient, api: Api, member: dict[str, str], globex: dict[str, str]
) -> None:
    # Arrange
    vendor = api.create_vendor(globex, "Globex Only")

    # Act
    response = client.get(f"/api/vendors/{vendor['id']}/audit", headers=member)

    # Assert
    assert response.status_code == 404
