# Extraction evals design

## Context

vendor-intake-app can extract fields from uploaded W-9s, insurance certificates, and contracts with Claude ([ADR 0001](adr/0001-grounded-llm-extraction.md)). A wrong field with high confidence is the costly failure: it reaches a reviewer looking trustworthy and gets approved. A prompt or model change can make that worse while average accuracy stays flat. The evals have to catch that, in CI, on every change, without an API key.

## Goals

- **Known answers without hand labels.** A seeded generator writes each document together with its ground truth.
- **Measure what matters to a reviewer:** confidently-wrong values, calibration, and injection success, not just accuracy.
- **Separate tuning from reporting.** Dev documents find prompt bugs; held-out and adversarial documents are only for reported numbers.
- **Free in CI.** Recordings of live runs are replayed through the current code and gated, with no key.
- **Gate prompt and model changes with a statistical test, and code changes exactly.**

## Non-goals

- **Real customer documents.** None can be published. The generator varies layout, format, and noise instead, and says so.
- **Ranking models on this set.** Sonnet and Opus are both perfect here; separating them would need harder documents.

## Design

| Part | What it does |
|---|---|
| Generator | Seeded and deterministic. 75 documents across dev, held-out, and adversarial splits, in text, PDF, and image layouts. CI checks the committed set is byte-identical to what the generator writes. |
| Harness | Live, Batch API, or replay modes. Recordings are keyed by prompt version, model and effort, document, and trial. Prompts are versioned objects, and a prompt change bumps the version. |
| Scoring | Per field: correct, missed, invented, wrong at confidence ≥ 0.8. Per run: field accuracy, documents fully right, calibration error (ECE) with a reliability table, adversarial accuracy, and injection success, each with an interval. |
| Gate | Same recordings (only the code changed): any field that got worse fails, since there's no sampling noise. New recordings (a new prompt or model): agent-eval-gate's paired test by document, at p < 0.05 and at least 5 points worse. |
| End to end | Playwright runs the API in replay mode, so an upload of an eval document gets the recorded model output through the real grounding code. |

## Options considered

| Option | Why not |
|---|---|
| Hand-labeled real documents | Unpublishable, slow to grow, and labels drift. |
| An LLM judge for correctness | The truth is exact values; string comparison after normalization is enough. |
| A statistical gate for code changes too | It missed a sabotage: removing grounding kept accuracy at 99% but made two values confidently wrong. Identical recordings have no noise, so exact comparison is the right test. |
| Live calls in CI | Cost, keys in CI, and run-to-run noise that a code change shouldn't have to beat. |

## Failure modes

| Failure | Guard |
|---|---|
| A prompt bug only visible on some fields | Dev-split runs. Two were found this way: a field named `tax_id_last4` returned four digits, and contract end dates came back null. |
| A digit transposed in a correct quote | Grounding: the value must appear in the quote. Confidence drops to 0, and a person reviews it. |
| Injection inside a document | The schema allows only fields, and the prompt treats the document as data. Measured 0/27 per model. |
| Eval data silently missing from git | An ignore rule once hid it. The data is now unignored, and CI checks with `git status --porcelain`. |
| Non-deterministic PDFs | A naive timestamp in PDF metadata made the files differ by timezone. Generation now uses UTC, verified byte-identical in a clean container. |

## Cost model

| Model | Per document | Held-out and adversarial, 3 trials |
|---|---|---|
| Haiku 5.5 | about $0.00036, live | about $0.04 |
| Sonnet 5.5 | about $0.003, batch | about $0.50 |
| Opus 5.5 | about $0.006, batch | about $1 |

CI costs nothing.

## Metrics

The published baseline is Haiku 5.5 with prompt v2 on held-out and adversarial documents:

- 99% field accuracy;
- 0 of 369 values wrong at confidence ≥ 0.8;
- calibration error 0.066;
- 0 of 27 injections succeeded.

A change ships only if the gate passes against that baseline.
