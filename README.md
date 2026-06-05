# OpenImpactCascade - AI-Powered Risk Assessment Platform

**Version:** v3.0.0 ( Filetree Context, enhanced LEF Decomposition with TEF × Vulnerability scoring control credits)  
**Port:** 8080  
**Python:** 3.8 - 3.11 (3.11 recommended)

AI-powered risk assessment questionnaire generator with enhanced FAIR methodology (TEF/LEF decomposition), MITRE ATT&CK integration, Markdown+Frontmatter knowledge base retrieval, intelligent web search, and comprehensive safety safeguards. Built for freemium SaaS deployment.

---

## 🔧 Technology Stack

- **Backend:** Flask 3.0+, Python 3.11
- **AI/ML:** Anthropic Claude Sonnet 4.6 (via API)
- **Knowledge Base:** File-based Markdown + Frontmatter Corpus with Cached Injection
- **Web Search:** Google Custom Search (Gap-fill)
- **Simulation:** NumPy, SciPy (Monte Carlo with lognormal distributions)
- **Deployment:** Gunicorn, Docker, GCP Cloud Run, Cloud SQL

---

## 🎯 Overview

OpenImpactCascade is a Flask-based web application that generates custom cybersecurity risk assessments tailored to specific industries and regions. It combines:

- **AI-generated questionnaires** based on verified threat intelligence
- **FAIR methodology** for quantitative risk analysis
- **Monte Carlo simulation** for risk distribution modeling
- **Real-time chat assistance** to guide users through assessments
- **API safeguards** for abuse prevention and compliance

---

## ✨ Key Features

### 🤖 AI-Generated Questionnaires
- Custom risk assessments based on industry and region
- Grounded in authoritative sources (MITRE ATT&CK, CISA, Verizon DBIR)
- Real-time web search for current threat intelligence
- Source verification before citation
- Transparent about data limitations

### 🧬 Cascade-Archetype Grounding (Path A) — flag-gated
Optional grounded-analysis mode for the **AI-Generated Questionnaire**. After choosing
industry and region (and org size), the presenter can select a **curated cascade archetype**
— a compressed, authoritative attack cascade — to anchor the assessment.

- **Selection step:** a dropdown on the generate form lists the available archetypes plus
  *"Let AI suggest threats"* (the existing web-only fallback, unchanged).
- **Full cascade view:** a *"View full cascade ↗"* link opens the complete card as a rendered
  HTML page (`/archetype/view/<id>`) in a **new tab**, with a Back button — so the in-progress
  selection is never lost.
- **Grounding pipeline (improves question quality):** when an archetype is selected, the
  generator assembles, **before the LLM is called**:
  1. the **cascade card** (authoritative, verbatim — the foundational block),
  2. a **cascade-grounded web search** — industry + region + card facts (`dbir_pattern`,
     anchor incident, regulatory drivers) form the query set, so Google Custom Search enriches
     *frequency/magnitude* framing rather than re-discovering the threat, and
  3. the **system context**.
  Precedence is enforced: web/industry context informs how often / how costly, and must **not**
  alter the cascade's steps or chokepoints.
- **Metadata:** generated questionnaires record `grounding_mode` (`cascade` | `web_only`),
  `selected_archetype_id`, and `selected_card_ids`.
- **Cards location:** `app/generated/cascade_archetypes/oic-ca-*.md`. Only this folder is copied
  into the Docker image; the detailed source flows remain in the codebase for now.
- **Default OFF.** With the flags unset the application behaves exactly as before (web-only
  generation). See **Configuration** below.

### 🎯 Custom Risk Scenario (Path B) — directional
The "Custom Risk Scenario Assessment" card is the **quick, directional** option: define any
threat scenario in your own words and get a fast questionnaire focused on it. Best when no
grounded archetype fits; for credible structured analysis, use Path A with a cascade archetype.

### 📊 Enhanced FAIR Risk Analysis
- **TEF × Vulnerability Decomposition**: Separates attack attempts from success probability
- **Threat Event Frequency (TEF)**: How often attackers attempt attacks
- **Vulnerability Assessment**: Control effectiveness mapped to attack success rates
- **Loss Event Frequency (LEF)**: Auto-calculated from TEF × Vulnerability
- **Loss Magnitude (LM)**: Financial impact per successful breach
- **Three-point PERT estimates** (min, most likely, max) for all components
- **Monte Carlo simulation** (10,000+ iterations) with PERT and lognormal distributions
- **Risk distribution visualization** with percentile reporting
- **Control ROI Analysis**: See how security investments reduce risk

