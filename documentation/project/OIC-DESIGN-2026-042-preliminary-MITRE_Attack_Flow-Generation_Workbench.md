# OIC-DESIGN-2026-0XX — Upstream MITRE Attack Flow `.afb` Generation Workbench

**Project:** OpenImpactCascade
**Feature Area:** Upstream scenario discovery, MITRE Attack Flow generation, threat-intel-grounded attack path authoring
**Status:** Draft
**Intended Audience:** OIC maintainers, coding agents, security architects, threat modelers, cyber risk analysts
**Primary Principle:** Generation is permissive; promotion is conservative.

---

## 1. Executive Summary

OpenImpactCascade currently focuses on decision-ready cyber risk scenarios: business-understandable cascade archetypes that can be used to guide questionnaire generation, FAIR-style loss modeling, and risk conversations. That is the correct abstraction for business risk quantification, but it assumes the maintainer or analyst already has a reasonable scenario to analyze.

The proposed `.afb` generation feature addresses the upstream discovery gap.

The feature will generate candidate MITRE Attack Flow `.afb` files from a small number of plain-language inputs such as protected asset, industry, organization size, and likely entry concern. These generated flows are not intended to be consumed directly by the core OpenImpactCascade risk quantification workflow. They are exploratory authoring artifacts. They exist to help maintainers, analysts, and asset owners recognize plausible threat paths before one or more paths are compressed into durable OIC cascade archetype cards.

The generated `.afb` output should be treated as:

* candidate scenario material;
* an attack-flow authoring aid;
* a way to explore plausible adversary progressions;
* a source artifact for later compression;
* a lineage-preserving bridge between public threat intelligence and OIC cascade cards.

It should not be treated as:

* a finished risk model;
* an authoritative incident reconstruction;
* a complete attack tree;
* a substitute for maintainer review;
* a source of operational exploit instructions;
* a business-facing questionnaire artifact.

This design intentionally creates a second standalone web application for initial testing. The standalone application should feel similar to the OpenImpactCascade questionnaire process, but it should stop at candidate `.afb` generation and review. It should not directly inject generated attack paths into the production OIC risk workflow.

---

## 2. Design Intent

The goal is to help an analyst or asset owner move from vague concern to concrete candidate attack paths.

Typical starting points include:

* “I need to protect Active Directory.”
* “We are worried about ransomware.”
* “We have remote access into operational technology.”
* “We are deploying AI agents with too much access.”
* “We are a mid-sized municipality and do not know what realistic cyber scenarios to model.”
* “We are an energy company and need realistic IT-to-OT cyber risk scenarios.”
* “We need examples that a business owner will recognize as plausible.”

The generator should convert these inputs into several candidate `.afb` flows that can be opened, reviewed, edited, and later compressed.

The intended user experience is not “the AI tells you the risk.” The intended experience is:

> “The AI provides several plausible threat paths, grounded in industry-relevant public intelligence, so the maintainer or analyst can decide what should become a governed OIC cascade archetype.”

---

## 3. Relationship to OpenImpactCascade Core

The `.afb` generation workbench must remain upstream of the governed OIC risk workflow.

The intended pipeline is:

```text
Plain-language scenario intake
        ↓
Threat-intel grounding by industry, region, size, asset, and entry concern
        ↓
Candidate MITRE Attack Flow generation
        ↓
Valid `.afb` files
        ↓
Maintainer / analyst review
        ↓
Cascade compression
        ↓
Curated OIC cascade archetype card
        ↓
OpenImpactCascade questionnaire and risk quantification workflow
```

The core OpenImpactCascade app should consume curated cascade cards, not unconstrained generated `.afb` files.

The standalone `.afb` generator is therefore an authoring and discovery tool. It should eventually feed the maintainer workflow, not bypass it.

---

## 4. Design Boundary: Generation vs Compression

This design depends on a strict separation between attack-flow generation and cascade compression.

### 4.1 Generation

Generation is intentionally broad. It may include:

* several possible attacker paths;
* alternate middle steps;
* assumptions;
* industry-specific patterns;
* several possible terminal outcomes;
* links to threat reports or public incidents;
* ATT&CK Enterprise or ATT&CK ICS mappings;
* confidence labels;
* uncertainty markers;
* source lineage;
* maintainer notes;
* branches that may later be dropped.

Generated flows are allowed to be imperfect, provided they are clearly labeled as generated candidates.

### 4.2 Compression

Compression is intentionally conservative. It should:

* prune paths that do not reach the declared terminal impact;
* cluster multiple technical steps into decision-useful stages;
* absorb tactical details into control gates;
* reframe technical actions into business-legible link names;
* preserve only durable attacker requirements;
* remove product/vendor/port/tool-specific leakage from cascade link names;
* record dropped, absorbed, and reframed nodes in a crosswalk file;
* produce one or more curated OIC cascade cards.

The compression maintainer is responsible for deciding whether a generated `.afb` flow deserves promotion.

### 4.3 Governing Principle

> Generation is permissive; promotion is conservative.

This phrase should be included in the feature README and developer documentation.

---

## 5. CAPEC Design Decision

### 5.1 Question

