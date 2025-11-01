# Naming Convention Update Summary

## Overview

All infrastructure files have been updated to use the standardized naming convention defined in `terraform/variables.tf`.

---

## Naming Convention Standards

### Resource Names
- **Service Account:** `oic-rarag` (not "risk-assessment-rag")
- **Bucket Suffix:** `rarag-kb` (not "rag-kb")
- **Corpus Name:** `oic-rarag-kb` (not "risk-assessment-kb")

### Environment Abbreviations
- **Production:** `prd` (not "prod")
- **Development:** `dev` (unchanged)
- **Testing:** `tst` (not "test")

### Code Streams
- **Production Paid:** `prd-paid` (not "prod-paid")
- **Production Free:** `prd-free` (not "prod-free")
- **Development Free:** `dev-free` (unchanged)
- **Testing Free:** `tst-free` (not "test-free")

### Project IDs
- **Production Paid:** `oic-prd-paid` (not "oic-prod-paid")
- **Production Free:** `oic-prd-free` (not "oic-prod-free")
- **Development Free:** `oic-dev-free` (unchanged)
- **Testing Free:** `oic-tst-free` (not "oic-test-free")

---

## Files Updated

### ✅ Scripts
1. **`bootstrap.sh`** - Recreated with correct naming
   - SERVICE_ACCOUNT_NAME="oic-rarag"
   - RAG_CORPUS_NAME="oic-rarag-kb"
   - BUCKET_SUFFIX="rarag-kb"

2. **`scripts/cleanup.sh`** - Updated
   - SERVICE_ACCOUNT_NAME="oic-rarag"
   - BUCKET_SUFFIX="rarag-kb"

3. **`scripts/verify-setup.sh`** - Updated
   - SERVICE_ACCOUNT_NAME="oic-rarag"
   - BUCKET_SUFFIX="rarag-kb"

4. **`scripts/create_corpus_cloudshell.sh`** - Updated
   - CORPUS_NAME="oic-rarag-kb"
   - Example updated

5. **`scripts/create_rag_corpus.py`** - Updated
   - All examples use "oic-rarag-kb"

### ✅ Terraform Code Streams
6. **`terraform/code-streams/prd-paid.tfvars`** - Renamed and updated
   - project_id = "oic-prd-paid"
   - environment = "prd"
   - code_stream = "prd-paid"
   - rag_corpus_name = "oic-prd-paid-rarag-kb"

7. **`terraform/code-streams/prd-free.tfvars`** - Renamed and updated
   - project_id = "oic-prd-free"
   - environment = "prd"
   - code_stream = "prd-free"
   - rag_corpus_name = "oic-prd-free-rarag-kb"

8. **`terraform/code-streams/dev-free.tfvars`** - Verified (already correct)
   - project_id = "oic-dev-free"
   - environment = "dev"
   - code_stream = "dev-free"
   - rag_corpus_name = "oic-dev-free-rarag-kb"

9. **`terraform/code-streams/tst-free.tfvars`** - Renamed and updated
   - project_id = "oic-tst-free"
   - environment = "tst"
   - code_stream = "tst-free"
   - rag_corpus_name = "oic-tst-free-rarag-kb"

### ✅ Terraform Configuration
10. **`terraform/terraform.tfvars.example`** - Updated all four code stream examples
    - prd-paid configuration
    - prd-free configuration
    - dev-free configuration
    - tst-free configuration

11. **`terraform/code-streams/README.md`** - Updated
    - All terraform apply commands
    - Code stream table
    - Multi-project deployment loop

### ✅ Documentation
12. **`FINOPS_IMPLEMENTATION_SUMMARY.md`** - Updated
    - All code stream configurations
    - Resource naming examples
    - Deployment commands
    - Budget tables
    - File lists

---

## File Renames

| Old Name | New Name |
|----------|----------|
| `terraform/code-streams/prod-paid.tfvars` | `terraform/code-streams/prd-paid.tfvars` |
| `terraform/code-streams/prod-free.tfvars` | `terraform/code-streams/prd-free.tfvars` |
| `terraform/code-streams/test-free.tfvars` | `terraform/code-streams/tst-free.tfvars` |

---

## Resource Naming Examples

### Production Paid (prd-paid)
```
Project ID:       oic-prd-paid
Service Account:  prd-oic-rarag@oic-prd-paid.iam.gserviceaccount.com
Bucket:           oic-prd-paid-prd-rarag-kb
Corpus:           oic-prd-paid-rarag-kb
```

### Production Free (prd-free)
```
Project ID:       oic-prd-free
Service Account:  prd-oic-rarag@oic-prd-free.iam.gserviceaccount.com
Bucket:           oic-prd-free-prd-rarag-kb
Corpus:           oic-prd-free-rarag-kb
```