### 💬 Interactive Chat Assistant
- Context-aware help for each question
- Industry and region-specific guidance
- Practical examples and explanations
- Conversational interface using Claude Sonnet 4
- Remembers conversation history

### 🛡️ Safety & Compliance
- User tracking with cryptographic hashing
- API call logging for abuse investigation
- Anthropic safeguards compliance
- Privacy-preserving minimal logging
- See **[SAFEGUARDS_README.md](SAFEGUARDS_README.md)** for details

### 🎨 Responsive Design
- Desktop: Persistent chat sidebar
- Mobile: Collapsible assistant with floating button
- Professional risk assessment interface
- Real-time validation and feedback

---

## 📁 Project Structure

```
app/
├── main.py                             # Main Flask application with LEF decomposition
├── ai_question_generator.py            # AI generator with Corpus grounding, web search, and TEF/Vulnerability
├── simulation.py                       # Monte Carlo simulation with PERT and lognormal distributions
├── user_tracking.py                    # User tracking & API safeguards
├── persistence.py                      # Cloud SQL access (replaces SQLite context_storage)
├── corpus/                             # Markdown + Frontmatter Knowledge Base package
│   ├── retrieve.py                     # Deterministic slice retrieval from index
│   ├── build_index.py                  # Scans and validates corpus, builds _index.json
│   └── schema.py                       # Frontmatter schema, vocabularies, and governance
├── cards/                              # Cascade-archetype card library (flag-gated)
│   └── library.py                      # Card loader (frontmatter+body parse, archetypes_for)
├── templates/
│   ├── home.html                       # Landing page
│   ├── generate.html                   # Standard questionnaire form (+ archetype dropdown)
│   ├── archetype_view.html             # Full cascade archetype rendered as HTML
│   ├── generate_custom.html            # Custom scenario generator
│   ├── questionnaire_chat_rationale.html  # Interactive questionnaire with chat
│   ├── results.html                    # Analysis results with chat sidebar
│   ├── error.html                      # Error page
│   ├── about_fair.html                 # FAIR methodology documentation
│   ├── about_mitre.html                # MITRE ATT&CK integration info
│   └── about_probability_weighting.html # Probability weighting explanation
├── static/                             # Static assets (CSS, JS, images)
├── generated/                          # Generated questionnaires saved here
│   └── cascade_archetypes/             # Curated cascade-archetype cards (oic-ca-*.md)
├── logs/
│   └── api_calls/                      # API call logs (JSONL format)
├── requirements.txt                    # Python dependencies
└── README.md                           # This file
```

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

**requirements.txt:**
```
# Web Framework
Flask>=3.0.0,<4.0
gunicorn>=21.2.0,<22.0

# AI/ML
anthropic>=0.39.0,<0.50
httpx>=0.25.0,<1.0

# GCP Vertex AI (RAG)
google-cloud-aiplatform>=1.70.0,<1.80
google-auth>=2.25.0,<3.0

# Scientific Computing
numpy>=1.26.2,<2.0
scipy>=1.11.4,<1.13

# Utilities
python-dotenv>=1.0.0,<2.0
typing-extensions>=4.8.0,<5.0
```

**Python Version:** 3.8 - 3.11 (3.11 recommended)

### 2. Set Up Environment Variables

**Required:**
- `ANTHROPIC_API_KEY` - Get from https://console.anthropic.com
- `SECRET_KEY` - Flask session secret (generate with `python -c "import secrets; print(secrets.token_hex(32))"`)

**GCP Services (Cloud Run, Cloud SQL, Secret Manager):**
- `GOOGLE_APPLICATION_CREDENTIALS` - Path to service account JSON key
- `GOOGLE_CLOUD_PROJECT` - Your GCP project ID
- `GCP_LOCATION` - GCP region (default: us-central1)

```bash
# Option 1: Environment variables
export ANTHROPIC_API_KEY='sk-ant-xxxxx'
export SECRET_KEY='your-secure-secret-key'
export GOOGLE_APPLICATION_CREDENTIALS='/path/to/service-account-key.json'
export GOOGLE_CLOUD_PROJECT='your-project-id'

# Option 2: .env file
cat > .env << EOF
ANTHROPIC_API_KEY=sk-ant-xxxxx
SECRET_KEY=your-secure-secret-key
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
GOOGLE_CLOUD_PROJECT=your-project-id
EOF
```

