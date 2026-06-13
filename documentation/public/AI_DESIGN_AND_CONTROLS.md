# AI Design and Controls: OpenImpactCascade

| Field | Value |
|-------|-------|
| **Document ID** | OIC-DOC-AIDC-001 |
| **Status** | Current |
| **Date** | 2026-06-13 |
| **Owner** | D. Leece |
| **Supersedes** | EXECUTIVE_SUMMARY.md, SAFEGUARDS_README.md (both copies), AI_Safeguards_DataExposure_README.md, TRAINING_CLARIFICATION_INDEX.md, TRAINING_DATA_CONFIRMATION.md |

---

## 1. Overview and Purpose

OpenImpactCascade (OIC) is a freemium SaaS application that helps small and medium businesses quantify cyber risk using the FAIR (Factor Analysis of Information Risk) methodology. The application uses a large language model (LLM) extensively: to generate industry-specific risk assessment questionnaires, to assist users during the questionnaire process via a chat interface, and to produce rationale that ties risk estimates to authoritative source material.

Because the application processes business risk data — including descriptions of industry, organization size, threat scenarios, and control maturity — users and security reviewers need a clear, accurate account of how AI is used, where data flows, and what controls are in place. This document provides that account. It consolidates and supersedes earlier individual documents on this topic, resolving known conflicts between them.

The organizing principle throughout this document is the same one that governs the application design: **commercial API use provides strong contractual protections against model training reuse, but the dominant exposure risks lie in operational data flow** — where data goes before, during, and after inference. Both sets of risks are addressed here.

---

## 2. AI Vendor and Model

### 2.1 Primary LLM Provider: Anthropic

OIC routes all generative AI requests through **Anthropic's commercial API**. The current default model is `claude-sonnet-4-6`, configured in `app/config.py` via the `OIC_MODEL` environment variable. The application also references a fast/cheap tier (`OIC_MODEL_FAST`, defaulting to `claude-haiku-4-5`) and a deep-analysis tier (`OIC_MODEL_DEEP`, defaulting to `claude-opus-4-8`), though the primary user-facing paths use the sonnet-tier model.

All model identifiers are environment-overridable. This means:
- No model strings are hardcoded across the application except in `config.py`
- Upgrading to a new model release requires a single configuration change
- Staging and production environments can use different models without code changes

### 2.2 API Endpoint Classification

The application uses **Anthropic's commercial/enterprise API endpoint**, not the consumer `claude.ai` service. This distinction is important and has direct consequences for data handling, which are covered in Section 4. All API keys are managed server-side via GCP Secret Manager. Client-side code holds no API credentials.

### 2.3 How the LLM Is Used

The LLM performs two distinct functions within OIC:

**Questionnaire generation.** When a user selects an industry and region, the application assembles a context block from a curated local corpus (`app/corpus/`) — filtered by industry, region, and scenario tags — and sends it to the LLM along with a system prompt encoding the FAIR methodology and output format requirements. The LLM returns a structured JSON questionnaire with PERT three-point estimates for each FAIR component and inline citations pointing back to the source documents. This generation step uses the primary model (`claude-sonnet-4-6`).

**Chat assistance.** During and after the questionnaire, users can interact with a chat assistant that has access to their current assessment context: the industry and region selected, the questions answered, the threat scenario chosen, the control maturity indicated, and the FAIR estimates accumulated so far. This context-aware framing allows the assistant to give specific, relevant guidance rather than generic answers. The chat is also served by the primary model and uses the same prompt caching infrastructure described in Section 3.

---

## 3. Performance Controls: Prompt Caching

### 3.1 What It Is and Why It Matters

Prompt caching is a cost and latency optimization that instructs the Anthropic API to retain a processed copy of static prompt sections across multiple requests within a short window. Cached input tokens bill at approximately 10% of the standard input token rate, and cached sections bypass re-processing, reducing response latency by 15–30% for cache hits.

For OIC's usage pattern, this matters because both questionnaire generation and chat assistance use large, stable system prompts that would otherwise be re-processed with every API call. Without caching, each user interaction would bill the full system prompt at standard rates. With caching, the first call per session writes the cache; subsequent calls within the same session read from it at a fraction of the cost.

### 3.2 Implementation

Prompt caching is implemented in `app/config.py` via the `build_system()` helper:

```python
def build_system(system_prompt: str, cache: bool = True) -> list[dict]:
    """Return the `system` argument as a content-block list, with prompt caching
    enabled by default. Caching a static system prompt bills cached input at ~10%."""
    block = {"type": "text", "text": system_prompt}
    if cache and ENABLE_PROMPT_CACHE:
        block["cache_control"] = {"type": "ephemeral"}
    return [block]
```

