# OpenImpactCascade — User Guide

| Field | Value |
|-------|-------|
| **Version** | Beta |
| **Date** | 2026-06-13 |
| **Product** | OpenImpactCascade (OIC) |

---

## Contents

1. [What Is OpenImpactCascade?](#1-what-is-openimpactcascade)
2. [Use Cases](#2-use-cases)
3. [Getting Started: The Application Interface](#3-getting-started-the-application-interface)
4. [Path A — Industry Risk Assessment](#4-path-a--industry-risk-assessment)
5. [Path B — Custom Scenario Assessment](#5-path-b--custom-scenario-assessment)
6. [Working Through the Questionnaire](#6-working-through-the-questionnaire)
7. [Understanding Your Results](#7-understanding-your-results)
8. [The Chat Assistant](#8-the-chat-assistant)
9. [Notable Features and Capabilities](#9-notable-features-and-capabilities)
10. [Advanced Options](#10-advanced-options)
11. [Deployment](#11-deployment)
12. [A Note on This Beta](#12-a-note-on-this-beta)

---

## 1. What Is OpenImpactCascade?

OpenImpactCascade (OIC) is a cyber risk quantification tool for small and medium businesses. It generates structured risk assessments using the **FAIR methodology** (Factor Analysis of Information Risk) — producing actual probability distributions and dollar-range estimates rather than traffic-light scores or narrative summaries.

The tool is designed to help organizations move from "we think ransomware is a high risk" to "for our industry and region, a ransomware event has a 34% annual probability and an expected loss of $85,000, with a 90th-percentile scenario reaching $310,000." That level of specificity is what justifies prioritization decisions, budget allocations, and conversations with leadership.

OIC is not a compliance checklist, a maturity assessment, or a substitute for professional security or legal advice. It is an analytical aid — a structured way to turn imprecise knowledge about threats and controls into defensible numbers.

---

## 2. Use Cases

### 2.1 The CIO Triage Workshop: Ten Risks in Four Hours

A working group — security lead, IT, one or two business owners — needs to rank a shortlist of risks and decide which ones deserve attention this quarter. The problem is not that the risks are unknown; it is that there is no common language for comparing them. "Ransomware feels more likely" and "a supply-chain compromise would be worse" are both opinions without a shared unit.

OIC structures that conversation. Each risk scenario produces a probability estimate, a loss magnitude range, and a calculated expected annual loss. Ten scenarios can be run in a morning and ranked side by side. The triage question — *which of these should we actually do something about first?* — becomes answerable from evidence rather than gut feel.

**How to use it for this purpose:**
- Run the Industry Risk Assessment (Path A) for each of the top scenarios your group has identified.
- Use the same industry, region, and organization size for every run so comparisons are apples-to-apples.
- Bring the results page to the room. The expected annual loss figures and percentile distributions are the common currency.

### 2.2 Training, Tabletop Exercises, and Teaching the Risk Process

Risk analysis is a skill. Most people who should be doing it — security managers, IT leads, risk officers at SMBs — have not had structured exposure to FAIR or probabilistic thinking. Reading about it is one thing; working through a real scenario with numbers is another.

OIC works well as a tabletop facilitation tool. Run a scenario live in a workshop: have participants make the choices (threat frequency, control maturity, loss magnitude), watch the simulation output change as they do, and discuss whether the numbers match their intuition. When they don't, that's the productive moment — it reveals assumptions worth examining.

**How to use it for this purpose:**
- Use Path A to generate a sector-appropriate questionnaire with real-world grounding.
- Present the questionnaire questions one at a time to the group and discuss each choice before selecting.
- After completing the questionnaire, use the results page to discuss what the distributions mean — particularly the gap between expected loss and the 90th-percentile scenario.
- The chat assistant can answer methodology questions ("why is this question asking about frequency in events per year?") in real time during the session.

### 2.3 Evaluating Control Effectiveness and Investment ROI

Organizations frequently face the question: *if we add this control, is it worth it?* EDR on endpoints, MFA on all accounts, offline backup — each costs money. What does each one actually do to the risk exposure?

OIC lets you run the same scenario twice with different control selections and compare the results. The difference in expected annual loss is the risk reduction purchased by the control investment. Divide the annual control cost by that reduction and you have a simple ROI frame that finance and leadership can evaluate.

**How to use it for this purpose:**
- Run Path A for your chosen scenario, selecting your current control tier.
- Note the expected annual loss from the results page.
- Run the same scenario again with the improved control tier you're considering.
- Compare the two expected annual loss figures. The difference is the annual risk reduction.
- Use the layered controls toggle during the questionnaire to adjust for secondary controls already in place.

### 2.4 Custom Scenario Development with LLM Grounding

The standard questionnaire paths surface scenarios that are common in your industry and region. But organizations sometimes need to assess a specific concern: a particular threat they have been briefed on, a scenario surfaced by a recent incident at a peer organization, or a custom risk posed by their specific environment.

Path B (Custom Scenario) allows you to describe your risk concern in plain language. The LLM takes that description and, using a curated corpus of industry and regional threat data, generates a structured questionnaire tuned to that specific scenario. You do not need to pre-define the FAIR components yourself — the system does that translation from your narrative description.

Critically, the LLM is grounded in data relevant to your industry, region, and organization size. This removes the need to prime the model with context in your own words, which often produces inconsistent or unfocused results. The grounding happens at the system level.

**How to use it for this purpose:**
- Choose Path B from the home screen.
- Select your industry, region, and organization size.
- Describe the specific risk scenario in the text field in plain language. Be as specific as you can about what you are worried about — the more concrete the description, the more targeted the questionnaire.
- Review the scenario options the system proposes and select the one that best matches your intent.
- The resulting questionnaire is purpose-built for your described scenario.

### 2.5 Current Threat-Informed Starting Position

Risk assessments that rely entirely on historical data or static frameworks can quickly become stale. A threat that was low-probability two years ago may now be the dominant pattern in your sector. OIC supplements its curated internal corpus with targeted web searches for current threat intelligence when the corpus signals a gap — high-freshness advisories, recent incident data, sector-specific current reporting.

This blending happens automatically. When the system detects that the current corpus does not have recent-enough data for your industry and region combination, it performs a bounded, focused web search and incorporates the results into the questionnaire grounding. The sources used are cited inline so you can verify them.

---

## 3. Getting Started: The Application Interface

### 3.1 Logging In

OIC uses simple username/password authentication. Enter the credentials provided by your administrator or deployment owner. If you are running the application yourself and have not set credentials, check the deployment documentation for the default configuration.

After logging in you will be taken to the **home screen**.

### 3.2 The Home Screen

The home screen presents two starting paths:

- **Assess Industry Risks** — generates a questionnaire based on your industry, region, and optionally a cascade attack archetype. This is the primary path for most use cases.
- **Assess a Specific Risk** — allows you to describe a particular concern in your own words and generates a targeted questionnaire from that description.

Each card on the home screen includes a short description of what it does and when to use it. The home screen also links to the learning resources available in the application (MITRE ATT&CK overview, FAIR methodology, cascade archetypes, layered controls).

---

## 4. Path A — Industry Risk Assessment

### Step 1: Select Your Context

On the **Generate Assessment** form you will be asked for:

**Industry** *(required)* — Select the sector your organization operates in. The questionnaire topics, threat scenarios, and reference data used to calibrate estimates are all specific to this selection. If your organization spans multiple sectors, choose the one where the risk you want to assess is most relevant.

**Region** *(required)* — Select the country or region where your organization primarily operates. Regional threat intelligence, regulatory context, and incident frequency data differ meaningfully between regions.

**Organization Size** *(optional but recommended)* — Describe your organization's size in terms of employees, revenue, or both. This is a free-text field; write something like "250 employees, $40M revenue" or "500 staff, healthcare operator." This information helps calibrate loss magnitude estimates — a breach costs a 50-person firm and a 500-person firm very differently.

### Step 2: Select a Cascade Archetype (if enabled)

If the cascade archetype feature is active, you will see an additional step: a selection of attack pattern cards to ground the assessment. Each card represents a credible, real-world-anchored attack scenario (e.g., ransomware delivered via phishing, exposed orchestrator to resource hijack).

Selecting an archetype grounds the questionnaire on that specific attack pattern. The questions will trace the steps of that cascade and evaluate your exposure at each link in the chain.

If no archetype matches what you want to assess, or if you want a broad industry survey rather than a specific attack pattern, select **"Let AI suggest scenarios"** or leave the selection as default — the system will generate based on industry/region data without archetype grounding.

See [Section 9.1](#91-cascade-archetypes) for a full explanation of what cascade archetypes are and why they are structured the way they are.

### Step 3: Generate

Click **Generate Questionnaire**. The system will:
1. Filter the curated corpus for your industry and region
2. Check whether current threat intelligence is needed and run a targeted web search if so
3. Call the LLM to construct a FAIR-structured questionnaire with inline citations
4. Validate the output and redirect you to the questionnaire page

This typically takes 95–140 seconds. The progress indicator lists the steps being done but is not interactively being updated. Performance is primarily dependent on the LLM API response time.

---

## 5. Path B — Custom Scenario Assessment

### Step 1: Set Your Context

As with Path A, select your **industry**, **region**, and optionally **organization size**.

### Step 2: Describe Your Scenario

In the text field, describe the specific risk you want to assess in plain language. Examples:

- *"We use a third-party payroll provider and I'm worried about a data breach affecting employee records."*
- *"Our manufacturing floor uses legacy SCADA systems with no network segmentation and I want to understand the ransomware exposure."*
- *"We recently moved to a cloud-only environment and I want to assess the risk of credential theft leading to data exfiltration."*

You do not need to frame this as a FAIR analysis or use technical vocabulary. Write it the way you would explain the concern to a colleague. The more concrete and specific you are, the more targeted the questionnaire will be.

### Step 3: Review Scenario Options

After submitting your description, the system will return two or three structured scenario options derived from your narrative. Each option translates your concern into a specific FAIR-framed scenario with a defined threat actor, asset target, and loss type.

Review the options and select the one that best matches what you were describing. If none of them quite captures it, the closest one is still a better starting point than the generic path.

### Step 4: Generate

Click **Generate Questionnaire**. The process from here is the same as Path A.

---

## 6. Working Through the Questionnaire

The questionnaire is structured to elicit the FAIR inputs needed for the Monte Carlo simulation. It proceeds through a defined sequence of question types.

### Question Types You Will Encounter

**Threat scenario selection** — Confirms or refines the type of attack being analyzed. For Path A this is drawn from your industry/region combination; for Path B it is derived from your narrative description.

**Asset target selection** — Identifies the primary asset at risk (patient records, financial data, operational systems, etc.). This affects the loss magnitude calibration.

**Threat Event Frequency (TEF)** — How often does this type of attack get *attempted* against organizations like yours in a year? You will be presented with a three-point estimate field (minimum, most likely, maximum). The help text and chat assistant can provide reference data if you are unsure.

**Vulnerability / Control Maturity** — Given an attempt, how likely is it to succeed? This is driven by your control selections. You will choose from a set of control tier descriptions; each tier carries a calibrated vulnerability percentage derived from the FAIR methodology.

**Layered Controls Toggle** — After selecting a control tier, a toggle will appear asking whether you have secondary controls in place. If you do — network segmentation, offline backups, EDR/XDR, a tested incident response plan — checking this box applies a 25% reduction to the vulnerability estimate. See the [Layered Controls](../app/templates/about_layered_controls.html) page for the mathematical basis.

**Loss Magnitude** — What is the financial impact of a successful event? You will enter three-point estimates for primary costs (direct response, notification, recovery) and secondary costs (regulatory, reputational, legal). The help text provides sector-specific reference ranges.

### Using the "Why Are You Asking This?" Rationale

Each question includes a rationale section explaining which FAIR component it addresses and why that component matters for the calculation. Expanding the rationale is particularly useful in a workshop or training context — it teaches the methodology as you work through it.

### Navigating Between Questions

Use the Next and Back buttons to move through the questionnaire. Your answers are saved to session state as you progress. If you need to revisit an earlier answer, use Back — your subsequent answers will remain intact unless you change a selection that logically depends on the one you are revising.

---

## 7. Understanding Your Results

When you complete the questionnaire, the application runs a Monte Carlo simulation (10,000 iterations) and presents the results page.

### Key Metrics

**Expected Annual Loss (EAL)** — The mean of the simulated loss distribution. This is the single number most useful for financial planning: on average, what does this risk cost per year?

**Annualized Loss Expectancy (ALE)** — Closely related to EAL; the product of the Loss Event Frequency and the expected Loss Magnitude. Use this as a baseline for comparing controls.

**90th Percentile Loss** — The loss amount exceeded in only 10% of simulated scenarios. This is the "bad year" figure — what you should be prepared for if things go worse than usual. It is typically 3–8× the expected annual loss for cyber scenarios, reflecting the heavy tail of cyber risk distributions.

**Loss Distribution Chart** — A visualization of all 10,000 simulations. Most outcomes cluster toward the left (lower losses); the long right tail represents the catastrophic but possible scenarios. The shape of this distribution matters: a wide distribution means high uncertainty; a narrow one means the risk is relatively predictable.

### FAIR Component Summary

The results page shows the input parameters that drove the simulation:
- TEF (Threat Event Frequency): attempted events per year
- Vulnerability: probability of success given an attempt
- LEF (Loss Event Frequency): successful events per year (TEF × Vulnerability)
- Loss Magnitude: financial impact per event

Reviewing these components helps you identify which variable is driving the result and where better data would change the answer most.

### Revisiting the Assessment

The results page includes a chat interface for follow-up questions and a link back to the questionnaire if you want to adjust inputs and re-run. Running the same scenario with different control tiers is the most common follow-on activity — see [Use Case 2.3](#23-evaluating-control-effectiveness-and-investment-roi).

---

## 8. The Chat Assistant

A chat assistant is available throughout the questionnaire and on the results page. It is context-aware: it knows your industry, region, organization size, the questions you have answered, the threat scenario selected, the control tier chosen, and the FAIR estimates accumulated so far.

### What It Is Good For

- **Calibrating estimates** — "How often do ransomware attacks get attempted against healthcare organizations in Canada?" The assistant can provide reference ranges grounded in the same data used to generate the questionnaire.
- **Understanding the methodology** — "What is the difference between TEF and LEF?" "Why does this tool use a lognormal distribution?" The assistant can explain the FAIR methodology, the probability math, and the design decisions behind the tool.
- **Working through specific assumptions** — "Our backups are cloud-based, not offline. Does that change the vulnerability estimate?" The assistant can reason about how your specific situation affects the inputs.
- **Interpreting results** — "What does a 90th-percentile loss of $310,000 mean for our cyber insurance coverage?" The assistant can help you draw practical conclusions from the numbers.

### What It Is Not

The chat assistant is not a replacement for a professional risk assessment, security advisory, legal counsel, or financial planning advice. It operates within the scope of the assessment being conducted. For decisions with significant financial or legal consequences, use the outputs as one input among several.

### Using the Quick Help Button

The **"?"** button on each questionnaire question opens a focused chat prompt pre-loaded with the context of that specific question. This is the fastest way to get calibration help without typing a full explanation of where you are in the assessment.

---

## 9. Notable Features and Capabilities

### 9.1 Cascade Archetypes

The cascade archetype feature is one of OIC's most distinctive capabilities. Rather than generic threat scenarios, each archetype card represents a **real-world attack pattern** drawn from a published MITRE Attack Flow — a forensically documented intrusion. The card is not a copy of that incident; it is a compression of it to the tactical level that survives across environments.

This distinction matters. The Black Basta ransomware card, for example, is not "what Black Basta did in a 2023 attack." It is "the pattern — phishing to credential access, lateral movement to backup deletion, ransomware deployment — that Black Basta (and actors using the same methods) execute, abstracted to the level at which you can ask whether *your* environment has the conditions for it to succeed."

**Why this is useful:** A triage room cannot meaningfully evaluate ten 38-node forensic graphs in four hours. Ten 5-7 link cascade cards, each with a probability estimate and a loss magnitude range, are a different proposition. The cascade archetype path makes that kind of structured, comparative triage feasible.

**The Pyramid of Pain connection:** The cards are deliberately written at the top of David Bianco's Pyramid of Pain — tactics and goals rather than tools and indicators. Indicators (IP addresses, malware hashes, domain names) are easy for attackers to change. Tactics and goals are much stickier. Grounding at the tactical level means the card stays accurate even as the threat actor updates their toolset, which makes it more durable for triage than IOC-based alternatives.

Each archetype card includes:
- A named cascade: the 5–7 decisive steps from initial access to impact
- A "succeeds when" gate at each step: the condition the defender must close to break the chain
- An anchor: the real incident that proves the pattern is achievable in the wild
- An odds-versus-size frame: how likely the cascade is to complete and what it costs when it does

### 9.2 Threat-Informed Web Search

When the curated corpus does not contain recent-enough data for your industry and region, the system performs a focused web search to supplement it. This is triggered automatically by internal gap-detection logic — it is not a general internet search. The queries are targeted at current threat advisories, recent incident data, and sector-specific reports.

The result is that questionnaires reflect the current threat landscape rather than the state of the corpus at last update. Sources retrieved by web search are cited inline in the questionnaire rationale so you can verify the reference.

### 9.3 FAIR Quantification and Monte Carlo Simulation

The simulation engine is local — it runs on the server without any additional API calls — and uses standard probabilistic methods:
- **PERT distributions** for three-point input elicitation (minimum, most likely, maximum)
- **Lognormal distributions** for loss magnitude (appropriate for cyber risk, which has heavy-tailed, asymmetric financial impacts)
- **10,000 Monte Carlo iterations** per run, producing stable percentile estimates

This is the same methodological foundation used in enterprise cyber risk quantification. The difference is that OIC makes it accessible without requiring users to understand the mathematics — the questionnaire does the translation from qualitative inputs to distribution parameters.

### 9.4 Layered Controls Adjustment

The control tier selections in the questionnaire assign a single vulnerability estimate based on overall control maturity. Organizations that have multiple independent control layers in place (endpoint protection, email filtering, network segmentation, tested backups, incident response capability) have an aggregate vulnerability that is lower than any single control tier implies — because an attack must defeat all of them, not just one.

The layered controls toggle applies a 25% reduction to account for this effect. The underlying math — multiplying independent failure rates — is explained in the [Layered Controls](../app/templates/about_layered_controls.html) explanation page linked from the toggle.

This is a simplified heuristic. It is useful for quick calibration. For scenarios where per-control precision matters, the explanation page includes a feedback link to share that need with the development team.

---

## 10. Advanced Options

### 10.1 Adding Custom Cascade Archetypes

The default archetype library ships with a set of pre-built cards covering common SMB threat patterns. Organizations that have access to specific incident data, red team reports, or internal threat intelligence can add custom cards to the library.

Custom cards follow the same schema as the built-in ones: a 5–7 link cascade, "succeeds when" gates, an anchor, and a loss-shape tag. The design methodology is documented in `documentation/project/OIC-DESIGN-2026-002-cascade-compression-revB.md`. Cards are stored as markdown files with YAML frontmatter and picked up automatically when the application starts.

Adding a custom card makes it available in the archetype selector on the generation form. This is the primary way to incorporate an organization's own threat intelligence into the structured quantification workflow.

### 10.2 Augmenting the Curated Corpus

The corpus of authoritative reference documents (NIST frameworks, CISA advisories, CCCS publications, Verizon DBIR data, IBM Cost of a Data Breach data) is the grounding layer for questionnaire generation. Administrators can add new corpus documents in markdown format with standardized YAML frontmatter — industry tags, region tags, freshness sensitivity, quality rating. New documents are indexed at startup and become part of the retrieval pool.

This is how organizations with proprietary sector analysis, internal red team findings, or specialized regulatory guidance can improve the grounding quality for their specific context.

### 10.3 Changing the LLM Model

The model used for questionnaire generation and chat assistance is configured in `app/config.py` via environment variables:

| Variable | Default | Purpose |
|----------|---------|---------|
| `OIC_MODEL` | `claude-sonnet-4-6` | Primary model (questionnaire generation, chat) |
| `OIC_MODEL_FAST` | `claude-haiku-4-5` | Fast/cheap subtasks |
| `OIC_MODEL_DEEP` | `claude-opus-4-8` | Deep analysis (future use) |

Any model supported by the Anthropic API can be substituted by setting these environment variables before startup. Organizations wishing to use a different provider (OpenAI, Google Gemini, local models via compatible APIs) would need to modify the API call layer in `app/ai_question_generator.py` — the architecture is designed with provider portability in mind, and the model identifiers are not hardcoded outside of `config.py`.

### 10.4 Threat Intelligence Integration

The web search component uses Google Custom Search. Organizations that want to point the web search at a specific curated set of sources — an internal threat intelligence platform, a licensed feed, or a restricted set of authoritative sites — can configure the Custom Search Engine scope via the GCP project settings. This allows the "current threat intelligence" layer to draw from trusted internal sources rather than the open web.

---

## 11. Deployment

OIC deploys on **Google Cloud Platform (GCP) Cloud Run** out of the box. The application is containerized with Docker and designed to run in a managed serverless environment. The default deployment handles scaling, certificate management, and secrets (via GCP Secret Manager) automatically.

The application is portable. It can run on any platform that supports:
- Docker
- Python 3.11+
- Outbound internet access (for web search and Anthropic API calls)
- An environment variable mechanism for secrets

This includes other cloud providers (AWS, Azure), on-premises infrastructure, or a local development environment. Running locally requires the Anthropic API key and optionally a Google Custom Search API key to be set as environment variables. All other functionality (the simulation engine, the local corpus, the FAIR quantification) works without network access.

For detailed deployment instructions, infrastructure configuration, and environment variable reference, see the deployment guide in the repository.

---

## 12. A Note on This Beta

OpenImpactCascade is a beta product under active development. You may encounter rough edges, incomplete features, or results that feel counterintuitive. That is expected at this stage, and your feedback is the most direct input to improving it.

**Using OIC appropriately means understanding its limitations:**

- Results are probability estimates, not predictions. A 34% annual probability of a ransomware event does not mean it will happen roughly every three years; it means that in any given year, the probability is 34%. Low-probability catastrophic outcomes are real possibilities even when the expected annual loss is modest.
- The estimates are only as good as the inputs. If you select a threat frequency that is significantly off for your context, the output will reflect that. Use the chat assistant to calibrate your inputs against reference data before accepting the defaults.
- The model's grounding corpus has coverage gaps. Some industries, regions, and scenario types have more reference data than others. When the system flags that it performed a web search to fill a gap, that is honest reporting of a limitation, not a failure — it means the corpus did not have what it needed and the system found an alternative.
- This tool is an aid to analysis, not a substitute for it. The outputs should inform decisions, not make them. For decisions with material legal, financial, or regulatory consequences, consult qualified professionals.

**We appreciate your patience.** OIC is being built incrementally, with each release shaped by feedback from people using it for real work. If a feature does not behave as you would expect, or if you have a use case that the current tool does not address well, the feedback link at `info@impactcascade.ca` goes directly to the people building it.

---

*OpenImpactCascade is licensed under the Apache License, Version 2.0.*
*© 2026 FirstFire Productions — [https://impactcascade.ca](https://impactcascade.ca)*
