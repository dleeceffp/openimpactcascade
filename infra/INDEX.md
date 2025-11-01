# Infrastructure Directory Index

Complete guide to GCP infrastructure setup for OpenImpactCascade Vertex AI RAG integration.

---

## 📁 Directory Structure

```
infra/
├── README.md                    # Main documentation (start here)
├── INDEX.md                     # This file
├── MANUAL_SETUP.md             # Step-by-step manual setup guide
├── .gitignore                  # Git ignore rules
│
├── bootstrap.sh                # Bash bootstrap script
│
├── scripts/
│   ├── cleanup.sh              # Remove all GCP resources
│   └── verify-setup.sh         # Verify setup is correct
│
└── terraform/
    ├── README.md               # Terraform documentation
    ├── main.tf                 # Main Terraform configuration
    ├── variables.tf            # Variable definitions
    ├── outputs.tf              # Output definitions
    ├── terraform.tfvars.example # Example variables file
    └── templates/
        └── env.tpl             # Environment file template
```

---

## 🚀 Quick Start Paths

### Path 1: Automated Bootstrap (Recommended)

```bash
cd infra
chmod +x bootstrap.sh
./bootstrap.sh your-project-id
```

**What it does:**
- Enables GCP APIs
- Creates service account
- Sets up IAM permissions
- Creates GCS bucket
- Generates configuration files

**Time:** ~5 minutes

---

### Path 2: Terraform (Infrastructure as Code)

```bash
cd infra/terraform

# Initialize
terraform init

# Configure
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your project ID

# Apply
terraform apply
```

**What it does:**
- Same as bootstrap script
- Manages state
- Repeatable and version-controlled
- Easier to update/destroy

**Time:** ~5 minutes

---

### Path 3: Manual Setup (Full Control)

Follow `MANUAL_SETUP.md` for step-by-step instructions.

**When to use:**
- Learning GCP
- Custom requirements
- Troubleshooting
- Corporate policies

**Time:** ~15 minutes

---

## 📚 Documentation Files

### README.md
**Purpose:** Main entry point and overview  
**Read if:** You're starting fresh  
**Contains:**
- Overview of what gets created
- Quick start instructions
- Cost estimates
- Security notes

### MANUAL_SETUP.md
**Purpose:** Detailed step-by-step manual setup  
**Read if:** You want full control or troubleshooting  
**Contains:**
- 13 detailed steps
- Verification commands
- Troubleshooting guide
- Cleanup instructions

### terraform/README.md
**Purpose:** Terraform-specific documentation  
**Read if:** Using Terraform approach  
**Contains:**
- Terraform commands
- Variable configuration
- State management
- Migration guide

---

## 🛠️ Scripts

### bootstrap.sh
**Purpose:** Automated GCP project setup  
**Usage:**
```bash
chmod +x bootstrap.sh
./bootstrap.sh PROJECT_ID [REGION]
```
**Creates:**
- Service account
- IAM bindings
- GCS bucket
- Local config files

### scripts/cleanup.sh
**Purpose:** Remove all created resources  
**Usage:**
```bash
./scripts/cleanup.sh PROJECT_ID
```
**⚠️ Warning:** Deletes all data!

### scripts/verify-setup.sh
**Purpose:** Verify setup is correct  
**Usage:**
```bash
./scripts/verify-setup.sh PROJECT_ID
```
**Checks:**
- APIs enabled
- Service account exists
- IAM roles granted
- Bucket created
- Python dependencies

---

## 🔑 Generated Files

After running bootstrap or Terraform, these files are created:

### service-account-key.json
- **Purpose:** GCP service account credentials
- **Location:** `infra/`
- **Security:** ⚠️ Never commit to git!
- **Usage:** Set as `GOOGLE_APPLICATION_CREDENTIALS`

### .env.gcp
- **Purpose:** Environment variables for application
- **Location:** `infra/`
- **Security:** ⚠️ Never commit to git!
- **Usage:** `source .env.gcp` before running app

---

## 🎯 Use Cases

### First-Time Setup
1. Read `README.md`
2. Run `bootstrap.sh` or `bootstrap.ps1`
3. Follow "Next Steps" in output
4. Run `scripts/verify-setup.sh`

### Using Terraform
1. Read `terraform/README.md`
2. Copy `terraform.tfvars.example`
3. Run `terraform init && terraform apply`
4. Review outputs

### Manual Setup
1. Read `MANUAL_SETUP.md`
2. Follow each step
3. Verify with `scripts/verify-setup.sh`

### Troubleshooting
1. Run `scripts/verify-setup.sh`
2. Check `MANUAL_SETUP.md` troubleshooting section
3. Review `terraform/README.md` if using Terraform

### Cleanup
1. Run `scripts/cleanup.sh PROJECT_ID`
2. Or `terraform destroy` if using Terraform

---

## 🔒 Security Best Practices

### Never Commit These Files:
- ❌ `service-account-key.json`
- ❌ `.env.gcp`
- ❌ `terraform.tfstate`
- ❌ `terraform.tfvars`

