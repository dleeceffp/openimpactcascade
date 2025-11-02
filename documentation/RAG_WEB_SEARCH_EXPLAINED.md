# ai_question_generator_with_rag.py - Detailed Explanation

## 🎯 Overview

This file integrates Vertex AI RAG grounding into the questionnaire generation process, creating a **two-stage information gathering approach**:

1. **Stage 1:** RAG retrieval (from your private knowledge base)
2. **Stage 2:** Web search (for current/conflicting guidance)

---

## 📊 How It Works - Step by Step

### Step 1: RAG Grounding (Lines 110-145)

```python
# Retrieve context from RAG corpus FIRST
rag_contexts = self.rag_engine.retrieve_risk_identification_context(
    industry=industry,
    region=region,
    organization_size=organization_size,
    max_results=5
)
```

**What happens:**
- Queries your private knowledge base in Vertex AI
- Retrieves 5 most relevant documents
- Examples: CISA advisories, MITRE techniques, internal threat reports

### Step 2: Inject RAG Context (Lines 234-241)

```python
if grounding_context:
    message_parts.append(grounding_context)
    message_parts.append("="*70)
    message_parts.append("IMPORTANT: The above grounding context contains VERIFIED, authoritative information.")
    message_parts.append("Use this context as your PRIMARY source for threat intelligence.")
    message_parts.append("="*70)
```

**What happens:**
- RAG context is placed at the TOP of the message
- Marked as "VERIFIED, authoritative information"
- Designated as "PRIMARY source"

### Step 3: Web Search Instructions (Lines 250-258)

**THIS IS WHERE WEB SEARCH IS TRIGGERED:**

```python
**Instructions:**
1. If grounding context is provided above, USE IT as your primary source
2. Search the web for additional current threat intelligence if needed  ⭐ KEY LINE
3. Generate 3-5 threat scenarios relevant to this industry/region
4. Include PERT estimates for Loss Event Frequency and Loss Magnitude
5. Reference specific MITRE ATT&CK techniques
6. Document all sources in metadata
```

**Line 252 is the explicit web search instruction:**
> "2. Search the web for additional current threat intelligence if needed"

---

## 🔍 Web Search Trigger Conditions

### When Claude Will Use Web Search

The system prompt (lines 67-81) and user message work together to trigger web search when:

#### 1. **Conflicting Information**
```python
# Line 73-74 in system prompt:
"If grounding context conflicts with general knowledge, PREFER grounding sources"
```
- Claude detects conflict between RAG sources and its training data
- Uses web search to find current authoritative resolution

#### 2. **Current Events/Recent Threats**
```python
# Line 252 in user message:
"Search the web for additional current threat intelligence if needed"
```
- RAG corpus might not have yesterday's threat advisory
- Claude searches for breaking threats/vulnerabilities

#### 3. **Data Limitations**
```python
# Line 80 in system prompt:
"Be transparent about data limitations"
```
- RAG context is sparse or outdated
- Claude uses web search to fill gaps

#### 4. **Verification Requirements**
```python
# Lines 77-79 in system prompt:
"All threat scenarios must reference VERIFIED sources (either grounding context or web search)"
"MITRE ATT&CK technique IDs must be accurate and relevant"
"Statistics must be traceable to authoritative reports"
```
- Claude needs to verify specific claims
- Uses web search for current statistics

---

## 📋 System Prompt Instructions (Lines 67-84)

### Critical RAG + Web Search Instructions

```python
**CRITICAL: Use Grounding Context**

When grounding context is provided from authoritative knowledge sources:
1. PRIORITIZE information from grounding sources over general knowledge      # RAG first
2. CITE specific sources when making claims (e.g., "According to CISA...")  # Attribution
3. VERIFY that grounding sources are relevant to the industry/region         # Relevance check
4. If grounding context conflicts with general knowledge, PREFER grounding   # Conflict resolution
5. Document which sources informed your threat scenarios                     # Transparency

**Quality Requirements:**
- All threat scenarios must reference VERIFIED sources (either grounding context or web search)  ⭐
- MITRE ATT&CK technique IDs must be accurate and relevant
- Statistics must be traceable to authoritative reports
- Be transparent about data limitations
```

**Key Points:**
- **Line 77:** "VERIFIED sources (either grounding context **or web search**)" ⭐
  - This explicitly allows/encourages web search as verification method
- **Line 80:** "Be transparent about data limitations"
  - Triggers web search when RAG context is insufficient

---

