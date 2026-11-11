"""The Claude extraction backend against a stub client: request shape, grounding, normalization,
and failure handling. No API calls."""

import json
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.conftest import Api
from vendor_intake.db import DocumentKind
from vendor_intake.services import llm_extraction as llm
from vendor_intake.services.extraction import Field

INSURANCE_DOC = (
    "CERTIFICATE OF LIABILITY INSURANCE\n"
    "Insurer A: Harbor Mutual Insurance Co.\n"
    "Policy No.: HM-55-1290\n"
    "Each occurrence: $2,000,000\n"
    "Policy expires: March 31, 2027\n"
)


def _item(value: str | None, quote: str | None, confidence: float = 0.9) -> dict[str, Any]:
    return {"quote": quote, "value": value, "confidence": confidence}


GOOD = {
    "insurer": _item("Harbor Mutual Insurance Co.", "Insurer A: Harbor Mutual Insurance Co."),
    "policy_number": _item("HM-55-1290", "Policy No.: HM-55-1290"),
    "coverage_amount": _item("2000000", "Each occurrence: $2,000,000"),
    "expiry_date": _item("2027-03-31", "Policy expires: March 31, 2027"),
}


def _fields(output: dict[str, Any], text: str | None = INSURANCE_DOC) -> dict[str, Field]:
    return llm.fields_from_output(DocumentKind.INSURANCE_CERTIFICATE, output, text)


def test_grounded_values_are_normalized_and_keep_their_confidence() -> None:
    # Act
    fields = _fields(GOOD)

    # Assert
    assert fields == {
        "insurer": {"value": "Harbor Mutual Insurance Co.", "confidence": 0.9},
        "policy_number": {"value": "HM-55-1290", "confidence": 0.9},
        "coverage_amount": {"value": "2000000", "confidence": 0.9},
        "expiry_date": {"value": "2027-03-31", "confidence": 0.9},
    }


@pytest.mark.parametrize(
    ("field", "item"),
    [
        # The quote isn't in the document: the model may have invented it.
        ("policy_number", _item("HM-55-1290", "Policy Number HM-55-1290")),
        # The quote is real but doesn't contain the value.
        ("insurer", _item("Harbor Life", "Insurer A: Harbor Mutual Insurance Co.")),
        ("coverage_amount", _item("5000000", "Each occurrence: $2,000,000")),
        # No quote at all.
        ("policy_number", _item("HM-55-1290", None)),
    ],
)
def test_ungrounded_values_keep_the_value_but_lose_all_confidence(
    field: str, item: dict[str, Any]
) -> None:
    fields = _fields({**GOOD, field: item})
    assert fields[field]["value"] is not None
    assert fields[field]["confidence"] == 0.0


@pytest.mark.parametrize(
    "item",
    [
        _item(None, None),
        _item("", None),
        _item("March 31, 2027", "Policy expires: March 31, 2027"),  # not ISO: doesn't parse
    ],
)
def test_missing_or_unparseable_values_are_null_with_zero_confidence(item: dict[str, Any]) -> None:
    assert _fields({**GOOD, "expiry_date": item})["expiry_date"] == {
        "value": None,
        "confidence": 0.0,
    }


def test_confidence_is_clamped_to_one() -> None:
    over = {**GOOD, "insurer": {**GOOD["insurer"], "confidence": 1.7}}
    assert _fields(over)["insurer"]["confidence"] == 1.0


def test_with_no_text_to_check_against_every_confidence_is_capped() -> None:
    # An image upload: quotes can't be verified, so nothing passes as certain.
    assert all(f["confidence"] == llm.UNVERIFIED_CAP for f in _fields(GOOD, text=None).values())


def test_w9_keeps_the_last_four_of_a_grounded_tax_id() -> None:
    text = "Name: Acme Freight LLC\nEmployer identification number: 12-3456789\n[x] LLC\n"
    output = {
        "legal_name": _item("Acme Freight LLC", "Name: Acme Freight LLC"),
        # The model sees `tax_id` (prompt v2); the app stores the last four as tax_id_last4.
        "tax_id": _item("123456789", "Employer identification number: 12-3456789"),
        "business_type": _item("LLC", "[x] LLC"),
    }
    fields = llm.fields_from_output(DocumentKind.W9, output, text)
    assert fields["tax_id_last4"] == {"value": "6789", "confidence": 0.9}
    assert fields["business_type"]["value"] == "LLC"


def test_request_sends_text_as_a_document_with_a_strict_schema() -> None:
    params = llm.request(DocumentKind.W9, b"Name: Acme", "text/plain", "claude-haiku-5-5", "low")
    block = params["messages"][0]["content"][0]
    assert block["type"] == "document" and block["source"]["type"] == "text"
    assert params["output_config"]["effort"] == "low"
    schema = params["output_config"]["format"]["schema"]
    assert schema["required"] == ["legal_name", "tax_id", "business_type"]
    assert schema["additionalProperties"] is False
    business = schema["properties"]["business_type"]["properties"]["value"]["anyOf"][0]
    assert business["enum"] == llm.BUSINESS_TYPES
    assert "untrusted upload" in params["system"]


