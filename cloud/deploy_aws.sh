#!/bin/bash
# Deploy GlassBox to Amazon Web Services (AWS)

echo "🚀 GlassBox - AWS Deployment"
echo "============================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo "This script helps you deploy GlassBox to AWS EC2"
echo ""
echo "Prerequisites:"
echo "1. AWS account: https://aws.amazon.com/"
echo "2. AWS CLI installed: brew install awscli"
echo "3. AWS credentials configured: aws configure"
echo ""
echo "Recommended instance: p3.2xlarge (1x V100) - ~$3/hour"
echo ""
echo "Continue? (y/n)"
read -r response

if [[ "$response" != "y" ]]; then
    exit 0
fi

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI not found${NC}"
    echo ""
    echo "Install with:"
    echo "  macOS: brew install awscli"
    echo "  Linux: curl \"https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip\" -o \"awscliv2.zip\" && unzip awscliv2.zip && sudo ./aws/install"
    echo ""
    exit 1
fi

# Check if configured
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${YELLOW}⚠️  AWS CLI not configured${NC}"
    echo ""
    echo "Configure with:"
    echo "  aws configure"
    echo ""
    echo "You'll need:"
    echo "  - AWS Access Key ID"
    echo "  - AWS Secret Access Key"
    echo "  - Default region (e.g., us-east-1)"
    echo ""
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo -e "${GREEN}✅ AWS Account: $ACCOUNT_ID${NC}"

echo ""
echo "Step 1: Region Selection"
echo "======================="
echo ""

echo "Select AWS region:"
echo "1. us-east-1 (N. Virginia) - Lowest cost"
echo "2. us-west-2 (Oregon) - Low cost"
echo "3. us-east-2 (Ohio) - Low cost"
echo "4. eu-west-1 (Ireland) - Medium cost"
echo "5. ap-southeast-1 (Singapore) - Medium cost"
echo ""
echo -n "Choice [1-5]: "
read -r region_choice

case "$region_choice" in
    1) REGION="us-east-1" ;;
    2) REGION="us-west-2" ;;
    3) REGION="us-east-2" ;;
    4) REGION="eu-west-1" ;;
    5) REGION="ap-southeast-1" ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

echo -e "${GREEN}✅ Using region: $REGION${NC}"

echo ""
echo "Step 2: Instance Type Selection"
echo "==============================="
echo ""

echo "Select instance type:"
echo "1. p3.2xlarge (1x V100, 8 vCPUs, 61GB RAM) - ~$3.00/hour"
echo "2. p3.8xlarge (4x V100, 32 vCPUs, 244GB RAM) - ~$12/hour (for Llama 70B)"
echo "3. g4dn.xlarge (1x T4, 4 vCPUs, 16GB RAM) - ~$0.50/hour (for testing)"
echo "4. p4d.24xlarge (8x A100, 96 vCPUs, 1152GB RAM) - ~$32/hour (production)"
echo ""
echo -n "Choice [1-4]: "
read -r instance_choice

case "$instance_choice" in
    1)
        INSTANCE_TYPE="p3.2xlarge"
        COST="$3.00/hour"
        ;;
    2)
        INSTANCE_TYPE="p3.8xlarge"
        COST="$12.00/hour"
        ;;
    3)
        INSTANCE_TYPE="g4dn.xlarge"
        COST="$0.50/hour"
        ;;
    4)
        INSTANCE_TYPE="p4d.24xlarge"
        COST="$32.00/hour"
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "Use spot instance? (70-90% cheaper, can be terminated)"
echo "Recommended for development/testing"
echo ""
echo -n "Use spot instance? (y/n): "
read -r use_spot

USE_SPOT_FLAG=""
if [[ "$use_spot" == "y" ]]; then
    USE_SPOT_FLAG="spot"
    echo -e "${GREEN}✅ Using spot instance (cheaper)${NC}"
fi

echo ""
echo "Step 3: Key Pair Setup"
echo "====================="
echo ""

# List existing key pairs
echo "Existing key pairs in $REGION:"
aws ec2 describe-key-pairs --region "$REGION" --query 'KeyPairs[*].KeyName' --output table 2>/dev/null || echo "None"
echo ""

echo "Enter key pair name (or press Enter to create new):"
read -r KEY_NAME

if [ -z "$KEY_NAME" ]; then
    KEY_NAME="glassbox-key-$(date +%s)"
    echo ""
    echo "Creating new key pair: $KEY_NAME"

    aws ec2 create-key-pair \
        --region "$REGION" \
        --key-name "$KEY_NAME" \
        --query 'KeyMaterial' \
        --output text > "$KEY_NAME.pem"

    chmod 400 "$KEY_NAME.pem"

    echo -e "${GREEN}✅ Key pair created and saved to: $KEY_NAME.pem${NC}"
    echo -e "${YELLOW}⚠️  Keep this file safe! You'll need it to connect.${NC}"
