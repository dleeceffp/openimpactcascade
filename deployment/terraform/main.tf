# Terraform configuration for OpenImpactCascade GCP infrastructure
# This creates all required resources for Vertex AI RAG integration

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Enable required APIs
resource "google_project_service" "aiplatform" {
  project = var.project_id
  service = "aiplatform.googleapis.com"
  
  disable_on_destroy = false
}

resource "google_project_service" "storage" {
  project = var.project_id
  service = "storage-api.googleapis.com"
  
  disable_on_destroy = false
}

resource "google_project_service" "iam" {
  project = var.project_id
  service = "iam.googleapis.com"
  
  disable_on_destroy = false
}

# Create service account for RAG operations
resource "google_service_account" "rag_service_account" {
  account_id   = "${var.environment}-${var.service_account_name}"
  display_name = "OIC RAG Service Account - ${var.code_stream}"
  description  = "Service account for Vertex AI RAG operations in OpenImpactCascade - ${var.code_stream}"
  project      = var.project_id
  
  depends_on = [google_project_service.iam]
}

# Grant Vertex AI User role
resource "google_project_iam_member" "rag_aiplatform_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.rag_service_account.email}"
  
  depends_on = [google_service_account.rag_service_account]
}

# Grant Storage Object Admin role
resource "google_project_iam_member" "rag_storage_admin" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.rag_service_account.email}"
  
  depends_on = [google_service_account.rag_service_account]
}

# Create GCS bucket for knowledge base
resource "google_storage_bucket" "rag_knowledge_base" {
  name          = "${var.project_id}-${var.environment}-${var.bucket_suffix}"
  location      = var.region
  project       = var.project_id
  
  uniform_bucket_level_access = true
  
  versioning {
    enabled = true
  }
  
  lifecycle_rule {
    condition {
      age = 365
      matches_prefix = ["archive/"]
    }
    action {
      type = "Delete"
    }
  }
  
  labels = {
    # Core identification
    application     = "openimpactcascade"
    component       = "rag-knowledge-base"
    
    # Environment & Code Stream
    environment     = var.environment
    code_stream     = var.code_stream
    subscription    = var.subscription_tier
    
    # Cost tracking
    cost_center     = var.cost_center
    budget_category = var.budget_category
    
    # Ownership
    team            = var.team
    owner           = replace(var.owner, "@", "-at-")
    
    # Lifecycle
    created_by      = "terraform"
    managed_by      = "terraform"
    
    # Compliance
    data_residency  = var.data_residency
    compliance      = var.compliance
  }
  
  depends_on = [google_project_service.storage]
}

# Grant service account access to bucket
resource "google_storage_bucket_iam_member" "rag_bucket_access" {
  bucket = google_storage_bucket.rag_knowledge_base.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.rag_service_account.email}"
  
  depends_on = [
    google_storage_bucket.rag_knowledge_base,
    google_service_account.rag_service_account
  ]
}

# Create service account key (stored in Terraform state - use with caution)
resource "google_service_account_key" "rag_key" {
  service_account_id = google_service_account.rag_service_account.name
  
  depends_on = [google_service_account.rag_service_account]
}

# Output the service account key to a local file
resource "local_file" "service_account_key" {
  content  = base64decode(google_service_account_key.rag_key.private_key)
  filename = "${path.module}/../service-account-key.json"
  
  file_permission = "0600"
}

# Create .env.gcp file
resource "local_file" "env_file" {
  content = templatefile("${path.module}/templates/env.tpl", {
    project_id     = var.project_id
    region         = var.region
    corpus_name    = var.rag_corpus_name
    bucket_name    = google_storage_bucket.rag_knowledge_base.name
    key_path       = abspath("${path.module}/../service-account-key.json")
  })
  
  filename = "${path.module}/../.env.gcp"
  
  file_permission = "0600"
  
  depends_on = [local_file.service_account_key]
}