The `ENABLE_PROMPT_CACHE` flag (controlled by the `OIC_PROMPT_CACHE` environment variable, defaulting to `"1"`) allows prompt caching to be disabled for debugging without code changes. The `cache_control: {type: "ephemeral"}` directive is the mechanism that activates caching on the Anthropic side; caches are retained for approximately 5 minutes and are scoped to the system prompt content and user session.

### 3.3 Cache Behavior and Expected Economics

For a medium-volume deployment (1,000 questionnaire generations and 5,000 chat interactions per month at a 75% cache hit rate), prompt caching is estimated to reduce API costs by roughly 15–20% compared to uncached requests. Cache hit rates improve as usage volume increases. The `OIC_PROMPT_CACHE=0` environment variable can be used to reproduce the uncached baseline for cost comparison.

---

## 4. Data Privacy: What Happens to Your Data

### 4.1 Training Data — The Correct Position

**API customer data is not used to train Anthropic's models. This protection is automatic and requires no opt-out.**

This is the correct, current position, and it reflects Anthropic's Commercial Terms as of the date of this document. Earlier internal documentation (specifically `EXECUTIVE_SUMMARY.md`) incorrectly stated that passing a `user_id` in API metadata via the `end-user-ids-2024-11-01` beta header "enables training opt-out." That framing was inaccurate. The `user_id` metadata mechanism serves a completely different purpose (covered in Section 5) and has no bearing on training data protection.

The training protection applies because OIC uses the **Anthropic API** rather than the consumer `claude.ai` service:

| Service | Training Data Handling |
|---------|----------------------|
| Anthropic API (OIC uses this) | Data **not** used for model training — default for all API customers |
| claude.ai consumer service | Data may be used for training unless user opts out |

Anthropic's Commercial Terms guarantee that API customer inputs and outputs are excluded from training corpora unless the customer explicitly opts into a data sharing program. No such opt-in is in place for OIC.

### 4.2 Vendor-Side Data Retention

While API data is not used for training, Anthropic's systems do process prompts and responses temporarily for abuse detection and safety monitoring. Anthropic's standard data retention window for this purpose is on the order of 30 days unless a Zero Data Retention (ZDR) agreement is in place. Enterprise agreements may offer ZDR or shorter retention windows; OIC does not currently have a ZDR agreement in place.

**Practical implication:** users should not submit raw credentials, private keys, or connection strings to the application. The risk model for any data submitted is not "will it train the model" (no) but "will it reside in Anthropic's abuse monitoring infrastructure temporarily" (yes, for up to ~30 days).

### 4.3 Authoritative Sources