Should CAPEC be used in the `.afb` generation workflow?

### 5.2 Recommendation

CAPEC should not be the primary vocabulary for this feature.

MITRE ATT&CK techniques and tactics should be the primary recognizable vocabulary because they are more familiar to detection engineers, threat intelligence analysts, incident responders, and many security leaders. ATT&CK also aligns naturally with Attack Flow semantics and with existing OIC cascade compression work.

CAPEC may be useful as optional secondary enrichment, but it is likely too fine-grained and software-weakness-oriented for the primary level of this threat modeling workflow.

### 5.3 Why CAPEC Is Too Fine-Grained for the Primary Layer

CAPEC describes common attack patterns. That can be valuable when analyzing application security patterns, software weaknesses, abuse cases, or threat modeling at the design-control level. However, the OIC `.afb` generation feature is trying to generate realistic cyber risk scenarios at a higher level of abstraction.

The target abstraction is:

* recognizable to asset owners;
* compatible with public threat intelligence;
* compressible into OIC cascade archetypes;
* suitable for risk quantification;
* focused on attacker progress toward business impact;
* useful for prevention and detection control discussion.

CAPEC can pull the model toward implementation-level software attack patterns too early. That risks generating flows that are technically interesting but not decision-ready for OIC’s risk modeling purpose.

For example, the business-relevant scenario may be:

> “An attacker gains access through a public-facing application, obtains privileged cloud access, discovers stored data, and causes regulatory exposure.”

At the OIC generation level, ATT&CK-style techniques are sufficient. A CAPEC mapping may be useful only if the maintainer wants to explain the specific application abuse pattern behind the initial access step.

### 5.4 Recommended CAPEC Usage

Use CAPEC as optional metadata only.

CAPEC may be included when:

* the scenario is explicitly about application security;
* the attack path depends on a recognizable software design flaw;
* the generated `.afb` node represents an abuse pattern rather than a general adversary technique;
* the maintainer wants richer traceability for secure design review;
* a coding agent can map CAPEC confidently without inventing details.

CAPEC should not be required for every generated node.

### 5.5 CAPEC Mapping Rule

A generated node may have:

```yaml
attack_mapping:
  primary_framework: "MITRE ATT&CK Enterprise"
  attack_technique_id: "T1190"
  attack_technique_name: "Exploit Public-Facing Application"
  optional_capec:
    capec_id: "CAPEC-###"
    capec_name: "Optional only when strongly justified"
    mapping_confidence: "low | medium | high"
```

If the CAPEC mapping is uncertain, omit it.

Never force a CAPEC mapping simply to make the generated flow look more complete.

---

## 6. Threat-Intel Grounding Requirements

The `.afb` generation workbench must reuse the same threat-intel grounding philosophy used by OpenImpactCascade.

The generator must not produce unconstrained free-association attack paths. It should use the user’s inputs to select relevant grounding material and then generate candidate flows from that context.

### 6.1 Required Grounding Inputs

The initial web application must collect the following:

1. **Protected asset or business function**

   * Example: Active Directory, customer data platform, payment system, remote access, cloud data lake, OT historian, pipeline control environment, municipal emergency services.

2. **Industry**

   * Example: energy, healthcare, financial services, local government, manufacturing, education, retail, SaaS, transportation.

3. **Organization size**

   * Example: small, mid-sized, large enterprise, critical infrastructure operator.
   * Size should influence attacker assumptions, control maturity, threat frequency reasoning, and likely exposure patterns.

4. **Region**

   * Example: Canada, United States, North America, Europe, global.
   * Region should influence public reporting sources, regulatory context, and industry incident examples.

5. **Entry concern**

   * Suggested controlled options:

     * phishing or social engineering;
     * remote access exposure;
     * public-facing application;
     * cloud identity or SaaS compromise;
     * supplier or managed service provider;
     * physical intrusion or removable media;
     * over-provisioned AI agent;
     * unknown / recommend likely entries.

6. **Terminal impact concern**

   * Suggested controlled options:

     * ransomware / business interruption;
     * data theft / privacy breach;
     * fraud or financial loss;
     * operational disruption;
     * safety-impacting control impairment;
     * regulatory exposure;
     * reputation damage;
     * unknown / recommend likely outcomes.

7. **Optional free-text concern**

   * Example: “We use a lot of contractors,” “We are worried about VPN appliances,” “Our OT network has legacy remote access,” “We are adopting autonomous AI workflows.”

### 6.2 Grounding Source Types

The generator should prioritize:

* existing OIC curated cascade archetype cards;
* OIC threat-intel corpus metadata;
* public incident reports;
* public cyber threat intelligence reports;
* sector-specific breach reports;
* MITRE ATT&CK Enterprise and ATT&CK ICS;
* regulatory or advisory sources where appropriate;
* curated search results already supported by the OpenImpactCascade approach.

The coding agent should avoid creating a new unrelated retrieval strategy. The first implementation should reuse or adapt the existing OIC grounding logic as much as possible.

### 6.3 Grounding Context Object

The generator should assemble a structured grounding context before asking the model to generate flows.

Recommended object:

