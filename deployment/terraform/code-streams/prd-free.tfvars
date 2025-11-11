# Production Free Code Stream Configuration
# GCP Project: oic-prd-free
# Subscription: Free tier
# Purpose: Production workload on free tier

# Project Configuration
project_id          = "oic-prd-free"
region              = "northamerica-northeast1"

# Environment & Code Stream
environment         = "prd"
code_stream         = "prd-free"
subscription_tier   = "free"

# Resource Naming
service_account_name = "oic-rarag"
bucket_suffix        = "rarag-kb"
rag_corpus_name      = "oic-prd-free-rarag-kb"

# FinOps Tags - Cost Tracking
cost_center         = "revenue"
budget_category     = "medium"

# FinOps Tags - Ownership
team                = "platform"
owner               = "platform-team@example.com"

# FinOps Tags - Compliance
data_residency      = "canada"
compliance          = "pipeda"