@pytest.mark.parametrize(
    ("content_type", "block_type"), [("application/pdf", "document"), ("image/png", "image")]
)
def test_request_sends_binary_uploads_as_base64(content_type: str, block_type: str) -> None:
    block = llm.request(DocumentKind.W9, b"\x00\x01", content_type, "m", "low")["messages"][0][
        "content"
    ][0]
    assert block["type"] == block_type
    assert block["source"] == {"type": "base64", "media_type": content_type, "data": "AAE="}


class StubMessages:
    def __init__(self, message: Any) -> None:
        self.message = message
        self.calls: list[dict[str, Any]] = []

    def create(self, **params: Any) -> Any:
        self.calls.append(params)
        return self.message


def _client(output: dict[str, Any] | str, stop_reason: str = "end_turn") -> Any:
    text = output if isinstance(output, str) else json.dumps(output)
    message = SimpleNamespace(
        stop_reason=stop_reason,
        # Thinking can come first; the output is the text block.
        content=[SimpleNamespace(type="thinking"), SimpleNamespace(type="text", text=text)],
        usage=SimpleNamespace(input_tokens=900, output_tokens=120),
    )
    return SimpleNamespace(messages=StubMessages(message))


def test_extractor_returns_fields_output_and_usage() -> None:
    stub = _client(GOOD)
    extractor = llm.ClaudeExtractor("claude-haiku-5-5", "low", client=stub)
    fields, output, usage = extractor.run(
        DocumentKind.INSURANCE_CERTIFICATE, INSURANCE_DOC.encode(), "text/plain"
    )
    assert fields["expiry_date"]["value"] == "2027-03-31"
    assert output == GOOD and usage.input_tokens == 900
    assert stub.messages.calls[0]["model"] == "claude-haiku-5-5"


@pytest.mark.parametrize(
    ("output", "stop_reason", "problem"),
    [
        (GOOD, "refusal", "declined"),
        (GOOD, "max_tokens", "max_tokens"),
        ("{not json", "end_turn", "not valid JSON"),
    ],
)
def test_extractor_failures_raise(output: Any, stop_reason: str, problem: str) -> None:
    extractor = llm.ClaudeExtractor("m", "low", client=_client(output, stop_reason))
    with pytest.raises(llm.ExtractionError, match=problem):
        extractor.extract(DocumentKind.INSURANCE_CERTIFICATE, b"x", "text/plain")


def test_uploads_go_through_the_configured_extractor(
    client: TestClient, api: Api, member: dict[str, str]
) -> None:
    # Arrange: any backend can be plugged in; this one reads PDFs.
    seen: list[str] = []

    def extractor(kind: DocumentKind, content: bytes, content_type: str) -> dict[str, Field]:
        seen.append(content_type)
        return {"insurer": {"value": "Harbor Mutual", "confidence": 0.4}}

    client.app.state.extractor = extractor  # type: ignore[attr-defined]
    vendor = api.create_vendor(member)

    # Act
    response = api.upload(
        member,
        vendor["id"],
        "insurance_certificate",
        b"%PDF-1.4 stub",
        "coi.pdf",
        "application/pdf",
    )

    # Assert
    assert response.status_code == 201
    assert seen == ["application/pdf"]
    extraction = api.extractions(member, vendor["id"])["insurance_certificate"]
    assert extraction["fields"] == {"insurer": {"value": "Harbor Mutual", "confidence": 0.4}}


def test_opus_and_sonnet_opt_into_refusal_fallback() -> None:
    stub = _client(GOOD)
    stub.beta = SimpleNamespace(messages=StubMessages(stub.messages.message))
    llm.ClaudeExtractor("claude-opus-5-5", "low", client=stub).extract(
        DocumentKind.INSURANCE_CERTIFICATE, INSURANCE_DOC.encode(), "text/plain"
    )
    call = stub.beta.messages.calls[0]
    assert call["fallbacks"] == "default" and call["betas"] == [llm.FALLBACK_BETA]
    assert stub.messages.calls == []


def test_millions_written_short_still_ground() -> None:
    text = "Limits: $2M per occurrence / $4M aggregate.\nOr $1.5 million umbrella."
    assert llm.grounded("coverage_amount", "2000000", "Limits: $2M per occurrence", text)
    assert llm.grounded("coverage_amount", "1500000", "Or $1.5 million umbrella.", text)
    assert not llm.grounded("coverage_amount", "4000000", "Limits: $2M per occurrence", text)


def test_older_prompt_versions_still_score_their_recorded_outputs() -> None:
    # v1 showed the model `tax_id_last4`; its recordings must replay under today's code.
    text = "Tax ID: 12-3456789"
    output = {"tax_id_last4": _item("123456789", "Tax ID: 12-3456789")}
    assert llm.fields_from_output(DocumentKind.W9, output, text, llm.V1)["tax_id_last4"] == {
        "value": "6789",
        "confidence": 0.9,
    }
    assert "tax_id_last4" in llm.schema(DocumentKind.W9, llm.V1)["properties"]