```json
{
  "request": {
    "asset": "Active Directory",
    "industry": "energy",
    "organization_size": "large enterprise",
    "region": "Canada",
    "entry_concern": "phishing",
    "terminal_impact": "ransomware / business interruption",
    "free_text": "Concerned about contractor accounts and remote access."
  },
  "matched_oic_cards": [
    {
      "card_id": "oic-ca-001-b",
      "title": "Generalized ransomware cascade",
      "match_reason": "Ransomware terminal impact and identity-oriented entry concern."
    }
  ],
  "matched_public_reports": [
    {
      "title": "Public report title",
      "publisher": "Publisher",
      "year": 2025,
      "relevance": "Sector ransomware activity, identity compromise, or remote access exposure.",
      "source_type": "threat_report | breach_report | advisory | case_study"
    }
  ],
  "matched_attack_techniques": [
    {
      "framework": "ATT&CK Enterprise",
      "technique_id": "T1566",
      "technique_name": "Phishing",
      "tactic": "Initial Access",
      "reason": "Selected entry concern."
    }
  ],
  "generation_constraints": {
    "max_flows": 5,
    "max_nodes_per_flow": 12,
    "allow_branches": true,
    "allow_speculation": true,
    "require_uncertainty_labels": true,
    "require_lineage_notes": true,
    "operational_detail_level": "defensive_summary_only"
  }
}
```

---

## 7. Generated Flow Requirements

The workbench should generate between three and five candidate `.afb` flows per request.

Each generated flow should have a distinct scenario shape. Avoid five variants that are merely wording changes.

Example spread for an energy-sector Active Directory ransomware concern:

1. Phishing to identity compromise to privileged access to ransomware.
2. VPN or remote access compromise to lateral movement to business interruption.
3. Supplier account compromise to administrative access to data theft and extortion.
4. Cloud identity compromise to SaaS data theft to regulatory exposure.
5. Helpdesk/social engineering to MFA reset to privileged access to ransomware.

Each flow should include:

* title;
* one-paragraph plain-language summary;
* declared protected asset;
* declared terminal impact;
* industry and size assumptions;
* entry vector;
* ATT&CK mappings;
* defensive interpretation;
* evidence and lineage notes;
* uncertainty labels;
* candidate status;
* generated timestamp;
* generator version;
* schema validation result;
* safety classification.

---

## 8. Node-Level Requirements

Each Attack Flow node should be understandable both to technical reviewers and to later compression maintainers.

Recommended node fields:

```json
{
  "node_id": "n003",
  "node_type": "attack_action",
  "name": "Obtain valid domain credentials",
  "description": "The attacker obtains credentials that allow access to internal identity-managed systems.",
  "attacker_goal": "Convert initial access into reusable authenticated access.",
  "attacker_requirement": "A credential, token, session, or account reset path must be available.",
  "defender_control_gate": "Phishing-resistant MFA, conditional access, credential monitoring, and helpdesk verification reduce this path.",
  "attack_mapping": {
    "framework": "MITRE ATT&CK Enterprise",
    "tactic": "Credential Access",
    "technique_id": "T####",
    "technique_name": "Technique Name"
  },
  "evidence": {
    "grounding_type": "public_report | oic_card | analyst_assumption | model_inference",
    "confidence": "low | medium | high",
    "lineage_note": "Explain why this node is included."
  },
  "compression_hint": {
    "likely_action": "cluster | absorb | preserve | drop",
    "candidate_cascade_link": "Identity compromise enables privileged access"
  }
}
```

The generated `.afb` file itself may not support every field natively. When native Attack Flow fields are insufficient, store OIC-specific metadata in notes, external references, extensions, or a sidecar JSON file.

---

## 9. Sidecar Metadata

Because `.afb` files are intended to remain compatible with MITRE Attack Flow tooling, OIC-specific metadata should not corrupt or over-customize the `.afb` schema.

The generator should create two outputs:

```text
candidate-flow.afb
candidate-flow.oic-meta.json
```

The sidecar file should contain OIC-specific metadata.

Recommended sidecar structure:

```json
{
  "schema_version": "oic-afb-meta-v0.1",
  "source_afb": "candidate-flow.afb",
  "candidate_id": "oic-afb-candidate-2026-000123",
  "status": "generated_candidate",
  "not_for_quantification": true,
  "request": {
    "asset": "Active Directory",
    "industry": "energy",
    "organization_size": "large enterprise",
    "region": "Canada",
    "entry_concern": "phishing",
    "terminal_impact": "ransomware / business interruption"
  },
  "grounding": {
    "oic_cards_used": [],
    "reports_used": [],
    "search_queries_used": [],
    "mitre_attack_version": "record version if available",
    "capec_used": false
  },
  "generation": {
    "model": "configured model name",
    "prompt_version": "oic-afb-generator-prompt-v0.1",
    "generated_at": "ISO-8601 timestamp",
    "temperature": "configured value",
    "safety_profile": "defensive_summary_only"
  },
  "review": {
    "review_status": "unreviewed",
    "reviewer": null,
    "review_notes": [],
    "promotion_decision": "not_decided"
  },
  "compression": {
    "compressed": false,
    "crosswalk_file": null,
    "promoted_card_id": null
  }
}
```