**Cascade-Archetype Grounding (optional, default OFF):**

| Variable | Default | Description |
|----------|---------|-------------|
| `OIC_CARDS_ENABLED` | `0` | Load the cascade-archetype card library and allow card grounding. Set to `1` to enable. |
| `OIC_ARCHETYPE_SELECT` | `0` | Show the archetype selection dropdown on the generate form. Set to `1` to enable. |
| `OIC_ARCHETYPE_LIMIT` | `3` | Maximum number of archetypes surfaced in the dropdown. |
| `OIC_CARDS_DIR` | `generated/cascade_archetypes` | Directory (relative to the app working dir / `/app` in Docker) holding `oic-ca-*.md` cards. |

```bash
# Enable Path A cascade-archetype grounding for the demo
export OIC_CARDS_ENABLED=1
export OIC_ARCHETYPE_SELECT=1
```

> Both flags must be `1` for the selection step and the `/archetype/view/<id>` page to appear.
> Google Custom Search keys (`GOOGLE_SEARCH_API_KEY`, `GOOGLE_SEARCH_CSE_ID`) are still used for
> the cascade-grounded web search; without them, generation falls back to card-only grounding.

### 3. Create Directories

```bash
mkdir -p generated logs/api_calls static
```

### 4. Run the Application

**Development:**
```bash
python main.py
```

**Production (with Gunicorn):**
```bash
gunicorn -w 4 -b 0.0.0.0:8080 --timeout 300 main:app
```

**Docker:**
```bash
docker build -t openimpactcascade:latest .
docker run -p 8080:8080 \
  -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  -e SECRET_KEY=$SECRET_KEY \
  -e GOOGLE_APPLICATION_CREDENTIALS=/app/service-account-key.json \
  -v $(pwd)/service-account-key.json:/app/service-account-key.json \
  openimpactcascade:latest
```

Access at: **http://localhost:8080**

**Default Port:** 8080 (configurable via `PORT` environment variable)

---

## 📖 User Guide

### Workflow

1. **Home** → Select "AI-Generated Questionnaire"
2. **Generate** → Choose industry and region (20-40 seconds)
3. **Complete** → Answer questions with AI chat assistance
4. **Analyze** → View Monte Carlo simulation results
5. **Adjust** → Modify controls to see risk reduction impact

### Example Session

```
1. Select: Healthcare / Canada
   ↓
2. AI generates questionnaire based on:
   - Canadian threat landscape
   - Healthcare-specific attacks
   - Verified CISA/ACSC advisories
   - MITRE ATT&CK techniques
   ↓
3. Answer questions with chat help:
   - "How to estimate ransomware frequency?"
   - "What costs to include in data breach?"
   ↓
4. View results:
   - Expected Annual Loss: $1,250,000
   - 90th percentile: $3,500,000
   - Risk reduction scenarios
```

### Chat Assistant Usage

**Quick Help Buttons** (context-aware):
- For frequency questions: "How to estimate frequency?"
- For magnitude questions: "What costs to include?"
- For controls: "How to improve security?"

**Chat Examples:**
```
You: "What's a typical ransomware frequency for hospitals?"
AI: For Canadian healthcare organizations with moderate security...

You: "Should I include reputation damage in the cost?"
AI: Yes! Reputation costs for healthcare breaches typically include...

You: "How does MFA reduce my risk?"
AI: Multi-factor authentication reduces likelihood by preventing...
```

---

## 📐 FAIR Methodology: TEF × Vulnerability Approach

### Understanding the LEF Decomposition

This platform implements the **Open FAIR standard** for risk quantification by decomposing Loss Event Frequency (LEF) into its fundamental components:

```
LEF = TEF × Vulnerability
```

**Where:**
- **TEF (Threat Event Frequency)**: How often threat actors **attempt** attacks (events/year)
- **Vulnerability**: Probability that an attack attempt **succeeds** and causes loss (0.0 to 1.0)
- **LEF (Loss Event Frequency)**: How often attacks **successfully cause loss** (events/year)

### Why This Matters

**The Problem:** Most users struggle to differentiate between "how often we're attacked" vs "how often attacks succeed." This is the **most-missed question on the FAIR certification exam**.

