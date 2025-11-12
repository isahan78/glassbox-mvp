#!/bin/bash
# Deploy GlassBox to Google Cloud Platform (GCP)

echo "🚀 GlassBox - Google Cloud Deployment"
echo "======================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo "This script helps you deploy GlassBox to Google Cloud Platform"
echo ""
echo "Prerequisites:"
echo "1. Google Cloud account: https://cloud.google.com/"
echo "2. gcloud CLI installed: brew install google-cloud-sdk"
echo "3. Billing enabled on your project"
echo ""
echo "Recommended instance: a2-highgpu-1g (1x A100) - ~$3/hour"
echo ""
echo "Continue? (y/n)"
read -r response

if [[ "$response" != "y" ]]; then
    exit 0
fi

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ gcloud CLI not found${NC}"
    echo ""
    echo "Install with:"
    echo "  macOS: brew install google-cloud-sdk"
    echo "  Linux: curl https://sdk.cloud.google.com | bash"
    echo ""
    exit 1
fi

# Check if logged in
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
    echo -e "${YELLOW}⚠️  Not logged in to Google Cloud${NC}"
    echo ""
    echo "Logging in..."
    gcloud auth login
fi

ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)")
echo -e "${GREEN}✅ Logged in as: $ACCOUNT${NC}"

echo ""
echo "Step 1: Project Setup"
echo "====================="
echo ""

# List existing projects
echo "Existing projects:"
gcloud projects list --format="table(projectId,name)"
echo ""

echo "Enter project ID (or press Enter to create new):"
read -r PROJECT_ID

if [ -z "$PROJECT_ID" ]; then
    echo ""
    echo "Enter new project ID (lowercase, hyphens allowed):"
    read -r NEW_PROJECT_ID

    if [ -z "$NEW_PROJECT_ID" ]; then
        echo "Error: No project ID provided"
        exit 1
    fi

    echo "Creating project: $NEW_PROJECT_ID"
    gcloud projects create "$NEW_PROJECT_ID"
    PROJECT_ID="$NEW_PROJECT_ID"
fi

# Set project
gcloud config set project "$PROJECT_ID"
echo -e "${GREEN}✅ Using project: $PROJECT_ID${NC}"

echo ""
echo "Step 2: Enable Required APIs"
echo "============================"
echo ""

echo "Enabling Compute Engine API..."
gcloud services enable compute.googleapis.com

echo "Enabling Container Registry API..."
gcloud services enable containerregistry.googleapis.com

echo -e "${GREEN}✅ APIs enabled${NC}"

echo ""
echo "Step 3: Instance Configuration"
echo "=============================="
echo ""

echo "Select instance type:"
echo "1. a2-highgpu-1g (1x A100, 12 vCPUs, 85GB RAM) - ~$3.00/hour"
echo "2. n1-standard-8 + 1x V100 (8 vCPUs, 30GB RAM) - ~$2.50/hour"
echo "3. n1-standard-4 + 1x T4 (4 vCPUs, 15GB RAM) - ~$0.70/hour (for testing)"
echo ""
echo -n "Choice [1-3]: "
read -r instance_choice

case "$instance_choice" in
    1)
        MACHINE_TYPE="a2-highgpu-1g"
        ACCELERATOR="type=nvidia-tesla-a100,count=1"
        COST="$3.00/hour"
        ;;
    2)
        MACHINE_TYPE="n1-standard-8"
        ACCELERATOR="type=nvidia-tesla-v100,count=1"
        COST="$2.50/hour"
        ;;
    3)
        MACHINE_TYPE="n1-standard-4"
        ACCELERATOR="type=nvidia-tesla-t4,count=1"
        COST="$0.70/hour"
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "Select region:"
echo "1. us-central1 (Iowa) - Lower cost"
echo "2. us-west1 (Oregon) - Lower cost"
echo "3. us-east1 (South Carolina) - Lower cost"
echo "4. europe-west4 (Netherlands) - Medium cost"
echo "5. asia-east1 (Taiwan) - Medium cost"
echo ""
echo -n "Choice [1-5]: "
read -r region_choice

case "$region_choice" in
    1) ZONE="us-central1-a" ;;
    2) ZONE="us-west1-b" ;;
    3) ZONE="us-east1-c" ;;
    4) ZONE="europe-west4-a" ;;
    5) ZONE="asia-east1-a" ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "Use spot/preemptible instance? (60-91% cheaper, can be terminated)"
echo "Recommended for development/testing"
echo ""
echo -n "Use spot instance? (y/n): "
read -r use_spot

SPOT_FLAG=""
if [[ "$use_spot" == "y" ]]; then
    SPOT_FLAG="--preemptible"
    echo -e "${GREEN}✅ Using spot instance (cheaper)${NC}"
fi

echo ""
echo "Instance name (or press Enter for 'glassbox-instance'):"
read -r INSTANCE_NAME

if [ -z "$INSTANCE_NAME" ]; then
    INSTANCE_NAME="glassbox-instance"
fi

echo ""
echo "Step 4: Creating Instance"
echo "========================"
echo ""
echo "Configuration:"
echo "  Name: $INSTANCE_NAME"
echo "  Machine: $MACHINE_TYPE"
echo "  GPU: $ACCELERATOR"
echo "  Zone: $ZONE"
echo "  Cost: $COST"
if [[ -n "$SPOT_FLAG" ]]; then
    echo "  Spot: Yes (60-91% discount)"
fi
echo ""
echo "Create instance? (y/n)"
read -r confirm

if [[ "$confirm" != "y" ]]; then
    echo "Cancelled"
    exit 0
fi

echo ""
echo "Creating instance..."

