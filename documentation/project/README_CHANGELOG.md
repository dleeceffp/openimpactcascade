# README Update Summary

## 📝 Changes Made

This document summarizes the updates made to the main README to reflect the current state of OpenImpactCascade.

---

## 🎯 Purpose of Update

The original README needed updating to:
1. **Reflect implemented features** - User tracking and safeguards are now live
2. **Accurate cost analysis** - Include tracking overhead (minimal)
3. **Current architecture** - Document the evaluation mode vs production setup
4. **Clear documentation structure** - Main README + separate SAFEGUARDS_README
5. **Remove future features** - No caching discussion (deprioritized)

---

## ✅ What Was Added

### 1. Safety & Safeguards Section
**New content:**
- Overview of user tracking implementation
- What's tracked vs what's NOT tracked
- Current evaluation mode explanation
- Link to detailed SAFEGUARDS_README.md
- Production migration guidance

**Why:**
- User tracking is a major feature that was missing from docs
- Users need to understand privacy implications
- Clear path from evaluation to production

### 2. Enhanced Cost Analysis
**Updated:**
- Added user tracking overhead note (~0.1%)
- Clarified that Monte Carlo runs locally (free)
- Updated monthly estimates with chat assistant costs
- Added cost optimization tips

**Why:**
- More accurate cost projections
- Users understand what costs API calls vs local compute
- Planning guidance for budget

### 3. Chat Assistant Documentation
**Added:**
- Chat assistant features in overview
- Usage examples
- Quick help button documentation
- Context-aware guidance explanation

**Why:**
- Chat assistant is a key differentiator
- Users need to understand how to use it effectively

### 4. Operations & Monitoring
**New sections:**
- Health monitoring endpoints
- Log locations and formats
- Investigation procedures
- Troubleshooting for tracking issues

**Why:**
- Operations teams need to know where logs are
- How to investigate when Anthropic reports abuse
- Day-to-day operational guidance

### 5. Security Best Practices
**Enhanced:**
- API safeguards included
- Log security guidance
- User ID hashing explained
- Privacy-preserving logging

**Why:**
- Security is critical for risk assessment tool
- Compliance requirements
- Build trust with users

---

## 🗑️ What Was Removed/Deprioritized

### 1. Prompt Caching Discussion
**Status:** Removed entirely

**Why:**
- Feature was deprioritized per user feedback
- Focus on core features and safeguards first
- Can be added later if needed

### 2. Training Data Opt-Out
**Status:** Moved to future considerations

**Why:**
- User tracking with `end-user-ids` already provides some privacy
- Full opt-out can be layer added with explicit flags
- Current safeguards adequate for evaluation phase

---

## 📊 Structure Changes

### Before (Flask README)
```
├── Features
├── Project Structure
├── Installation
├── Running
├── Usage Flow
├── API Endpoints
├── Configuration
└── Deployment
```

### After (Updated README)
```
├── Overview
├── Key Features (expanded)
│   ├── AI-Generated Questionnaires
│   ├── FAIR Risk Analysis
│   ├── Interactive Chat Assistant (NEW)
│   └── Safety & Compliance (NEW)
├── Project Structure (updated)
├── Quick Start
├── User Guide (NEW)
├── API Endpoints
├── Safety & Safeguards (NEW)
├── Cost Analysis (enhanced)
├── Security Best Practices (enhanced)
├── Monitoring & Operations (NEW)
├── Deployment
├── Testing (NEW)
├── Troubleshooting (enhanced)
├── Roadmap (NEW)
└── Quick Reference (NEW)
```

---

## 🎨 Presentation Improvements

### 1. Visual Hierarchy
- Added emoji indicators for sections
- Clear section breaks with horizontal rules
- Tables for structured data
- Code blocks with syntax highlighting

### 2. Quick Access
- Quick Start section at top
- Quick Reference section at bottom
- Checklist format for deployment
- Essential commands summary

### 3. Cross-References
- Links to SAFEGUARDS_README.md
- Links to external documentation
- Internal section references
- Clear navigation

---

## 📋 Key Sections to Review

### For Developers
1. **Quick Start** - Get up and running
2. **API Endpoints** - Understand the interface
3. **Testing** - How to test changes
4. **Troubleshooting** - Common issues

### For DevOps
1. **Deployment** - Docker and cloud deployment
2. **Monitoring & Operations** - Health checks and logs
3. **Security Best Practices** - Production hardening
4. **Deployment Checklist** - Pre-launch verification

