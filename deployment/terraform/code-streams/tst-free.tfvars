# Testing Free Code Stream Configuration
# GCP Project: oic-tst-free
# Subscription: Free tier
# Purpose: QA and integration testing

# Project Configuration
project_id          = "oic-tst-free"
region              = "northamerica-northeast1"

# Environment & Code Stream
environment         = "tst"
code_stream         = "tst-free"
subscription_tier   = "free"

# Resource Naming
service_account_name = "oic-rarag"
bucket_suffix        = "rarag-kb"
rag_corpus_name      = "oic-tst-free-rarag-kb"

# FinOps Tags - Cost Tracking
cost_center         = "qa"
budget_category     = "low"

# FinOps Tags - Ownership
team                = "platform"
owner               = "platform-team@example.com"

# FinOps Tags - Compliance
data_residency      = "canada"
compliance          = "pipeda"