gcloud compute instances create "$INSTANCE_NAME" \
    --zone="$ZONE" \
    --machine-type="$MACHINE_TYPE" \
    --accelerator="$ACCELERATOR" \
    --image-family=pytorch-latest-gpu \
    --image-project=deeplearning-platform-release \
    --boot-disk-size=200GB \
    --boot-disk-type=pd-ssd \
    --metadata="install-nvidia-driver=True" \
    --scopes=https://www.googleapis.com/auth/cloud-platform \
    $SPOT_FLAG

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to create instance${NC}"
    echo ""
    echo "Common issues:"
    echo "1. Quota exceeded - request GPU quota increase"
    echo "2. GPUs not available in zone - try different zone"
    echo "3. Billing not enabled - enable billing in console"
    exit 1
fi

echo -e "${GREEN}✅ Instance created${NC}"

# Wait for instance to be ready
echo ""
echo "Waiting for instance to start..."
sleep 10

# Get instance IP
INSTANCE_IP=$(gcloud compute instances describe "$INSTANCE_NAME" \
    --zone="$ZONE" \
    --format='get(networkInterfaces[0].accessConfigs[0].natIP)')

echo ""
echo -e "${GREEN}✅ Instance IP: $INSTANCE_IP${NC}"

echo ""
echo "Step 5: Deploying GlassBox"
echo "=========================="
echo ""

# Create setup script
cat > /tmp/setup_gcp.sh << 'EOF'
#!/bin/bash
set -e

echo "📦 Installing system dependencies..."
sudo apt-get update -qq
sudo apt-get install -y git python3-pip

echo "📥 Cloning GlassBox repository..."
if [ ! -d "glassbox_mvp" ]; then
    # Replace with your actual repo
    echo "Note: Replace this with your actual repository"
    git clone https://github.com/glassbox-ai/glassbox-mvp.git || \
    mkdir -p glassbox_mvp
fi

cd glassbox_mvp

echo "🐍 Installing Python dependencies..."
pip3 install --upgrade pip
pip3 install -q transformers accelerate sentencepiece protobuf torch
pip3 install -q fastapi uvicorn streamlit plotly pandas

echo "🔐 Setting up HuggingFace token..."
echo "You need to login to HuggingFace to access Llama models"
echo "Get token from: https://huggingface.co/settings/tokens"
huggingface-cli login

echo "🧪 Testing GPU..."
python3 -c "
import torch
print(f'CUDA available: {torch.cuda.is_available()}')
print(f'GPU count: {torch.cuda.device_count()}')
if torch.cuda.is_available():
    print(f'GPU: {torch.cuda.get_device_name(0)}')
"

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start the API server:"
echo "  cd glassbox_mvp"
echo "  export GLASSBOX_MODEL=meta-llama/Llama-2-70b-hf  # or any model"
echo "  uvicorn api.server:app --host 0.0.0.0 --port 8000"
echo ""
echo "To test:"
echo "  curl http://localhost:8000/"
EOF

# Copy and run setup script
echo "Copying setup script to instance..."
gcloud compute scp /tmp/setup_gcp.sh "$INSTANCE_NAME":/tmp/setup_gcp.sh --zone="$ZONE"

echo ""
echo "Running setup on instance..."
echo "This will prompt you for HuggingFace login..."
echo ""
gcloud compute ssh "$INSTANCE_NAME" --zone="$ZONE" --command="bash /tmp/setup_gcp.sh"

echo ""
echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Deployment Complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo ""
echo "Your GlassBox instance is ready!"
echo ""
echo "Connection details:"
echo "  Instance: $INSTANCE_NAME"
echo "  IP: $INSTANCE_IP"
echo "  Zone: $ZONE"
echo "  Cost: $COST"
echo ""
echo "To connect:"
echo "  gcloud compute ssh $INSTANCE_NAME --zone=$ZONE"
echo ""
echo "To start the API server:"
echo "  gcloud compute ssh $INSTANCE_NAME --zone=$ZONE"
echo "  cd glassbox_mvp"
echo "  export GLASSBOX_MODEL=meta-llama/Llama-2-70b-hf"
echo "  uvicorn api.server:app --host 0.0.0.0 --port 8000 &"
echo ""
echo "To access from your machine:"
echo "  1. Create firewall rule:"
echo "     gcloud compute firewall-rules create allow-glassbox \\"
echo "       --allow tcp:8000 \\"
echo "       --source-ranges 0.0.0.0/0 \\"
echo "       --target-tags glassbox"
echo ""
echo "  2. Add tag to instance:"
echo "     gcloud compute instances add-tags $INSTANCE_NAME \\"
echo "       --zone=$ZONE --tags=glassbox"
echo ""
echo "  3. Access API:"
echo "     curl http://$INSTANCE_IP:8000/"
echo ""
echo "To stop instance (save money):"
echo "  gcloud compute instances stop $INSTANCE_NAME --zone=$ZONE"
echo ""
echo "To delete instance:"
echo "  gcloud compute instances delete $INSTANCE_NAME --zone=$ZONE"
echo ""

# Save connection info
cat > cloud_connection_gcp.txt << EOF
Instance Name: $INSTANCE_NAME
Instance IP: $INSTANCE_IP
Zone: $ZONE
Project: $PROJECT_ID
Cost: $COST
Provider: Google Cloud Platform

Connect:
  gcloud compute ssh $INSTANCE_NAME --zone=$ZONE

API:
  http://$INSTANCE_IP:8000

Stop:
  gcloud compute instances stop $INSTANCE_NAME --zone=$ZONE

Delete:
  gcloud compute instances delete $INSTANCE_NAME --zone=$ZONE
EOF

echo "Connection details saved to: cloud_connection_gcp.txt"
echo ""