**The Solution:** Separate questions for:
1. **Threat frequency** (attempts) - Based on threat intelligence
2. **Control effectiveness** (vulnerability) - Based on your security posture
3. **Loss frequency** (successes) - Auto-calculated from TEF × Vulnerability

### Real-World Example

**Scenario:** Ransomware targeting healthcare organization

**Step 1 - Threat Event Frequency:**
```
"How often do ransomware groups attempt attacks?"
→ Answer: 6 attempts per year (based on CISA data)
```

**Step 2 - Control Effectiveness:**
```
"What ransomware defenses do you have?"
→ Answer: EDR + training + tested backups = 15% vulnerability
   (Meaning: 15% of attacks succeed, 85% are blocked)
```

**Step 3 - Calculated Loss Event Frequency:**
```
LEF = 6 attempts/year × 0.15 vulnerability = 0.9 successful breaches/year
Interpretation: ~1 successful breach every 13 months
```

### Control Effectiveness Mapping

| Control Maturity | Vulnerability | Attack Success Rate |
|-----------------|---------------|---------------------|
| **Minimal** (Basic AV only) | 70% | 7 out of 10 attacks succeed |
| **Basic** (AV + email filtering) | 40% | 4 out of 10 attacks succeed |
| **Intermediate** (EDR + training + backups) | 15% | 1.5 out of 10 attacks succeed |
| **Advanced** (EDR + SIEM + MFA + immutable backups) | 5% | 0.5 out of 10 attacks succeed |

### Benefits

**For Users:**
- ✅ Clearer mental model (separate "attempts" from "successes")
- ✅ Better control assessment (see direct impact of security investments)
- ✅ More accurate estimates (easier to think about components separately)
- ✅ Learn proper FAIR methodology

**For Risk Analysis:**
- ✅ Higher fidelity risk quantification
- ✅ Independent sensitivity analysis (vary TEF or Vulnerability separately)
- ✅ Control ROI calculations (show how investments reduce LEF)
- ✅ Full audit trail for risk estimates

### Documentation

For complete implementation details, see:
- **[FAIR_LEF_DECOMPOSITION_PROPOSAL.md](documentation/FAIR_LEF_DECOMPOSITION_PROPOSAL.md)** - Full methodology
- **[about_fair.html](app/templates/about_fair.html)** - User-facing FAIR explanation
- **FAIR Institute:** https://www.fairinstitute.org/blog/fair-terminology-101-risk-threat-event-frequency-and-vulnerability

---

## 🔧 API Endpoints

### Public Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Home page |
| GET | `/generate` | Questionnaire generation form (shows archetype dropdown when flags enabled) |
| POST | `/generate` | Generate questionnaire (requires industry, region; optional `selected_archetype_id`) |
| GET | `/archetype/view/<id>` | Render a full cascade archetype as an HTML page (flag-gated) |
| GET | `/questionnaire` | Display generated questionnaire |
| POST | `/analyze` | Run Monte Carlo simulation |
| POST | `/chat/assist` | AI chat assistance (AJAX) |
| POST | `/recalculate` | Recalculate with adjusted controls (AJAX) |
| GET | `/download/<filename>` | Download questionnaire JSON |
| GET | `/health` | Health check |

### Request Examples

**Generate Questionnaire:**
```bash
curl -X POST http://localhost:8080/generate \
  -F "industry=Healthcare" \
  -F "region=Canada" \
  -F "organization_size=500 employees"
```

**Chat Assistance:**
```bash
curl -X POST http://localhost:8080/chat/assist \
  -H "Content-Type: application/json" \
  -d '{
    "message": "How to estimate ransomware frequency?",
    "context": {
      "question_type": "pert_estimate",
      "fair_component": "LEF",
      "industry": "Healthcare",
      "region": "Canada"
    },
    "history": []
  }'
```

---

## 🛡️ Safety & Safeguards

### User Tracking (Implemented)

The application implements Anthropic's recommended safeguards:

**What's Tracked:**
- ✅ Session-based user IDs (evaluation mode)
- ✅ Cryptographically hashed IDs (SHA-256)
- ✅ API call logs (timestamp, type, model)
- ✅ Minimal metadata (industry, region)

**What's NOT Tracked:**
- ❌ Prompts or responses
- ❌ User account information
- ❌ Personal identifiable information (PII)