fi

echo ""
echo "Step 4: Security Group Setup"
echo "============================"
echo ""

SG_NAME="glassbox-sg-$(date +%s)"

echo "Creating security group: $SG_NAME"

# Get default VPC
VPC_ID=$(aws ec2 describe-vpcs --region "$REGION" --filters "Name=isDefault,Values=true" --query 'Vpcs[0].VpcId' --output text)

if [ "$VPC_ID" == "None" ]; then
    echo -e "${RED}❌ No default VPC found${NC}"
    echo "Please create a VPC in the AWS console first"
    exit 1
fi

# Create security group
SG_ID=$(aws ec2 create-security-group \
    --region "$REGION" \
    --group-name "$SG_NAME" \
    --description "GlassBox security group" \
    --vpc-id "$VPC_ID" \
    --query 'GroupId' \
    --output text)

echo -e "${GREEN}✅ Security group created: $SG_ID${NC}"

# Add SSH rule
aws ec2 authorize-security-group-ingress \
    --region "$REGION" \
    --group-id "$SG_ID" \
    --protocol tcp \
    --port 22 \
    --cidr 0.0.0.0/0 \
    > /dev/null

echo "  ✅ SSH access enabled (port 22)"

# Add API rule
aws ec2 authorize-security-group-ingress \
    --region "$REGION" \
    --group-id "$SG_ID" \
    --protocol tcp \
    --port 8000 \
    --cidr 0.0.0.0/0 \
    > /dev/null

echo "  ✅ API access enabled (port 8000)"

echo ""
echo "Step 5: Launching Instance"
echo "=========================="
echo ""

# Get Deep Learning AMI
echo "Finding latest Deep Learning AMI (Ubuntu)..."
AMI_ID=$(aws ec2 describe-images \
    --region "$REGION" \
    --owners amazon \
    --filters "Name=name,Values=Deep Learning AMI GPU PyTorch * (Ubuntu 20.04)*" \
              "Name=state,Values=available" \
    --query 'reverse(sort_by(Images, &CreationDate))[0].ImageId' \
    --output text)

if [ -z "$AMI_ID" ] || [ "$AMI_ID" == "None" ]; then
    echo -e "${RED}❌ Could not find Deep Learning AMI${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Using AMI: $AMI_ID${NC}"

echo ""
echo "Configuration Summary:"
echo "  Instance Type: $INSTANCE_TYPE"
echo "  Region: $REGION"
echo "  Key Pair: $KEY_NAME"
echo "  Security Group: $SG_ID"
echo "  Cost: $COST"
if [[ "$USE_SPOT_FLAG" == "spot" ]]; then
    echo "  Spot Instance: Yes (70-90% discount)"
fi
echo ""
echo "Launch instance? (y/n)"
read -r confirm

if [[ "$confirm" != "y" ]]; then
    echo "Cancelled"
    exit 0
fi

echo ""
echo "Launching instance..."

if [[ "$USE_SPOT_FLAG" == "spot" ]]; then
    # Launch spot instance
    SPOT_REQUEST=$(aws ec2 request-spot-instances \
        --region "$REGION" \
        --spot-price "100.00" \
        --instance-count 1 \
        --type "one-time" \
        --launch-specification "{
            \"ImageId\": \"$AMI_ID\",
            \"InstanceType\": \"$INSTANCE_TYPE\",
            \"KeyName\": \"$KEY_NAME\",
            \"SecurityGroupIds\": [\"$SG_ID\"],
            \"BlockDeviceMappings\": [{
                \"DeviceName\": \"/dev/sda1\",
                \"Ebs\": {
                    \"VolumeSize\": 200,
                    \"VolumeType\": \"gp3\"
                }
            }]
        }" \
        --query 'SpotInstanceRequests[0].SpotInstanceRequestId' \
        --output text)

    echo "Waiting for spot request to be fulfilled..."
    aws ec2 wait spot-instance-request-fulfilled \
        --region "$REGION" \
        --spot-instance-request-ids "$SPOT_REQUEST"

    INSTANCE_ID=$(aws ec2 describe-spot-instance-requests \
        --region "$REGION" \
        --spot-instance-request-ids "$SPOT_REQUEST" \
        --query 'SpotInstanceRequests[0].InstanceId' \
        --output text)
else
    # Launch on-demand instance
    INSTANCE_ID=$(aws ec2 run-instances \
        --region "$REGION" \
        --image-id "$AMI_ID" \
        --instance-type "$INSTANCE_TYPE" \
        --key-name "$KEY_NAME" \
        --security-group-ids "$SG_ID" \
        --block-device-mappings "[{\"DeviceName\":\"/dev/sda1\",\"Ebs\":{\"VolumeSize\":200,\"VolumeType\":\"gp3\"}}]" \
        --query 'Instances[0].InstanceId' \
        --output text)
