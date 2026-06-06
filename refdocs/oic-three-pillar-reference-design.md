# OIC — The Three-Pillar Reference Layer (Design)

**Doc:** OIC-DD-2026-009 · **Status:** draft for review
**Builds on:** OIC-DD-2026-008 (periodic reference artifacts). This generalizes that idea into a
three-pillar **reference layer** — the curated knowledge base that makes OIC a *reference*, not just
a calculator.

---

## 1. The shared discipline (true of all three pillars)

Every pillar obeys the same rules, inherited from the cards and the periodic-artifacts work. These
are non-negotiable and are what make the layer defensible:

- **Distilled, not dumped.** Each source becomes a few curated columns in a structured file, never a
  raw report. The curation is the compression, and the compression is the value.
- **Evidence, not standards.** Ground on what happened and what it cost (incident write-ups, claims,
  surveys, loss data) — not prescriptive standards. Standards appear only as labeling vocabulary
  (ATT&CK).
- **Curated, not scraped.** Figures are hand-entered by a practitioner. Hand entry is more accurate
  at this volume, keeps clear of reproducing copyrighted content, and *is* the moat.
- **Paraphrase and cite, per edition.** Store figures plus a citation; any narrative context is
  reworded. Each edition/year row carries its own citation. Never reproduce report prose or tables.
- **`[REVIEW]` until verified.** New entries are provisional until checked against the source.
- **Select a slice at runtime.** The file on disk can be larger than what reaches the model; the app
  injects only the rows relevant to the assessment. Curation chooses contents twice — once authoring
  the table, once selecting the row.

What differs between pillars is **the question each answers**, and therefore the schema and the
app's use. Three questions → three data models.

| Pillar | Question it answers | Evidence kind | Feeds |
|---|---|---|---|
| Financial | "What does this cost / what should I budget?" | incurred-loss, claims, survey | magnitude inputs + board framing |
| Breach | "How do attacks actually unfold?" | incident write-ups, intrusion studies | cascade authoring + pattern priors |
| Threat landscape | "Is this a credible threat to *my* org?" | prevalence/trajectory by sector | archetype selection + credibility framing |

---

## 2. Pillar 1 — Financial

### 2.1 Purpose
Answers cost and budget questions across the full range from "what did a breach cost" (tactical
proof) to "where are budgets and risk tolerance heading" (strategic). Spans two evidence kinds that
must not be blended.

### 2.2 Evidence kinds (the key distinction)
- **incurred_loss / claims** — IBM Cost of a Data Breach (incurred), NetDiligence (claims). These
  feed the **magnitude** side of the math.
- **survey / sentiment** — Deloitte Future of Cyber and similar board surveys. These inform the
  **"what should I do / where is this heading"** narrative. They are **not** loss figures and do
  **not** feed the magnitude inputs.

### 2.3 Schema (per source × edition)
```
publisher:            "IBM Cost of a Data Breach"
edition:              "2025"
published:            "2025-07"
citation_url:         "..."
evidence_type:        incurred_loss | claims | survey
unit:                 "USD per breach" | "USD per claim" | "% of respondents" ...
banding:              headcount | revenue | none        # how this source segments
comparable_series:    "ibm-cost-by-industry"            # rows sharing this key are trendable
methodology_note:     "..."                              # flag changes vs prior editions
review_status:        reviewed | [REVIEW]
figures:
  <industry>:
    <band>: { value: ..., basis: avg|median }
```
- `comparable_series` is what makes trends honest: only rows sharing a key **and** publisher are
  compared. Never trend across publishers.
- `banding` lets the app reconcile each source's segmentation (IBM/Deloitte vary; NetDiligence uses
  revenue; OIC uses headcount bands 1–50, 51–250, 251–500, 501–2500, 2501–5000, 5000+). The
  band-mapping is a curation judgment recorded in `methodology_note`.

### 2.4 What the app does with it
- **Magnitude estimate:** pull the most recent `incurred_loss`/`claims` rows for the assessment's
  industry and size band → frame the loss-magnitude (LM) inputs. (How tightly this feeds the PERT
  inputs vs. just frames them is the open base-rate question from OIC-DD-2026-006.)
- **Trend:** pull prior editions of the **same publisher/series** → present "this segment's figure
  has moved X% over three years." A within-publisher series only; never a merged number.
