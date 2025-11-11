#!/bin/bash
#
# Cloud Shell wrapper for creating RAG corpus
# This script sets up the environment and runs the Python corpus creation script
#
# Usage: ./create_corpus_cloudshell.sh [PROJECT_ID] [CORPUS_NAME]
#
# Example: ./create_corpus_cloudshell.sh oicsbx risk-assessment-kb
#

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Get parameters
PROJECT_ID=${1:-""}
CORPUS_NAME=${2:-"oic-rarag-kb"}
LOCATION=${3:-"northamerica-northeast1"}

# Banner
echo "=============================================="
echo "  Vertex AI RAG Corpus Setup"
echo "  OpenImpactCascade Risk Assessment"
echo "=============================================="
echo ""

# Check if running in Cloud Shell
if [ -n "$CLOUD_SHELL" ]; then
    print_info "Running in Cloud Shell ✓"
else
    print_warning "Not running in Cloud Shell (this is OK)"
fi

# Get project ID if not provided
if [ -z "$PROJECT_ID" ]; then
    # Try to get from gcloud config
    PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
    
    if [ -z "$PROJECT_ID" ]; then
        print_error "Project ID is required"
        echo ""
        echo "Usage: $0 PROJECT_ID [CORPUS_NAME] [LOCATION]"
        echo ""
        echo "Example: $0 oicsbx oic-rarag-kb northamerica-northeast1"
        echo ""
        echo "Or set default project:"
        echo "  gcloud config set project YOUR_PROJECT_ID"
        exit 1
    fi
    
    print_info "Using project from gcloud config: $PROJECT_ID"
fi

print_info "Configuration:"
echo "  Project ID:   $PROJECT_ID"
echo "  Corpus Name:  $CORPUS_NAME"
echo "  Location:     $LOCATION"
echo ""

# Check if gcloud is authenticated
print_info "Checking authentication..."
if gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q "@"; then
    ACTIVE_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)")
    print_success "Authenticated as: $ACTIVE_ACCOUNT"
else
    print_error "Not authenticated to gcloud"
    echo ""
    echo "Run: gcloud auth login"
    exit 1
fi

# Set project
print_info "Setting active project..."
gcloud config set project "$PROJECT_ID" >/dev/null 2>&1
print_success "Project set to: $PROJECT_ID"

# Check if Vertex AI API is enabled
print_info "Checking Vertex AI API..."
if gcloud services list --enabled --filter="name:aiplatform.googleapis.com" --format="value(name)" 2>/dev/null | grep -q "aiplatform"; then
    print_success "Vertex AI API is enabled"
else
    print_warning "Vertex AI API is not enabled"
    read -p "Enable Vertex AI API? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Enabling Vertex AI API..."
        gcloud services enable aiplatform.googleapis.com --project="$PROJECT_ID"
        print_success "API enabled"
        
        print_info "Waiting for API to be ready (30 seconds)..."
        sleep 30
    else
        print_error "Vertex AI API is required"
        exit 1
    fi
fi

# Check Python version
print_info "Checking Python..."
if command -v python3 >/dev/null 2>&1; then
    PYTHON_VERSION=$(python3 --version)
    print_success "Python available: $PYTHON_VERSION"
else
    print_error "Python 3 is required"
    exit 1
fi

# Check if google-cloud-aiplatform is installed
print_info "Checking Python dependencies..."
if python3 -c "import vertexai" 2>/dev/null; then
    print_success "google-cloud-aiplatform is installed"
else
    print_warning "google-cloud-aiplatform is not installed"
    read -p "Install google-cloud-aiplatform? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Installing google-cloud-aiplatform..."
        pip3 install --user google-cloud-aiplatform --quiet
        print_success "Package installed"
    else
        print_error "google-cloud-aiplatform is required"
        echo "Install with: pip3 install google-cloud-aiplatform"
        exit 1
    fi
fi

# Check if script exists
SCRIPT_PATH="$(dirname "$0")/create_rag_corpus.py"
if [ ! -f "$SCRIPT_PATH" ]; then
    print_error "Script not found: $SCRIPT_PATH"
    echo ""
    echo "Make sure create_rag_corpus.py is in the same directory as this script"
    exit 1
fi

# Run the Python script
echo ""
print_info "Creating RAG corpus..."
echo ""

python3 "$SCRIPT_PATH" \
    --project-id "$PROJECT_ID" \
    --display-name "$CORPUS_NAME" \
    --location "$LOCATION" \
    --description "Knowledge base for OpenImpactCascade risk assessment platform" \
    --verify

EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    print_success "Corpus creation completed successfully!"
    
    echo ""
    echo "=============================================="
    echo "  Configuration for .env.gcp"
    echo "=============================================="
    echo ""
    echo "Add these to your .env.gcp file:"
    echo ""
    echo "GOOGLE_CLOUD_PROJECT=$PROJECT_ID"
    echo "GCP_REGION=$LOCATION"
    echo "VERTEX_RAG_CORPUS=$CORPUS_NAME"
    echo ""
    echo "=============================================="
    
else
    print_error "Corpus creation failed"
    exit $EXIT_CODE
fi
