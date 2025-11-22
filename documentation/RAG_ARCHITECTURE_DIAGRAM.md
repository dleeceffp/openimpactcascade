# Vertex AI RAG Architecture Diagrams

Visual representations of the RAG integration architecture.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                              │
│                    (Browser / API Client)                           │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             │ HTTP Request
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│                      FLASK APPLICATION                              │
│                     (flask_app_chat.py)                             │
│                                                                     │
│  ┌──────────────────┐              ┌──────────────────┐            │
│  │  /generate       │              │  /chat/assist    │            │
│  │  (Questionnaire) │              │  (Chat Coaching) │            │
│  └────────┬─────────┘              └────────┬─────────┘            │
└───────────┼──────────────────────────────────┼──────────────────────┘
            │                                  │
            │                                  │
┌───────────▼──────────────────────────────────▼──────────────────────┐
│              AI QUESTION GENERATOR MODULE                           │
│              (ai_question_generator.py)                             │
│                                                                     │
│  ┌──────────────────────────────────────────────────────┐          │
│  │  _build_contextual_prompt()                          │          │
│  │  _build_custom_scenario_prompt()                     │          │
│  └────────┬─────────────────────────────────────────────┘          │
└───────────┼──────────────────────────────────────────────────────────┘
            │
            │ Request Context
            │
┌───────────▼──────────────────────────────────────────────────────────┐
│                    VERTEX RAG ENGINE                                 │
│                    (vertex_rag.py)                                   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────┐       │
│  │  retrieve_risk_identification_context()                  │       │
│  │  - Industry: Healthcare                                  │       │
│  │  - Region: Canada                                        │       │
│  │  - Max Results: 5                                        │       │
│  └────────┬─────────────────────────────────────────────────┘       │
│           │                                                          │
│  ┌────────▼─────────────────────────────────────────────────┐       │
│  │  retrieve_coaching_context()                             │       │
│  │  - User Question: "How to estimate frequency?"           │       │
│  │  - FAIR Component: LEF                                   │       │
│  │  - Max Results: 3                                        │       │
│  └────────┬─────────────────────────────────────────────────┘       │
└───────────┼──────────────────────────────────────────────────────────┘
            │
            │ RAG Query
            │
┌───────────▼──────────────────────────────────────────────────────────┐
│                    GCP VERTEX AI RAG API                             │
│                    (Google Cloud Platform)                           │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────┐       │
│  │  RAG Corpus: "risk-assessment-kb"                        │       │
│  │  - Vector Search                                         │       │
│  │  - Metadata Filtering                                    │       │
│  │  - Similarity Ranking                                    │       │
│  └────────┬─────────────────────────────────────────────────┘       │
└───────────┼──────────────────────────────────────────────────────────┘
            │
            │ Query Knowledge Base
            │
┌───────────▼──────────────────────────────────────────────────────────┐
│                    KNOWLEDGE BASE CORPUS                             │
│                    (GCS Bucket + Vector Index)                       │
│                                                                      │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────┐   │
│  │ Threat Intel     │  │ MITRE ATT&CK     │  │ Industry Reports│   │
│  │ - CISA Advisories│  │ - Techniques     │  │ - Verizon DBIR  │   │
│  │ - CERT Alerts    │  │ - Groups         │  │ - IBM Breach    │   │
│  │ - Vendor Reports │  │ - Software       │  │ - Sector Data   │   │
│  └──────────────────┘  └──────────────────┘  └─────────────────┘   │
│                                                                      │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────┐   │
│  │ Compliance       │  │ Best Practices   │  │ Case Studies    │   │
│  │ - GDPR           │  │ - NIST           │  │ - Incidents     │   │
│  │ - HIPAA          │  │ - CIS            │  │ - Lessons       │   │
│  │ - Regional Regs  │  │ - Industry Guides│  │ - Benchmarks    │   │
│  └──────────────────┘  └──────────────────┘  └─────────────────┘   │
└───────────┬──────────────────────────────────────────────────────────┘
            │
            │ Retrieved Contexts
            │
┌───────────▼──────────────────────────────────────────────────────────┐
│                    RAG CONTEXT FORMATTER                             │
│                    (vertex_rag.py)                                   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────┐       │
│  │  format_context_for_prompt()                             │       │
│  │  - Source: CISA AA24-249A                                │       │
│  │  - Relevance: 0.92                                       │       │
│  │  - Content: "Ransomware attacks targeting..."           │       │
│  │  - Metadata: {industry: Healthcare, region: Canada}      │       │
│  └────────┬─────────────────────────────────────────────────┘       │
└───────────┼──────────────────────────────────────────────────────────┘
            │
            │ Formatted Grounding Context
            │
