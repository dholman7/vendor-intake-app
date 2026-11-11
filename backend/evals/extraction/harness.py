"""Runs the Claude extractor over the eval set and records every response.

Three modes: `live` calls the model one document at a time (and times it), `batch` sends the
whole run through the Message Batches API at half price, and `replay` re-scores recorded outputs
without calling the model, which is how CI runs. Recordings are keyed by prompt version, model,
and effort, so a changed prompt can never be scored with a stale recording.
"""

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml

from vendor_intake.db import DocumentKind
from vendor_intake.services import llm_extraction as llm

ROOT = Path(__file__).parent
DATA = ROOT / "data"
RECORDINGS = ROOT / "recordings"
Mode = Literal["live", "batch", "replay"]


@dataclass
class EvalDoc:
    id: str
    kind: DocumentKind
    split: str
    content_type: str
    layout: str
    content: bytes
    expected: dict[str, Any]
    attack: dict[str, str] = field(default_factory=dict)


@dataclass
class Recording:
    output: dict[str, Any] | None
    error: str | None
    usage: dict[str, int]
    latency_s: float | None
    served_model: str | None


def load(splits: list[str], data: Path = DATA) -> list[EvalDoc]:
    truth = yaml.safe_load((data / "truth.yaml").read_text())["docs"]
    return [
        EvalDoc(
            id=t["id"],
            kind=DocumentKind(t["kind"]),
            split=t["split"],
            content_type=t["content_type"],
            layout=t["layout"],
            content=(data / "docs" / t["file"]).read_bytes(),
            expected=t["expected"],
            attack=t.get("attack", {}),
        )
        for t in truth
        if t["split"] in splits
    ]


def _path(prompt: llm.Prompt, model: str, effort: str, doc_id: str, trial: int) -> Path:
    return RECORDINGS / prompt.version / f"{model}@{effort}" / doc_id / f"trial-{trial}.json"


def _usage(usage: Any) -> dict[str, int]:
    return {
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "cache_read_input_tokens": getattr(usage, "cache_read_input_tokens", None) or 0,
        "cache_write_input_tokens": getattr(usage, "cache_creation_input_tokens", None) or 0,
    }


def _save(path: Path, recording: Recording) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(recording.__dict__, indent=2, sort_keys=True) + "\n")


def _from_message(message: Any, latency_s: float | None) -> Recording:
    try:
        output, error = llm.output_from_message(message), None
    except llm.ExtractionError as exc:
        output, error = None, str(exc)
    return Recording(output, error, _usage(message.usage), latency_s, message.model)


def run(
    docs: list[EvalDoc],
    model: str,
    effort: str,
    trials: int,
    mode: Mode,
    prompt: llm.Prompt = llm.CURRENT,
    client: Any = None,
) -> dict[tuple[str, int], Recording]:
    """A recording per (document, trial). Live and batch runs save theirs; replay reads them."""
    jobs = [(doc, trial) for doc in docs for trial in range(trials)]

    def path(doc_id: str, trial: int) -> Path:
        return _path(prompt, model, effort, doc_id, trial)

    if mode == "replay":
        missing = [str(path(d.id, t)) for d, t in jobs if not path(d.id, t).is_file()]
        if missing:
            raise FileNotFoundError(
                f"{len(missing)} recordings missing for prompt {prompt.version},"
                f" {model}@{effort}"
                f" (first: {missing[0]}). A changed prompt needs a live or batch run."
            )
        return {(d.id, t): Recording(**json.loads(path(d.id, t).read_text())) for d, t in jobs}
    if client is None:
        import anthropic

        client = anthropic.Anthropic()
    if mode == "live":
        extractor = llm.ClaudeExtractor(model, effort, client, prompt)
        recordings: dict[tuple[str, int], Recording] = {}
        for doc, trial in jobs:
            started = time.monotonic()
            message = extractor.message(doc.kind, doc.content, doc.content_type)
            recording = _from_message(message, round(time.monotonic() - started, 2))
            _save(path(doc.id, trial), recording)
            recordings[(doc.id, trial)] = recording
        return recordings
    return _batch(client, jobs, model, effort, prompt)


def custom_id(doc_id: str, trial: int) -> str:
    """A batch request id; the API allows only [a-zA-Z0-9_-], up to 64 characters."""
    return f"{doc_id}__{trial}"


def _batch(
    client: Any, jobs: list[tuple[EvalDoc, int]], model: str, effort: str, prompt: llm.Prompt
) -> dict[tuple[str, int], Recording]:
    # Fallbacks aren't accepted on the Batches API, so batch requests go without them.
    batch = client.messages.batches.create(
        requests=[
            {
                "custom_id": custom_id(doc.id, trial),
                "params": llm.request(
                    doc.kind, doc.content, doc.content_type, model, effort, prompt
                ),
            }
            for doc, trial in jobs
        ]
    )
    while (batch := client.messages.batches.retrieve(batch.id)).processing_status != "ended":
        time.sleep(30)
    recordings: dict[tuple[str, int], Recording] = {}
    for result in client.messages.batches.results(batch.id):
        doc_id, trial = result.custom_id.rsplit("__", 1)
        if result.result.type == "succeeded":
            recording = _from_message(result.result.message, None)
        else:
            recording = Recording(None, f"batch request {result.result.type}", {}, None, None)
        _save(_path(prompt, model, effort, doc_id, int(trial)), recording)
        recordings[(doc_id, int(trial))] = recording
    return recordings