## 🎭 The Two-Stage Strategy in Action

### Example: Healthcare Ransomware Query

#### Stage 1: RAG Grounding
```
Query: Healthcare + Canada + ransomware

RAG Returns:
1. CISA Advisory AA24-242A (2024-08-29) - Relevance: 0.85
2. Healthcare Breach Report 2023 - Relevance: 0.78
3. MITRE T1486 (Ransomware) - Relevance: 0.72
```

#### Stage 2: Claude Decision Process

**Scenario A: RAG is Sufficient**
```
Claude thinks: "RAG context has recent CISA advisory from August 2024,
specific to healthcare in North America. This is current and authoritative.
I'll use this as primary source. No web search needed."

Output: Uses CISA AA24-242A as main source
```

**Scenario B: RAG Needs Supplement**
```
Claude thinks: "RAG context is from August 2024, but today is November 2024.
There may be newer advisories. The instruction says 'additional CURRENT threat
intelligence if needed.' I should search for recent threats."

Claude searches: "healthcare ransomware November 2024 CISA Canada"

Output: Combines RAG context + web search results
```

**Scenario C: RAG Has Conflict**
```
Claude thinks: "RAG context says ransomware frequency is X, but my training
data says Y. The system prompt says 'If grounding context conflicts with
general knowledge, PREFER grounding sources.' But I should verify with
current web data to resolve this."

Claude searches: "healthcare ransomware frequency 2024 statistics"

Output: Uses RAG as primary, cites web search for verification
```

---

## 💡 Key Design Decisions

### 1. RAG Context Position (Lines 234-241)
**Decision:** Place RAG context at the BEGINNING of the message

**Why:**
- Primacy effect: First information carries more weight
- Clearly marked as "VERIFIED, authoritative"
- Separated by visual markers (======)

### 2. Web Search as "Additional" (Line 252)
**Decision:** "additional current threat intelligence **if needed**"

**Why:**
- Not mandatory (avoids unnecessary searches)
- Conditional on need (gaps, conflicts, currency)
- Cost-effective (RAG is free, web search has limits)

### 3. Source Documentation (Lines 183-190)
**Decision:** Track and include RAG sources in metadata

**Why:**
```python
questionnaire['metadata']['rag_grounding_enabled'] = bool(grounding_context)
questionnaire['metadata']['rag_sources_count'] = len(rag_sources_used)
questionnaire['metadata']['rag_sources'] = rag_sources_used
```
- Transparency for users
- Audit trail for compliance
- Quality assurance

---

## 🔧 How to Modify Web Search Behavior

### Make Web Search More Aggressive

**Current (lines 251-252):**
```python
2. Search the web for additional current threat intelligence if needed
```

**More Aggressive:**
```python
2. ALWAYS search the web for the LATEST threat intelligence from the past 30 days
3. Compare web search results with RAG grounding context
4. If web search reveals newer threats, PRIORITIZE them over RAG context
5. Document any discrepancies between RAG and web sources
```

### Make Web Search More Conservative

**Current:**
```python
2. Search the web for additional current threat intelligence if needed
```

**More Conservative:**
```python
2. Only search the web if:
   - RAG context is older than 6 months
   - RAG context has no relevant information for the industry/region
   - RAG context explicitly indicates a need for current data
3. Prefer RAG context even if slightly outdated (e.g., 3-6 months old)
```

### Add Specific Search Triggers

**Enhanced (add to line 252):**
```python
2. Search the web for current threat intelligence in these specific cases:
   - Breaking threats/0-days from the last 7 days
   - Regional advisories not in RAG context
   - Statistical updates (incident rates, breach costs)
   - New MITRE techniques published after RAG corpus date
   - Regulatory changes (GDPR, HIPAA updates)
3. When searching, focus on authoritative sources: CISA, MITRE, vendor advisories
```

---

## 📊 Comparison: With vs Without RAG

### Without RAG (Original)
```python
Claude relies on:
1. Training data (cutoff: January 2025)
2. Web search for current info
3. General cybersecurity knowledge

Limitations:
- No access to private/paywalled documents
- Must search web for everything
- No organizational knowledge
```

### With RAG (This File)
```python
Claude relies on:
1. RAG grounding context (your private corpus) ⭐ FIRST
2. Training data (general knowledge)
3. Web search (only when needed) ⭐ SUPPLEMENTARY

Benefits:
+ Access to private documents
+ Faster (RAG retrieval < 2 sec)
+ More authoritative (your curated sources)
+ Cost-effective (fewer web searches)
+ Consistent (same corpus for all queries)
```