---

## 10. Compression Crosswalk

Although compression is out of scope for the `.afb` generator, the generator should produce hints that make later compression easier.

When a maintainer compresses a generated `.afb`, the workbench should produce a crosswalk file.

Recommended output:

```json
{
  "schema_version": "oic-compression-crosswalk-v0.1",
  "source_afb": "candidate-flow.afb",
  "source_meta": "candidate-flow.oic-meta.json",
  "promoted_card": "oic-ca-0XX-example.md",
  "compression_status": "draft | reviewed | promoted | rejected",
  "node_decisions": [
    {
      "source_node_id": "n001",
      "source_node_name": "Phishing email reaches user",
      "decision": "absorb",
      "target_cascade_link": "Initial access through identity compromise",
      "rationale": "The exact phishing mechanism is less durable than the identity-control gate."
    },
    {
      "source_node_id": "n004",
      "source_node_name": "Discover domain trust relationships",
      "decision": "cluster",
      "target_cascade_link": "Authenticated access enables privilege discovery",
      "rationale": "Discovery is relevant only as part of the attacker requirement to identify a path to privilege."
    },
    {
      "source_node_id": "n009",
      "source_node_name": "Attempt unrelated data theft branch",
      "decision": "drop",
      "target_cascade_link": null,
      "rationale": "Branch does not contribute to declared terminal impact for this card."
    }
  ],
  "promoted_links": [
    {
      "link_number": 1,
      "link_name": "Initial access through identity compromise",
      "source_nodes": ["n001", "n002", "n003"],
      "succeeds_when": "A user, contractor, or helpdesk process allows attacker-controlled authentication to an internal identity-managed system.",
      "control_gate": "Phishing-resistant MFA, conditional access, identity monitoring, and helpdesk verification."
    }
  ]
}
```

The crosswalk is essential for trust. It records why the maintainer converted a rich attack flow into a shorter decision-ready cascade.

---

## 11. Standalone Web Application

A second standalone web application should be created for initial testing.

Working name:

```text
OIC Flow Lab
```

Alternative names:

* OIC Attack Flow Lab
* OIC Scenario Generator
* OIC Flow Workbench
* OIC Candidate Flow Generator

Recommended name:

```text
OIC Flow Lab
```

This name clearly separates the feature from the governed OIC risk quantification app.

---

## 12. OIC Flow Lab User Experience

The standalone app should be similar in feel to the OpenImpactCascade questionnaire process, but its output is different.

OpenImpactCascade asks questions to produce a risk analysis.

OIC Flow Lab asks questions to produce candidate attack flows.

### 12.1 User Journey

```text
Home
  ↓
Scenario intake
  ↓
Threat-intel grounding preview
  ↓
Candidate flow generation
  ↓
Flow review
  ↓
Download `.afb`
  ↓
Download sidecar metadata
  ↓
Optional maintainer notes
  ↓
Optional compression handoff
```

### 12.2 Screen 1 — Home

Purpose:

* explain that this is an upstream candidate-flow generator;
* warn that generated flows are not curated risk models;
* explain that outputs require maintainer review;
* link back to OpenImpactCascade.

Suggested copy:

> OIC Flow Lab generates candidate MITRE Attack Flow files for scenario discovery. Generated flows are exploratory artifacts. They are not risk assessments and are not consumed directly by OpenImpactCascade until reviewed and compressed into curated cascade archetypes.

### 12.3 Screen 2 — Scenario Intake

The form should collect:

* asset or business function;
* industry;
* organization size;
* region;
* entry concern;
* terminal impact concern;
* optional free-text concern;
* number of candidate flows;
* whether to include alternate branches;
* whether to include ATT&CK ICS when relevant.

The form should use controlled options wherever possible.

Free text should enrich the scenario, not define the whole generation space.

### 12.4 Screen 3 — Grounding Preview

Before generating flows, the app should show a grounding preview.

This should include:

* matched OIC cascade cards;
* matched industry threat reports;
* matched ATT&CK tactics and techniques;
* selected assumptions;
* unavailable or weak grounding areas.

This screen is important because it builds user trust and gives the maintainer a chance to catch a bad grounding path before generation.

Example warning:

> Grounding is weak for “small Canadian energy cooperative with over-provisioned AI agent.” The generator will use broader energy-sector and identity-governance patterns and label the AI-agent path as low-confidence.

### 12.5 Screen 4 — Candidate Flow Generation

After grounding confirmation, the app generates candidate flows.

The generation output should include:

* list of candidate flows;
* scenario summaries;
* entry vector;
* terminal impact;
* number of nodes;
* ATT&CK coverage;
* confidence level;
* grounding quality;
* download buttons;
* “open in Attack Flow Builder” guidance;
* maintainer notes field.

### 12.6 Screen 5 — Flow Review

The review screen should let the maintainer:

* inspect nodes;
* inspect edges;
* inspect ATT&CK mappings;
* view source lineage;
* mark nodes as plausible, weak, irrelevant, or unsafe;
* add comments;
* mark a candidate as suitable for compression;
* reject a candidate;
* export `.afb` and sidecar metadata.

