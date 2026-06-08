"""Stage D - validation checklist + build report (build spec §7-8)."""

from __future__ import annotations

from dataclasses import dataclass, field

from .enrich import Extract, DBIR_PATTERNS
from .resources import GroundingIndex


@dataclass
class ValidationResult:
    ok: bool
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    review_markers: list[str] = field(default_factory=list)


def _veris_ok(value: str, index: GroundingIndex) -> bool:
    if "[REVIEW" in value:
        return True
    return index.veris.is_valid(value.split("#")[0].strip())


def validate(ex: Extract, index: GroundingIndex) -> ValidationResult:
    failures: list[str] = []
    warnings: list[str] = []

    if len(ex.steps) < 2:
        failures.append(f"need >= 2 ordered actions, got {len(ex.steps)}")
    if not any(s.is_terminal or s.is_impact for s in ex.steps):
        failures.append("no terminal/impact action identified")

    if not _veris_ok(ex.veris_entry, index):
        failures.append(f"veris_entry not a valid enum string or [REVIEW]: {ex.veris_entry}")
    if not _veris_ok(ex.veris_terminal, index):
        failures.append(f"veris_terminal not a valid enum string or [REVIEW]: {ex.veris_terminal}")

    if ex.dbir_pattern not in DBIR_PATTERNS and "[REVIEW" not in ex.dbir_pattern:
        failures.append(f"dbir_pattern not in allowed set or [REVIEW]: {ex.dbir_pattern}")

    for s in ex.steps:
        if s.lever not in ("odds", "dwell", "spread", "size"):
            failures.append(f"step {s.order} has invalid lever tag: {s.lever}")

    # Provenance fully populated.
    required_build = {"source_flow", "attack_flow_schema", "attack_version",
                      "veris_version", "mapping_version", "generated"}
    missing = required_build - set(ex.build)
    if missing:
        failures.append(f"build provenance missing keys: {sorted(missing)}")

    if not any(s.lever == "size" for s in ex.steps):
        warnings.append("no step classified as 'size' (no impact tactic detected)")

    return ValidationResult(
        ok=not failures,
        failures=failures,
        warnings=warnings,
        review_markers=list(ex.review_markers),
    )


def build_report(ex: Extract, result: ValidationResult) -> str:
    lines = [f"# Build report — {ex.source_file}", ""]
    lines.append(f"- status: {'PASS' if result.ok else 'FAIL'}")
    lines.append(f"- steps: {len(ex.steps)}  | dbir_pattern: {ex.dbir_pattern}")
    lines.append(f"- veris_entry: {ex.veris_entry}")
    lines.append(f"- veris_terminal: {ex.veris_terminal}")
    lines.append("")
    lines.append("## Provenance")
    for k, v in ex.build.items():
        lines.append(f"- {k}: {v}")
    if result.failures:
        lines.append("\n## Failures")
        lines += [f"- {f}" for f in result.failures]
    if result.warnings:
        lines.append("\n## Warnings")
        lines += [f"- {w}" for w in result.warnings]
    lines.append("\n## [REVIEW] markers (human review checklist, spec §8)")
    if result.review_markers:
        lines += [f"- {m}" for m in result.review_markers]
    else:
        lines.append("- none")
    lines.append("\n## Per-step lever / mapping")
    for s in ex.steps:
        caps = ", ".join(s.veris_candidates) or "(no VERIS mapping)"
        lines.append(f"- {s.order}. {s.technique_id or '-'} {s.name} "
                     f"[{s.lever}] tactics={list(s.tactic_shortnames)} -> {caps}")
    return "\n".join(lines) + "\n"
