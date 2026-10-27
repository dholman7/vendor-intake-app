"""Deterministic stand-in for AI field extraction.

Reads `Key: Value` lines from text uploads. Binary uploads (PDF, images) yield every field
with a null value and zero confidence, which routes them to manual review.
"""

import re
from collections.abc import Callable
from datetime import date, datetime

from vendor_intake.db import DocumentKind

Field = dict[str, str | float | None]
Parser = Callable[[str], tuple[str | None, float]]


def _text(raw: str) -> tuple[str | None, float]:
    return (raw, 0.95) if raw else (None, 0.0)


def _date(raw: str) -> tuple[str | None, float]:
    for fmt, confidence in (("%Y-%m-%d", 0.95), ("%m/%d/%Y", 0.85)):
        try:
            return datetime.strptime(raw, fmt).date().isoformat(), confidence
        except ValueError:
            continue
    return None, 0.3


def _money(raw: str) -> tuple[str | None, float]:
    cleaned = raw.replace("$", "").replace(",", "").strip()
    if re.fullmatch(r"\d+(\.\d{1,2})?", cleaned):
        return str(int(float(cleaned))), 0.9
    return None, 0.3


def _tax_id_last4(raw: str) -> tuple[str | None, float]:
    digits = re.sub(r"\D", "", raw)
    return (digits[-4:], 0.95) if len(digits) == 9 else (None, 0.3)


FIELD_SPECS: dict[DocumentKind, dict[str, tuple[str, Parser]]] = {
    DocumentKind.W9: {
        "legal_name": ("legal_name", _text),
        "tax_id_last4": ("tax_id", _tax_id_last4),
        "business_type": ("business_type", _text),
    },
    DocumentKind.INSURANCE_CERTIFICATE: {
        "insurer": ("insurer", _text),
        "policy_number": ("policy_number", _text),
        "coverage_amount": ("coverage_amount", _money),
        "expiry_date": ("expiry_date", _date),
    },
    DocumentKind.CONTRACT: {
        "counterparty": ("counterparty", _text),
        "effective_date": ("effective_date", _date),
        "expiry_date": ("expiry_date", _date),
    },
}


def _parse_lines(text: str) -> dict[str, str]:
    pairs: dict[str, str] = {}
    for line in text.splitlines():
        key, sep, value = line.partition(":")
        if sep:
            pairs[re.sub(r"[^a-z0-9]+", "_", key.strip().lower()).strip("_")] = value.strip()
    return pairs


def extract_fields(kind: DocumentKind, content: bytes, content_type: str) -> dict[str, Field]:
    specs = FIELD_SPECS[kind]
    if content_type != "text/plain":
        return {name: {"value": None, "confidence": 0.0} for name in specs}
    pairs = _parse_lines(content.decode("utf-8", errors="replace"))
    fields: dict[str, Field] = {}
    for name, (source_key, parse) in specs.items():
        raw = pairs.get(source_key)
        value, confidence = parse(raw) if raw is not None else (None, 0.0)
        fields[name] = {"value": value, "confidence": confidence}
    return fields


def lowest_confidence(fields: dict[str, Field]) -> float:
    return min((float(f["confidence"] or 0.0) for f in fields.values()), default=0.0)


def field_date(fields: dict[str, Field], name: str) -> date | None:
    value = fields.get(name, {}).get("value")
    return date.fromisoformat(value) if isinstance(value, str) else None