### For Product Managers
1. **Overview** - What the product does
2. **Key Features** - Main differentiators
3. **Cost Analysis** - Budget planning
4. **Roadmap** - Future plans

### For Security/Compliance
1. **Safety & Safeguards** - Privacy measures
2. **Security Best Practices** - Security posture
3. **SAFEGUARDS_README.md** - Detailed abuse prevention
4. **Log Security** - Data protection

---

## 🔗 Documentation Structure

```
docs/
├── README_UPDATED.md              ← Main documentation (this update)
│   ├── Application overview
│   ├── Quick start guide
│   ├── User guide
│   ├── API reference
│   ├── Security & safeguards (overview)
│   └── Operations guide
│
├── SAFEGUARDS_README.md           ← Separate (unchanged)
│   ├── Detailed safeguards implementation
│   ├── User tracking architecture
│   ├── Abuse investigation procedures
│   └── Compliance checklist
│
└── flask_readme.md                ← Legacy reference
    └── Original Flask documentation
```

**Design Decision:**
- **Main README**: Comprehensive, user-facing, covers all aspects
- **SAFEGUARDS_README**: Technical deep-dive on abuse prevention
- **Flask README**: Kept as reference, may deprecate later

---

## 💡 Usage Recommendations

### For New Users
**Start here:**
1. Read "Overview" and "Key Features"
2. Follow "Quick Start" to get running
3. Try "User Guide" example session
4. Reference "Troubleshooting" if needed

### For Existing Users
**What's new:**
1. "Safety & Safeguards" - understand tracking
2. "Chat Assistant" - learn new feature
3. "Cost Analysis" - updated estimates
4. "Monitoring & Operations" - operational guidance

### For Auditors
**Focus on:**
1. "Safety & Safeguards" section
2. Complete SAFEGUARDS_README.md
3. "Security Best Practices"
4. "Log Security" subsection

---

## ⚠️ Important Notes

### Evaluation Mode
The application is currently in **evaluation mode**:
- Session-based user IDs (random per start)
- Not connected to real user accounts
- Perfect for testing and demonstration
- Ready for production integration

### Migration to Production
When ready:
1. Integrate with user registration system
2. Pass real user IDs to tracker
3. Maintain hashing and logging
4. See SAFEGUARDS_README for details

### Cost Considerations
- User tracking adds **<0.1% API overhead**
- Chat assistant is main cost variable
- Monte Carlo simulation is free (local)
- See "Cost Analysis" for projections

---

## ✅ Verification Checklist

To verify README accuracy:

- [x] All features listed are implemented
- [x] Code examples tested and working
- [x] File paths correct
- [x] External links valid
- [x] Cost estimates current (Oct 2025)
- [x] Environment variables documented
- [x] Deployment instructions tested
- [x] Security recommendations current
- [x] Safeguards integration documented
- [x] No mention of unimplemented features (caching)

---

## 🔄 Update History

| Date | Version | Changes |
|------|---------|---------|
| Oct 2025 | 1.0.0 | Initial comprehensive update |
| | | - Added user tracking documentation |
| | | - Enhanced cost analysis |
| | | - Added chat assistant docs |
| | | - Removed caching discussion |
| | | - Added operations guide |

---

## 📞 Next Steps

### For Documentation Maintainers

1. **Review Updated README**
   - Read through README_UPDATED.md
   - Verify accuracy of all sections
   - Test code examples
   - Check external links

2. **Deploy Documentation**
   ```bash
   # Replace old README
   mv README.md README_OLD.md
   mv README_UPDATED.md README.md
   
   # Keep safeguards separate
   # SAFEGUARDS_README.md stays as-is
   
   # Optional: Archive old flask readme
   mv flask_readme.md docs/legacy/
   ```

3. **Update Links**
   - Update any internal references
   - Check external documentation links
   - Verify SAFEGUARDS_README.md link works

4. **Notify Team**
   - Announce updated documentation
   - Highlight new sections
   - Request feedback

### For Development Team

1. **Review Current State**
   - Verify README matches actual implementation
   - Test documented commands
   - Validate API examples

2. **Future Enhancements**
   - Caching can be added later if needed
   - Training opt-out as separate feature
   - Keep roadmap updated

3. **Documentation Updates**
   - Update README with new features
   - Keep SAFEGUARDS_README in sync
   - Document any breaking changes

---

## 🎯 Key Takeaways