┌───────────▼──────────────────────────────────────────────────────────┐
│                    PROMPT CONSTRUCTION                               │
│                    (ai_question_generator.py)                        │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────┐       │
│  │  Enhanced Prompt = Base Prompt + RAG Context             │       │
│  │                                                           │       │
│  │  "Create questionnaire for Healthcare in Canada...       │       │
│  │                                                           │       │
│  │   **Grounding Context from Knowledge Base:**             │       │
│  │   Source 1: CISA AA24-249A (Relevance: 0.92)             │       │
│  │   - Ransomware attacks targeting healthcare...           │       │
│  │                                                           │       │
│  │   Source 2: MITRE T1486 (Relevance: 0.88)                │       │
│  │   - Data Encrypted for Impact technique...               │       │
│  │                                                           │       │
│  │   Use this grounding context to inform your response."   │       │
│  └────────┬─────────────────────────────────────────────────┘       │
└───────────┼──────────────────────────────────────────────────────────┘
            │
            │ Enhanced Prompt
            │
┌───────────▼──────────────────────────────────────────────────────────┐
│                    ANTHROPIC CLAUDE API                              │
│                    (Claude Sonnet 4)                                 │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────┐       │
│  │  Process Enhanced Prompt                                 │       │
│  │  - System: Expert risk consultant                        │       │
│  │  - Context: RAG grounding + user context                 │       │
│  │  - Generate: Questionnaire or chat response              │       │
│  └────────┬─────────────────────────────────────────────────┘       │
└───────────┼──────────────────────────────────────────────────────────┘
            │
            │ Generated Response
            │
┌───────────▼──────────────────────────────────────────────────────────┐
│                    RESPONSE PROCESSING                               │
│                    (flask_app_chat.py)                               │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────┐       │
│  │  - Validate JSON (questionnaire)                         │       │
│  │  - Format response (chat)                                │       │
│  │  - Log API call (user_tracking.py)                       │       │
│  │  - Return to user                                        │       │
│  └────────┬─────────────────────────────────────────────────┘       │
└───────────┼──────────────────────────────────────────────────────────┘
            │
            │ Final Response
            │
┌───────────▼──────────────────────────────────────────────────────────┐
│                         USER INTERFACE                               │
│                    (Questionnaire or Chat Answer)                    │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow: Risk Identification

```
User Input                    RAG Query                  Knowledge Base
─────────────                ───────────                ──────────────

Industry: Healthcare    →    Query: "Healthcare        →  Search Corpus:
Region: Canada               cybersecurity threats         - Metadata filter:
Org Size: 500 employees      Canada ransomware              industry=Healthcare
                             MITRE ATT&CK"                  region=Canada
                                                           - Vector similarity
                                                           - Rank by relevance

                                    ↓

                         Retrieved Contexts
                         ──────────────────
                         
                         Context 1 (Score: 0.92)
                         ┌────────────────────────────┐
                         │ Source: CISA AA24-249A     │
                         │ Type: Threat Intelligence  │
                         │ Content: "Ransomware       │
                         │ attacks targeting          │
                         │ healthcare organizations   │
                         │ in North America..."       │
                         └────────────────────────────┘
                         
                         Context 2 (Score: 0.88)
                         ┌────────────────────────────┐
                         │ Source: MITRE T1486        │
                         │ Type: ATT&CK Technique     │
                         │ Content: "Data Encrypted   │
                         │ for Impact - adversaries   │
                         │ encrypt data..."           │
                         └────────────────────────────┘
                         
                         Context 3 (Score: 0.85)
                         ┌────────────────────────────┐
                         │ Source: Verizon DBIR 2024  │
                         │ Type: Industry Report      │
                         │ Content: "Healthcare       │
                         │ sector experienced 2.3     │
                         │ ransomware incidents..."   │
                         └────────────────────────────┘

                                    ↓

                         Format for Prompt
                         ─────────────────
                         
                         **Grounding Context:**
                         Source 1 (0.92): CISA AA24-249A
                         - Ransomware attacks targeting...
                         
                         Source 2 (0.88): MITRE T1486
                         - Data Encrypted for Impact...
                         
                         Source 3 (0.85): Verizon DBIR
                         - Healthcare sector experienced...

                                    ↓

                         Enhanced Prompt
                         ───────────────
                         
                         System: Expert risk consultant
                         Context: [RAG grounding above]
                         Task: Generate questionnaire
                         
                         → Send to Claude API

                                    ↓

                         Generated Questionnaire
                         ──────────────────────
                         
                         {
                           "questions": {
                             "threat_selection": {
                               "choices": [
                                 {
                                   "text": "Ransomware attack on EHR systems",
                                   "description": "Based on CISA AA24-249A...",
                                   "mitre_techniques": ["T1486"],
                                   "source": "CISA AA24-249A"
                                 }
                               ]
                             }
                           }
                         }
```

