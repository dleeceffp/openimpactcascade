# OIC PillarReader — Load/Cache + `slice_likelihood` Spec

**Artifact:** `oic-pillar-reader-likelihood-spec`
**Status:** proposed (OIC-authored)
**Scope:** Build step 2 of N. Stand up `PillarReader` — load and cache the
pillar YAML files on startup — and implement **one** slice method,
`slice_likelihood(industry)`, against the **DBIR** pillar only. This proves the
crosswalk resolves end-to-end against real file keys before NetDiligence bands,
IBM, formatting, or any generator wiring are added.

**Depends on:** `pillar_crosswalk.py` (step 1, complete).

---

## 1. Purpose

`PillarReader` is the in-memory owner of the curated pillar corpus. On startup
it globs the pillar directory, parses each YAML once, and indexes the files by
`comparable_series` and `edition` so the latest edition of each series is
selectable in O(1). `slice_likelihood(industry)` returns a structured,
audit-faithful slice of the **latest DBIR edition** for one industry: threat
composition, actors, motives, the sector narrative, and the corpus-wide anchors.

This step deliberately does one pillar so the crosswalk's judgment calls
(`real_estate`, the shared `information` key) are validated against real DBIR
keys in isolation, with nothing else able to mask a resolution bug.

## 2. Non-goals (defer to later steps — do NOT build here)

- **No NetDiligence, no IBM.** `slice_magnitude` is a separate step.
- **No band resolution.** `slice_likelihood` takes `industry` only — no
  `org_size`, no revenue/headcount bands.
- **No size splits yet.** DBIR's `incidents_small/large` and the
  `_small_business`/`_large_business` anchors are carried through verbatim when
  present but are NOT selected on — they become useful when `org_size` flows in
  with the band step.
- **No prompt rendering.** `format_context_for_prompt` and the compact
  LIKELIHOOD/MAGNITUDE block are a later step. This method returns a dict.
- **No `ContextSlice`/`EvidenceDoc` wrapping.** The slice is a plain dict; the
  retriever-integration step wraps it into the `ctx.content/source/relevance_score`
  shape the generator consumes.
- **No trend/YoY.** Only the latest edition is selected. Sibling editions stay
  loaded (for a later trend step) but are not compared here.
- **No changes** to `retrieve.py`, `ai_question_generator.py`, or `main.py`.
  Nothing consumes `PillarReader` yet; this step is invisible to the live app.

## 3. File to create

`pillar_reader.py`, in the same package as `pillar_crosswalk.py` and
`retrieve.py` (i.e. `app/corpus/`). Import the crosswalk — do NOT reimplement
resolution:

```python
from corpus.pillar_crosswalk import resolve_industry_key, SERIES_VERIZON_DBIR
```

(Match the import style already used by `ai_question_generator.py`'s
`from corpus.retrieve import ...`.)

## 4. Dependency: PyYAML

These files are nested YAML (maps of maps, multi-line `>` blocks, inline
comments) — the hand-rolled flat-frontmatter parser in `library.py` cannot read
them. Use `yaml.safe_load`. **Prerequisite:** confirm `PyYAML` is in
`requirements.txt`; if absent, add it. This is the only new dependency in the
pillar pipeline and the build network already permits PyPI. Leave `library.py`
on its dependency-free parser untouched — cards stay flat.

## 5. Config additions (mirror the `OIC_CARDS_*` block)

Add to `config.py`, following the existing additive, env-overridable pattern:

```python
# --- Pillar reference grounding (additive, flag-gated) ---
OIC_PILLARS_ENABLED = os.getenv("OIC_PILLARS_ENABLED", "1") == "1"
OIC_PILLARS_DIR     = os.getenv("OIC_PILLARS_DIR", "ref_pillars")  # CONFIRM actual dir
```

