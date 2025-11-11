# FinOps Tagging Strategy for OpenImpactCascade

## Overview

Comprehensive cost tracking and resource tagging strategy for four code streams across multiple GCP projects with granular cost attribution for both GCP and external services.

---

## Code Streams

### 1. Production Paid (prod-paid)
- **GCP Project:** `oic-prod-paid`
- **Subscription:** Paid/Premium tier
- **Purpose:** Production workloads with paid features
- **Cost Center:** Revenue-generating
- **Budget:** High priority

### 2. Production Free (prod-free)
- **GCP Project:** `oic-prod-free`
- **Subscription:** Free tier
- **Purpose:** Production workloads on free tier
- **Cost Center:** Cost-optimized production
- **Budget:** Medium priority

### 3. Development Free (dev-free)
- **GCP Project:** `oic-dev-free`
- **Subscription:** Free tier
- **Purpose:** Development and testing
- **Cost Center:** Development
- **Budget:** Low priority

### 4. Testing Free (test-free)
- **GCP Project:** `oic-test-free`
- **Subscription:** Free tier
- **Purpose:** QA, integration testing, staging
- **Cost Center:** Quality assurance
- **Budget:** Low priority

---

## Standard Label Schema

### Required Labels (All Resources)

```hcl
labels = {
  # Core identification
  application     = "openimpactcascade"
  component       = "rag-engine|api-service|storage|compute"
  
  # Environment & Code Stream
  environment     = "prod|dev|test"
  code_stream     = "prod-paid|prod-free|dev-free|test-free"
  subscription    = "paid|free"
  
  # Cost tracking
  cost_center     = "revenue|development|qa|infrastructure"
  budget_category = "high|medium|low"
  
  # Ownership
  team            = "platform|data|ml|infrastructure"
  owner           = "email-or-id"
  
  # Lifecycle
  created_by      = "terraform|manual|script"
  managed_by      = "terraform"
  
  # Compliance
  data_residency  = "canada|us|global"
  compliance      = "pipeda|gdpr|none"
}
```

### Optional Labels

```hcl
labels = {
  # Feature tracking
  feature         = "rag|questionnaire|analysis|chat"
  
  # Version tracking
  version         = "v1-0-0"
  
  # Business tracking
  customer_tier   = "enterprise|professional|free"
  
  # Operational
  backup_policy   = "daily|weekly|none"
  retention_days  = "30|90|365"
}
```

---

## External Service Tagging

For services outside GCP (Anthropic, other frontier models), use application-level tags:

### Application Tags (Logged in Database/Files)

```json
{
  "request_id": "uuid",
  "timestamp": "2025-11-01T12:00:00Z",
  
  "code_stream": "prod-paid",
  "environment": "prod",
  "subscription": "paid",
  
  "service": "anthropic|openai|google-gemini|cohere",
  "model": "claude-3-5-sonnet|gpt-4|gemini-pro",
  "operation": "questionnaire|analysis|chat|embedding",
  
  "cost_tracking": {
    "tokens_input": 1000,
    "tokens_output": 500,
    "estimated_cost_usd": 0.015,
    "cost_center": "revenue",
    "budget_category": "high"
  },
  
  "user_context": {
    "user_id": "hashed-id",
    "session_id": "session-uuid",
    "customer_tier": "enterprise"
  }
}
```

---

## Resource Naming Convention

### Pattern
```
{project-prefix}-{environment}-{component}-{resource-type}
```

### Examples by Code Stream

**Production Paid:**
```
Service Account: oic-prod-paid-rarag@oic-prod-paid.iam.gserviceaccount.com
Bucket:          oic-prod-paid-rarag-kb
Corpus:          oic-prod-paid-rarag-kb
```

**Production Free:**
```
Service Account: oic-prod-free-rarag@oic-prod-free.iam.gserviceaccount.com
Bucket:          oic-prod-free-rarag-kb
Corpus:          oic-prod-free-rarag-kb
```

**Development Free:**
```
Service Account: oic-dev-free-rarag@oic-dev-free.iam.gserviceaccount.com
Bucket:          oic-dev-free-rarag-kb
Corpus:          oic-dev-free-rarag-kb
```

**Testing Free:**
```
Service Account: oic-test-free-rarag@oic-test-free.iam.gserviceaccount.com
Bucket:          oic-test-free-rarag-kb
Corpus:          oic-test-free-rarag-kb
```

---

## Terraform Variables by Code Stream

