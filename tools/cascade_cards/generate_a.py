"""Alternate driver: emit BOTH card versions per flow for side-by-side comparison.

For every ``.afb`` in the corpus this writes:
  * ``oic-ca-NNN-<slug>.card.md``    - v1 (description-led "succeeds when")
  * ``oic-ca-NNN-a-<slug>.card.md``  - v2 (prerequisite-led + grounded mitigations)
plus a build report per version. The ``-a`` suffix distinguishes the two ids.

Usage:
    python -m tools.cascade_cards.generate_a --out app/generated
    python -m tools.cascade_cards.generate_a "refdocs/flowcorpus/REvil.afb" --seq 27
    python -m tools.cascade_cards.generate_a --out app/generated --emit-prompt
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from .config import FLOW_CORPUS_DIR, load_resources
from .resources import GroundingIndex
from .mitigations import MitigationIndex
from . import generate_card                       # v1
from .afb import parse
from .enrich_a import enrich_a, ExtractA
from .render_a import render_scaffold_a, build_llm_prompt_a
from .validate import validate, build_report


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:60]


def _build_report_a(ex: ExtractA, result, base_report: str) -> str:
    """Augment the standard build report with the mitigations summary (reviewer view)."""
    lines = [base_report, "## Grounded mitigations (Addendum B)"]
    if ex.mitigation_options:
        for m in ex.mitigation_options:
            lines.append(f"- {m.mcode} {m.name} [{m.effect}] "
                         f"covers steps {m.covered_steps} ({m.coverage_count}) -> {m.techniques}")
    else:
        lines.append("- none mapped")
    lines.append(f"\nno_preventive_mitigation_steps: {ex.no_preventive_mitigation_steps}")
    return "\n".join(lines) + "\n"


def generate_card_a(flow_path, index: GroundingIndex, mit_index: MitigationIndex,
                    card_id: str = "oic-ca-NNN-a"):
    """Run the alternate pipeline (Stage A reused, Stage B/C alternate, Stage D reused)."""
    flow = parse(flow_path)
    extract = enrich_a(flow, index, mit_index)
    result = validate(extract, index)            # duck-typed: ExtractA satisfies validate
    card = render_scaffold_a(extract, card_id=card_id)
    report = _build_report_a(extract, result, build_report(extract, result))
    return card, report, result, extract


def _write(out_dir: Path, stem: str, card: str, report: str):
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{stem}.card.md").write_text(card, encoding="utf-8")
    (out_dir / f"{stem}.build-report.md").write_text(report, encoding="utf-8")


def _process(flow_path: Path, index, mit_index, args, seq: int):
    card_id = f"oic-ca-{seq:03d}"
    # v1
    card1, report1, res1, ex1 = generate_card(flow_path, index=index, card_id=card_id)
    # v2 (-a)
    card2, report2, res2, ex2 = generate_card_a(flow_path, index, mit_index, card_id=f"{card_id}-a")

    print(f"[{ 'PASS' if res1.ok else 'FAIL'}/{ 'PASS' if res2.ok else 'FAIL'}] "
          f"{flow_path.name}  v1={len(ex1.steps)} steps · "
          f"v2 mitigations={len(ex2.mitigation_options)} no-prev={len(ex2.no_preventive_mitigation_steps)}")
    for f in res1.failures + res2.failures:
        print(f"    FAIL: {f}")

    if args.out:
        out_dir = Path(args.out)
        slug = _slug(ex1.flow_name)
        _write(out_dir, f"{card_id}-{slug}", card1, report1)
        _write(out_dir, f"{card_id}-a-{slug}", card2, report2)
        if args.emit_prompt:
            system, user = build_llm_prompt_a(ex2)
            (out_dir / f"{card_id}-a-{slug}.llm-prompt.json").write_text(
                json.dumps({"system": system, "user": user}, indent=2), encoding="utf-8")
    else:
        print("\n" + card2)
    return res1.ok and res2.ok


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Generate v1 + v2(-a) cascade cards for comparison.")
    ap.add_argument("flow", nargs="?", help="Single .afb path (default: whole corpus)")
    ap.add_argument("--out", help="Output directory")
    ap.add_argument("--seq", type=int, default=1, help="Starting id sequence number (single-flow mode)")
    ap.add_argument("--emit-prompt", action="store_true", help="Also write the v2 LLM prompt")
    args = ap.parse_args(argv)

    resources = load_resources()
    index = GroundingIndex.build(resources)
    mit_index = MitigationIndex(resources)

    if args.flow:
        ok = _process(Path(args.flow), index, mit_index, args, args.seq)
        return 0 if ok else 1

    flows = sorted(FLOW_CORPUS_DIR.glob("*.afb"))
    ok = 0
    for i, fp in enumerate(flows, start=1):
        try:
            if _process(fp, index, mit_index, args, i):
                ok += 1
        except Exception as exc:
            print(f"[ERROR] {fp.name}: {exc}")
    print(f"\n{ok}/{len(flows)} flows produced both versions cleanly.")
    return 0 if ok == len(flows) else 1


if __name__ == "__main__":
    sys.exit(main())
