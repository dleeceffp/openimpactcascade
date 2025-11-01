# Development Free Code Stream Configuration
# GCP Project: oic-dev-free
# Subscription: Free tier
# Purpose: Development and testing

# Project Configuration
project_id          = "oic-dev-free"
region              = "northamerica-northeast1"

# Environment & Code Stream
environment         = "dev"
code_stream         = "dev-free"
subscription_tier   = "free"

# Resource Naming
service_account_name = "oic-rarag"
bucket_suffix        = "rarag-kb"
rag_corpus_name      = "oic-dev-free-rarag-kb"

# FinOps Tags - Cost Tracking
cost_center         = "development"
budget_category     = "low"

# FinOps Tags - Ownership
team                = "platform"
owner               = "platform-team@example.com"

# FinOps Tags - Compliance
data_residency      = "canada"
compliance          = "pipeda"