**Benefits:**
- Respond to Anthropic abuse complaints
- Investigate violations without storing user data
- Maintain privacy while enabling accountability

**For Details:** See **[SAFEGUARDS_README.md](SAFEGUARDS_README.md)**

### Current Mode: Evaluation

The system generates random session-based user IDs:
- Format: `eval-user-{random-12-chars}`
- New ID per application start
- Allows testing without real user accounts

### Production Ready

When integrating with user registration:
1. Update `flask_app_chat.py` to use real user IDs
2. Pass IDs from your auth system
3. Maintain hashing and logging
4. See SAFEGUARDS_README for migration guide

---

## 💰 Cost Analysis

### Anthropic API Costs (Claude Sonnet 4)

**Per Request:**
- Input: $3.00 per million tokens
- Output: $15.00 per million tokens

**Typical Usage:**

| Action | Tokens | Cost |
|--------|--------|------|
| Questionnaire Generation | ~5,600 | $0.05-0.15 |
| Chat Message | ~1,200 | $0.01-0.02 |
| Analysis (local) | 0 | $0.00 |

**Monthly Estimates:**

| Volume | Questionnaires | Chat | Total/Month |
|--------|---------------|------|-------------|
| Small | 10 | 100 | $1.50-2.50 |
| Medium | 100 | 1,000 | $15-25 |
| Large | 1,000 | 10,000 | $150-250 |

**Notes:**
- Monte Carlo simulation runs locally (no API cost)
- User tracking adds minimal API overhead (~0.1%)
- Web search for verification included in generation time
- Retries (if needed) may increase costs by 2-3x

### Cost Optimization Tips

1. **Cache questionnaires**: Store generated questions for common industry/region combinations
2. **Batch generation**: Pre-generate popular combinations during off-peak hours
3. **Rate limiting**: Limit free users to prevent abuse
4. **Session management**: Clean up old sessions to reduce storage

---

## 🔐 Security Best Practices

### API Key Protection
- ✅ Never commit API keys to version control
- ✅ Use environment variables or `.env` files
- ✅ Rotate keys periodically
- ✅ Use different keys for dev/staging/prod

### Session Security
- ✅ Strong random secret key in production
- ✅ HTTPS only (never HTTP)
- ✅ Secure cookie flags (HttpOnly, Secure, SameSite)
- ✅ Session timeout (30-60 minutes)

### Input Validation
- ✅ All form inputs validated
- ✅ Industry/region whitelisted
- ✅ PERT values range-checked
- ✅ XSS protection via template escaping

### API Safeguards
- ✅ User tracking enabled
- ✅ API call logging active
- ✅ Hashed IDs passed to Anthropic
- ✅ Investigation tools ready

### Log Security
- ✅ Restrict log file access
- ✅ No PII in logs
- ✅ Regular log rotation
- ✅ Encrypted at rest (recommended)

---

## 📊 Monitoring & Operations

### Health Monitoring

```bash
curl http://localhost:8080/health
```

Response:
```json
{
  "status": "healthy",
  "ai_enabled": true
}
```

### Log Locations

| Log Type | Location | Format |
|----------|----------|--------|
| API calls | `./logs/api_calls/YYYY-MM-DD_api_calls.jsonl` | JSONL |
| Application | stdout/stderr | Text |
| Flask | Flask console | Text |

### Investigating Issues

**Check API call logs:**
```bash
# View today's API calls
tail -f ./logs/api_calls/$(date +%Y-%m-%d)_api_calls.jsonl

# Search by user ID
python investigate_abuse.py --user-id eval-user-abc123

# Get user statistics
python investigate_abuse.py --user-id eval-user-abc123 --stats
```

**Check for errors:**
```bash
# If JSON parsing fails, check debug file
cat json_error_debug.json

# Check Flask logs
tail -f /path/to/flask.log
```

---

## 🚀 Deployment

### Docker

**Dockerfile:**
```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create directories
RUN mkdir -p generated logs/api_calls

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8080", "main:app"]
```

**Build and run:**
```bash
docker build -t openimpactcascade .
docker run -p 8080:8080 \
  -e ANTHROPIC_API_KEY='your-key' \
  -e SECRET_KEY='your-secret' \
  -v $(pwd)/logs:/app/logs \
  openimpactcascade
```

### Google Cloud Run