The training data protection position can be verified independently:
- [Anthropic Commercial Terms](https://www.anthropic.com/legal/commercial-terms) — Section on data usage and training
- [Anthropic Trust Center](https://trust.anthropic.com) — Data processing commitments for API customers
- [Anthropic API Privacy Docs](https://docs.anthropic.com/en/api/privacy) — Training data policies and API vs. consumer differences

---

## 5. Safeguards: Abuse Prevention and User Tracking

### 5.1 Purpose

Anthropic requires API operators to implement safeguards that enable investigation and response to reported abuse. Specifically, Anthropic's [API Safeguards guidance](https://support.claude.com/en/articles/9199617-api-safeguards-tools) expects operators to maintain the ability to identify which end-user generated a given API call when Anthropic reports a policy violation. The `user_tracking.py` module in `app/` implements this requirement.

This system is for **abuse prevention and compliance** only. It does not affect whether data is used for training (which it isn't). It does not provide additional privacy protection beyond what the commercial terms already guarantee.

### 5.2 How It Works

The user tracking system follows a three-stage flow:

**Stage 1 — User ID assignment.** At application start, if no authenticated user system is integrated, the tracker generates a random session-scoped identifier in the format `eval-{code_generator}-{random_hex_12}`. In production mode, a stable identifier from the registration system (e.g., an internal user account ID) replaces the session-generated ID. In either case, the ID is not a name, email address, or any other personally identifiable information.

**Stage 2 — Hashing before transmission.** Before the user ID is passed to Anthropic's API, it is processed through SHA-256 (as recommended by Anthropic). The hashed identifier is what Anthropic sees; the original internal identifier is retained only in OIC's own logs. This ensures that if Anthropic's systems are ever queried by a third party, they cannot recover the operator's internal user vocabulary from the hashed values.

**Stage 3 — Minimal local logging.** Each API call generates a log record written to daily JSONL files at `./logs/api_calls/YYYY-MM-DD_api_calls.jsonl`. Each record contains:
- Timestamp
- Original user ID (internal use only)
- Hashed user ID (the value shared with Anthropic)
- API call type (`questionnaire_generation` or `chat_assist`)
- Model name
- Anthropic request ID
- Metadata (industry, region — no prompts or responses)

**What is explicitly not logged:** the contents of user prompts, the contents of API responses, personal account information, or any data that could reconstruct the conversation.

The complete flow:

```
User request
    ↓
Generate/retrieve user_id
    ↓
Hash with SHA-256 → hashed_id
    ↓
Pass hashed_id to Anthropic API metadata
    ↓
Log: timestamp | user_id | hashed_id | api_type | request_id
    ↓
Store in ./logs/api_calls/YYYY-MM-DD_api_calls.jsonl
```

### 5.3 Responding to an Abuse Report

When Anthropic contacts OIC about a policy violation, they provide the hashed user ID from their system. The investigation tool at `tools/investigate_abuse.py` can search the local log files for that hashed ID and return:

- All API calls from that identifier (timestamps, call types, metadata)
- The corresponding internal user ID
- Recommendations for next steps

Based on the severity of the violation, appropriate actions include: issuing a warning referencing [Anthropic's Usage Policy](https://www.anthropic.com/legal/aup), temporarily suspending access, or permanently banning the user.

### 5.4 Current Mode: Evaluation vs. Production

The tracker is currently configured in **evaluation mode** (`session_based=True`). Each application start generates a fresh random user ID. This is appropriate for pre-launch testing — it verifies that the tracking pipeline is functional and that the hashed IDs appear correctly in Anthropic's metadata, without requiring a real user registration system.

When OIC launches with a registration system, the integration change is:

```python
# Evaluation mode (current):
tracker = get_tracker(session_based=True, code_generator="wsa")

# Production mode (future):
tracker = get_tracker(session_based=False, code_generator="wsa")
user_id = tracker.get_user_id(provided_user_id=current_user.id)
```

User IDs in production should be stable internal identifiers (e.g., `user-12345`, `uuid-abc-def`) rather than email addresses or names.

---

## 6. Operational Data Exposure: What to Know Before Submitting Data

The vendor-side training question is often the first question asked and is also the lowest-risk dimension of data handling. The more significant risks are operational. The following table summarizes the exposure profile of different data types within OIC's architecture.

### 6.1 Content Risk Classification

| Data Type | Risk Level | Guidance |
|-----------|-----------|---------|
| Active credentials, API keys, connection strings, private keys | **Unacceptable** | Never submit. If accidentally submitted, rotate immediately. |
| Unique proprietary source code, schemas, internal algorithms | **High** | Exercise caution. High-entropy technical artifacts are materially sensitive if exposed through any log or third-party connector. |
| Named internal projects, staff names, vendor names, dates, internal acronyms | **Medium–High** | Acceptable if you are comfortable with this data residing in secure internal logs and Anthropic's temporary abuse monitoring cache. |
| Generic risk assessment prose, industry-level descriptions, control maturity selections | **Low** | This is the intended use case. Safe for processing. |
| Redacted, templated, or synthetic examples | **Very Low** | Safe. |

### 6.2 Operational Exposure Points

Beyond the Anthropic API, data traverses several systems within OIC's architecture. Users and security reviewers should be aware of the following:

**Application logs and traces.** The application logs API call metadata (not prompt contents) to JSONL files. Standard application logs may capture error context that includes partial request data. Log files should be treated as internal sensitive data and protected accordingly.

**Local corpus and context storage.** The questionnaire context (industry, region, answers, FAIR estimates) is persisted in Flask session storage and optionally in `context_storage.py` (SQLite-backed). These stores hold the accumulated assessment state for a session. They are internal stores, not transmitted to Anthropic, but they are durable and must be considered when scoping data retention policies.

**AI-generated outputs.** Summaries, rationale text, and estimates produced by the LLM may incorporate internal facts from the assessment. When these outputs are shared externally — in reports, emails, tickets, or presentations — they carry the same sensitivity classification as the input data from which they were derived. Standard Data Loss Prevention (DLP) practices apply to outputs.

**Backup and SIEM pipelines.** If application logs or the SQLite database are captured in backup or SIEM systems, those archives may retain assessment data beyond the lifecycle of the original application instance. Ensure backup retention policies align with the sensitivity of the data being processed.

**Third-party tool integrations.** If external tool calls or remote connectors (such as MCP servers or web search integrations) are active, data sent to those third parties is subject to their respective data handling policies. The current Google Custom Search integration is triggered only when the local corpus cannot satisfy a freshness requirement; the search queries contain industry and threat-scenario context, not full prompt text.

---

## 7. Architecture Summary: AI Data Flow

The following describes the complete data flow for a questionnaire generation request, from user action to API response:

1. User selects industry and region via the web UI.
2. `app/main.py` receives the `POST /generate` request and initializes or clears the assessment context.
3. `app/user_tracking.py` retrieves or generates the session user ID and computes its SHA-256 hash.
4. `app/ai_question_generator.py` calls `app/corpus/retrieve.py` to filter the local markdown corpus by the selected facets and assemble a context slice within a token budget.
5. The generator constructs the API request: a cached system prompt block (via `config.build_system()`), the corpus slice, and the dynamic user instruction requesting structured JSON output.
6. The API call is dispatched to `claude-sonnet-4-6` with the hashed user ID in the request metadata and the prompt caching headers.
7. The response is validated (JSON schema check; up to 3 retries with tightened parameters if validation fails).
8. The API call is logged to `./logs/api_calls/` with metadata only (no prompt or response content).
9. The validated questionnaire is stored in the session and rendered to the user.

The chat assistant path is structurally the same: context assembly from session state, cached system prompt, API call with hashed user ID, response, log record.

---

## 8. Security Best Practices for Operators

The following practices are recommended for anyone operating or evaluating OIC in a production context:

**API key management.** API keys must reside only in GCP Secret Manager (or equivalent secrets management). They must never appear in environment files committed to version control, application logs, or client-side code. Rotate keys on any suspected exposure.

**Log access control.** The `./logs/api_calls/` directory contains internal user IDs (pre-hash). Access to this directory should be restricted to operations personnel who have a legitimate need to conduct abuse investigations. Treat these files as sensitive internal data.

**User ID hygiene.** In production mode, user IDs passed to the tracker must be stable, opaque, internal identifiers — not email addresses, names, or any other PII. The hashing step protects identity only when the pre-hash value is not itself a PII identifier.

**Output handling.** AI-generated risk assessments, rationale documents, and chat transcripts derived from organizational data should be classified at the same sensitivity level as the source data. Apply normal document handling and sharing controls before distributing outputs externally.

**Dependency maintenance.** The Anthropic Python SDK, Flask, and all other dependencies should be kept current. Prompt caching requires Anthropic SDK >= 0.27.0. The application's model tier configuration in `config.py` should be reviewed whenever Anthropic releases a new model generation to ensure the selected models remain supported.

**Consumer path prohibition.** OIC data must never be processed through consumer interfaces such as `claude.ai`, `ChatGPT`, or Gemini's consumer tier. These services operate under different data handling terms and may use inputs for model training unless users explicitly opt out. The enterprise API pathway used by OIC is the only sanctioned path for organizational data.

---

## 9. Compliance Summary

| Requirement | Status | Mechanism |
|-------------|--------|-----------|
| Training data protection | Satisfied by default | Anthropic Commercial Terms cover all API customers |
| Abuse reporting capability | Implemented | `user_tracking.py` — hashed IDs + JSONL logs |
| Anthropic safeguards compliance | Implemented | End-user ID in API metadata per Anthropic guidance |
| No PII in vendor metadata | Implemented | SHA-256 hashing before transmission |
| Minimal logging (no prompts/responses) | Implemented | Log schema excludes content fields |
| API key security | Implemented | GCP Secret Manager; no client-side keys |
| Prompt caching for cost control | Implemented | `config.build_system()` with `cache_control` |
| Consumer path prohibition | Policy | No code paths route to consumer interfaces |

---

## 10. Document History and Superseded Files

This document consolidates and supersedes the following files, which have been moved to `documentation/historical/`:

| Superseded File | Original Location | Primary Topic |
|----------------|-------------------|---------------|
| `EXECUTIVE_SUMMARY.md` | `documentation/` | Prompt caching and training opt-out (contained inaccurate training opt-out framing) |
| `SAFEGUARDS_README.md` | `documentation/` | Abuse prevention architecture |
| `SAFEGUARDS_README.md` | project root | Duplicate of above |
| `AI_Safeguards_DataExposure_README.md` | project root | Data exposure risk classification |
| `TRAINING_CLARIFICATION_INDEX.md` | `documentation/` | Index of training data clarification documents |
| `TRAINING_DATA_CONFIRMATION.md` | `documentation/` | Confirmation of training data protection status |

The key correction made in this consolidated document relative to the superseded files is:

> The `EXECUTIVE_SUMMARY.md` claimed that passing `metadata={"user_id": ...}` with the `end-user-ids-2024-11-01` beta header "enables training opt-out." This was incorrect. API data is excluded from Anthropic's training pipeline automatically under the Commercial Terms. The `user_id` metadata mechanism is for abuse investigation and compliance only. The `TRAINING_CLARIFICATION_INDEX.md` and `TRAINING_DATA_CONFIRMATION.md` had already corrected this misunderstanding, but the contradiction across documents created ongoing confusion. This document reflects the correct, consistent position throughout.
