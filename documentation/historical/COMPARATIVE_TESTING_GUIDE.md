# Comparative Testing Guide: Three RAG Approaches

## Overview

This guide explains how to run and compare three different approaches to AI-powered risk assessment questionnaire generation:

1. **Version 1 (v1-web)**: LLM with Web Search Only (No RAG)
2. **Version 2 (v2-rag)**: RAG + LLM with Web Search
3. **Version 3 (v3-cot)**: RAG with Chain of Thought

---

## Quick Start

### 1. Start All Three Versions

**Terminal 1 - Version 1 (Port 8000):**
```bash
cd ~/oic/oic_v2/OIC_SBX
source ~/oic/ocivenv/bin/activate
python flask_app_chat_v1_websearch.py
```

**Terminal 2 - Version 2 (Port 8080):**
```bash
cd ~/oic/oic_v2/OIC_SBX
source ~/oic/ocivenv/bin/activate
python flask_app_chat_v2_rag.py
```

**Terminal 3 - Version 3 (Port 8888):**
```bash
cd ~/oic/oic_v2/OIC_SBX
source ~/oic/ocivenv/bin/activate
python flask_app_chat_v3_rag_cot.py
```

### 2. Access the Applications

- **Version 1**: http://localhost:8000
- **Version 2**: http://localhost:8080
- **Version 3**: http://localhost:8888

---

## Version Details

### Version 1: LLM with Web Search Only
- **Port**: 8000
- **Code Generator ID**: `v1-web`
- **User ID Format**: `eval-v1-web-XXXXXXXXXXXX`
- **Approach**: Uses Claude with web search capabilities only
- **File**: `flask_app_chat_v1_websearch.py`
- **Generator**: `ai_question_generator.py`

**Characteristics:**
- No RAG corpus access
- Relies entirely on Claude's web search for current information
- Baseline for comparison
- Fastest response time (no RAG retrieval overhead)

### Version 2: RAG + LLM with Web Search
- **Port**: 8080
- **Code Generator ID**: `v2-rag`
- **User ID Format**: `eval-v2-rag-XXXXXXXXXXXX`
- **Approach**: Retrieves grounding context from RAG corpus, then uses Claude with web search
- **File**: `flask_app_chat_v2_rag.py`
- **Generator**: `ai_question_generator_with_rag.py`

**Characteristics:**
- Retrieves 3-5 relevant documents from RAG corpus
- Provides grounding context to Claude
- Still uses web search for current events
- Combines authoritative knowledge base with real-time information

### Version 3: RAG with Chain of Thought
- **Port**: 8888
- **Code Generator ID**: `v3-cot`
- **User ID Format**: `eval-v3-cot-XXXXXXXXXXXX`
- **Approach**: RAG retrieval with structured Chain of Thought reasoning
- **File**: `flask_app_chat_v3_rag_cot.py`
- **Generator**: `ai_question_generator_with_rag_cot.py`

**Characteristics:**
- Retrieves 3-5 relevant documents from RAG corpus
- Uses structured reasoning process (analyze → review → apply → synthesize → advise)
- Lower temperature (0.2) for more focused reasoning
- Higher max tokens (3072) to accommodate reasoning steps
- Explicit CoT prompting for transparent reasoning

---

## User ID Tracking

Each version uses a unique prefix in the user ID to track costs separately:

| Version | Prefix | Example User ID |
|---------|--------|-----------------|
| v1-web  | `v1-web` | `eval-v1-web-a1b2c3d4e5f6` |
| v2-rag  | `v2-rag` | `eval-v2-rag-7g8h9i0j1k2l` |
| v3-cot  | `v3-cot` | `eval-v3-cot-m3n4o5p6q7r8` |

### Tracking in Logs

All API calls are logged in `./logs/api_calls.jsonl` with the following structure:

```json
{
  "timestamp": "2025-11-02T14:30:00.123456",
  "user_id": "eval-v2-rag-a1b2c3d4e5f6",
  "hashed_user_id": "sha256_hash...",
  "api_type": "questionnaire_generation",
  "model": "claude-sonnet-4-20250514",
  "request_id": "msg_abc123",
  "metadata": {
    "version": "v2-rag",
    "industry": "Healthcare",
    "region": "Canada",
    "rag_contexts_retrieved": 5,
    "rag_enabled": true
  }
}
```

### Cost Analysis Queries

**Count API calls by version:**
```bash
grep '"version": "v1-web"' logs/api_calls.jsonl | wc -l
grep '"version": "v2-rag"' logs/api_calls.jsonl | wc -l
grep '"version": "v3-cot"' logs/api_calls.jsonl | wc -l
```

**Extract user IDs by version:**
```bash
grep -o '"user_id": "eval-v1-web-[^"]*"' logs/api_calls.jsonl | sort | uniq
grep -o '"user_id": "eval-v2-rag-[^"]*"' logs/api_calls.jsonl | sort | uniq
grep -o '"user_id": "eval-v3-cot-[^"]*"' logs/api_calls.jsonl | sort | uniq
```

