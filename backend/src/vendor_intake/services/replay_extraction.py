"""Extraction from recorded model outputs, for end-to-end tests: VI_EXTRACTION_BACKEND=replay.

The extraction evals record what Claude returned for every document in the eval set. This
backend indexes those documents by the SHA-256 of their bytes. An upload that matches one gets
the recorded output, run through the same normalization and grounding as a live call, so a UI
test of the AI feature is deterministic and needs no API key. Anything else falls back to the
deterministic backend, so other tests behave as before.
"""

import hashlib
import json
from pathlib import Path

from vendor_intake.db import DocumentKind
from vendor_intake.services import llm_extraction as llm
from vendor_intake.services.extraction import Field, extract_fields


class ReplayExtractor:
    def __init__(
        self,
        root: Path,
        model: str = "claude-haiku-5-5",
        effort: str = "low",
        prompt: llm.Prompt = llm.CURRENT,
    ) -> None:
        self.recordings = root / "recordings" / prompt.version / f"{model}@{effort}"
        self.prompt = prompt
        docs = root / "data" / "docs"
        self.index = {
            hashlib.sha256(path.read_bytes()).hexdigest(): path.stem
            for path in (sorted(docs.iterdir()) if docs.is_dir() else [])
        }

    def extract(self, kind: DocumentKind, content: bytes, content_type: str) -> dict[str, Field]:
        doc_id = self.index.get(hashlib.sha256(content).hexdigest())
        recording = self.recordings / str(doc_id) / "trial-0.json"
        if doc_id is None or not recording.is_file():
            return extract_fields(kind, content, content_type)
        output = json.loads(recording.read_text())["output"] or {}
        return llm.fields_from_output(
            kind, output, llm.source_text(content, content_type), self.prompt
        )
