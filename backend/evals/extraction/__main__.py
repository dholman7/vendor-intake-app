"""Extraction evals for the Claude backend. From backend/, with the `llm` extra and `evals` group:

uv run python -m evals.extraction generate
uv run python -m evals.extraction run --model claude-haiku-5-5 --split dev --mode live
uv run python -m evals.extraction run ... --mode replay        # CI: no key, recorded outputs
uv run python -m evals.extraction gate --baseline A.json --current B.json
uv run python -m evals.extraction report results/A.json
"""

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from evals.extraction import generate, harness, score
from vendor_intake.services import llm_extraction as llm

RESULTS = Path(__file__).parent / "results"


def cmd_generate(_: argparse.Namespace) -> int:
    docs = generate.build()
    generate.write(docs)
    print(f"wrote {len(docs)} documents to {generate.DATA}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    splits = ["dev", "heldout", "adversarial"] if args.split == "all" else args.split.split(",")
    docs = harness.load(splits)
    prompt = llm.PROMPTS[args.prompt]
    recordings = harness.run(docs, args.model, args.effort, args.trials, args.mode, prompt)
    rows = score.score(docs, recordings, prompt)
    batch = args.mode == "batch" or (
        args.mode == "replay" and all(r.latency_s is None for r in recordings.values())
    )
    result = {
        "meta": {
            "prompt_version": prompt.version,
            "model": args.model,
            "effort": args.effort,
            "splits": splits,
            "trials": args.trials,
            "documents": len(docs),
            "mode": args.mode,
            "priced_as_batch": batch,
            "created": datetime.now(UTC).isoformat(timespec="seconds"),
        },
        "summary": score.summarize(rows, recordings, args.model, batch),
        "fields": [r.__dict__ for r in rows],
    }
    out = (
        Path(args.out)
        if args.out
        else RESULTS / f"{prompt.version}-{args.model}-{args.effort}-{args.split}.json"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(report(result))
    return 0


def _pct(rate: dict[str, Any]) -> str:
    interval = f"CI {rate['low']:.0%}-{rate['high']:.0%}"
    return f"{rate['value']:.0%} ({rate['successes']}/{rate['n']}, {interval})"


def report(result: dict[str, Any]) -> str:
    m, s = result["meta"], result["summary"]
    lines = [
        f"### {m['model']} @ {m['effort']}, prompt {m['prompt_version']}: {', '.join(m['splits'])}"
        f" ({m['documents']} documents x {m['trials']} trials)",
        "",
        "| Metric | Result |",
        "|---|---|",
        f"| Field accuracy | {_pct(s['field_accuracy'])} |",
        f"| Every field right | {_pct(s['document_all_correct'])} |",
        f"| Present but missed | {_pct(s['missed'])} |",
        f"| Absent but invented | {_pct(s['invented'])} |",
        f"| Wrong with confidence >= {score.CONFIDENT} | {_pct(s['confident_wrong'])} |",
        f"| Calibration error (ECE) | {s['calibration_error']:.3f} |",
    ]
    if s["adversarial_accuracy"]["n"]:
        lines += [
            f"| Adversarial field accuracy | {_pct(s['adversarial_accuracy'])} |",
            f"| Injection succeeded | {_pct(s['injection_success'])} |",
        ]
    latency = (
        f", p50 {s['latency_p50_s']}s, p95 {s['latency_p95_s']}s" if s["latency_p50_s"] else ""
    )
    priced = " (batch)" if m["priced_as_batch"] else ""
    lines += [
        f"| Cost per document | ${s['cost_per_document_usd']:.5f}{priced}{latency} |",
        f"| Failed calls | {s['errors']} |",
        "",
        "| Confidence | Values | Mean confidence | Accuracy |",
        "|---|---|---|---|",
        *[
            f"| {b['bin']} | {b['n']} | {b['confidence']:.2f} | {b['accuracy']:.0%} |"
            for b in s["reliability"]
        ],
    ]
    return "\n".join(lines) + "\n"


def cmd_report(args: argparse.Namespace) -> int:
    print(report(json.loads(Path(args.result).read_text())))
    return 0


def cmd_gate(args: argparse.Namespace) -> int:
    baseline = json.loads(Path(args.baseline).read_text())
    current = json.loads(Path(args.current).read_text())
    checks = score.gate(baseline, current, args.min_effect)
    print("| Metric | Documents | Mean change | p | Result |\n|---|---|---|---|---|")
    for c in checks:
        print(
            f"| {c['metric']} | {c['documents']} | {c['mean_change'] * 100:+.1f} pts"
            f" | {c['p_value']:.3f} | {'regressed' if c['regressed'] else 'ok'} |"
        )
    failed = any(c["regressed"] for c in checks)
    print("\nGate failed." if failed else "\nGate passed.")
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m evals.extraction", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("generate", help="rebuild the eval documents and truth").set_defaults(
        func=cmd_generate
    )
    r = sub.add_parser("run", help="extract every document and score it")
    r.add_argument("--model", default="claude-haiku-5-5")
    r.add_argument("--effort", default="low", choices=["low", "medium", "high"])
    r.add_argument(
        "--split", default="dev", help="dev, heldout, adversarial, comma-separated, or all"
    )
    r.add_argument("--trials", type=int, default=1)
    r.add_argument("--mode", default="live", choices=["live", "batch", "replay"])
    r.add_argument("--prompt", default=llm.PROMPT_VERSION, choices=sorted(llm.PROMPTS))
    r.add_argument("--out")
    r.set_defaults(func=cmd_run)
    g = sub.add_parser("gate", help="fail if a run regressed against a baseline")
    g.add_argument("--baseline", required=True)
    g.add_argument("--current", required=True)
    g.add_argument("--min-effect", type=float, default=0.05)
    g.set_defaults(func=cmd_gate)
    p = sub.add_parser("report", help="print a result file as Markdown")
    p.add_argument("result")
    p.set_defaults(func=cmd_report)
    args = parser.parse_args(argv)
    code: int = args.func(args)
    return code


if __name__ == "__main__":
    sys.exit(main())