---

## Data Flow: Chat Coaching

```
User Question                RAG Query                  Knowledge Base
─────────────               ───────────                ──────────────

"How often do          →    Query: "ransomware        →  Search Corpus:
ransomware attacks          frequency estimation          - Metadata filter:
happen in healthcare?"      healthcare Canada              document_type=
                            loss event frequency           guidance, benchmarks
                            LEF"                          - Vector similarity
                                                          - Rank by relevance

                                    ↓

                         Retrieved Contexts
                         ──────────────────
                         
                         Context 1 (Score: 0.94)
                         ┌────────────────────────────┐
                         │ Source: Verizon DBIR 2024  │
                         │ Type: Benchmark            │
                         │ Content: "Healthcare orgs  │
                         │ experienced avg 2.3        │
                         │ ransomware incidents/year, │
                         │ 67% reported at least 1"   │
                         └────────────────────────────┘
                         
                         Context 2 (Score: 0.89)
                         ┌────────────────────────────┐
                         │ Source: IBM Breach 2024    │
                         │ Type: Industry Report      │
                         │ Content: "Healthcare shows │
                         │ 15% increase in ransomware │
                         │ frequency vs 2023, avg     │
                         │ detection time 236 days"   │
                         └────────────────────────────┘
                         
                         Context 3 (Score: 0.86)
                         ┌────────────────────────────┐
                         │ Source: NIST Guide         │
                         │ Type: Best Practice        │
                         │ Content: "When estimating  │
                         │ LEF, consider historical   │
                         │ data, industry benchmarks" │
                         └────────────────────────────┘

                                    ↓

                         Enhanced Chat Prompt
                         ───────────────────
                         
                         System: Risk consultant
                         Context: [RAG grounding above]
                         User: "How often do ransomware
                               attacks happen in healthcare?"
                         
                         → Send to Claude API

                                    ↓

                         Chat Response
                         ─────────────
                         
                         "Based on recent industry data,
                         healthcare organizations in Canada
                         experience an average of 2-3
                         ransomware incidents per year
                         (Verizon DBIR 2024).
                         
                         For your PERT estimate:
                         - Minimum: 0.5 (once every 2 years)
                         - Most Likely: 2.0 (twice per year)
                         - Maximum: 5.0 (5 times per year)
                         
                         This is based on organizations with
                         moderate security controls..."
```

---

## Knowledge Base Organization

```
GCS Bucket: your-project-rag-kb
│
├── knowledge_base/
│   │
│   ├── threat_intelligence/
│   │   ├── cisa_advisories/
│   │   │   ├── aa24-249a.pdf ──────────┐
│   │   │   ├── aa24-250a.pdf           │
│   │   │   └── aa24-251a.pdf           │
│   │   │                               │
│   │   ├── cert_alerts/                │
│   │   │   ├── acsc_2024_001.pdf       │
│   │   │   └── ncsc_alert_2024.pdf     │
│   │   │                               │
│   │   └── vendor_reports/             │
│   │       ├── crowdstrike_2024.pdf    │
│   │       └── mandiant_m_trends.pdf   │
│   │                                   │
│   ├── mitre_attack/                   │
│   │   ├── techniques/                 │
│   │   │   ├── t1486.json ─────────────┤
│   │   │   ├── t1566_001.json          │
│   │   │   └── t1078.json              │
│   │   │                               │
│   │   ├── groups/                     │
│   │   │   └── apt29.json              │
│   │   │                               │
│   │   └── software/                   │
│   │       └── ransomware_x.json       │
│   │                                   │
│   ├── industry_reports/               │
│   │   ├── verizon_dbir/               │
│   │   │   ├── dbir_2024.pdf ──────────┤
│   │   │   └── dbir_2023.pdf           │
│   │   │                               │
│   │   ├── ibm_breach_cost/            │
│   │   │   └── cost_2024.pdf           │
│   │   │                               │
│   │   └── sector_specific/            │
│   │       ├── healthcare_2024.pdf     │
│   │       └── finance_2024.pdf        │
│   │                                   │
│   └── [other categories...]           │
│                                       │
│                                       ▼
│                              RAG Corpus Index
│                              ─────────────────
│                              
│                              Vector Embeddings:
│                              ┌─────────────────────┐
│                              │ Doc 1: [0.23, 0.45, │
│                              │         0.12, ...]  │
│                              │ Metadata: {         │
│                              │   type: threat_intel│
│                              │   industry: HC      │
│                              │   region: CA        │
│                              │ }                   │
│                              └─────────────────────┘
│                              
│                              ┌─────────────────────┐
│                              │ Doc 2: [0.67, 0.21, │
│                              │         0.89, ...]  │
│                              │ Metadata: {         │
│                              │   type: mitre       │
│                              │   technique: T1486  │
│                              │ }                   │
│                              └─────────────────────┘
│                              
│                              [... more documents ...]
```

