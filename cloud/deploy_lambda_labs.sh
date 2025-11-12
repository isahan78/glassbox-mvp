#!/bin/bash
# Deploy GlassBox to Lambda Labs (Cheapest GPU Option)

echo "🚀 GlassBox - Lambda Labs Deployment"
echo "====================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "This script helps you deploy GlassBox to Lambda Labs GPU instances"
echo ""
echo "Prerequisites:"
echo "1. Lambda Labs account: https://lambdalabs.com/"
echo "2. SSH key added to Lambda Labs"
echo "3. Payment method configured"
echo ""
echo "Recommended instance: 1x A100 (80GB) - $1.29/hour"
echo ""
echo "Continue? (y/n)"
read -r response

if [[ "$response" != "y" ]]; then
    exit 0
fi

echo ""
echo "Step 1: Launch Instance on Lambda Labs"
echo "========================================"
echo ""
echo "1. Go to: https://cloud.lambdalabs.com/instances"
echo "2. Click 'Launch instance'"
echo "3. Select: '1x A100 (80GB SXM4)' ($1.29/hour)"
echo "4. Region: Choose closest to you"
echo "5. Click 'Launch instance'"
echo ""
echo "Have you launched the instance? (y/n)"
read -r launched

if [[ "$launched" != "y" ]]; then
    echo "Please launch instance first, then run this script again"
    exit 0
fi

echo ""
echo "Step 2: Get Instance IP"
echo "======================="
echo ""
echo "From Lambda Labs dashboard, copy the instance IP:"
echo ""
echo -n "Enter instance IP: "
read -r INSTANCE_IP

if [ -z "$INSTANCE_IP" ]; then
    echo "Error: No IP provided"
    exit 1
fi

echo ""
echo "Instance IP: $INSTANCE_IP"

# Test SSH connection
echo ""
echo "Step 3: Testing SSH Connection"
echo "==============================="
echo ""

ssh -o ConnectTimeout=5 ubuntu@$INSTANCE_IP "echo 'SSH connection successful'" 2>/dev/null

if [ $? -ne 0 ]; then
    echo -e "${YELLOW}⚠️  Cannot connect via SSH${NC}"
    echo ""
    echo "Make sure:"
    echo "1. Your SSH key is added to Lambda Labs"
    echo "2. Instance is fully booted (may take 1-2 minutes)"
    echo "3. Firewall allows SSH (port 22)"
    echo ""
    echo "Try again? (y/n)"
    read -r retry

    if [[ "$retry" == "y" ]]; then
        ssh ubuntu@$INSTANCE_IP "echo 'SSH connection successful'"
    else
        exit 1
    fi
fi

echo -e "${GREEN}✅ SSH connection working${NC}"

# Setup script
echo ""
echo "Step 4: Deploying GlassBox"
echo "==========================="
echo ""

cat > /tmp/setup_remote.sh << 'EOF'
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

echo "🧪 Testing model load..."
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
scp /tmp/setup_remote.sh ubuntu@$INSTANCE_IP:/tmp/

echo "Running setup on instance..."
ssh ubuntu@$INSTANCE_IP "bash /tmp/setup_remote.sh"

echo ""
echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Deployment Complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo ""
echo "Your GlassBox instance is ready at: $INSTANCE_IP"
echo ""
echo "To start the API server:"
echo "  ssh ubuntu@$INSTANCE_IP"
echo "  cd glassbox_mvp"
echo "  export GLASSBOX_MODEL=meta-llama/Llama-2-70b-hf"
echo "  uvicorn api.server:app --host 0.0.0.0 --port 8000 &"
echo ""
echo "To access from your machine:"
echo "  curl http://$INSTANCE_IP:8000/"
echo ""
echo "Cost: $1.29/hour while running"
echo "Remember to STOP instance when not in use!"
echo ""

# Save connection info
cat > cloud_connection.txt << EOF
Instance IP: $INSTANCE_IP
SSH: ssh ubuntu@$INSTANCE_IP
API: http://$INSTANCE_IP:8000
Cost: $1.29/hour
Provider: Lambda Labs
EOF

echo "Connection details saved to: cloud_connection.txt"