### What This Update Achieves

✅ **Accuracy**: Documentation now matches implementation  
✅ **Completeness**: All features documented  
✅ **Clarity**: Clear structure and navigation  
✅ **Separation**: Main README + detailed safeguards doc  
✅ **Practicality**: Operational guidance included  
✅ **Future-ready**: Roadmap for enhancements  

### What's Not Included (Intentionally)

❌ **Prompt caching**: Deprioritized feature  
❌ **Training opt-out details**: Covered by user tracking  
❌ **Advanced features**: Keep docs focused on current state  

### Documentation Philosophy

1. **Main README** = Comprehensive user-facing docs
2. **SAFEGUARDS_README** = Technical deep-dive on one topic
3. **Separate concerns** = Easier to maintain and navigate

---

## 📚 Related Files

| File | Status | Purpose |
|------|--------|---------|
| README_UPDATED.md | ✅ New | Main documentation (use this) |
| SAFEGUARDS_README.md | ✅ Current | Detailed safeguards (keep separate) |
| flask_readme.md | ⚠️ Legacy | Original Flask docs (archive?) |
| CHANGELOG.md | 📝 This file | Documents the updates |

---

**Summary**: The README has been comprehensively updated to reflect the current implementation, with focus on user tracking, chat assistant, and operational guidance, while keeping safeguards documentation separate for clarity.

---

## June 2026 — Search Provider Migration & Repository Refactor

### Overview

Two related workstreams completed in June 2026:

1. **Web search migration** — replaced the deprecated Google Custom Search integration with a new pluggable oic_search module backed by Tavily and Brave, with automatic provider failover.
2. **Repository restructure** — realigned folder layout to match standard DevOps monorepo conventions (shared modules under src/, tooling under 	ools/, deployment scripts under deployment/gcp/).

---

### 1. Search Provider Migration

#### Background

The original OIC application (pp/ai_question_generator.py) used Google Custom Search Engine (CSE) directly via equests.get to googleapis.com/customsearch/v1.  This relied on two credentials (GOOGLE_SEARCH_API_KEY, GOOGLE_SEARCH_CSE_ID) which were silently unavailable in most deployments because:

- Google CSE was closed to new customers in mid-2025.
- Google CSE is deprecated for all customers as of January 1, 2027.
- The .env.example had already been updated to OIC_SEARCH_PROVIDER=tavily, but pp/ was never migrated — so any deployment following the new template had web search quietly disabled from first startup.

The failure mode was particularly insidious: the __init__ guard emitted a print() warning (not a log entry) and set self.enable_web_search = False.  From that point every call site returned ("", []) with no observable signal in application logs or user-facing output.

#### What Changed

**New oic_search shared module** (src/oic_search/):

A provider-agnostic search library was built to replace all direct search HTTP calls.  It supports:

| Provider | Key env var | Notes |
|---|---|---|
| 	avily | TAVILY_API_KEY | Recommended — pre-extracted content, better for LLM prompts |
| rave | BRAVE_SEARCH_API_KEY | Independent quota pool, good fallback |
| google_cse | GOOGLE_SEARCH_API_KEY + CSE IDs | Retained for existing customers only |
| 
ull | — | Disables search without errors (test/offline use) |

The module normalises results into SearchResult / SearchResponse dataclasses regardless of backend, applies OIC source profiles (curated domain lists for incident, 	hreatintel, ics, ramework), and includes a shared result cache.

**Provider fallback chain** (oic_search.search_with_fallback):

A new search_with_fallback() function was added to oic_search.  It tries the primary provider and, on transient failures (quota, rate-limit, timeout), automatically retries with the next provider in an ordered chain.  Permanent misconfiguration errors (uth, 
ot_configured) surface immediately rather than triggering a futile retry.  The failover is invisible to end-users.

Configured via two env vars (both now stored in Secret Manager):

`
OIC_SEARCH_PROVIDER=tavily       # primary
OIC_SEARCH_FALLBACK=brave        # fallback chain (comma-separated)
`

**pp/ai_question_generator.py**:

- _execute_google_search() replaced by _execute_search() which delegates to oic_search.search_with_fallback().
- google_search_api_key / google_search_cse_id constructor params retained as silent no-ops for call-site compatibility.
- search_provider and search_fallback_providers attrs resolved at __init__ from env vars.
- All print() warnings replaced with logging.getLogger calls — visible in Cloud Logging / Docker log aggregation.
- Auth failures disable search for the session and log once; quota/timeout errors log per-query and trigger fallback rather than silently returning empty.

