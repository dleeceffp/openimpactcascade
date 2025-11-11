# Terraform variables for OpenImpactCascade GCP infrastructure

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region for resources"
  type        = string
  default     = "northamerica-northeast1"
}

variable "service_account_name" {
  description = "Name of the service account for RAG operations"
  type        = string
  default     = "oic-rarag"
}

variable "bucket_suffix" {
  description = "Suffix for the GCS bucket name"
  type        = string
  default     = "rarag-kb"
}

variable "rag_corpus_name" {
  description = "Name of the Vertex AI RAG corpus"
  type        = string
  default     = "oic-rarag-kb"
}

variable "environment" {
  description = "Environment name (prd, dev, tst)"
  type        = string
  default     = "dev"
  validation {
    condition     = contains(["prd", "dev", "tst"], var.environment)
    error_message = "Environment must be prd, dev, or tst."
  }
}

variable "code_stream" {
  description = "Code stream identifier (prd-paid, prd-free, dev-free, tst-free)"
  type        = string
  validation {
    condition     = contains(["prd-paid", "prd-free", "dev-free", "tst-free"], var.code_stream)
    error_message = "Code stream must be prd-paid, prd-free, dev-free, or tst-free."
  }
}

variable "subscription_tier" {
  description = "Subscription tier (paid, free)"
  type        = string
  default     = "free"
  validation {
    condition     = contains(["paid", "free"], var.subscription_tier)
    error_message = "Subscription tier must be paid or free."
  }
}

variable "cost_center" {
  description = "Cost center for billing (revenue, development, qa, infrastructure)"
  type        = string
  validation {
    condition     = contains(["revenue", "development", "qa", "infrastructure"], var.cost_center)
    error_message = "Cost center must be revenue, development, qa, or infrastructure."
  }
}

variable "budget_category" {
  description = "Budget priority category (high, medium, low)"
  type        = string
  default     = "low"
  validation {
    condition     = contains(["high", "medium", "low"], var.budget_category)
    error_message = "Budget category must be high, medium, or low."
  }
}

variable "team" {
  description = "Team responsible for the resources"
  type        = string
  default     = "platform"
}

variable "owner" {
  description = "Owner email or identifier"
  type        = string
  default     = "platform-team"
}

variable "data_residency" {
  description = "Data residency requirement (canada, us, global)"
  type        = string
  default     = "canada"
}

variable "compliance" {
  description = "Compliance requirements (pipeda, gdpr, none)"
  type        = string
  default     = "pipeda"
}