"""features/auth.feature"""

import pytest
from fastapi.testclient import TestClient

from vendor_intake.seed import DEMO_PASSWORD


def test_successful_sign_in_returns_token_and_httponly_cookie(client: TestClient) -> None:
    # Act
    response = client.post(
        "/api/auth/login", json={"email": "member@northwind.test", "password": DEMO_PASSWORD}
    )

    # Assert
    assert response.status_code == 200
    assert response.json()["access_token"]
    cookie_header = response.headers["set-cookie"].lower()
    assert cookie_header.startswith("session=")
    assert "httponly" in cookie_header


@pytest.mark.parametrize(
    ("email", "password"),
    [("member@northwind.test", "wrong-password"), ("nobody@northwind.test", DEMO_PASSWORD)],
)
def test_bad_credentials_get_the_same_error(client: TestClient, email: str, password: str) -> None:
    # Act
    response = client.post("/api/auth/login", json={"email": email, "password": password})

    # Assert
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


def test_profile_shows_role_and_tenant(client: TestClient, member: dict[str, str]) -> None:
    # Act
    response = client.get("/api/me", headers=member)

    # Assert
    assert response.status_code == 200
    assert response.json()["role"] == "member"
    assert response.json()["tenant"]["name"] == "Northwind Supply"


def test_session_cookie_alone_authenticates(client: TestClient) -> None:
    # Arrange
    client.post(
        "/api/auth/login", json={"email": "member@northwind.test", "password": DEMO_PASSWORD}
    )

    # Act
    response = client.get("/api/me")

    # Assert
    assert response.status_code == 200


def test_requests_without_session_are_rejected(client: TestClient) -> None:
    # Act
    response = client.get("/api/me")

    # Assert
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"


def test_tampered_token_is_rejected(client: TestClient) -> None:
    # Act
    response = client.get("/api/me", headers={"Authorization": "Bearer not.a.token"})

    # Assert
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_session"


def test_sign_out_clears_cookie(client: TestClient, member: dict[str, str]) -> None:
    # Act
    response = client.post("/api/auth/logout", headers=member)

    # Assert
    assert response.status_code == 204
    cookie_header = response.headers["set-cookie"].lower()
    assert cookie_header.startswith('session=""') or "max-age=0" in cookie_header
