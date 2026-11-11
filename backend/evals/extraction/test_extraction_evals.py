"""The eval's own scoring and gate. Run with `uv run pytest evals` (needs the evals group)."""

import re
from typing import Any

import pytest
from fpdf import FPDF

from evals.extraction import generate, harness, score
from vendor_intake.db import DocumentKind
from vendor_intake.services import llm_extraction as llm
from vendor_intake.services.extraction import FIELD_SPECS


@pytest.mark.parametrize(
    ("name", "expected", "value", "ok"),
    [
        ("insurer", "Harbor Mutual Insurance Co.", "harbor  mutual insurance co", True),
        ("policy_number", "HM-55-1290", "HM-55-1291", False),
        ("expiry_date", ["2028-03-10", "2028-03-11"], "2028-03-11", True),
        ("expiry_date", None, None, True),
        ("expiry_date", None, "2028-03-11", False),  # invented
        ("coverage_amount", "2000000", None, False),  # missed
    ],
)
def test_matches(name: str, expected: Any, value: str | None, ok: bool) -> None:
    assert score.matches(name, expected, value) is ok


def _row(doc: str, correct: bool = True, confidence: float = 0.9, trial: int = 0) -> dict[str, Any]:
    return {
        "doc": doc,
        "trial": trial,
        "field": "insurer",
        "split": "heldout",
        "value": "x",
        "correct": correct,
        "confidence": confidence,
    }


def _result(rows: list[dict[str, Any]], prompt: str = "v2") -> dict[str, Any]:
    meta = {
        "prompt_version": prompt,
        "model": "m",
        "effort": "low",
        "trials": 1,
        "splits": ["heldout"],
    }
    return {"meta": meta, "fields": rows}


BASE = [_row(f"D{i:02}") for i in range(40)]


def test_same_recordings_pass_when_nothing_changed() -> None:
    checks = score.gate(_result(BASE), _result(BASE))
    assert {c["mode"] for c in checks} == {"exact"}
    assert not any(c["regressed"] for c in checks)


def test_same_recordings_fail_on_a_single_new_confidently_wrong_value() -> None:
    # One field out of 40 is under any statistical gate's threshold, and still the worst case.
    current = [*BASE[:-1], _row("D39", correct=False, confidence=0.95)]
    checks = {c["metric"]: c for c in score.gate(_result(BASE), _result(current))}
    assert checks["confidently wrong"]["regressed"]
    assert checks["confidently wrong"]["examples"] == ["D39/insurer#0"]
    assert checks["field accuracy"]["regressed"]


def test_a_wrong_value_sent_to_review_is_worse_accuracy_but_not_confidently_wrong() -> None:
    current = [*BASE[:-1], _row("D39", correct=False, confidence=0.0)]
    checks = {c["metric"]: c for c in score.gate(_result(BASE), _result(current))}
    assert checks["field accuracy"]["regressed"]
    assert not checks["confidently wrong"]["regressed"]


def test_a_new_prompt_is_gated_statistically_by_document() -> None:
    worse = [_row(f"D{i:02}", correct=i >= 10) for i in range(40)]
    checks = {c["metric"]: c for c in score.gate(_result(BASE), _result(worse, prompt="v3"))}
    assert checks["field accuracy"]["mode"] == "paired"
    assert checks["field accuracy"]["regressed"]
    assert checks["field accuracy"]["mean_change"] == pytest.approx(-0.25)
    small = [_row(f"D{i:02}", correct=i >= 1) for i in range(40)]
    assert not score.gate(_result(BASE), _result(small, prompt="v3"))[0]["regressed"]


def test_runs_on_different_splits_cannot_be_compared() -> None:
    other = _result(BASE)
    other["meta"] = {**other["meta"], "splits": ["dev"]}
    with pytest.raises(ValueError, match="different splits"):
        score.gate(_result(BASE), other)


def test_calibration_error_is_zero_for_a_perfectly_calibrated_bin() -> None:
    rows = [
        score.FieldScore(
            "d", 0, "w9", "dev", "form", "legal_name", "a", "a", 0.9, i < 9, False, False
        )
        for i in range(10)
    ]
    error, table = score.calibration(rows)
    assert error == pytest.approx(0.0)
    assert table == [{"bin": "0.8-1.0", "n": 10, "confidence": 0.9, "accuracy": 0.9}]


def test_the_generator_is_deterministic_and_labels_every_field() -> None:
    first, second = generate.build(), generate.build()
    assert [(d.id, d.text, d.expected) for d in first] == [
        (d.id, d.text, d.expected) for d in second
    ]
    for doc in first:
        assert set(doc.expected) == set(FIELD_SPECS[DocumentKind(doc.kind)]), doc.id
    assert {d.split for d in first} == {"dev", "heldout", "adversarial"}
    assert all(d.attack for d in first if d.layout.startswith("inject"))


def test_every_batch_request_id_is_one_the_api_accepts() -> None:
    ids = [harness.custom_id(d.id, t) for d in generate.build() for t in range(3)]
    assert all(re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", i) for i in ids)
    assert len(set(ids)) == len(ids)


def test_pdf_text_is_read_for_grounding() -> None:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", size=12)
    pdf.cell(text="Policy No.: HM-55-1290")
    text = llm.source_text(bytes(pdf.output()), "application/pdf")
    assert text is not None and "HM-55-1290" in text
    assert llm.source_text(b"\x89PNG", "image/png") is None