Initial implementation can keep this simple. Editing the graph itself can be deferred.

### 12.7 Screen 6 — Export

Each candidate should export:

```text
candidate-name.afb
candidate-name.oic-meta.json
candidate-name.review.md
```

Future exports may include:

```text
candidate-name.compression-crosswalk.json
candidate-name.oic-card-draft.md
```

---

## 13. Application Architecture

### 13.1 Initial Local / Developer Architecture

For the first test version:

```text
Flask app
  ├── routes
  │   ├── /
  │   ├── /generate
  │   ├── /grounding-preview
  │   ├── /candidate/<id>
  │   ├── /download/<id>.afb
  │   ├── /download/<id>.json
  │   └── /review/<id>
  ├── services
  │   ├── grounding_service.py
  │   ├── attack_flow_generator.py
  │   ├── afb_validator.py
  │   ├── mitre_mapping_service.py
  │   ├── capec_optional_mapper.py
  │   ├── export_service.py
  │   └── review_service.py
  ├── templates
  │   ├── home.html
  │   ├── intake.html
  │   ├── grounding_preview.html
  │   ├── generated_flows.html
  │   ├── candidate_detail.html
  │   └── review.html
  ├── generated
  │   ├── afb/
  │   ├── metadata/
  │   └── reviews/
  └── tests
      ├── test_grounding.py
      ├── test_afb_generation.py
      ├── test_afb_validation.py
      └── test_exports.py
```

### 13.2 Future GCP Architecture

For a GCP-hosted test environment:

```text
Cloud Run: oic-flow-lab-web
  ↓
Cloud Run: oic-flow-generator-worker
  ↓
Cloud Storage: candidate `.afb`, metadata, reviews
  ↓
Cloud SQL or Firestore: request metadata and review status
  ↓
Secret Manager: model keys, search keys, config secrets
  ↓
Cloud Logging: generation events, validation events, errors
  ↓
BigQuery: optional analytics for test telemetry
  ↓
Vertex AI or configured LLM provider: generation and summarization
```

Use Cloud Run for the first deployed version because the app is container-friendly, stateless by design, and aligned with the current OpenImpactCascade deployment pattern.

Use Cloud Storage for generated artifacts because `.afb`, JSON metadata, and review notes are file-like outputs.

Use Secret Manager for API keys and model credentials.

Use Cloud Logging and structured logs from the beginning. This feature needs traceability because generated cyber scenarios must be reviewable.

Use Cloud SQL or Firestore only when review workflow state becomes important. For a first local test, filesystem storage is acceptable.

---

## 14. Coding Agent Instructions

The coding agent must build a separate standalone web application for `.afb` creation. Do not modify the production OpenImpactCascade workflow to consume generated `.afb` files directly.

### 14.1 Repository Strategy

Preferred initial approach:

```text
/openimpactcascade
/oic-flow-lab
```

The standalone app may live in the same repository under a separate directory or in a separate experimental repository. During early testing, separation is more important than code reuse purity.

The coding agent should reuse logic from OpenImpactCascade where appropriate, especially:

* industry and region input patterns;
* organization-size handling;
* existing threat-intel grounding methods;
* existing web search enrichment logic;
* existing curated cascade archetype loading;
* current prompt discipline around factual grounding;
* current UI style and questionnaire-like flow.

The coding agent should not fork the entire OIC app unless necessary.

### 14.2 Required First Implementation

Build a Flask application named `oic-flow-lab`.

Minimum routes:

```text
GET  /
GET  /intake
POST /grounding-preview
POST /generate
GET  /candidate/<candidate_id>
GET  /download/<candidate_id>/afb
GET  /download/<candidate_id>/metadata
POST /review/<candidate_id>
GET  /health
```

Minimum templates:

```text
home.html
intake.html
grounding_preview.html
generated_flows.html
candidate_detail.html
review.html
error.html
```

Minimum services:

```text
grounding_service.py
attack_flow_generator.py
afb_builder.py
afb_validator.py
metadata_builder.py
export_service.py
review_service.py
```

### 14.3 Reuse OpenImpactCascade Threat-Intel Grounding

The coding agent must inspect the current OpenImpactCascade codebase and identify the modules responsible for:

* industry-specific grounding;
* organization-size-sensitive context;
* region-sensitive context;
* cascade archetype card loading;
* AI questionnaire grounding;
* web search gap-fill;
* rationale generation;
* source citation or source summary handling.

The coding agent should adapt those mechanisms into `grounding_service.py`.

The first implementation should not invent an entirely new RAG system. It should use the same style of curated corpus plus targeted web search that OIC already uses.

### 14.4 Grounding Service Contract

Implement:

```python
class GroundingService:
    def build_grounding_context(self, request: FlowGenerationRequest) -> GroundingContext:
        ...
```

Required behavior:

1. Accept asset, industry, size, region, entry concern, terminal impact, and free text.
2. Search local curated OIC cascade archetype cards.
3. Search or retrieve industry-specific public threat intelligence summaries.
4. Identify likely ATT&CK Enterprise or ATT&CK ICS tactics and techniques.
5. Return structured grounding context.
6. Label weak grounding explicitly.
7. Preserve source lineage.
8. Avoid unsupported claims.