### Production Paid (terraform.tfvars)
```hcl
project_id          = "oic-prod-paid"
environment         = "prod"
code_stream         = "prod-paid"
subscription_tier   = "paid"

service_account_name = "oic-prod-paid-rarag"
bucket_suffix        = "rarag-kb"
rag_corpus_name      = "oic-prod-paid-rarag-kb"

cost_center         = "revenue"
budget_category     = "high"
team                = "platform"
data_residency      = "canada"
```

### Production Free (terraform.tfvars)
```hcl
project_id          = "oic-prod-free"
environment         = "prod"
code_stream         = "prod-free"
subscription_tier   = "free"

service_account_name = "oic-prod-free-rarag"
bucket_suffix        = "rarag-kb"
rag_corpus_name      = "oic-prod-free-rarag-kb"

cost_center         = "revenue"
budget_category     = "medium"
team                = "platform"
data_residency      = "canada"
```

### Development Free (terraform.tfvars)
```hcl
project_id          = "oic-dev-free"
environment         = "dev"
code_stream         = "dev-free"
subscription_tier   = "free"

service_account_name = "oic-dev-free-rarag"
bucket_suffix        = "rarag-kb"
rag_corpus_name      = "oic-dev-free-rarag-kb"

cost_center         = "development"
budget_category     = "low"
team                = "platform"
data_residency      = "canada"
```

### Testing Free (terraform.tfvars)
```hcl
project_id          = "oic-test-free"
environment         = "test"
code_stream         = "test-free"
subscription_tier   = "free"

service_account_name = "oic-test-free-rarag"
bucket_suffix        = "rarag-kb"
rag_corpus_name      = "oic-test-free-rarag-kb"

cost_center         = "qa"
budget_category     = "low"
team                = "platform"
data_residency      = "canada"
```

---

## Cost Tracking Implementation

### 1. GCP Resources (via Labels)

All GCP resources automatically tagged via Terraform:
- Service Accounts
- GCS Buckets
- Compute instances
- Cloud Run services
- Any other GCP resources

**Query costs by code stream:**
```bash
# BigQuery SQL for cost analysis
SELECT
  labels.value AS code_stream,
  SUM(cost) AS total_cost,
  service.description AS service
FROM `project.dataset.gcp_billing_export`
WHERE labels.key = 'code_stream'
GROUP BY code_stream, service
ORDER BY total_cost DESC
```

### 2. External API Calls (via Application Logging)

**Log Structure:**
```python
# api_cost_tracker.py
import json
from datetime import datetime
from typing import Dict, Any

class APICostTracker:
    def __init__(self, code_stream: str, environment: str):
        self.code_stream = code_stream
        self.environment = environment
        
    def log_api_call(
        self,
        service: str,
        model: str,
        operation: str,
        tokens_input: int,
        tokens_output: int,
        cost_usd: float,
        metadata: Dict[str, Any] = None
    ):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "code_stream": self.code_stream,
            "environment": self.environment,
            "subscription": self._get_subscription_tier(),
            
            "service": service,
            "model": model,
            "operation": operation,
            
            "usage": {
                "tokens_input": tokens_input,
                "tokens_output": tokens_output,
                "tokens_total": tokens_input + tokens_output
            },
            
            "cost": {
                "amount_usd": cost_usd,
                "cost_center": self._get_cost_center(),
                "budget_category": self._get_budget_category()
            },
            
            "metadata": metadata or {}
        }
        
        # Write to structured log
        self._write_log(log_entry)
        
        # Optionally send to BigQuery for analysis
        self._send_to_bigquery(log_entry)
```

### 3. Cost Allocation Matrix

| Code Stream | GCP Project | Subscription | Cost Center | Budget | Priority |
|-------------|-------------|--------------|-------------|--------|----------|
| prod-paid | oic-prod-paid | Paid | Revenue | High | 1 |
| prod-free | oic-prod-free | Free | Revenue | Medium | 2 |
| dev-free | oic-dev-free | Free | Development | Low | 3 |
| test-free | oic-test-free | Free | QA | Low | 4 |

---

## Budget Allocation

### Recommended Monthly Budgets

**Production Paid (prod-paid):**
- GCP: $500-2000/month
- Anthropic API: $1000-5000/month
- Other APIs: $200-500/month
- **Total:** $1700-7500/month

**Production Free (prod-free):**
- GCP: $50-200/month
- Anthropic API: $200-1000/month
- Other APIs: $50-100/month
- **Total:** $300-1300/month

