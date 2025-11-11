# Production Paid Code Stream Configuration
# GCP Project: oic-prd-paid
# Subscription: Paid/Premium tier
# Purpose: Revenue-generating production workload

# Project Configuration
project_id          = "oic-prd-paid"
region              = "northamerica-northeast1"

# Environment & Code Stream
environment         = "prd"
code_stream         = "prd-paid"
subscription_tier   = "paid"

# Resource Naming
service_account_name = "oic-rarag"
bucket_suffix        = "rarag-kb"
rag_corpus_name      = "oic-prd-paid-rarag-kb"

# FinOps Tags - Cost Tracking
cost_center         = "revenue"
budget_category     = "high"

# FinOps Tags - Ownership
team                = "platform"
owner               = "platform-team@example.com"

# FinOps Tags - Compliance
data_residency      = "canada"
compliance          = "pipeda"