### 14.5 Flow Generation Service Contract

Implement:

```python
class AttackFlowGenerator:
    def generate_candidate_flows(self, grounding_context: GroundingContext) -> list[CandidateFlow]:
        ...
```

Required behavior:

1. Generate three to five candidate flows.
2. Use grounding context as the primary source.
3. Keep flows defensive and high-level.
4. Produce valid `.afb` output.
5. Produce OIC sidecar metadata.
6. Include ATT&CK mappings where appropriate.
7. Include optional CAPEC only when strongly justified.
8. Include uncertainty labels.
9. Include compression hints.
10. Never include exploit code, malware instructions, credential theft instructions, or procedural offensive detail.

### 14.6 AFB Builder Contract

Implement:

```python
class AFBBuilder:
    def build_afb(self, candidate_flow: CandidateFlow) -> dict:
        ...
```

Required behavior:

1. Build a valid Attack Flow JSON object.
2. Preserve node order and relationships.
3. Include Attack Flow actions, assets, operators, and conditions where appropriate.
4. Store OIC-specific metadata only in safe extension points or sidecar files.
5. Keep the `.afb` compatible with Attack Flow Builder.
6. Run schema validation before export.

### 14.7 Validator Contract

Implement:

```python
class AFBValidator:
    def validate(self, afb_json: dict) -> ValidationResult:
        ...
```

Required behavior:

1. Validate JSON structure.
2. Validate required Attack Flow fields.
3. Validate edges reference existing nodes.
4. Validate candidate status metadata exists.
5. Validate every node has a plain-language defensive description.
6. Validate every ATT&CK mapping is syntactically plausible.
7. Warn when CAPEC is used.
8. Fail closed if the flow contains operational exploit instructions.

### 14.8 Safety Filter Contract

Implement a safety review before file export.

The filter should reject or require manual review if generated content includes:

* exploit steps;
* malware build instructions;
* evasion instructions;
* credential theft procedures;
* stealth guidance;
* payload commands;
* real target identification;
* instructions to bypass controls;
* weaponized scripts;
* instructions that materially enable unauthorized activity.

The generator may describe attacker requirements and defender control gates. It must not provide procedural offensive instructions.

Allowed:

> “The attacker requires authenticated access to a remote service.”

Not allowed:

> Specific procedural instructions for stealing, bypassing, or exploiting access.

### 14.9 Prompting Requirements

The generation prompt must include:

* candidate status;
* defensive-use framing;
* grounding context;
* industry and size assumptions;
* requested number of flows;
* required output schema;
* prohibition on operational exploit detail;
* instruction to label uncertainty;
* instruction to avoid inventing source claims;
* instruction to include ATT&CK mappings only when appropriate;
* instruction to use CAPEC only as optional metadata;
* instruction to include compression hints.

Prompt design should use structured JSON outputs wherever possible. Avoid asking the model for prose first and then trying to parse it.

### 14.10 Testing Requirements

Implement tests for:

* controlled intake choices;
* grounding context creation;
* weak-grounding warning;
* `.afb` JSON generation;
* schema validation;
* export naming;
* metadata sidecar creation;
* safety rejection;
* CAPEC omission by default;
* ATT&CK mapping presence for common entry concerns;
* review status update.

Add test fixtures for at least:

1. Energy, large enterprise, Active Directory, phishing, ransomware.
2. Healthcare, mid-sized, patient records, SaaS compromise, data breach.
3. Local government, small, remote access, ransomware.
4. Manufacturing, OT historian, supplier compromise, operational disruption.
5. SaaS startup, AI agent, over-provisioned access, data exposure.

---

## 15. Initial Data Models

### 15.1 FlowGenerationRequest

```python
@dataclass
class FlowGenerationRequest:
    asset: str
    industry: str
    organization_size: str
    region: str
    entry_concern: str
    terminal_impact: str
    free_text: str | None = None
    number_of_flows: int = 5
    allow_branches: bool = True
    include_ics: bool = False
    include_capec: bool = False
```

### 15.2 GroundingContext

```python
@dataclass
class GroundingContext:
    request: FlowGenerationRequest
    matched_oic_cards: list[dict]
    matched_reports: list[dict]
    matched_attack_techniques: list[dict]
    industry_context: dict
    size_context: dict
    region_context: dict
    assumptions: list[str]
    weak_grounding_warnings: list[str]
    source_lineage: list[dict]
```

### 15.3 CandidateFlow

```python
@dataclass
class CandidateFlow:
    candidate_id: str
    title: str
    summary: str
    asset: str
    industry: str
    organization_size: str
    region: str
    entry_vector: str
    terminal_impact: str
    nodes: list[FlowNode]
    edges: list[FlowEdge]
    assumptions: list[str]
    uncertainty: list[str]
    grounding_refs: list[dict]
    compression_hints: list[dict]
```

### 15.4 FlowNode