---

## Integration Timeline

```
Week 1: Setup & Configuration
├── Day 1: GCP Setup
│   ├── Enable Vertex AI API
│   ├── Create service account
│   ├── Create GCS bucket
│   └── Configure environment
│
├── Day 2: Knowledge Base Structure
│   ├── Create directory structure
│   ├── Collect initial documents
│   └── Test document upload
│
└── Day 3: RAG Corpus Creation
    ├── Create RAG corpus
    ├── Upload documents
    └── Test retrieval

Week 2: Integration
├── Day 4-5: Question Generator
│   ├── Add RAG imports
│   ├── Modify prompt building
│   ├── Test generation
│   └── Validate quality
│
└── Day 6-7: Chat Assistant
    ├── Add RAG to chat endpoints
    ├── Test coaching responses
    ├── Validate relevance
    └── Performance testing

Week 3: Testing & Deployment
├── Day 8-9: Quality Assurance
│   ├── Functional testing
│   ├── Performance testing
│   └── User acceptance testing
│
└── Day 10: Production Deployment
    ├── Deploy to staging
    ├── Monitor and adjust
    └── Deploy to production
```

---

## Monitoring Dashboard (Conceptual)

```
┌─────────────────────────────────────────────────────────────┐
│                   RAG MONITORING DASHBOARD                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  RAG Engine Status: ✅ OPERATIONAL                          │
│  Corpus: risk-assessment-kb                                │
│  Last Updated: 2024-11-01 10:30 UTC                        │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  QUERY METRICS (Last 24 Hours)                             │
│  ┌───────────────────────────────────────────────────┐     │
│  │ Total Queries:        1,247                       │     │
│  │ Risk Identification:    892 (71%)                 │     │
│  │ Coaching:               355 (29%)                 │     │
│  │ Avg Latency:          127ms                       │     │
│  │ Fallback Rate:        2.3%                        │     │
│  └───────────────────────────────────────────────────┘     │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  RELEVANCE SCORES                                          │
│  ┌───────────────────────────────────────────────────┐     │
│  │ Average Score:        0.87                        │     │
│  │ >0.9 (Excellent):     45%                         │     │
│  │ 0.7-0.9 (Good):       42%                         │     │
│  │ <0.7 (Poor):          13%                         │     │
│  └───────────────────────────────────────────────────┘     │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  KNOWLEDGE BASE                                            │
│  ┌───────────────────────────────────────────────────┐     │
│  │ Total Documents:      1,234                       │     │
│  │ Threat Intel:          456 (37%)                  │     │
│  │ MITRE ATT&CK:          289 (23%)                  │     │
│  │ Industry Reports:      178 (14%)                  │     │
│  │ Other:                 311 (26%)                  │     │
│  │ Storage Used:         8.7 GB                      │     │
│  └───────────────────────────────────────────────────┘     │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  COST TRACKING (Month to Date)                            │
│  ┌───────────────────────────────────────────────────┐     │
│  │ Storage:              $0.87                       │     │
│  │ Queries:              $8.45                       │     │
│  │ Total:                $9.32                       │     │
│  │ Projected Monthly:   $12.50                       │     │
│  └───────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

---

**Version**: 1.0.0  
**Last Updated**: November 2025  
**Purpose**: Visual reference for RAG integration architecture
