# Code Stream Configurations

Pre-configured Terraform variable files for each code stream.

## Usage

### Apply a Specific Code Stream

```bash
# Production Paid
terraform apply -var-file="code-streams/prd-paid.tfvars"

# Production Free
terraform apply -var-file="code-streams/prd-free.tfvars"

# Development Free
terraform apply -var-file="code-streams/dev-free.tfvars"

# Testing Free
terraform apply -var-file="code-streams/tst-free.tfvars"
```

### Plan Before Apply

```bash
terraform plan -var-file="code-streams/dev-free.tfvars"
```

## Code Streams

| Code Stream | Project ID | Environment | Subscription | Cost Center | Budget |
|-------------|------------|-------------|--------------|-------------|--------|
| prd-paid | oic-prd-paid | prd | paid | revenue | high |
| prd-free | oic-prd-free | prd | free | revenue | medium |
| dev-free | oic-dev-free | dev | free | development | low |
| tst-free | oic-tst-free | tst | free | qa | low |

## Resource Naming

Resources are named with environment prefix:

**Example for dev-free:**
- Service Account: `dev-oic-rarag@oic-dev-free.iam.gserviceaccount.com`
- Bucket: `oic-dev-free-dev-rarag-kb`
- Corpus: `oic-dev-free-rarag-kb`

## FinOps Labels

All resources are tagged with:
- `code_stream` - Code stream identifier
- `environment` - Environment name
- `subscription` - Subscription tier
- `cost_center` - Cost center for billing
- `budget_category` - Budget priority
- `team` - Owning team
- `owner` - Owner contact
- `data_residency` - Data location requirement
- `compliance` - Compliance framework

## Customization

Copy a file and modify as needed:

```bash
cp code-streams/dev-free.tfvars terraform.tfvars
# Edit terraform.tfvars
terraform apply
```

## Multi-Project Deployment

Deploy to all code streams:

```bash
for stream in prd-paid prd-free dev-free tst-free; do
  echo "Deploying $stream..."
  terraform apply -var-file="code-streams/${stream}.tfvars" -auto-approve
done
```

**Note:** Ensure each project exists before deploying.
