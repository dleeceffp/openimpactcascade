"""Driver for version '-b' cards (plain-language prerequisites, no M-codes in prose).

Writes ``oic-ca-NNN-b-<slug>.card.md`` (+ build report) per flow, using the same id
sequence as :mod:`generate_a` so the ``-b`` files line up next to the ``-a`` files for
three-way comparison (base / -a / -b).

Usage:
    python -m tools.cascade_cards.generate_b --out app/generated
    python -m tools.cascade_cards.generate_b "refdocs/flowcorpus/Cobalt Kitty Campaign.afb" --seq 6
    python -m tools.cascade_cards.generate_b --out app/generated --emit-prompt
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import FLOW_CORPUS_DIR, load_resources
from .resources import GroundingIndex
from .mitigations import MitigationIndex
from .afb import parse
from .enrich_b import enrich_b
from .render_b import render_scaffold_b, build_llm_prompt_b
from .validate import validate, build_report
from .generate_a import _slug, _build_report_a, _write


def generate_card_b(flow_path, index: GroundingIndex, mit_index: MitigationIndex,
                    card_id: str = "oic-ca-NNN-b"):
    flow = parse(flow_path)
    extract = enrich_b(flow, index, mit_index)
    result = validate(extract, index)            # ExtractA satisfies validate (duck-typed)
    card = render_scaffold_b(extract, card_id=card_id)
    report = _build_report_a(extract, result, build_report(extract, result))
    return card, report, result, extract


def _process(flow_path: Path, index, mit_index, args, seq: int) -> bool:
    card_id = f"oic-ca-{seq:03d}-b"
    card, report, result, ex = generate_card_b(flow_path, index, mit_index, card_id=card_id)
    print(f"[{'PASS' if result.ok else 'FAIL'}] {flow_path.name}  "
          f"v3(-b): {len(ex.steps)} steps · mitigations={len(ex.mitigation_options)} "
          f"· no-prev={len(ex.no_preventive_mitigation_steps)}")
    for f in result.failures:
        print(f"    FAIL: {f}")
    if args.out:
        out_dir = Path(args.out)
        stem = f"{card_id}-{_slug(ex.flow_name)}"
        _write(out_dir, stem, card, report)
        if args.emit_prompt:
            system, user = build_llm_prompt_b(ex)
            (out_dir / f"{stem}.llm-prompt.json").write_text(
                json.dumps({"system": system, "user": user}, indent=2), encoding="utf-8")
    else:
        print("\n" + card)
    return result.ok


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Generate v3 (-b) plain-language cascade cards.")
    ap.add_argument("flow", nargs="?", help="Single .afb path (default: whole corpus)")
    ap.add_argument("--out", help="Output directory")
    ap.add_argument("--seq", type=int, default=1, help="Starting id sequence number (single-flow mode)")
    ap.add_argument("--emit-prompt", action="store_true", help="Also write the v3 LLM prompt")
    args = ap.parse_args(argv)

    resources = load_resources()
    index = GroundingIndex.build(resources)
    mit_index = MitigationIndex(resources)

    if args.flow:
        return 0 if _process(Path(args.flow), index, mit_index, args, args.seq) else 1

    flows = sorted(FLOW_CORPUS_DIR.glob("*.afb"))
    ok = 0
    for i, fp in enumerate(flows, start=1):
        try:
            if _process(fp, index, mit_index, args, i):
                ok += 1
        except Exception as exc:
            print(f"[ERROR] {fp.name}: {exc}")
    print(f"\n{ok}/{len(flows)} flows produced -b cleanly.")
    return 0 if ok == len(flows) else 1


if __name__ == "__main__":
    sys.exit(main())