- **Strategic/board framing:** surface `survey` data ("boards report rising budgets / shifting risk
  tolerance") as narrative context in the report and recommendations — explicitly separate from the
  loss math.
- **Tiering:** free sees a current headline figure; paid sees the normalized, trend-aware,
  multi-source comparison and the strategic read.

---

## 3. Pillar 2 — Breach

### 3.1 Purpose
Answers "how do attacks actually unfold." Two altitudes: big aggregate studies (DBIR, Palo Alto
Unit 42) for patterns and prevalence, and individual incident write-ups for mechanism. **Its highest
use is as the raw material for the cascade-compression step** — it is the supply chain for the
archetype moat, not just a reference.

### 3.2 Schema (per write-up or study)
```
source:               "Unit 42 Incident Response Report" | "<vendor> incident write-up"
edition / incident:   "2025" | "incident-2025-acme"
citation_url:         "..."
scope:                aggregate_study | individual_incident
dbir_pattern:         system_intrusion | ...            # coarse anchor
sectors_observed:     [...]                              # where it actually occurred
entry:                "phishing attachment" | "exploited VPN" ...
chokepoints:                                             # the compression target
  - step: "initial access"
    lever: odds
    prerequisite: "attachments reach inboxes unfiltered"
  - step: "inhibit recovery"
    lever: size
    prerequisite: "backups reachable from production"
terminal_impact:      "domain-wide encryption" | "loss of control" ...
odds_size_summary:    "few high-leverage gates; recovery inhibition is the size pivot"
review_status:        reviewed | [REVIEW]
```
- For **aggregate studies**, capture prevalence/initial-vector distributions (e.g., "stolen creds =
  Nth most common initial vector") as priors.
- For **individual incidents**, the `chokepoints`/`entry`/`terminal_impact` block is deliberately the
  same shape the cascade cards use — so a breach-pillar entry is one curation step away from being an
  archetype.

### 3.3 What the app does with it
- **Cascade authoring (offline):** the breach pillar is the input to the compress-to-≤6-chokepoints
  step. Aggregate studies validate that an archetype's chokepoints reflect real prevalence; incident
  write-ups supply new candidate archetypes. This is curation tooling, not a runtime feature.
- **Pattern priors (runtime):** aggregate distributions (initial-access vectors, pattern prevalence)
  can frame the odds side of the questionnaire alongside DBIR.
- **Reference (both tiers):** "here's how this class of attack actually broke, grounded in real
  incidents" — free gets the headline, paid gets the full chokepoint/odds-size breakdown.

---

## 4. Pillar 3 — Threat landscape

### 4.1 Purpose
Answers the hardest, highest-value question: **"is this a credible threat to the organization I'm
protecting?"** — not "does this threat exist." This is the industry's weak spot (most fall back on
"the past predicts the future"), and the pillar that most resists AI replacement, because
credibility-for-*this*-org needs both the threat data and knowledge of the org.

### 4.2 Schema (per threat × source)
```
threat:               "ransomware via phishing" | "IT-to-OT pivot" ...
source:               "ENISA Threat Landscape" | "<sector ISAC>" | "Unit 42" ...
edition:              "2025"
citation_url:         "..."
sectors_targeted:     [...]                              # who it actually hits
size_relevance:       "SME-heavy" | "enterprise-skewed" | "all" 
prevalence_signal:    rising | stable | declining        # trajectory, not just presence
credibility_notes:    "preconditions that make this credible for a given org"
linked_archetype:     oic-ca-001-b | none                # ties to a cascade card if one exists
review_status:        reviewed | [REVIEW]
```
- `sectors_targeted` + `size_relevance` are what convert "a threat exists" into "credible for *you*."
- `prevalence_signal` is trajectory — the forward-looking element, paraphrased and cited.
- `linked_archetype` connects the landscape pillar to the cascade library and to Pillar 2.

### 4.3 What the app does with it
- **Archetype selection / ranking:** for the assessment's industry and size, rank which threats (and
  thus which cascade archetypes) are *credible* — replacing the unreliable auto-`sectors` field with
  curated relevance. This is the principled fix for "which 3 archetypes do I show this org."
- **Credibility framing:** state, with citation, why a threat is or isn't credible for this org —
  the "is this real for me" answer the rest of the market hand-waves.
- **Tiering:** free sees that a threat exists and is trending; paid sees the credibility read for
  their sector/size and the linked cascade.

---

## 5. How the pillars interlock

```
THREAT LANDSCAPE ──ranks credible threats──▶ which CASCADE ARCHETYPES to surface
       │                                            ▲
       │                                            │ authored from
       ▼                                            │
   BREACH pillar ──compresses incidents──▶ cascade chokepoints (odds/size)
                                                    │
FINANCIAL pillar ──loss magnitude + trend + board framing──▶ the quantification & the recommendation
```

- Landscape decides **what's worth assessing**; Breach supplies **how it unfolds** (and authors the
  cascades); Financial supplies **what it costs and what to do about the budget**.
- The cascade cards sit at the centre — fed by Breach, selected by Landscape, costed by Financial.
- All four (three pillars + cards) share one engine: distilled YAML, paraphrase-and-cite, slice
  injected at runtime ahead of web search, the model reasons but never invents.

---

## 6. App-wide behaviour (common to all pillars)

- **Loader per pillar:** parse the pillar's YAML files, validate against that pillar's schema, cache.
- **Runtime selection:** given (industry, size, threat/archetype), select the relevant slice from
  each pillar; inject only those rows.
- **Source provenance:** every figure used in a run is attributable to a publisher + edition + URL —
  drive the "sources used" placard from what was actually consumed, not a hardcoded list.
- **Trend computation:** runtime, from per-edition rows sharing a `comparable_series` + publisher
  (recommended over baking deltas into the files, to keep files as pure data).
- **Tier gate:** free = existence + one current figure; paid = normalized, trended, credibility-read,
  cross-source comparison.

---

## 7. Build sequence (deepest value, least waste)

One pillar deep beats three shallow. Order:

1. **Financial** — closest to done (IBM, NetDiligence, Deloitte), clearest free-vs-paid story, direct
   feed to the math. Ship it first.
2. **Breach** — pays for itself by feeding cascade authoring; build alongside archetype curation.
3. **Threat landscape** — highest value, hardest (credibility-for-this-org). Build deliberately, not
   in a rush; it's the pillar that most resists copying.

Hold the small-clean line at the pillar level: a chosen few sources per pillar, curated deeply —
**not** "everything annual." Breadth is the dilution trap; depth is the moat.

---

## 8. Open items

- Base-rate feed: how tightly Financial/Breach priors drive the math vs. frame the LLM inputs
  (carried from OIC-DD-2026-006).
- Band reconciliation: mapping each financial publisher's segmentation onto OIC headcount bands.
- Trend storage: confirm runtime computation over curation-time (recommended runtime).
- Pillar refresh cadences: each pillar refreshes on its own schedule; define per pillar.