```bash
# Build
gcloud builds submit --tag gcr.io/$PROJECT_ID/openimpactcascade

# Deploy
gcloud run deploy openimpactcascade \
  --image gcr.io/$PROJECT_ID/openimpactcascade \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars ANTHROPIC_API_KEY='your-key',SECRET_KEY='your-secret' \
  --memory 1Gi \
  --timeout 300
```

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | Yes | - | API key from console.anthropic.com |
| `SECRET_KEY` | Yes (prod) | - | Flask session secret (generate with `openssl rand -hex 32`) |
| `FLASK_ENV` | No | production | `development` or `production` |
| `PORT` | No | 8080 | Port to run application on |

---

## 🧪 Testing

### Manual Testing

```bash
# Test questionnaire generation
python ai_question_generator.py

# Test simulation
python simulation.py

# Test user tracking
python user_tracking.py
```

### Integration Testing

```bash
# Start the app
python main.py

# In another terminal:
# Test health endpoint
curl http://localhost:8080/health

# Test questionnaire generation
curl -X POST http://localhost:8080/generate \
  -F "industry=Healthcare" \
  -F "region=Canada"

# Check logs
ls -la ./logs/api_calls/
```

---

## ✅ Cascade-Archetype Test Plan

Use this checklist to validate the cascade-archetype grounding feature (Path A) before/at the demo.
It is organized so you can run the **flags-OFF regression** first (prove nothing broke), then the
**flags-ON feature** tests.

### Pre-flight

```bash
# 1. Confirm the cards are present and parse (no server needed)
python -c "import sys; sys.path.insert(0,'app'); from cards.library import CardLibrary; \
lib=CardLibrary('app/generated/cascade_archetypes'); lib.load(); \
print('cards:', [c.id for c in lib.all()])"
# Expect: cards: ['oic-ca-001-b', 'oic-ca-010', 'oic-ca-011']

# 2. Byte-compile the edited modules
python -m py_compile app/config.py app/cards/library.py app/ai_question_generator.py app/main.py
```

### A. Regression — flags OFF (default)

> Goal: prove the app is unchanged when the feature is disabled.

| # | Step | Expected result |
|---|------|-----------------|
| A1 | Start app with `OIC_CARDS_ENABLED` / `OIC_ARCHETYPE_SELECT` **unset** | App boots; `/health` returns healthy |
| A2 | Open `/generate` | **No** archetype dropdown is shown; only industry/region/org size |
| A3 | Generate a questionnaire (Healthcare / Canada) | Succeeds exactly as before; metadata `grounding_mode` = `web_only` (or absent) |
| A4 | Visit `/archetype/view/oic-ca-010` | Returns the error page with HTTP 404 ("not enabled") |
| A5 | Home page | Path A = "grounded analysis", Path B = "directional" copy renders correctly |

### B. Feature — flags ON

```bash
export OIC_CARDS_ENABLED=1
export OIC_ARCHETYPE_SELECT=1
# restart the app
```

| # | Step | Expected result |
|---|------|-----------------|
| B1 | Open `/generate` | Archetype **dropdown** appears after org size, defaulting to *"Let AI suggest threats"* |
| B2 | Open the dropdown | Lists the 3 archetypes (`001-b` ransomware, `010` IT→OT pivot, `011` SIS), each with an `[IT]`/`[OT]` badge; scenario hint updates on change |
| B3 | Select an archetype (e.g. `010`) | *"View full cascade ↗"* link appears |
| B4 | Click *"View full cascade ↗"* | Opens `/archetype/view/oic-ca-010` in a **new tab**, rendered as HTML (headings, lists), with a **Back** button; the generate form is untouched in the original tab |
| B5 | Click **Back** on the view page | New tab closes (or navigates back to the form); the in-progress selection is preserved |
| B6 | Choose `oic-ca-001-b` + Healthcare/Canada and Generate | Server log shows `Grounding on cascade archetype: oic-ca-001-b` and a **cascade-grounded** web search; questionnaire generates |
| B7 | Inspect generated questionnaire metadata | `grounding_mode` = `cascade`, `selected_archetype_id` = `oic-ca-001-b`, `selected_card_ids` = `["oic-ca-001-b"]` |
| B8 | Review questions | Exposure questions reflect the cascade's chokepoints; rationales cite the archetype/anchor incident; web context shaped frequency/magnitude (not new threats) |
| B9 | Select *"Let AI suggest threats"* and Generate | Falls back to the existing web-only path; `grounding_mode` = `web_only` |
| B10 | Generate with an OT archetype (`010`/`011`) | Cascade-grounded queries use the card's `dbir_pattern` and anchor incident (check server log query lines) |

