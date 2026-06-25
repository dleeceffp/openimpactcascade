"""Formatter for multi-path terminal-anchored generation output (OIC-DESIGN-2026-044).

Produces:
  - summary.md  : the full reasoning artifact (header, per-credible-route prose,
                  monitored assumptions for no_credible_path verdicts, different-
                  terminal notes, convergence note)
  - Per-bundle STIX JSON is handled by stix_serializer.convert() — this module
    only writes the narrative markdown.

Firewall: this module NEVER emits 'succeeds when', control-prescription language,
or unconditional 'impossible'/'cannot' statements.  Monitored assumptions are
framed as structural preconditions with flip conditions — living risk-register
entries, not closed verdicts.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from multi_path_generator import MultiPathResult, RouteResult


def _slug(text: str) -> str:
    """Make a filesystem-safe slug from a label."""
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:40]


def render_summary_markdown(result: MultiPathResult) -> str:
    """Render the full summary.md for a MultiPathResult."""
    lines: List[str] = []

    # ---------------------------------------------------------------
    # Header
    # ---------------------------------------------------------------
    lines += [
        f"# Attack Path Analysis: {result.asset}",
        "",
        "## Context",
        f"| Field | Value |",
        f"|-------|-------|",
        f"| **Protected asset** | {result.asset} |",
        f"| **Terminal (compromise outcome)** | {result.terminal} |",
        f"| **Industry** | {result.industry} |",
        f"| **Region** | {result.region} |",
        f"| **Organization size** | {result.organization_size} |",
        f"| **Generated** | {result.generated_at} |",
        f"| **Model** | {result.llm_provider} / {result.llm_model} |",
        f"| **Search** | {result.search_provider} (performed: {result.search_performed}) |",
        "",
    ]

    # Path-count summary
    n_credible = len(result.credible_routes)
    n_no_path = len(result.no_path_routes)
    n_diff = len(result.different_terminal_routes)
    total = len(result.routes)

    lines += [
        "## Summary",
        f"- **Entries evaluated:** {total}",
        f"- **Credible routes:** {n_credible}",
        f"- **No credible path (ruled out conditionally):** {n_no_path}",
        f"- **Different terminal:** {n_diff}",
        "",
    ]

    if n_credible == 0:
        lines += [
            "> **Note:** No credible routes were found for this terminal under the "
            "entries evaluated. See the Monitored Assumptions section for what would "
            "need to change to make routes credible.",
            "",
        ]
    elif n_credible == 1:
        lines += [
            "> **Note:** Only one credible route was found under the considered entries. "
            "This does not mean only one path exists — it reflects the scope of entries "
            "evaluated. Additional entries or attacker profiles may yield further routes.",
            "",
        ]

    # ---------------------------------------------------------------
    # Credible routes
    # ---------------------------------------------------------------
    if result.credible_routes:
        lines += ["---", "", "## Credible Routes", ""]
        for i, route in enumerate(result.credible_routes, 1):
            lines += _render_credible_route(i, route)

    # ---------------------------------------------------------------
    # Convergence note
    # ---------------------------------------------------------------
    convergence = _find_convergence(result.credible_routes)
    if convergence:
        lines += ["---", "", "## Convergence Note", ""]
        lines += [
            "The following techniques appear in multiple credible routes. "
            "This is a structural observation — not a control prescription.",
            "",
        ]
        for tech_id, route_labels in sorted(convergence.items()):
            lines.append(f"- **{tech_id}** — shared by: {', '.join(route_labels)}")
        lines.append("")

    # ---------------------------------------------------------------
    # Monitored Assumptions (the high-value artifact)
    # ---------------------------------------------------------------
    if result.no_path_routes:
        lines += [
            "---",
            "",
            "## Monitored Assumptions",
            "",
            "These are entries that do not currently have a credible path to the terminal "
            "under the assessed conditions. Each entry is a **living risk-register item**: "
            "the verdict holds only while the listed assumptions remain true. "
            "Review when a flip condition fires.",
            "",
        ]
        for route in result.no_path_routes:
            lines += _render_no_path_entry(route)

    # ---------------------------------------------------------------
    # Different-terminal notes
    # ---------------------------------------------------------------
    if result.different_terminal_routes:
        lines += [
            "---",
            "",
            "## Different Terminal Notes",
            "",
            "The following entries do not lead to the assessed terminal but threaten "
            "other assets. They may warrant separate analysis.",
            "",
        ]
        for route in result.different_terminal_routes:
            lines += _render_different_terminal(route)

    # ---------------------------------------------------------------
    # Footer
    # ---------------------------------------------------------------
    lines += [
        "---",
        "",
        "## Viewing the Bundles",
        "",
        "Open `attack_flow_viewer.html` in this directory and load any `route_NN_*.json` "
        "file to visualise the attack graph.",
        "",
        "_Generated by OIC Attack Flow Workbench — "
        f"{result.llm_provider}/{result.llm_model}_",
    ]

    return "\n".join(lines)


def _render_credible_route(index: int, route: RouteResult) -> List[str]:
    lines: List[str] = []
    badge = ""
    if not route.user_named and route.evidence_basis:
        badge = f" *(discovered — {route.evidence_basis})*"
    lines += [
        f"### Route {index}: {route.entry_label}{badge}",
        "",
    ]
    if not route.user_named and route.evidence_citation:
        lines += [f"**Evidence basis:** {route.evidence_citation}", ""]

    if route.prose_narrative:
        lines += [route.prose_narrative, ""]

    # Action table
    actions = (route.flow_data or {}).get("attack_actions", [])
    if actions:
        lines += [
            "**Attack actions:**",
            "",
            "| Step | Tactic | Technique | Confidence |",
            "|------|--------|-----------|------------|",
        ]
        for a in actions:
            tech = a.get("technique_id", "")
            name = a.get("name", "")
            tactic = a.get("tactic", "")
            conf = a.get("confidence", "")
            conf_marker = {"observed": "✓", "reported": "~", "speculative": "?"}.get(conf, conf)
            lines.append(f"| {a.get('id','')} | {tactic} | {tech} {name} | {conf_marker} {conf} |")
        lines.append("")

    assets = (route.flow_data or {}).get("assets", [])
    if assets:
        lines += [f"**Targeted assets:** {', '.join(assets)}", ""]

    threat_actor = (route.flow_data or {}).get("threat_actor", "")
    if threat_actor:
        lines += [f"**Threat actor:** {threat_actor}", ""]

    lines.append("")
    return lines


def _render_no_path_entry(route: RouteResult) -> List[str]:
    lines: List[str] = []
    user_label = " *(user-named)*" if route.user_named else ""
    lines += [
        f"### {route.entry_label}{user_label}",
        "",
        f"**Where the chain ends:** {route.break_point}",
        "",
        f"**Why:** {route.break_reason}",
        "",
    ]

    if route.monitored_assumptions:
        lines += ["**Monitored assumptions** *(verdict holds while these are true)*:", ""]
        for assumption in route.monitored_assumptions:
            lines.append(f"- {assumption}")
        lines.append("")

    if route.flip_conditions:
        lines += ["**Flip conditions** *(re-evaluate this entry if any of these change)*:", ""]
        for fc in route.flip_conditions:
            lines.append(f"- {fc}")
        lines.append("")

    lines.append("")
    return lines


def _render_different_terminal(route: RouteResult) -> List[str]:
    return [
        f"### {route.entry_label}",
        "",
        f"**Threatens:** {route.threatened_asset}",
        "",
        f"This entry does not lead to the assessed terminal. "
        f"Consider a separate analysis with terminal = '{route.threatened_asset}'.",
        "",
        "",
    ]


def _find_convergence(
    credible_routes: List[RouteResult],
) -> Dict[str, List[str]]:
    """Return a dict of technique_id -> [route_label, ...] for techniques shared by ≥2 routes."""
    from collections import defaultdict
    tech_to_routes: Dict[str, List[str]] = defaultdict(list)
    for route in credible_routes:
        for action in (route.flow_data or {}).get("attack_actions", []):
            tech = action.get("technique_id", "")
            if tech:
                tech_to_routes[tech].append(route.entry_label)
    return {t: labels for t, labels in tech_to_routes.items() if len(labels) >= 2}


# ---------------------------------------------------------------------------
# Output directory writer
# ---------------------------------------------------------------------------

def write_run_output(
    result: MultiPathResult,
    output_dir: Path,
    viewer_src: Optional[Path] = None,
) -> List[Path]:
    """Write all outputs for a multi-path run into output_dir.

    Creates:
      output_dir/route_01_<entry-slug>.json   (one per credible route)
      output_dir/summary.md
      output_dir/attack_flow_viewer.html      (copied from viewer_src if provided)

    Returns list of written paths.
    """
    import shutil
    from stix_serializer import convert as to_stix_bundle

    output_dir.mkdir(parents=True, exist_ok=True)
    written: List[Path] = []

    # Write STIX bundles for credible routes
    for i, route in enumerate(result.credible_routes, 1):
        if not route.flow_data:
            continue
        # Attach provenance to flow_data for the serializer
        route.flow_data["x_oic_context"] = {
            "asset": result.asset,
            "terminal": result.terminal,
            "industry": result.industry,
            "region": result.region,
            "organization_size": result.organization_size,
            "entry_point": route.entry_label,
            "generated_at": result.generated_at,
            "generator": "OIC Attack Flow Workbench v0.1.0 (multi-path)",
            "generation_status": "generated",
            "llm_provider": route.llm_provider,
            "llm_model": route.llm_model,
            "search_provider": result.search_provider,
            "search_performed": result.search_performed,
        }
        bundle = to_stix_bundle(route.flow_data)
        slug = _slug(route.entry_label)
        bundle_path = output_dir / f"route_{i:02d}_{slug}.json"
        bundle_path.write_text(
            json.dumps(bundle, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        written.append(bundle_path)

    # Write summary.md
    summary_path = output_dir / "summary.md"
    summary_path.write_text(
        render_summary_markdown(result), encoding="utf-8"
    )
    written.append(summary_path)

    # Copy viewer
    if viewer_src and viewer_src.exists():
        viewer_dst = output_dir / "attack_flow_viewer.html"
        shutil.copy2(viewer_src, viewer_dst)
        written.append(viewer_dst)

    return written