fi

if [ -z "$INSTANCE_ID" ]; then
    echo -e "${RED}❌ Failed to launch instance${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Instance launched: $INSTANCE_ID${NC}"

# Wait for instance to be running
echo ""
echo "Waiting for instance to start..."
aws ec2 wait instance-running --region "$REGION" --instance-ids "$INSTANCE_ID"

# Get instance IP
INSTANCE_IP=$(aws ec2 describe-instances \
    --region "$REGION" \
    --instance-ids "$INSTANCE_ID" \
    --query 'Reservations[0].Instances[0].PublicIpAddress' \
    --output text)

echo -e "${GREEN}✅ Instance IP: $INSTANCE_IP${NC}"

# Wait a bit more for SSH to be ready
echo ""
echo "Waiting for SSH to be ready (may take 1-2 minutes)..."
sleep 30

echo ""
echo "Step 6: Deploying GlassBox"
echo "=========================="
echo ""

# Create setup script
cat > /tmp/setup_aws.sh << 'EOF'
#!/bin/bash
set -e

echo "📦 Installing system dependencies..."
sudo apt-get update -qq
sudo apt-get install -y git

echo "📥 Cloning GlassBox repository..."
if [ ! -d "glassbox_mvp" ]; then
    # Replace with your actual repo
    echo "Note: Replace this with your actual repository"
    git clone https://github.com/glassbox-ai/glassbox-engine.git || \
    mkdir -p glassbox_mvp
fi

cd glassbox_mvp

echo "🐍 Installing Python dependencies..."
pip install --upgrade pip
pip install -q transformers accelerate sentencepiece protobuf
pip install -q fastapi uvicorn streamlit plotly pandas

echo "🔐 Setting up HuggingFace token..."
echo "You need to login to HuggingFace to access Llama models"
echo "Get token from: https://huggingface.co/settings/tokens"
huggingface-cli login

echo "🧪 Testing GPU..."
python -c "
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
EOF

# Copy and run setup script
SSH_OPTIONS="-i $KEY_NAME.pem -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"

echo "Copying setup script to instance..."
scp $SSH_OPTIONS /tmp/setup_aws.sh ubuntu@$INSTANCE_IP:/tmp/setup_aws.sh

echo ""
echo "Running setup on instance..."
echo "This will prompt you for HuggingFace login..."
echo ""
ssh $SSH_OPTIONS ubuntu@$INSTANCE_IP "bash /tmp/setup_aws.sh"

echo ""
echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Deployment Complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo ""
echo "Your GlassBox instance is ready!"
echo ""
echo "Connection details:"
echo "  Instance ID: $INSTANCE_ID"
echo "  IP: $INSTANCE_IP"
echo "  Region: $REGION"
echo "  Cost: $COST"
echo ""
echo "To connect:"
echo "  ssh -i $KEY_NAME.pem ubuntu@$INSTANCE_IP"
echo ""
echo "To start the API server:"
echo "  ssh -i $KEY_NAME.pem ubuntu@$INSTANCE_IP"
echo "  cd glassbox_mvp"
echo "  export GLASSBOX_MODEL=meta-llama/Llama-2-70b-hf"
echo "  uvicorn api.server:app --host 0.0.0.0 --port 8000 &"
echo ""
echo "To access from your machine:"
echo "  curl http://$INSTANCE_IP:8000/"
echo ""
echo "To stop instance (save money):"
echo "  aws ec2 stop-instances --region $REGION --instance-ids $INSTANCE_ID"
echo ""
echo "To terminate instance:"
echo "  aws ec2 terminate-instances --region $REGION --instance-ids $INSTANCE_ID"
echo ""

# Save connection info
cat > cloud_connection_aws.txt << EOF
Instance ID: $INSTANCE_ID
Instance IP: $INSTANCE_IP
Region: $REGION
Instance Type: $INSTANCE_TYPE
Key File: $KEY_NAME.pem
Cost: $COST
Provider: Amazon Web Services

Connect:
  ssh -i $KEY_NAME.pem ubuntu@$INSTANCE_IP

API:
  http://$INSTANCE_IP:8000

Stop:
  aws ec2 stop-instances --region $REGION --instance-ids $INSTANCE_ID

Terminate:
  aws ec2 terminate-instances --region $REGION --instance-ids $INSTANCE_ID

Security Group: $SG_ID
EOF

echo "Connection details saved to: cloud_connection_aws.txt"
echo ""
echo -e "${YELLOW}⚠️  Important: Keep $KEY_NAME.pem safe!${NC}"
echo ""