### C. Edge cases

| # | Step | Expected result |
|---|------|-----------------|
| C1 | POST `/generate` with an unknown `selected_archetype_id` | Logs a warning and falls back to web-only generation (no crash) |
| C2 | Visit `/archetype/view/does-not-exist` (flags ON) | Error page, HTTP 404 ("not found") |
| C3 | `markdown` package missing | View page still renders the card as preformatted text (graceful fallback) |
| C4 | Generate with web search keys absent | Card-only grounding still produces a questionnaire |

### D. Docker / deploy validation

```bash
docker build -t openimpactcascade:demo .

# Confirm the cards shipped inside the image
docker run --rm openimpactcascade:demo ls /app/generated/cascade_archetypes
# Expect the three oic-ca-*.md files

docker run -p 8080:8080 \
  -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  -e SECRET_KEY=$SECRET_KEY \
  -e OIC_CARDS_ENABLED=1 -e OIC_ARCHETYPE_SELECT=1 \
  openimpactcascade:demo
# Then re-run section B against the container
```

---

## 🐛 Troubleshooting

### Common Issues

**"ANTHROPIC_API_KEY environment variable must be set"**
```bash
# Check if set
echo $ANTHROPIC_API_KEY

# Set it
export ANTHROPIC_API_KEY='your-key-here'
```

**JSON Parsing Errors**
- The AI occasionally generates invalid JSON
- App retries up to 3 times with adjusted parameters
- Check `json_error_debug.json` for details
- Try a different industry/region combination

**Long Generation Times (20-40 seconds)**
- **This is normal!** The AI is:
  - Searching threat intelligence sources
  - Verifying advisory content
  - Cross-referencing MITRE ATT&CK
  - Researching documented incidents
- Shows progress messages during generation

**Chat Assistant Not Working**
```bash
# Check if AI is enabled
curl http://localhost:8080/health

# Check browser console for errors
# Verify API key is set
# Check Flask logs for exceptions
```

**Session Cookie Warnings**
- Set `SECRET_KEY` in production:
  ```bash
  export SECRET_KEY=$(openssl rand -hex 32)
  ```

**Log Files Not Created**
```bash
# Ensure directory exists
mkdir -p ./logs/api_calls

# Check permissions
chmod 755 ./logs/api_calls
```

---

## 🔄 Roadmap & Future Enhancements

### Planned Features

1. **User Authentication**
   - Registration and login system
   - Multi-tenant support
   - Team collaboration

2. **Enhanced Analytics**
   - Historical risk tracking
   - Trend analysis
   - Benchmarking against industry

3. **Advanced Controls**
   - Control effectiveness scoring
   - ROI calculations
   - Control recommendation engine

4. **Reporting**
   - PDF report generation
   - Executive summaries
   - Custom report templates

5. **API Enhancements**
   - RESTful API for integrations
   - Webhook support
   - Batch processing

6. **Performance**
   - Questionnaire caching (future optimization)
   - Faster generation with optimized prompts
   - Background processing for large analyses

---

### 📚 Retrieval Architecture (File-Based Corpus)

Instead of relying on a managed Vector DB (like Vertex AI RAG), OpenImpactCascade now uses a **Markdown + Frontmatter** architecture (detailed in `ADR-0012`):
- **Deterministic Filtering**: Retrieves context slices based on specific metadata facets (industry, region, tags) from `_index.json`.
- **Low Marginal Cost**: Maximizes prompt caching by injecting stable document slices, allowing for viable free-tier SaaS scaling.
- **Traceable Curation**: Markdown corpus with structured YAML frontmatter ensures transparent source traceability and strict governance over content ingested.
- **Web Search Gap-Fill**: Dynamically executes web searches only when the corpus lacks coverage, regulated by domain/org-level policy rules.

---

## 📚 Documentation

### Core Documentation
- **README.md** (this file) - Main application documentation
- **SAFEGUARDS_README.md** - API safeguards and abuse prevention
- **flask_readme.md** - Additional Flask implementation details

### Code Documentation
- `ai_question_generator.py` - See docstrings for AI generation
- `simulation.py` - See docstrings for Monte Carlo analysis
- `user_tracking.py` - See docstrings for tracking system

