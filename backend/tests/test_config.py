import json
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from vendor_intake import export_openapi
from vendor_intake.config import DEV_JWT_SECRET, Settings


def test_production_refuses_the_built_in_dev_secret() -> None:
    # Act / Assert
    with pytest.raises(ValidationError, match="VI_JWT_SECRET must be set"):
        Settings(environment="production", jwt_secret=DEV_JWT_SECRET)


def test_production_accepts_a_real_secret() -> None:
    # Act
    settings = Settings(environment="production", jwt_secret="x" * 48)

    # Assert
    assert settings.jwt_secret == "x" * 48


def test_development_allows_the_default_secret() -> None:
    # Act / Assert
    assert Settings(environment="development").jwt_secret == DEV_JWT_SECRET


def test_prepare_paths_creates_storage_and_sqlite_parent(tmp_path: Path) -> None:
    # Arrange
    settings = Settings(
        database_url=f"sqlite:///{tmp_path}/db/app.db", storage_dir=tmp_path / "uploads"
    )

    # Act
    settings.prepare_paths()

    # Assert
    assert (tmp_path / "uploads").is_dir()
    assert (tmp_path / "db").is_dir()


def test_export_openapi_writes_every_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    target = tmp_path / "openapi.json"
    monkeypatch.setattr(sys, "argv", ["export_openapi", str(target)])

    # Act
    export_openapi.main()

    # Assert
    document = json.loads(target.read_text())
    assert "/api/vendors/{vendor_id}/submit" in document["paths"]
    assert len(document["paths"]) == 13