### Always:
- ✅ Use `.gitignore` (already configured)
- ✅ Rotate service account keys regularly
- ✅ Use least-privilege IAM roles
- ✅ Enable audit logging
- ✅ Review IAM bindings periodically

### Production:
- Use Workload Identity instead of keys
- Store Terraform state remotely (GCS)
- Enable VPC Service Controls
- Use Secret Manager for API keys

---

## 💰 Cost Breakdown

### One-Time Setup
- **Cost:** $0 (free)
- **Time:** 5-15 minutes

### Monthly Ongoing
- **Storage:** $0.10-1.00 (knowledge base)
- **RAG Queries:** $0.001 per query
- **Estimated Total:** $2-20/month

### Cost Optimization
- Use lifecycle policies (already configured)
- Archive old documents
- Monitor query volume
- Set up billing alerts

---

## 🔄 Workflow Comparison

| Feature | Bootstrap Script | Terraform | Manual |
|---------|-----------------|-----------|--------|
| **Speed** | ⚡ Fast (5 min) | ⚡ Fast (5 min) | 🐌 Slow (15 min) |
| **Repeatability** | ✅ Good | ✅✅ Excellent | ❌ Manual |
| **State Management** | ❌ No | ✅ Yes | ❌ No |
| **Version Control** | ⚠️ Limited | ✅ Full | ❌ No |
| **Learning Curve** | ✅ Easy | ⚠️ Medium | ✅ Easy |
| **Customization** | ⚠️ Limited | ✅ Full | ✅ Full |
| **Cleanup** | ✅ Script | ✅ `destroy` | ⚠️ Manual |
| **Best For** | Quick start | Production | Learning |
| **Platform** | Linux/Mac | Any | Any |

---

## 📋 Checklist

### Before You Start
- [ ] GCP account with billing enabled
- [ ] `gcloud` CLI installed
- [ ] Authenticated to GCP
- [ ] Project created (or ID ready)
- [ ] Appropriate permissions

### After Bootstrap/Terraform
- [ ] `service-account-key.json` created
- [ ] `.env.gcp` created
- [ ] APIs enabled
- [ ] Service account created
- [ ] IAM roles granted
- [ ] GCS bucket created
- [ ] Verification passed

### Before Using Application
- [ ] Environment variables sourced
- [ ] Python dependencies installed
- [ ] RAG corpus created
- [ ] Knowledge base populated
- [ ] RAG engine tested

---

## 🆘 Getting Help

### Common Issues

**"Permission denied"**
→ Check IAM roles in `MANUAL_SETUP.md`

**"API not enabled"**
→ Run `scripts/verify-setup.sh`

**"Bucket already exists"**
→ Choose different project ID or bucket suffix

**"Terraform state locked"**
→ See `terraform/README.md` troubleshooting

### Resources

- 📖 Main docs: `../documentation/VERTEX_RAG_INTEGRATION.md`
- 🚀 Quick start: `../QUICKSTART_RAG.md`
- 💻 Code examples: `../ai_question_generator_rag_example.py`
- 🔧 RAG engine: `../vertex_rag.py`

---

## 🎓 Learning Path

### Beginner
1. Read `README.md`
2. Run `bootstrap.sh`
3. Follow "Next Steps"
4. Test with `vertex_rag.py`

### Intermediate
1. Read `MANUAL_SETUP.md`
2. Set up manually
3. Understand each component
4. Customize configuration

### Advanced
1. Read `terraform/README.md`
2. Use Terraform
3. Customize infrastructure
4. Set up CI/CD pipeline

---

## 📊 What Gets Created

### GCP Resources
```
your-project-id
├── APIs Enabled
│   ├── aiplatform.googleapis.com
│   ├── storage-api.googleapis.com
│   └── iam.googleapis.com
│
├── Service Account
│   └── risk-assessment-rag@your-project-id.iam.gserviceaccount.com
│       ├── Role: aiplatform.user
│       └── Role: storage.objectAdmin
│
└── GCS Bucket
    └── your-project-id-rag-kb
        ├── Location: us-central1
        ├── Versioning: Enabled
        └── Lifecycle: Delete archive/ after 365 days
```

### Local Files
```
infra/
├── service-account-key.json  (credentials)
└── .env.gcp                  (environment config)
```

---

## 🔄 Next Steps After Setup

1. **Source environment:**
   ```bash
   source infra/.env.gcp
   ```

2. **Create RAG corpus:**
   ```bash
   python -c "from knowledge_base_manager import KnowledgeBaseManager; kb = KnowledgeBaseManager(); kb.create_rag_corpus('risk-assessment-kb', 'Knowledge base')"
   ```

3. **Populate knowledge base:**
   ```bash
   python knowledge_base_manager.py
   ```

4. **Test RAG engine:**
   ```bash
   python vertex_rag.py
   ```

5. **Integrate into application:**
   - See `../documentation/VERTEX_RAG_INTEGRATION.md`
   - See `../ai_question_generator_rag_example.py`

---

**Ready to start?** Choose your path above and begin setup!

For questions or issues, see the troubleshooting sections in the respective documentation files.