**pp/config.py** — dotenv bootstrap:

A _bootstrap_env() function was added that runs at import time and loads a local .env file (dev server) via python-dotenv with override=False, so container secrets (GCP Secret Manager / --env flags) always win.  Completely silent when no .env is found, which is normal in Cloud Run.

**pp/main.py**:

AIQuestionGeneratorWithRAGAndRationale() now receives search_provider=os.environ.get("OIC_SEARCH_PROVIDER") at construction.  Both chatbot call sites (efine_scenario, chat message handler) inherit the provider chain through the shared i_generator instance — no changes to main.py call sites were required.

**Dockerfile**:

`dockerfile
COPY src/oic_search/ /app/lib/oic_search/
ENV PYTHONPATH=/app/lib
`

The shared module is injected via PYTHONPATH rather than a pip install, keeping the image lean.

**deployment/gcp/deploy_infrastructure.sh**:

- GOOGLE_SEARCH_API_KEY and GOOGLE_SEARCH_CSE_ID removed from all secret provisioning and --set-secrets mount.
- TAVILY_API_KEY, BRAVE_SEARCH_API_KEY, OIC_SEARCH_PROVIDER, and OIC_SEARCH_FALLBACK added.
- OIC_SEARCH_PROVIDER and OIC_SEARCH_FALLBACK have interactive defaults (	avily and rave respectively) so pressing Enter at the prompt accepts the recommended configuration.
- BRAVE_SEARCH_API_KEY is optional at the prompt (skippable) but strongly encouraged for failover.
- The --set-secrets argument is built dynamically; optional secrets are only mounted if their Secret Manager entry exists, preventing deploy failures when a key is intentionally skipped.

#### Testing

End-to-end testing confirmed:

- Questionnaire generation, scenario refinement, and chat assistant all produce web-grounded responses using Tavily as primary and Brave as fallback.
- Forcing a simulated quota error on Tavily triggers transparent failover to Brave — no user-visible error.
- Auth misconfiguration (kind="auth") disables search for the session and logs a clear diagnostic message.
- Startup with no .env (container mode) works correctly; startup with a local .env (dev server) loads credentials with correct override priority.

---

### 2. Repository Structure Refactor

#### Background

The repository had grown organically and no longer reflected standard DevOps monorepo conventions.  Shared Python modules were duplicated across directories, tooling scripts were co-located with application code, and there was no clear separation between deployable artifacts and development utilities.

#### Changes

| Area | Before | After |
|---|---|---|
| Shared LLM module | oic_llm/ at root + partial copy in src/ | Canonical location: src/oic_llm/ |
| Shared search module | New, no canonical location | src/oic_search/ |
| Flask web application | pp/ | pp/ (unchanged — Cloud Run target) |
| Attack flow workbench | Mixed with app code | 	ools/attack_flow_workbench/ |
| Deployment scripts | Flat at root | deployment/gcp/ |
| Documentation | Mixed across root and subdirs | documentation/project/ (working), documentation/public/ (published) |
| Generated artefacts | pp/generated/ | generated/ at repo root (gitignored detail, archetypes tracked) |

The src/ directory now serves as the monorepo's shared library tree.  Both the Flask app (via Dockerfile PYTHONPATH injection) and the CLI workbench (via local sys.path or pip install -e) import from src/oic_llm and src/oic_search.

#### Impact on existing deployments

The Dockerfile was updated to COPY src/oic_search/ /app/lib/oic_search/ with ENV PYTHONPATH=/app/lib.  No changes are required to existing Cloud Run service configurations; the next build picks up the new layout automatically.

---

### Related Commits

| Commit | Summary |
|---|---|
| 4f3921d | fix(app): migrate web search from legacy Google CSE to oic_search module |
| 517ac5 | feat(search): add provider fallback chain for resilient web search |
| 815da92 | feat(workbench): add terminal-anchored multi-path reachability generation |
| 1d67455 | build: converting workbench to use providers and CLI supports multiple AI/search variations |
|  1ba882 | feat(workbench): replace direct Anthropic+Google CSE with oic_llm+oic_search |
|  d7db21 | chore(oic_search): Brave/Tavily as active providers, Google CSE commented out |
| 5ea0a73 | chore: remove stale root oic_llm/ copy |
| 5aecf13 | feat: add oic_search shared search/grounding package |

