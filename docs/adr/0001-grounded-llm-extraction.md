# 1. Model extraction with code-side grounding, evaluated on generated documents

Status: accepted, 2026-11-11

## Context

Uploads were read by a deterministic stand-in that parsed `Key: Value` text and gave every PDF or image zero confidence. A model can read real documents, but its output can't be stored as fact: the review queue sorts by confidence, and a wrong value with high confidence is the one a reviewer approves without looking.

## Decision

- **The model proposes; code decides.** Per field, the model returns a verbatim quote, the value in canonical form, and a confidence. Code normalizes the value with the deterministic backend's parsers. It also grounds it: the quote has to appear in the document's own text (pypdf for PDFs), and the value has to appear in the quote. An ungrounded value keeps its value but gets confidence 0, so it goes to a person. With no text to check against (images, scans), confidence is capped at 0.5.
- **Deterministic stays the default.** Benchmarks, CI, and the demo stay keyless and reproducible. The model backend is opt-in: `VI_EXTRACTION_BACKEND=claude`.
- **Generated eval set, not hand-labeled.** A seeded generator writes documents and their ground truth together, covering layouts, distractors, arithmetic, absent fields, and attacks. Labels can't drift or be argued with, and the set can grow by changing code.
- **Prompts are versioned objects.** Recordings are keyed by prompt version, model, and effort. A prompt change can't be scored with stale outputs, and old versions can still be re-run.
- **Two gate modes.** If the same recordings are re-scored by changed code, there's no noise, so any field that got worse fails. A new prompt or model gets agent-eval-gate's paired test by document.

## Alternatives considered

- **Citations API for grounding.** It would ground quotes server-side, but it can't be combined with structured outputs (`output_config.format`), and the strict schema matters more here.
- **Trust the model's confidence.** The v2 held-out run had one document where the model transposed digits in a tax ID but quoted it correctly, at confidences up to 0.96. Grounding is what set them to 0.
- **Real documents with hand labels.** More realistic, but costly to label, sensitive (tax IDs), and they'd anchor the eval to one labeler's reading. The generator covers the failure modes deliberately; real documents would be the next step for a production system.
- **LLM judge for free-text fields.** Every field here has a canonical form, so exact scoring is the right tool. The judge-plus-κ pattern lives in review-loop, where outputs are prose.

## Consequences

- CI gates normalization and grounding changes on every PR with no key. A prompt change needs a live run whose recordings are committed in the PR: the evidence sits in the diff.
- Sabotage check: removing grounding leaves field accuracy at 99%, but the exact gate fails on two newly confident-wrong values. An accuracy-only gate would have passed it.
- The documents are synthetic. They measure the pipeline's handling of known hazards, not accuracy on real-world scans.
