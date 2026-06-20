# Cleanup Notes — OIC_SBX

Deferred work items from the June 2026 structural reorganisation.
Each item is small and self-contained. Prioritise before the next major feature.

---

## Done in this pass (branch `v31devin_01`)

| What | Where |
|---|---|
| Scripts moved out of repo root | `scripts/test_llm_cli.py`, `scripts/validate_models.py` |
| Root `pyproject.toml` added | pytest, ruff, mypy config unified at repo root |
| `src/` layout introduced | `src/oic_llm/`, `src/oic_corpus/` — both importable via `pytest`/`pip install -e .` |
| Single `generated/` tree | All runtime output under root `generated/` with per-feature subdirs |
| Cascade archetype cards moved | `app/generated/cascade_archetypes/` → `generated/cascade_archetypes/` |
| Dockerfile updated | COPY source for archetypes now `generated/cascade_archetypes/` |
| Unified test runner | `pytest` from repo root runs all non-integration tests |
| `tests/conftest.py` created | Adds `src/` + `app/` + `tools/` to `sys.path`; shared fixtures |
| oic_llm tests migrated | `oic_llm/tests/` → `tests/oic_llm/`; absolute imports; integration marker added |

---

## Deferred — next cleanup pass

### 1. Remove the root-level `oic_llm/` directory

**What:** The original `oic_llm/` at the repo root is now superseded by `src/oic_llm/`.
It is kept temporarily so any outstanding branches that `import oic_llm` without adding `src/`
to the path don't break immediately.

**Action:**
```
git rm -r oic_llm/
```
Then update any remaining `sys.path` references (there should be none after this pass).

**Blocker:** Confirm no other branch or tool imports from the root copy.

---

### 2. Remove `app/generated/` entirely

**What:** `app/generated/` is empty of committed content (all files moved to root `generated/`).
The `.gitignore` still has a legacy exception for it to avoid Docker build failures.

**Action:**
```
git rm -r --cached app/generated/
```
Remove the `app/generated/*` exception from `.gitignore`.
Update `Dockerfile` `mkdir` command to remove `app/generated` if still present.

---

### 3. Rename `refdocs/` → `data/`

**What:** `refdocs/` is a non-standard name; `data/` is the 2025 convention for
static reference files (MITRE matrices, VERIS enums, flow schema, pillar YAMLs).

**Action:**
```
git mv refdocs data
```
Update two path constants:
- `tools/cascade_cards/config.py` — `REFDOCS = REPO_ROOT / "refdocs"` → `"data"`
- `tools/attack_flow_workbench/config.py` — `MITRE_MATRICES_DIR` and `ATTACK_FLOW_SCHEMA_FILE`

**Note:** `refdocs/flowcorpus/` has its own `.gitignore` — move that file too.

---

### 4. Move pillar YAML data out of `app/`

**What:** `app/corpus/ref_pillars/*.yaml` is reference data, not application code.
It should live at `data/corpus/ref_pillars/` (after item 3 above).

**Action:** Move the YAML files. Update:
- `tools/attack_flow_workbench/config.py` — `OIC_PILLARS_DIR` default
- `app/config.py` — `OIC_PILLARS_DIR` default
- `Dockerfile` — `COPY` source path for corpus data

---

### 5. `assessment_contexts.db` — confirm never committed

**What:** SQLite runtime database sitting at the repo root. It is covered by the
root `.gitignore` (`*.db`) but should be explicitly listed for clarity.

**Action:**
Add to `.gitignore`:
```
# Runtime SQLite databases
assessment_contexts.db
```
Verify it was never committed:
```
git log --all -- assessment_contexts.db
```
If committed, remove from history:
```
git rm --cached assessment_contexts.db
git commit -m "chore: remove runtime db from tracking"
```

---

### 6. Documentation branch policy — design docs vs. `main`

**Context:** `documentation/coding_instructions/` and `documentation/project/` contain
implementation briefs and ADRs that are essential for developers on feature branches but
must not appear in the public `main` branch.

**Current state:** `documentation/.gitignore` re-includes `coding_instructions/` and
`project/` — they are tracked on feature branches.

**Action before merging to `main`:**

Option A (recommended) — exclude on merge via `.gitignore` on `main`:
```bash
# On main, documentation/.gitignore should NOT re-include project/ or coding_instructions/
# Remove the !project/ and !coding_instructions/ lines before merging.
```

Option B — use a protected branch rule in GitHub:
Add a PR check or CODEOWNERS entry that requires manual review of any changes to
`documentation/project/` or `documentation/coding_instructions/` before merge to `main`.

Option C — move to a private wiki or Confluence and remove from repo entirely.

**Recommendation:** Option A for now (simple, no external dependency).
Before any merge to `main`, confirm `documentation/.gitignore` blocks those directories.

---

### 7. `app/.gitignore` — review for redundancy

**What:** `app/.gitignore` has entries that may now be covered by the root `.gitignore`.
**Action:** Audit and remove duplicates; keep any app-specific entries (session files, etc.).

---

### 8. `oic_llm/pyproject.toml` vs `src/oic_llm/pyproject.toml`

After item 1 (removing root `oic_llm/`), only `src/oic_llm/pyproject.toml` remains.
Review that it does not hard-code `where = ["."]` — it should be `where = ["."]` relative
to `src/oic_llm/` (correct) or removed in favour of the root `pyproject.toml`'s
`[tool.setuptools.packages.find] where = ["src"]`.

---

*Last updated: 2026-06-20*