`OIC_PILLARS_ENABLED` is the kill switch; when false, `load()` no-ops and slices
return a `coverage: False` result. Because nothing consumes the reader yet,
enabling it has no user-facing effect this step — it only governs whether files
load. Confirm the real directory name/path inside the container (open item #1).

## 6. Loading & indexing contract

- **Key on file *content*, never on filename.** Read `comparable_series` and
  `edition` from each parsed file. Filenames vary (`dbir-likelihood-by-industry_2025.yaml`)
  and are not authoritative; `comparable_series: "dbir-by-industry"` +
  `edition: "2025"` are.
- **Index shape:** `{comparable_series: {edition: parsed_dict}}`.
- **Latest selection:** parse `edition` as int for comparison; if non-numeric,
  fall back to string sort and log a warning. `_latest(series)` returns the
  parsed dict for the max edition, or `None`.
- **Resilience (mirror `library.py` / `retrieve.py`):**
  - Glob `OIC_PILLARS_DIR` recursively (`**/*.yaml`, `**/*.yml`).
  - A file that fails `safe_load` → log, skip, continue (one bad file never
    breaks startup).
  - A file missing `comparable_series` or `edition` → log warning, skip.
  - Two files with the same series+edition → log warning, last-loaded wins.
  - Empty/missing directory → empty index, slices return `coverage: False`,
    no exception.
- **Caching & threading:** cached singleton with a `threading.Lock` and a
  `load(force=False)` method, exactly like `CardLibrary`. Provide a
  `get_pillar_reader()` factory pulling `OIC_PILLARS_DIR` from config on first
  use. Recommend the app factory call `get_pillar_reader().load()` at startup
  (eager), but keep lazy load-on-first-slice as a safety net.

## 7. `slice_likelihood` contract

```python
def slice_likelihood(self, industry: str) -> dict:
    """Return the latest-DBIR likelihood slice for one industry.

    Resolution: resolve_industry_key(industry, SERIES_VERIZON_DBIR) -> [keys].
    First-hit semantics: use the first resolved key that exists in the latest
    DBIR file's `figures`. If a key is resolved but absent in this edition, try
    the next; log DEBUG on fallback. If none resolve/exist, coverage is False
    but the corpus-wide `overall` anchors are STILL returned.

    Never raises. Never derives a probability (see §8).
    """
```

**Return schema (plain dict, JSON-serializable):**

```python
{
    "pillar": "likelihood",
    "coverage": True,                       # False if no sector row resolved
    "industry_canonical": "real estate",    # from normalize_industry
    "resolved_key": "real_estate",          # the DBIR key used, or None
    "source": "Verizon DBIR 2025",          # ready for ctx.source later
    "provenance": {
        "publisher":         "Verizon Data Breach Investigations Report (DBIR)",
        "edition":           "2025",
        "comparable_series": "dbir-by-industry",
        "citation_url":      "https://www.verizon.com/business/resources/reports/dbir/",
        "evidence_type":     "incident_corpus",
        "review_status":     "[REVIEW]",
    },
    "sector": {                             # present only when coverage True
        "top_patterns":     "...",
        "threat_actors":    "External 73%, Internal 27% (breaches)",
        "actor_motives":    "Financial 95%, Espionage 2% (breaches)",
        "data_compromised": "...",
        "notable":          "...",
        "incidents":        1710,
        "breaches":         1542,
        # size splits copied verbatim IF present in the row (not selected on):
        "incidents_small":  115, "incidents_large": 153,
        "breaches_small":   105, "breaches_large":  132,
    },
    "overall": {                            # ALWAYS present when a DBIR file loaded
        "top_breach_patterns":         {...},
        "leading_initial_vectors":     {...},
        "ransomware_share_of_breaches": 0.44,
        "third_party_involvement":      0.30,
        "espionage_motive_share":       0.17,
        "smb_ransomware_share":         0.88,
        "median_ransom_paid_usd":       115000,
    },
}
```

**Pass-through, not transform.** Copy fields straight from the YAML; do not
rename, recompute, round, or reformat. The slice is a *selection* of curated
figures, preserving the "distilled not dumped / figures as the source presents
them" discipline and the audit trail. Only include `sector` size-split keys that
actually exist in the row (some DBIR sectors have no small/large split).

## 8. Honesty guards (enforced in this method)

The DBIR file is explicit: its numbers are **corpus counts, not population base
rates**, and likelihood must be expressed as composition + credibility, never as
a derived annual probability. Therefore:

- The slice MUST NOT contain any computed `annual_probability`, `incidence_rate`,
  `breach_likelihood_pct`, or similar derived field. It carries counts and
  shares **as published** only.
- Do not divide breaches by anything to manufacture a rate. Do not annualize.
- An acceptance test asserts no such key exists (see §9).

This guard is the whole reason likelihood is its own slice carrying no dollar
figure — magnitude lives in the later NetDiligence/IBM slice.

## 9. Acceptance tests

Copy the real uploaded DBIR files (`..._2024.yaml`, `..._2025.yaml`) into
`tests/fixtures/pillars/` and point a `PillarReader` at that dir.

```python
import pytest
from corpus.pillar_reader import PillarReader

@pytest.fixture
def reader():
    r = PillarReader(pillars_dir="tests/fixtures/pillars", enabled=True)
    r.load()
    return r

def test_latest_edition_selected(reader):
    s = reader.slice_likelihood("Healthcare")
    assert s["provenance"]["edition"] == "2025"          # not 2024
    assert s["provenance"]["comparable_series"] == "dbir-by-industry"

def test_healthcare_round_trip(reader):
    s = reader.slice_likelihood("Healthcare")
    assert s["coverage"] is True
    assert s["resolved_key"] == "healthcare"
    assert s["sector"]["incidents"] == 1710
    assert "External 73%" in s["sector"]["threat_actors"]

def test_real_estate_uses_dedicated_dbir_row(reader):
    # validates the step-1 crosswalk judgment end-to-end
    s = reader.slice_likelihood("Real Estate")
    assert s["coverage"] is True
    assert s["resolved_key"] == "real_estate"
    assert "bec" in s["sector"]["notable"].lower() or "wire" in s["sector"]["notable"].lower()

def test_technology_resolves_to_information(reader):
    # many-canonical -> one DBIR key
    s = reader.slice_likelihood("Technology")
    assert s["resolved_key"] == "information"
    assert s["coverage"] is True

def test_overall_anchors_always_present(reader):
    s = reader.slice_likelihood("Healthcare")
    assert s["overall"]["ransomware_share_of_breaches"] == 0.44
    assert s["overall"]["median_ransom_paid_usd"] == 115000

def test_uncovered_industry_keeps_anchors_no_raise(reader):
    # pharmaceuticals has no DBIR column in the crosswalk
    s = reader.slice_likelihood("Pharmaceuticals")
    assert s["coverage"] is False
    assert s["resolved_key"] is None
    assert "overall" in s and s["overall"]["ransomware_share_of_breaches"] == 0.44

def test_unknown_industry_no_raise(reader):
    s = reader.slice_likelihood("underwater basket weaving")
    assert s["coverage"] is False

def test_no_derived_probability_anywhere(reader):
    s = reader.slice_likelihood("Healthcare")
    blob = repr(s).lower()
    for forbidden in ("annual_probability", "incidence_rate", "breach_likelihood"):
        assert forbidden not in blob

def test_pass_through_not_transformed(reader):
    # value is copied verbatim from YAML, not recomputed
    s = reader.slice_likelihood("Healthcare")
    assert s["sector"]["breaches"] == 1542

def test_missing_dir_is_graceful():
    r = PillarReader(pillars_dir="tests/fixtures/does_not_exist", enabled=True)
    r.load()
    s = r.slice_likelihood("Healthcare")
    assert s["coverage"] is False           # no exception

def test_disabled_flag_no_ops():
    r = PillarReader(pillars_dir="tests/fixtures/pillars", enabled=False)
    r.load()
    s = r.slice_likelihood("Healthcare")
    assert s["coverage"] is False
```

## 10. Optional ops helper (build if cheap, not required to pass)

A non-default `coverage_report()` that, for every `canonical_industries()` entry,
reports whether its resolved DBIR key exists in the latest file. This is the
end-to-end integrity check that catches a crosswalk key that doesn't match a
real DBIR `figures` key (a silent-wrong-number guard, and the natural CI check
to pair with the dropdown validation from step 1). No runtime cost unless called.

## 11. Open items to confirm

1. **Pillar directory.** Confirm the real container path/name (`ref_pillars`?
   `app/ref_pillars`? a GCS-synced mount?) and set `OIC_PILLARS_DIR` default
   accordingly. The reader keys on file content, so the exact path only affects
   the glob root.
2. **PyYAML in `requirements.txt`** — confirm present or add.
3. **Eager vs lazy load.** Confirm where the app factory lives (likely
   `main.py`) so startup can call `get_pillar_reader().load()` once; lazy
   fallback stays regardless.
