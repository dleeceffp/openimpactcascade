# OIC Corpus Setup Guide

The application grounds its AI responses on two file-based corpora. Neither requires a cloud
service — both are loaded directly from the filesystem at startup.

---

## Corpus 1 — Cascade Archetype Cards

**What it is:** Markdown grounding cards derived from CTID Attack Flow (`.afb`) files. Each
card encodes a real-world attack chain with techniques, VERIS mappings, DBIR pattern,
levers, and mitigations. The AI uses these cards to anchor questionnaire generation and
chat responses to documented threat scenarios.

**Where the app looks:**
```
app/generated/cascade_archetypes/      (default)
```
Overridden at runtime with the `OIC_CARDS_DIR` environment variable.
Enabled/disabled with `OIC_CARDS_ENABLED=1` (default on).

**How to add or update cards:**

The `tools/cascade_cards/` pipeline converts `.afb` source files into `.card.md` outputs.

### Prerequisites

```bash
# pyyaml is the only non-stdlib dependency
pip install pyyaml
```

You also need the reference data under `refdocs/` to be present (pinned files, not downloaded
at runtime — they are part of the repo):

```
refdocs/
├── flowcorpus/          ← your .afb source files go here
├── flowschema/          ← attack-flow-schema-2.0.0.json
├── matrices/            ← enterprise-attack-19.1.json, ics-attack-19.1.json
├── veris/               ← verisc-enum.json
├── ctidmapping/         ← veris-1.4.0_attack-16.1-enterprise/ics.json
└── oic-mitigation-glosses.yaml
```

### Generate cards (single file)

```bash
cd tools/cascade_cards
python cli.py path/to/your-flow.afb --out ../../app/generated/cascade_archetypes/
```

### Generate cards (entire corpus, `-b` variant — recommended)

```bash
cd tools/cascade_cards
python generate_b.py --corpus ../../refdocs/flowcorpus/ --out ../../app/generated/cascade_archetypes/
```

The `-b` variant produces plain-language prerequisites (no raw MITRE M-codes in the card
body). The pipeline writes a build report alongside each card listing any `[REVIEW]` tokens
that need human confirmation before the card is considered final.

### Card naming convention

Output files follow the pattern `oic-ca-NNN-<slug>-card.md`. The NNN is the archetype
sequence number from the source `.afb` metadata.

---

## Corpus 2 — Statistical Pillar Files

**What it is:** Annual YAML files containing industry-segmented loss and likelihood data
from three published sources: Verizon DBIR, IBM Cost of a Data Breach, and NetDiligence
Cyber Claims. The AI uses these to calibrate probability and cost estimates to the
respondent's industry.

**Where the app looks:**
```
app/corpus/ref_pillars/
├── breach_reports/
│   ├── dbir-likelihood-by-industry.2023.yaml
│   ├── dbir-likelihood-by-industry.2024.yaml
│   └── dbir-likelihood-by-industry.2025.yaml
├── financal/
│   ├── ibm-cost-by-industry.2023.yaml
│   ├── ibm-cost-by-industry.2024.yaml
│   └── ibm-cost-by-industry.2025.yaml
└── threat_landscape/
    ├── netdiligence-cyber-claims.2023.yaml
    ├── netdiligence-cyber-claims.2024.yaml
    └── netdiligence-cyber-claims.2025.yaml
```
Overridden at runtime with `OIC_PILLARS_DIR`. Enabled/disabled with `OIC_PILLARS_ENABLED=1`
(default on).

### Adding a new annual edition

1. Copy an existing file for the same series as a template, e.g.:
   ```
   cp app/corpus/ref_pillars/breach_reports/dbir-likelihood-by-industry.2025.yaml \
      app/corpus/ref_pillars/breach_reports/dbir-likelihood-by-industry.2026.yaml
   ```
2. Update the `edition:` field and all data values from the new published report.
3. The app auto-discovers new files on startup via glob — no code changes required.

### YAML schema

Each file is indexed by `comparable_series` and `edition`. The `PillarReader` in
`app/corpus/pillar_reader.py` documents the expected structure. The `pillar_crosswalk.py`
module handles industry name normalization across series.

---

## Verifying corpus load at startup

Both corpora log their load status at `INFO` level. To confirm they loaded correctly, check
the startup logs for lines from `oic.pillar_reader` and from the cards loader in
`app/ai_question_generator.py`.

You can also hit the `/health` endpoint after starting the app — corpus status is included
in the response.

---

## Environment variable reference

| Variable | Default | Description |
|---|---|---|
| `OIC_CARDS_ENABLED` | `1` | Set to `0` to disable cascade archetype grounding |
| `OIC_CARDS_DIR` | `generated/cascade_archetypes` | Path to `.card.md` files (relative to `/app` in container) |
| `OIC_PILLARS_ENABLED` | `1` | Set to `0` to disable pillar data loading |
| `OIC_PILLARS_DIR` | `corpus/ref_pillars` | Path to pillar YAML directory (relative to `/app` in container) |