```python
@dataclass
class FlowNode:
    node_id: str
    node_type: str
    name: str
    description: str
    attacker_goal: str
    attacker_requirement: str
    defender_control_gate: str
    attack_tactic: str | None
    attack_technique_id: str | None
    attack_technique_name: str | None
    capec_id: str | None = None
    capec_name: str | None = None
    evidence_confidence: str = "medium"
    lineage_note: str | None = None
    compression_hint: str | None = None
```

---

## 16. Prompt Output Contract

The model should produce candidate flows in a structured intermediate format before `.afb` conversion.

Example:

```json
{
  "flows": [
    {
      "title": "Phishing-led identity compromise to ransomware impact",
      "summary": "A user or contractor account is compromised, allowing authenticated access that supports privilege discovery and later business interruption.",
      "entry_vector": "phishing",
      "terminal_impact": "ransomware / business interruption",
      "confidence": "medium",
      "nodes": [
        {
          "id": "n001",
          "name": "User receives targeted phishing message",
          "type": "attack_action",
          "attacker_goal": "Create an opportunity for initial access.",
          "attacker_requirement": "A user can be induced to interact with attacker-controlled content.",
          "defender_control_gate": "Email filtering, user reporting, phishing-resistant authentication, and security awareness reduce this path.",
          "attack_mapping": {
            "framework": "MITRE ATT&CK Enterprise",
            "tactic": "Initial Access",
            "technique_id": "T1566",
            "technique_name": "Phishing"
          },
          "evidence_confidence": "medium",
          "lineage_note": "Included because phishing was selected as the entry concern and is common in public ransomware reporting.",
          "compression_hint": "Likely absorbed into an identity compromise cascade link."
        }
      ],
      "edges": [
        {
          "source": "n001",
          "target": "n002",
          "relationship": "enables"
        }
      ],
      "uncertainty": [
        "Specific phishing mechanism is not asserted.",
        "Privilege path depends on local identity and access controls."
      ]
    }
  ]
}
```

The conversion from this intermediate structure to `.afb` should be deterministic.

---

## 17. Review and Promotion Workflow

The standalone app should support review states.

Recommended states:

```text
generated
review_started
needs_revision
rejected
candidate_for_compression
compressed_draft
promoted_to_oic_card
archived
```

Only `promoted_to_oic_card` artifacts should be eligible for the core OIC app.

The review UI should force the maintainer to answer:

1. Is the scenario plausible for the stated industry and size?
2. Is the entry vector plausible?
3. Is the terminal impact plausible?
4. Are the ATT&CK mappings reasonable?
5. Are any branches too speculative?
6. Is any content too operational or unsafe?
7. Should this become one cascade card, several cascade cards, or no card?
8. What should be pruned, clustered, absorbed, reframed, or preserved?

---

## 18. Security and Abuse Safeguards

The `.afb` workbench is a cyber scenario generation system and must be treated as dual-use.

Required safeguards:

* authenticated access for any hosted version;
* no anonymous public generation endpoint during early testing;
* generation rate limits;
* structured logs;
* prompt and output retention for review;
* explicit defensive-use banner;
* safety classifier before export;
* no exploit code or procedural offensive detail;
* no targeting of real named organizations unless the user is working from a public incident report and the output remains defensive;
* no enrichment that turns a scenario into a how-to attack guide;
* no real credential, token, or secret processing;
* no scanning or active reconnaissance features;
* no automatic attack execution or validation.

The app should help users understand threat paths. It should not operationalize those paths.

---

## 19. GCP Deployment Recommendations

Initial hosted deployment should use Google Cloud Platform with a minimal, auditable footprint.

### 19.1 Recommended Services

Use:

* **Cloud Run** for the Flask web app and later worker service.
* **Cloud Storage** for `.afb`, sidecar metadata, and review files.
* **Secret Manager** for API keys and model credentials.
* **Cloud Logging** for structured generation and validation logs.
* **Cloud IAM** for least-privilege service accounts.
* **Cloud SQL or Firestore** only when persistent review state is needed.
* **BigQuery** later for usage analytics and grounding quality metrics.
* **Vertex AI** if the project standardizes on Gemini or GCP-native model invocation.

### 19.2 Deployment Environments

Use at least three environments:

```text
local
dev
review
```

Avoid a public production environment until the safety, review, and validation workflow is stable.

### 19.3 Service Accounts

Create separate service accounts:

```text
oic-flow-lab-web
oic-flow-lab-generator
oic-flow-lab-storage-writer
oic-flow-lab-secret-reader
```

Do not run the app with broad owner/editor permissions.

### 19.4 Artifact Buckets

Recommended buckets:

```text
oic-flow-lab-dev-candidates
oic-flow-lab-review-candidates
```

Recommended object structure:

```text
/candidates/{candidate_id}/flow.afb
/candidates/{candidate_id}/metadata.json
/candidates/{candidate_id}/review.md
/candidates/{candidate_id}/generation_prompt.json
/candidates/{candidate_id}/validation.json
```

### 19.5 Logging

Use structured logs with fields:

```json
{
  "event": "candidate_flow_generated",
  "candidate_id": "oic-afb-candidate-2026-000123",
  "industry": "energy",
  "organization_size": "large enterprise",
  "region": "Canada",
  "entry_concern": "phishing",
  "terminal_impact": "ransomware",
  "grounding_quality": "medium",
  "validation_status": "passed",
  "safety_status": "passed"
}
```

Do not log secrets, full prompts containing sensitive customer details, or uploaded proprietary reports unless explicitly permitted.

---

## 20. Developer Upskilling Recommendations

For a small startup team building this on GCP, prioritize hands-on learning in the following areas:

1. Cloud Run service deployment.
2. Secret Manager and service account IAM.
3. Cloud Logging and structured logs.
4. Cloud Storage object lifecycle and signed URLs.
5. Vertex AI model invocation and prompt governance.
6. BigQuery basics for telemetry analysis.
7. Secure CI/CD for containerized Python apps.

The team should use Google Skills / Cloud Skills Boost labs for hands-on practice before hardening the deployed version.

---

## 21. Minimum Viable Product

The MVP should not attempt full graph editing, automated compression, or production OIC integration.

MVP scope:

* standalone Flask app;
* questionnaire-like intake;
* grounding preview;
* generate three candidate flows;
* export `.afb`;
* export sidecar metadata;
* show ATT&CK mappings;
* omit CAPEC by default;
* include weak-grounding warnings;
* include review notes;
* validate generated `.afb`;
* prevent operational exploit detail;
* store outputs locally or in a dev bucket.

Explicitly out of scope for MVP:

* automatic promotion into OIC;
* automated cascade compression;
* graph editing UI;
* multi-user workflow;
* enterprise tenant isolation;
* full CAPEC mapping;
* attack simulation;
* exploit validation;
* production SaaS deployment.

---

## 22. Future Enhancements

Potential future features:

1. Upload an existing `.afb` and ask the workbench to suggest compression candidates.
2. Generate a draft compression crosswalk.
3. Generate a draft OIC cascade card for maintainer review.
4. Compare several candidate flows side by side.
5. Add confidence scoring for grounding quality.
6. Add industry-specific scenario packs.
7. Add private enterprise corpus grounding.
8. Add control mapping to ATT&CK mitigations or CTID defensive measures.
9. Add “business-owner preview” that explains the flow without technical mappings.
10. Add “why this matters” explanations for each attacker requirement.
11. Add support for ATT&CK ICS when industry and asset justify it.
12. Add optional CAPEC enrichment for application-security-specific paths.
13. Add a queue-based worker for long-running generation.
14. Add signed download links for hosted artifacts.
15. Add export packages suitable for maintainer pull requests.

---

## 23. Open Questions

1. Should the first implementation generate native `.afb` directly or generate intermediate JSON first and then convert deterministically?

   * Recommendation: generate intermediate JSON first.

2. Should generated flows be stored permanently?

   * Recommendation: yes in dev/review environments, with retention controls.

3. Should users be able to edit flows in the first version?

   * Recommendation: no. Allow review notes first.

4. Should CAPEC be enabled by default?

   * Recommendation: no.

5. Should generated flows appear inside the main OIC app?

   * Recommendation: no. Only promoted cascade cards should appear in OIC.

6. Should the generator create five flows every time?

   * Recommendation: default to three for speed and quality; allow five for richer exploration.

7. Should the model cite sources inside `.afb`?

   * Recommendation: include short lineage notes inside `.afb` and full source detail in sidecar metadata.

8. Should AI-agent abuse be treated as a first-class entry concern?

   * Recommendation: yes, but label as emerging and use conservative grounding.

---

## 24. Success Criteria

The feature is successful if:

* a maintainer can generate plausible candidate flows from simple inputs;
* flows are valid `.afb` files;
* flows can be opened in Attack Flow Builder;
* flows are grounded in industry and organization-size context;
* generated paths are recognizable to asset owners;
* generated paths do not contain operational offensive instructions;
* maintainers can review and reject weak flows;
* at least one generated flow can be compressed into an OIC cascade card;
* the core OIC app remains governed and does not consume unreviewed `.afb` files.

The feature fails if:

* generated flows are treated as authoritative;
* the main OIC app consumes unreviewed flows;
* flows contain exploit instructions;
* CAPEC mappings create false precision;
* generated branches overwhelm the maintainer;
* source lineage is missing;
* every flow looks like generic ransomware regardless of industry, size, or asset;
* the app becomes a disconnected prototype instead of reusing OIC’s grounding approach.

---

## 25. Final Recommendation

Build OIC Flow Lab as a standalone upstream application.

Keep it questionnaire-like, but make the output candidate `.afb` files rather than risk assessments.

Use MITRE ATT&CK as the primary recognizable vocabulary. Use ATT&CK ICS when the asset and industry justify it. Treat CAPEC as optional enrichment for application-security-specific paths, not as a core dependency.

Reuse OpenImpactCascade’s threat-intel grounding approach for industry, region, organization size, and curated cascade-card context. Do not create a disconnected generation engine.

Most importantly, preserve the firewall between generated attack flows and governed OIC cascade archetypes.

The maintainer remains responsible for compression, promotion, and risk-model quality.

Generation is permissive.

Promotion is conservative.
