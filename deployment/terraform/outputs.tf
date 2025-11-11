# Terraform outputs for OpenImpactCascade GCP infrastructure

output "project_id" {
  description = "GCP project ID"
  value       = var.project_id
}

output "region" {
  description = "GCP region"
  value       = var.region
}

output "service_account_email" {
  description = "Email of the created service account"
  value       = google_service_account.rag_service_account.email
}

output "bucket_name" {
  description = "Name of the GCS bucket for knowledge base"
  value       = google_storage_bucket.rag_knowledge_base.name
}

output "bucket_url" {
  description = "URL of the GCS bucket"
  value       = google_storage_bucket.rag_knowledge_base.url
}

output "rag_corpus_name" {
  description = "Name of the RAG corpus"
  value       = var.rag_corpus_name
}

output "service_account_key_path" {
  description = "Path to the service account key file"
  value       = abspath("${path.module}/../service-account-key.json")
  sensitive   = true
}

output "env_file_path" {
  description = "Path to the .env.gcp file"
  value       = abspath("${path.module}/../.env.gcp")
}

output "code_stream" {
  description = "Code stream identifier"
  value       = var.code_stream
}

output "environment" {
  description = "Environment name"
  value       = var.environment
}

output "finops_tags" {
  description = "FinOps tags applied to resources"
  value = {
    code_stream     = var.code_stream
    environment     = var.environment
    subscription    = var.subscription_tier
    cost_center     = var.cost_center
    budget_category = var.budget_category
    team            = var.team
    data_residency  = var.data_residency
  }
}

output "resource_names" {
  description = "Created resource names with environment prefix"
  value = {
    service_account = google_service_account.rag_service_account.email
    bucket          = google_storage_bucket.rag_knowledge_base.name
    corpus          = var.rag_corpus_name
  }
}

output "next_steps" {
  description = "Next steps after Terraform apply"
  value = <<-EOT
    
    ========================================
    Infrastructure Created Successfully!
    ========================================
    
    Code Stream: ${var.code_stream}
    Environment: ${var.environment}
    Subscription: ${var.subscription_tier}
    
    Resources:
      - Service Account: ${google_service_account.rag_service_account.email}
      - GCS Bucket: ${google_storage_bucket.rag_knowledge_base.name}
      - RAG Corpus: ${var.rag_corpus_name}
      - Region: ${var.region}
    
    FinOps Tags:
      - Cost Center: ${var.cost_center}
      - Budget Category: ${var.budget_category}
      - Team: ${var.team}
      - Data Residency: ${var.data_residency}
    
    Next Steps:
      1. Source environment variables:
         source ${abspath("${path.module}/../.env.gcp")}
      
      2. Create RAG corpus:
         cd ../..
         python -c "from knowledge_base_manager import KnowledgeBaseManager; kb = KnowledgeBaseManager(); kb.create_rag_corpus('${var.rag_corpus_name}', 'Risk assessment knowledge base')"
      
      3. Populate knowledge base:
         python knowledge_base_manager.py
      
      4. Test RAG engine:
         python vertex_rag.py
      
      5. Configure API cost tracking:
         export CODE_STREAM=${var.code_stream}
         export ENVIRONMENT=${var.environment}
         export SUBSCRIPTION_TIER=${var.subscription_tier}
         export COST_CENTER=${var.cost_center}
         export BUDGET_CATEGORY=${var.budget_category}
    
    ⚠️  IMPORTANT: Never commit service-account-key.json or .env.gcp to version control!
    
  EOT
}