### Development Free (dev-free)
```
Project ID:       oic-dev-free
Service Account:  dev-oic-rarag@oic-dev-free.iam.gserviceaccount.com
Bucket:           oic-dev-free-dev-rarag-kb
Corpus:           oic-dev-free-rarag-kb
```

### Testing Free (tst-free)
```
Project ID:       oic-tst-free
Service Account:  tst-oic-rarag@oic-tst-free.iam.gserviceaccount.com
Bucket:           oic-tst-free-tst-rarag-kb
Corpus:           oic-tst-free-rarag-kb
```

---

## Deployment Commands

### Using Bootstrap Script
```bash
cd infra
chmod +x bootstrap.sh
./bootstrap.sh oic-dev-free
```

### Using Terraform
```bash
cd infra/terraform

# Single code stream
terraform apply -var-file="code-streams/prd-paid.tfvars"

# All code streams
for stream in prd-paid prd-free dev-free tst-free; do
  terraform apply -var-file="code-streams/${stream}.tfvars"
done
```

---

## Validation

### Check Naming Convention
```bash
# Verify service account name
grep SERVICE_ACCOUNT_NAME infra/bootstrap.sh
# Should show: SERVICE_ACCOUNT_NAME="oic-rarag"

# Verify corpus name
grep RAG_CORPUS_NAME infra/bootstrap.sh
# Should show: RAG_CORPUS_NAME="oic-rarag-kb"

# Verify bucket suffix
grep BUCKET_SUFFIX infra/bootstrap.sh
# Should show: BUCKET_SUFFIX="rarag-kb"
```

### Check Code Stream Files
```bash
ls infra/terraform/code-streams/
# Should show: prd-paid.tfvars prd-free.tfvars dev-free.tfvars tst-free.tfvars
```

### Check Environment Values
```bash
grep "environment.*=" infra/terraform/code-streams/*.tfvars
# Should show: prd, dev, tst (not prod or test)
```

---

## Breaking Changes

### ⚠️ Important Notes

1. **File Renames:** Three code stream files were renamed
   - Old deployments using `prod-paid.tfvars` must update to `prd-paid.tfvars`
   - Old deployments using `prod-free.tfvars` must update to `prd-free.tfvars`
   - Old deployments using `test-free.tfvars` must update to `tst-free.tfvars`

2. **Project IDs Changed:**
   - `oic-prod-paid` → `oic-prd-paid`
   - `oic-prod-free` → `oic-prd-free`
   - `oic-test-free` → `oic-tst-free`

3. **Environment Values Changed:**
   - `prod` → `prd`
   - `test` → `tst`

4. **Resource Names Changed:**
   - Service accounts now use `oic-rarag` (not `risk-assessment-rag`)
   - Buckets now use `rarag-kb` suffix (not `rag-kb`)
   - Corpora now use `oic-rarag-kb` pattern (not `risk-assessment-kb`)

### Migration Path

If you have existing resources with old names:

1. **Option A: Recreate Resources** (Recommended for dev/test)
   ```bash
   # Delete old resources
   ./scripts/cleanup.sh old-project-id
   
   # Create new resources with correct naming
   ./bootstrap.sh new-project-id
   ```

2. **Option B: Rename Resources** (For production)
   - Rename GCS buckets via console or gsutil
   - Recreate service accounts (cannot be renamed)
   - Update all references in code

---

## Consistency Check

All files now consistently use:
- ✅ `oic-rarag` for service account base name
- ✅ `rarag-kb` for bucket suffix
- ✅ `oic-rarag-kb` for corpus name pattern
- ✅ `prd` for production environment
- ✅ `tst` for testing environment
- ✅ `dev` for development environment
- ✅ `prd-paid`, `prd-free`, `dev-free`, `tst-free` for code streams

---

## Next Steps

1. **Verify Changes:**
   ```bash
   # Check all files updated
   grep -r "prod-paid" infra/
   grep -r "test-free" infra/
   grep -r "risk-assessment" infra/
   # Should return no results
   ```

2. **Test Deployment:**
   ```bash
   cd infra/terraform
   terraform plan -var-file="code-streams/dev-free.tfvars"
   ```

3. **Update CI/CD:**
   - Update any CI/CD pipelines to use new file names
   - Update environment variable values
   - Update project IDs

4. **Update Documentation:**
   - All documentation has been updated
   - Review `FINOPS_IMPLEMENTATION_SUMMARY.md`
   - Review code-stream specific tfvars files

---

**Status:** ✅ Complete  
**Date:** November 2025  
**Files Updated:** 12 files  
**Files Renamed:** 3 files  
**Naming Convention:** Standardized across all infrastructure