**Get Anthropic request IDs for cost tracking:**
```bash
# Version 1
grep '"version": "v1-web"' logs/api_calls.jsonl | grep -o '"request_id": "[^"]*"'

# Version 2
grep '"version": "v2-rag"' logs/api_calls.jsonl | grep -o '"request_id": "[^"]*"'

# Version 3
grep '"version": "v3-cot"' logs/api_calls.jsonl | grep -o '"request_id": "[^"]*"'
```

---

## Testing Methodology

### Recommended Test Scenarios

For fair comparison, test each version with identical scenarios:

#### Scenario 1: Healthcare - Canada
```
Industry: Healthcare
Region: Canada
Organization Size: 500 employees
```

#### Scenario 2: Financial Services - United States
```
Industry: Financial Services
Region: United States
Organization Size: 1000 employees
```

#### Scenario 3: Manufacturing - Europe
```
Industry: Manufacturing
Region: Europe
Organization Size: 250 employees
```

### Test Process

1. **Generate Questionnaire**: Use the same industry/region/size for all three versions
2. **Answer Questions**: Provide identical answers across versions
3. **Use Chat Assistant**: Ask the same questions in each version's chat
4. **Record Observations**: Note response quality, speed, accuracy

### Metrics to Compare

#### Qualitative Metrics
- **Accuracy**: Are the threats and recommendations factually correct?
- **Relevance**: How well does the content match the industry/region?
- **Specificity**: Are examples concrete or generic?
- **Source Quality**: Are sources authoritative and current?
- **Reasoning Quality**: (v3 only) Is the reasoning process helpful?

#### Quantitative Metrics
- **Response Time**: How long to generate questionnaire?
- **API Calls**: How many Claude API calls per session?
- **Token Usage**: Input and output tokens (from Anthropic dashboard)
- **Cost**: Total cost per session (from Anthropic dashboard)
- **RAG Retrieval**: (v2/v3) Number of contexts retrieved

#### User Experience Metrics
- **Ease of Use**: Is the interface intuitive?
- **Chat Quality**: Are chat responses helpful?
- **Error Rate**: Any failures or retries?

---

## Health Check Endpoints

Each version has a health check endpoint showing its configuration:

```bash
# Version 1
curl http://localhost:8000/health

# Version 2
curl http://localhost:8080/health

# Version 3
curl http://localhost:8888/health
```

**Example Response:**
```json
{
  "status": "healthy",
  "version": "v2-rag",
  "port": 8080,
  "ai_available": true,
  "approach": "RAG + LLM with Web Search",
  "rag_enabled": true,
  "rag_status": {
    "enabled": true,
    "corpus_found": true,
    "corpus_resource_name": "projects/oicsbx/locations/northamerica-northeast1/ragCorpora/6917529027641081856"
  }
}
```

---

## Cost Tracking with Anthropic Dashboard

### 1. Access Anthropic Console
https://console.anthropic.com/

### 2. View Usage by User ID

Navigate to: **Usage** → **API Logs**

Filter by user ID prefix:
- `eval-v1-web-*` for Version 1
- `eval-v2-rag-*` for Version 2
- `eval-v3-cot-*` for Version 3

### 3. Export Cost Data

Use the Anthropic API to get detailed usage:

```python
import anthropic
import os
from datetime import datetime, timedelta

client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))

# Get usage for last 7 days
end_date = datetime.now()
start_date = end_date - timedelta(days=7)

# Note: Actual API endpoint may vary - check Anthropic docs
# This is conceptual code
```

### 4. Calculate Costs

**Claude Sonnet 4 Pricing (as of Nov 2024):**
- Input: $3.00 per million tokens
- Output: $15.00 per million tokens

**Example Calculation:**
```
Version 1 Session:
- Input tokens: 5,000
- Output tokens: 2,000
- Cost: (5000 * $3.00 / 1M) + (2000 * $15.00 / 1M) = $0.015 + $0.030 = $0.045

Version 2 Session (with RAG):
- Input tokens: 8,000 (includes RAG context)
- Output tokens: 2,000
- Cost: (8000 * $3.00 / 1M) + (2000 * $15.00 / 1M) = $0.024 + $0.030 = $0.054

Version 3 Session (with CoT):
- Input tokens: 8,000 (includes RAG context)
- Output tokens: 3,000 (more detailed reasoning)
- Cost: (8000 * $3.00 / 1M) + (3000 * $15.00 / 1M) = $0.024 + $0.045 = $0.069
```

---

## Expected Differences

### Token Usage

| Version | Expected Input Tokens | Expected Output Tokens | Notes |
|---------|----------------------|------------------------|-------|
| v1-web  | 3,000 - 5,000 | 1,500 - 2,500 | Baseline |
| v2-rag  | 5,000 - 8,000 | 1,500 - 2,500 | +RAG context |
| v3-cot  | 5,000 - 8,000 | 2,000 - 3,500 | +CoT reasoning |

### Response Characteristics

**Version 1 (Web Search Only):**
- ✅ Fast responses
- ✅ Current information via web search
- ⚠️ May lack depth in specialized topics
- ⚠️ Dependent on web search quality

