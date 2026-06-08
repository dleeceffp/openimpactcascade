"""CLI for the OIC cascade-card generator.

Examples
--------
    # One flow -> print card + report
    python -m tools.cascade_cards.cli "refdocs/flowcorpus/Maastricht University Ransomware.afb"

    # Write outputs to a directory, give it an id, and emit the LLM prompt
    python -m tools.cascade_cards.cli "...Maastricht University Ransomware.afb" \
        --id oic-ca-001 --out app/generated --emit-prompt

    # Batch the whole corpus
    python -m tools.cascade_cards.cli --all --out app/generated
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from .config import FLOW_CORPUS_DIR, load_resources
from .resources import GroundingIndex
from . import generate_card
from .render import build_llm_prompt


def _slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s[:60]


def _process(flow_path: Path, index: GroundingIndex, args, seq: int | None = None) -> bool:
    card_id = args.id or (f"oic-ca-{seq:03d}" if seq is not None else "oic-ca-NNN")
    card, report, result, extract = generate_card(flow_path, index=index, card_id=card_id)

    status = "PASS" if result.ok else "FAIL"
    print(f"[{status}] {flow_path.name}  ({len(extract.steps)} steps, "
          f"pattern={extract.dbir_pattern}, reviews={len(result.review_markers)})")
    for f in result.failures:
        print(f"    FAIL: {f}")

    if args.out:
        out_dir = Path(args.out)
        out_dir.mkdir(parents=True, exist_ok=True)
        slug = _slug(extract.flow_name)
        stem = f"{card_id}-{slug}" if card_id != "oic-ca-NNN" else slug
        (out_dir / f"{stem}.card.md").write_text(card, encoding="utf-8")
        (out_dir / f"{stem}.build-report.md").write_text(report, encoding="utf-8")
        if args.emit_prompt:
            system, user = build_llm_prompt(extract)
            (out_dir / f"{stem}.llm-prompt.json").write_text(
                json.dumps({"system": system, "user": user}, indent=2), encoding="utf-8")
    else:
        print("\n" + card)
        if args.report:
            print("\n" + report)
    return result.ok


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Generate OIC cascade grounding cards from Attack Flow files.")
    ap.add_argument("flow", nargs="?", help="Path to a .afb flow file")
    ap.add_argument("--all", action="store_true", help="Process every .afb in the corpus")
    ap.add_argument("--id", help="Card id, e.g. oic-ca-001 (single-flow mode)")
    ap.add_argument("--out", help="Output directory for .card.md + report (+ prompt)")
    ap.add_argument("--emit-prompt", action="store_true", help="Also write the Stage C LLM prompt")
    ap.add_argument("--report", action="store_true", help="Print build report to stdout")
    args = ap.parse_args(argv)

    if not args.all and not args.flow:
        ap.error("provide a flow path or --all")

    index = GroundingIndex.build(load_resources())

    if args.all:
        flows = sorted(FLOW_CORPUS_DIR.glob("*.afb"))
        ok = 0
        for i, fp in enumerate(flows, start=1):
            try:
                if _process(fp, index, args, seq=i):
                    ok += 1
            except Exception as exc:  # keep batch going; report per-file
                print(f"[ERROR] {fp.name}: {exc}")
        print(f"\n{ok}/{len(flows)} flows passed validation.")
        return 0 if ok == len(flows) else 1

    ok = _process(Path(args.flow), index, args)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