### External Resources
- [Anthropic API Documentation](https://docs.anthropic.com)
- [FAIR Methodology](https://www.fairinstitute.org)
- [MITRE ATT&CK](https://attack.mitre.org)
- [Anthropic API Safeguards](https://support.claude.com/en/articles/9199617-api-safeguards-tools)

---

## 🤝 Contributing

### Development Setup

1. Clone repository
2. Create virtual environment: `python -m venv venv`
3. Activate: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Set up API key: `export ANTHROPIC_API_KEY='your-key'`
6. Run tests: `python -m pytest tests/`
7. Start app: `python flask_oic_v215.py`

### Code Style

- Follow PEP 8
- Use type hints where possible
- Add docstrings to all functions
- Keep functions focused and small

### Submitting Changes

1. Create feature branch: `git checkout -b feature/your-feature`
2. Make changes with clear commits
3. Test thoroughly
4. Update documentation
5. Submit pull request

---

## 📄 License

[Your License Here]

---

## 📞 Support

### Getting Help

1. **Documentation**: Check this README and SAFEGUARDS_README.md
2. **Logs**: Review application and API call logs
3. **Health Check**: `curl http://localhost:8080/health`
4. **Debug File**: Check `json_error_debug.json` for parsing errors

### Reporting Issues

When reporting issues, include:
- Application version
- Environment (dev/prod)
- Steps to reproduce
- Error messages from logs
- Browser console errors (if UI issue)

### Contact

For questions about:
- **Application**: Review documentation
- **API Safeguards**: See SAFEGUARDS_README.md
- **Anthropic API**: Contact [email protected]
- **Security Issues**: Report privately to maintainers

---

## 🎯 Quick Reference

### Essential Commands

```bash
# Start application
python main.py

# Check health
curl http://localhost:8080/health

# View API logs
tail -f ./logs/api_calls/$(date +%Y-%m-%d)_api_calls.jsonl

# Test user tracking
python user_tracking.py

# Investigate user
python investigate_abuse.py --user-id <user-id>

# Generate requirements
pip freeze > requirements.txt
```

### Key Files

| File | Purpose |
|------|---------|
| `main.py` | Main Flask application with LEF decomposition |
| `ai_question_generator.py` | AI question generation with TEF/Vulnerability |
| `simulation.py` | Monte Carlo simulation with PERT/lognormal |
| `corpus/` | Markdown + Frontmatter Knowledge Base package |
| `user_tracking.py` | User tracking & API safeguards |
| `templates/questionnaire_chat_rationale.html` | Interactive UI with rationale display |
| `documentation/FAIR_LEF_DECOMPOSITION_PROPOSAL.md` | TEF × Vulnerability methodology |
| `SAFEGUARDS_README.md` | Abuse prevention documentation |

### Important URLs

| URL | Purpose |
|-----|---------|
| http://localhost:8080 | Application home |
| http://localhost:8080/health | Health check |
| http://localhost:8080/generate | Generate questionnaire |
| https://console.anthropic.com | API key management |

---

## ✅ Deployment Checklist

Before deploying to production:

- [ ] Set `ANTHROPIC_API_KEY`
- [ ] Set `SECRET_KEY` (generate with `openssl rand -hex 32`)
- [ ] Set `FLASK_ENV=production`
- [ ] Enable HTTPS only
- [ ] Configure secure session cookies
- [ ] Set up log rotation
- [ ] Enable rate limiting
- [ ] Configure user authentication (if needed)
- [ ] Test health endpoint
- [ ] Test questionnaire generation
- [ ] Test chat assistant
- [ ] Verify user tracking logs
- [ ] Document abuse response procedure
- [ ] Update privacy policy
- [ ] Train support team

---

**Version**: 2.2.1 (LEF Decomposition) + Cascade-Archetype Grounding (Path A, flag-gated)  
**Last Updated**: June 2026  
**Status**: Production Ready (Evaluation Mode)  
**Key Enhancement**: TEF × Vulnerability decomposition; optional cascade-archetype grounding with cascade-grounded web search

For detailed safeguards implementation, see **[SAFEGUARDS_README.md](SAFEGUARDS_README.md)**  
For LEF decomposition methodology, see **[FAIR_LEF_DECOMPOSITION_PROPOSAL.md](documentation/FAIR_LEF_DECOMPOSITION_PROPOSAL.md)**