---

## 🎯 Real-World Flow Example

### Query: "Generate questionnaire for Healthcare in Canada"

**Step 1: RAG Retrieval** (Lines 114-145)
```
Searching corpus: "healthcare canada ransomware threats 2024"
Found 5 documents:
1. CISA AA24-242A (Aug 2024) - 0.85 relevance
2. Canadian Cyber Threat Assessment 2023-2024 - 0.82 relevance
3. Healthcare Breach Report 2023 - 0.78 relevance
4. MITRE T1486 (Ransomware) - 0.72 relevance
5. HIPAA Security Framework - 0.68 relevance
```

**Step 2: Context Injection** (Lines 234-241)
```
Message to Claude:

**Grounding Context from Authoritative Knowledge Base:**

**Source 1** (Relevance: 0.85):
- Source: gs://dev-rarag-kb/threat_intelligence/cisa_advisories/AA24-242A.pdf
- Content: CISA Alert AA24-242A: Ransomware Threats to Healthcare Sector...

[4 more sources...]

======================================================================
IMPORTANT: The above grounding context contains VERIFIED, authoritative information.
Use this context as your PRIMARY source for threat intelligence.
======================================================================

**Instructions:**
1. If grounding context is provided above, USE IT as your primary source
2. Search the web for additional current threat intelligence if needed  ⭐
3. Generate 3-5 threat scenarios...
```

**Step 3: Claude's Decision Process**
```
Claude analyzes:
- RAG context is from August 2024 (3 months old)
- Covers healthcare ransomware thoroughly
- Canadian threat assessment is comprehensive
- Has specific MITRE techniques

Claude decides:
✓ Use RAG context as primary source
✓ Search web for "healthcare ransomware November 2024" for CURRENT threats
✓ Combine RAG foundation + web updates
```

**Step 4: Generation**
```
Claude generates questionnaire:
- Threat Scenario 1: Based on CISA AA24-242A (RAG)
  + Updated with Nov 2024 Lockbit 3.0 variant (Web Search)
  
- Threat Scenario 2: Based on Canadian Threat Assessment (RAG)
  + Updated with recent Quebec healthcare incidents (Web Search)
  
- Threat Scenario 3: Based on MITRE T1486 (RAG)
  + Updated with 2024 detection methods (Web Search)
```

---

## 🔍 How to Verify Web Search is Working

### Check Claude's Response

Look for these indicators that web search was used:

1. **Temporal References**
```json
"threat_scenarios": [
  {
    "title": "Ransomware Attack (LockBit 3.0 - November 2024 variant)",
    "source": "CISA AA24-242A, updated with November 2024 threat intelligence"
  }
]
```

2. **Current Statistics**
```json
"loss_magnitude": {
  "description": "According to October 2024 IBM Cost of Data Breach Report, healthcare breaches average $10.93M"
}
```

3. **Recent Events**
```json
"likelihood_reasoning": "Based on Q4 2024 CISA advisories, ransomware attacks on healthcare increased 23% year-over-year"
```

4. **Metadata Sources**
```json
"metadata": {
  "sources": [
    "CISA AA24-242A (RAG grounding)",
    "IBM Cost of Data Breach Report 2024 (web search)",
    "MITRE ATT&CK T1486 (RAG grounding)",
    "Healthcare Cybersecurity Coordination Center Nov 2024 Alert (web search)"
  ]
}
```

---

## ✅ Summary

### Where Web Search Instructions Are

**Primary Location (Line 252):**
```python
"2. Search the web for additional current threat intelligence if needed"
```

**Supporting Location (Line 77):**
```python
"All threat scenarios must reference VERIFIED sources (either grounding context or web search)"
```

### How It Works

1. **RAG First:** Retrieve from private corpus
2. **Inject Context:** Place RAG sources at top of prompt
3. **Instruct Search:** Tell Claude to supplement with web search if needed
4. **Quality Check:** Require verified sources (RAG or web)
5. **Track Sources:** Document what was used in metadata

### Why This Design

- **Efficient:** Uses free RAG before paid web search
- **Authoritative:** Prioritizes curated internal sources
- **Current:** Supplements with latest web intelligence
- **Flexible:** "if needed" allows Claude to decide
- **Transparent:** Tracks which sources were used

---

*This creates a hybrid approach: Your private knowledge base provides the foundation, and web search adds the cutting-edge current intelligence!*