**Development Free (dev-free):**
- GCP: $20-100/month
- Anthropic API: $50-200/month
- Other APIs: $10-50/month
- **Total:** $80-350/month

**Testing Free (test-free):**
- GCP: $10-50/month
- Anthropic API: $20-100/month
- Other APIs: $5-20/month
- **Total:** $35-170/month

---

## Reporting Queries

### GCP Cost by Code Stream
```sql
SELECT
  labels.value AS code_stream,
  labels.value AS environment,
  service.description,
  SUM(cost) AS total_cost,
  SUM(usage.amount) AS usage_amount,
  usage.unit
FROM `project.dataset.gcp_billing_export`
WHERE labels.key IN ('code_stream', 'environment')
  AND _PARTITIONTIME >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
GROUP BY code_stream, environment, service.description, usage.unit
ORDER BY total_cost DESC
```

### External API Cost by Code Stream
```sql
SELECT
  code_stream,
  service,
  model,
  COUNT(*) AS request_count,
  SUM(usage.tokens_total) AS total_tokens,
  SUM(cost.amount_usd) AS total_cost_usd,
  AVG(cost.amount_usd) AS avg_cost_per_request
FROM `project.dataset.api_cost_logs`
WHERE DATE(timestamp) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY code_stream, service, model
ORDER BY total_cost_usd DESC
```

### Combined Cost Report
```sql
WITH gcp_costs AS (
  SELECT
    labels.value AS code_stream,
    'GCP' AS source,
    service.description AS service,
    SUM(cost) AS cost_usd
  FROM `project.dataset.gcp_billing_export`
  WHERE labels.key = 'code_stream'
  GROUP BY code_stream, service
),
api_costs AS (
  SELECT
    code_stream,
    'External API' AS source,
    CONCAT(service, ' - ', model) AS service,
    SUM(cost.amount_usd) AS cost_usd
  FROM `project.dataset.api_cost_logs`
  GROUP BY code_stream, service, model
)
SELECT * FROM gcp_costs
UNION ALL
SELECT * FROM api_costs
ORDER BY code_stream, cost_usd DESC
```

---

## Implementation Checklist

### Infrastructure
- [ ] Update Terraform variables with FinOps tags
- [ ] Apply naming convention to all resources
- [ ] Add labels to service accounts
- [ ] Add labels to GCS buckets
- [ ] Add labels to compute resources
- [ ] Enable GCP billing export to BigQuery

### Application
- [ ] Implement APICostTracker class
- [ ] Add cost tracking to Anthropic API calls
- [ ] Add cost tracking to other frontier model calls
- [ ] Create BigQuery dataset for API cost logs
- [ ] Set up log streaming to BigQuery

### Monitoring
- [ ] Create cost dashboards per code stream
- [ ] Set up budget alerts
- [ ] Configure anomaly detection
- [ ] Schedule weekly cost reports

### Documentation
- [ ] Document tagging standards
- [ ] Create runbook for cost analysis
- [ ] Train team on cost tracking
- [ ] Establish cost review cadence

---

## Best Practices

### 1. Consistent Tagging
- Always use lowercase for label values
- Use hyphens for multi-word values
- Never use spaces or special characters
- Validate labels in CI/CD

### 2. Cost Attribution
- Tag at resource creation time
- Never modify tags manually
- Use Terraform for all infrastructure
- Log all external API calls

### 3. Regular Reviews
- Weekly cost reviews per code stream
- Monthly budget vs actual analysis
- Quarterly optimization opportunities
- Annual budget planning

### 4. Automation
- Automate tag validation
- Automate cost reports
- Automate budget alerts
- Automate anomaly detection

---

## Migration Guide

### Existing Resources

**Step 1: Inventory**
```bash
# List all resources without proper tags
gcloud asset search-all-resources \
  --scope=projects/PROJECT_ID \
  --query="labels.code_stream:*" \
  --format=json
```

**Step 2: Tag Existing Resources**
```bash
# Update bucket labels
gsutil label ch -l code_stream:prod-paid gs://BUCKET_NAME
gsutil label ch -l environment:prod gs://BUCKET_NAME
gsutil label ch -l cost_center:revenue gs://BUCKET_NAME
```

**Step 3: Verify**
```bash
# Check labels
gsutil ls -L -b gs://BUCKET_NAME | grep Labels
```

---

**Status:** Production Ready  
**Version:** 1.0  
**Last Updated:** November 2025
