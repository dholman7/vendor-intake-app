from datetime import date

import pytest

from vendor_intake.db import DocumentKind
from vendor_intake.services.extraction import extract_fields, field_date, lowest_confidence

INSURANCE = b"""Insurer: Harbor Mutual
Policy Number: HM-55-1290
Coverage Amount: $2,000,000
Expiry Date: 2027-03-31
"""


def test_insurance_certificate_fields_are_parsed_and_normalized() -> None:
    # Act
    fields = extract_fields(DocumentKind.INSURANCE_CERTIFICATE, INSURANCE, "text/plain")

    # Assert
    assert fields == {
        "insurer": {"value": "Harbor Mutual", "confidence": 0.95},
        "policy_number": {"value": "HM-55-1290", "confidence": 0.95},
        "coverage_amount": {"value": "2000000", "confidence": 0.9},
        "expiry_date": {"value": "2027-03-31", "confidence": 0.95},
    }


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("2027-03-31", ("2027-03-31", 0.95)),
        ("03/31/2027", ("2027-03-31", 0.85)),
        ("next spring", (None, 0.3)),
        ("2027-02-30", (None, 0.3)),
    ],
)
def test_dates_parse_with_format_dependent_confidence(
    raw: str, expected: tuple[str | None, float]
) -> None:
    # Arrange
    content = f"Counterparty: Acme\nEffective Date: {raw}\n".encode()

    # Act
    fields = extract_fields(DocumentKind.CONTRACT, content, "text/plain")

    # Assert
    assert (fields["effective_date"]["value"], fields["effective_date"]["confidence"]) == expected


def test_missing_fields_have_null_value_and_zero_confidence() -> None:
    # Act
    fields = extract_fields(DocumentKind.W9, b"Legal Name: Acme LLC\n", "text/plain")

    # Assert
    assert fields["tax_id_last4"] == {"value": None, "confidence": 0.0}
    assert fields["business_type"] == {"value": None, "confidence": 0.0}


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("12-3456789", ("6789", 0.95)), ("123-45-678", (None, 0.3))],
)
def test_tax_id_keeps_only_last_four_digits(raw: str, expected: tuple[str | None, float]) -> None:
    # Act
    fields = extract_fields(DocumentKind.W9, f"Tax ID: {raw}\n".encode(), "text/plain")

    # Assert
    assert (fields["tax_id_last4"]["value"], fields["tax_id_last4"]["confidence"]) == expected


def test_binary_uploads_route_every_field_to_manual_review() -> None:
    # Act
    fields = extract_fields(DocumentKind.W9, b"%PDF-1.7 ...", "application/pdf")

    # Assert
    assert all(f == {"value": None, "confidence": 0.0} for f in fields.values())


def test_lowest_confidence_and_field_date_helpers() -> None:
    # Arrange
    fields = extract_fields(DocumentKind.INSURANCE_CERTIFICATE, INSURANCE, "text/plain")

    # Act / Assert
    assert lowest_confidence(fields) == 0.9
    assert field_date(fields, "expiry_date") == date(2027, 3, 31)
    assert field_date(fields, "insurer_missing") is None