**Version 2 (RAG + Web Search):**
- ✅ Authoritative grounding from knowledge base
- ✅ Current information via web search
- ✅ Better specificity for known topics
- ⚠️ Slightly slower (RAG retrieval overhead)
- ⚠️ Higher token usage

**Version 3 (RAG + CoT):**
- ✅ Structured, transparent reasoning
- ✅ Authoritative grounding from knowledge base
- ✅ More detailed explanations
- ✅ Better for complex questions
- ⚠️ Highest token usage
- ⚠️ Slower responses

---

## Troubleshooting

### Port Already in Use

```bash
# Find process using port
lsof -i :8000
lsof -i :8080
lsof -i :8888

# Kill process
kill -9 <PID>
```

### RAG Not Available (v2/v3)

Check RAG status:
```bash
curl http://localhost:8080/health | jq '.rag_status'
curl http://localhost:8888/health | jq '.rag_status'
```

If RAG is disabled:
1. Verify `GOOGLE_CLOUD_PROJECT` environment variable is set
2. Verify `VERTEX_RAG_CORPUS` environment variable is set
3. Check authentication: `gcloud auth application-default login`
4. Verify corpus exists: `python vertex_rag_complete.py`

### API Key Issues

Ensure `ANTHROPIC_API_KEY` is set:
```bash
echo $ANTHROPIC_API_KEY
```

If not set:
```bash
export ANTHROPIC_API_KEY="your-api-key-here"
```

---

## Data Collection Template

Use this template to record your observations:

```markdown
## Test Session: [Date/Time]

### Scenario
- Industry: _______________
- Region: _______________
- Organization Size: _______________

### Version 1 (v1-web) - Port 8000
- User ID: _______________
- Generation Time: _____ seconds
- Questionnaire Quality: ⭐⭐⭐⭐⭐
- Chat Response Quality: ⭐⭐⭐⭐⭐
- Observations:
  - 
  - 

### Version 2 (v2-rag) - Port 8080
- User ID: _______________
- Generation Time: _____ seconds
- RAG Contexts Retrieved: _____
- Questionnaire Quality: ⭐⭐⭐⭐⭐
- Chat Response Quality: ⭐⭐⭐⭐⭐
- Observations:
  - 
  - 

### Version 3 (v3-cot) - Port 8888
- User ID: _______________
- Generation Time: _____ seconds
- RAG Contexts Retrieved: _____
- Questionnaire Quality: ⭐⭐⭐⭐⭐
- Chat Response Quality: ⭐⭐⭐⭐⭐
- Reasoning Quality: ⭐⭐⭐⭐⭐
- Observations:
  - 
  - 

### Cost Comparison (from Anthropic Dashboard)
- Version 1 Total Cost: $_______________
- Version 2 Total Cost: $_______________
- Version 3 Total Cost: $_______________

### Winner
Best Overall: _______________
Best Value: _______________
Best Quality: _______________
```

---

## Analysis Scripts

### Extract Cost Data from Logs

```python
#!/usr/bin/env python3
"""Analyze API call logs by version."""

import json
from collections import defaultdict
from pathlib import Path

def analyze_logs(log_file='./logs/api_calls.jsonl'):
    """Analyze API calls by version."""
    
    stats = defaultdict(lambda: {
        'count': 0,
        'questionnaire_gen': 0,
        'chat_assist': 0,
        'users': set()
    })
    
    with open(log_file, 'r') as f:
        for line in f:
            try:
                entry = json.loads(line)
                version = entry.get('metadata', {}).get('version', 'unknown')
                api_type = entry.get('api_type', 'unknown')
                user_id = entry.get('user_id', 'unknown')
                
                stats[version]['count'] += 1
                stats[version]['users'].add(user_id)
                
                if api_type == 'questionnaire_generation':
                    stats[version]['questionnaire_gen'] += 1
                elif api_type == 'chat_assist':
                    stats[version]['chat_assist'] += 1
                    
            except json.JSONDecodeError:
                continue
    
    # Print results
    print("="*60)
    print("API CALL ANALYSIS BY VERSION")
    print("="*60)
    
    for version in sorted(stats.keys()):
        s = stats[version]
        print(f"\n{version}:")
        print(f"  Total API Calls: {s['count']}")
        print(f"  Questionnaire Generation: {s['questionnaire_gen']}")
        print(f"  Chat Assistance: {s['chat_assist']}")
        print(f"  Unique Users: {len(s['users'])}")
        print(f"  User IDs: {', '.join(sorted(s['users']))}")

if __name__ == '__main__':
    analyze_logs()
```

Save as `analyze_costs.py` and run:
```bash
python analyze_costs.py
```

---

## Summary

This comparative testing setup allows you to:

1. ✅ Run three different approaches simultaneously
2. ✅ Track costs separately via user ID prefixes
3. ✅ Compare response quality and accuracy
4. ✅ Measure performance differences
5. ✅ Analyze token usage and costs
6. ✅ Make data-driven decisions about which approach to use

**Next Steps:**
1. Start all three versions
2. Run identical test scenarios
3. Collect qualitative and quantitative data
4. Analyze costs from Anthropic dashboard
5. Choose the best approach for your use case
