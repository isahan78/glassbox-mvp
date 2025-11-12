# GlassBox Cloud Deployment

Automated deployment scripts for running GlassBox on cloud infrastructure with GPU support.

## 🎯 Why Cloud?

Your local machine (36GB RAM) can run **Llama 2 7B** perfectly. But for bigger models, you need cloud:

| Model | RAM Needed | Your Machine | Solution |
|-------|------------|--------------|----------|
| Llama 2 7B | 30GB | ✅ Works | Local |
| Llama 2 13B | 52GB | ❌ Won't fit | Cloud |
| Llama 2 70B | 140GB | ❌ Won't fit | Cloud |
| Llama 3 70B | 140GB | ❌ Won't fit | Cloud |

---

## 📁 Available Deployment Scripts

### 1. Lambda Labs (Recommended - Cheapest)
```bash
./cloud/deploy_lambda_labs.sh
```

**Best for:** Development and testing
- **Cost:** $1.29/hour (1x A100 80GB)
- **Pros:** Cheapest GPU instances, simple setup
- **Cons:** Limited regions, manual instance launch

**What it does:**
1. Guides you through launching a Lambda Labs instance
2. Tests SSH connection
3. Deploys GlassBox automatically
4. Sets up HuggingFace authentication
5. Provides connection details

---

### 2. Google Cloud Platform (GCP)
```bash
./cloud/deploy_gcp.sh
```

**Best for:** Enterprise deployment with auto-scaling
- **Cost:** $0.70-3.00/hour depending on GPU
- **Pros:** Excellent ML ecosystem, TPUs available, auto-scaling
- **Cons:** More expensive, complex setup

**What it does:**
1. Creates/selects GCP project
2. Enables required APIs
3. Launches GPU instance (A100, V100, or T4)
4. Option for spot instances (60-91% cheaper)
5. Deploys and configures GlassBox
6. Sets up firewall rules

**Instance options:**
- `a2-highgpu-1g`: 1x A100, ~$3/hour
- `n1-standard-8 + V100`: ~$2.50/hour
- `n1-standard-4 + T4`: ~$0.70/hour (testing)

---

### 3. Amazon Web Services (AWS)
```bash
./cloud/deploy_aws.sh
```

**Best for:** Full-featured cloud with AWS ecosystem
- **Cost:** $0.50-32/hour depending on instance
- **Pros:** Most features, global availability, integrations
- **Cons:** Most expensive, complex pricing

**What it does:**
1. Configures AWS credentials
2. Creates security groups and key pairs
3. Launches EC2 GPU instance
4. Option for spot instances (70-90% cheaper)
5. Deploys GlassBox with Deep Learning AMI
6. Provides SSH key file

**Instance options:**
- `p3.2xlarge`: 1x V100, ~$3/hour
- `p3.8xlarge`: 4x V100, ~$12/hour (Llama 70B)
- `g4dn.xlarge`: 1x T4, ~$0.50/hour (testing)
- `p4d.24xlarge`: 8x A100, ~$32/hour (production)

---

## 🚀 Quick Start

### Option 1: Lambda Labs (Easiest)

```bash
# 1. Run deployment script
./cloud/deploy_lambda_labs.sh

# Follow prompts:
# - Launch instance at https://cloud.lambdalabs.com/
# - Enter instance IP
# - Script handles the rest

# 2. Connect to instance
ssh ubuntu@YOUR_INSTANCE_IP

# 3. Start API server
cd glassbox_mvp
export GLASSBOX_MODEL=meta-llama/Llama-2-70b-hf
uvicorn api.server:app --host 0.0.0.0 --port 8000 &

# 4. Test from your local machine
curl http://YOUR_INSTANCE_IP:8000/
```

---

### Option 2: Google Cloud

```bash
# Prerequisites
brew install google-cloud-sdk  # macOS
# or: apt install google-cloud-sdk  # Linux

gcloud auth login

# Run deployment
./cloud/deploy_gcp.sh

# Follow prompts to configure instance
# Script will deploy automatically

# Connection details saved to: cloud_connection_gcp.txt
```

---

### Option 3: AWS

```bash
# Prerequisites
brew install awscli  # macOS
# or: apt install awscli  # Linux

aws configure  # Enter credentials

# Run deployment
./cloud/deploy_aws.sh

# Follow prompts to configure instance
# Script will deploy automatically

# Connection details saved to: cloud_connection_aws.txt
# SSH key saved to: glassbox-key-*.pem
```

---

## 💰 Cost Comparison

### Development/Testing (8 hours/day, 20 days/month)

| Provider | Instance | Cost/Hour | Monthly |
|----------|----------|-----------|---------|
| **Lambda Labs** | 1x A100 | $1.29 | $206 |
| **GCP** (spot) | 1x A100 | $1.20 | $192 |
| **AWS** (spot) | 1x V100 | $0.90 | $144 |

### Production (24/7)

| Provider | Instance | Cost/Hour | Monthly |
|----------|----------|-----------|---------|
| **Lambda Labs** | 1x A100 | $1.29 | $929 |
| **GCP** | 1x A100 | $3.00 | $2,160 |
| **AWS** | 1x V100 | $3.00 | $2,160 |

**💡 Pro tip:** Use spot/preemptible instances for 60-90% savings!

---

## 🐳 Docker Deployment

For containerized deployment:

### Build and Run Locally
```bash
# Build image
docker build -t glassbox:latest .

# Run with GPU
docker run --gpus all -p 8000:8000 \
  -e GLASSBOX_MODEL=meta-llama/Llama-2-70b-hf \
  -e HF_TOKEN=your_token \
  glassbox:latest

# Or use docker-compose
docker-compose up
```

### Push to Cloud Registry

**Google Cloud:**
```bash
# Tag and push
docker tag glassbox:latest gcr.io/your-project/glassbox:latest
docker push gcr.io/your-project/glassbox:latest

# Deploy to Cloud Run
gcloud run deploy glassbox-api \
  --image gcr.io/your-project/glassbox:latest \
  --platform managed
```

**AWS ECR:**
```bash
# Authenticate
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com

# Tag and push
docker tag glassbox:latest \
  YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/glassbox:latest
docker push YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/glassbox:latest
```

---

## 🔌 Using Remote Instances

Once deployed, use the client library to connect:

```python
from glassbox import GlassBoxClient

# Connect to your cloud instance
client = GlassBoxClient("http://your-instance-ip:8000")

# Analyze decisions remotely
probs = client.analyze_choices(
    "Q: Approve loan? A:",
    ["yes", "no"]
)
print(f"P(yes) = {probs['yes']:.2%}")

# See examples/remote_client_example.py for more
```

---

## 📊 Model Requirements by Cloud Instance

### Lambda Labs

| Model | Recommended Instance | Cost/Hour |
|-------|---------------------|-----------|
| Llama 2 7B | 1x A100 (40GB) | $0.80 |
| Llama 2 13B | 1x A100 (80GB) | $1.29 |
| Llama 2 70B | 4x A100 (80GB) | $5.16 |

### Google Cloud

| Model | Instance Type | GPUs | Cost/Hour |
|-------|---------------|------|-----------|
| Llama 2 7B | n1-standard-4 + T4 | 1 | $0.70 |
| Llama 2 13B | a2-highgpu-1g | 1x A100 | $3.00 |
| Llama 2 70B | a2-highgpu-4g | 4x A100 | $12.00 |

### AWS

| Model | Instance Type | GPUs | Cost/Hour |
|-------|---------------|------|-----------|
| Llama 2 7B | g4dn.xlarge | 1x T4 | $0.50 |
| Llama 2 13B | p3.2xlarge | 1x V100 | $3.00 |
| Llama 2 70B | p3.8xlarge | 4x V100 | $12.00 |

---

## 🛡️ Best Practices

### 1. Cost Management

**Use spot/preemptible instances:**
- 60-91% cheaper than on-demand
- Good for development and non-critical workloads

**Auto-shutdown when idle:**
```bash
# Add to your startup script
timeout 3600 uvicorn api.server:app  # Auto-stop after 1 hour
```

**Set billing alerts:**
```bash
# GCP
gcloud billing budgets create \
  --billing-account=ACCOUNT_ID \
  --display-name="GlassBox Budget" \
  --budget-amount=500

# AWS
aws budgets create-budget \
  --account-id=ACCOUNT_ID \
  --budget BudgetName=GlassBox,BudgetLimit=500
```

---

### 2. Security

**Restrict API access:**
```bash
# Only allow your IP
gcloud compute firewall-rules create allow-glassbox \
  --allow tcp:8000 \
  --source-ranges YOUR_IP/32

# AWS
aws ec2 authorize-security-group-ingress \
  --group-id sg-xxx \
  --protocol tcp \
  --port 8000 \
  --cidr YOUR_IP/32
```

**Use API keys:**
```python
# Add authentication to API
# See api/server.py for implementation
```

---

### 3. Monitoring

**Check costs regularly:**
```bash
# GCP
gcloud billing accounts list
gcloud billing accounts describe ACCOUNT_ID

# AWS
aws ce get-cost-and-usage \
  --time-period Start=2025-01-01,End=2025-01-31 \
  --granularity MONTHLY
```

**Monitor GPU usage:**
```bash
# On instance
nvidia-smi -l 1  # Update every second
```

---

## 🔧 Troubleshooting

### Connection Issues

**Can't connect to instance:**
```bash
# Check instance is running
gcloud compute instances list  # GCP
aws ec2 describe-instances     # AWS

# Check firewall rules
gcloud compute firewall-rules list  # GCP
aws ec2 describe-security-groups    # AWS

# Test connectivity
ping YOUR_INSTANCE_IP
telnet YOUR_INSTANCE_IP 8000
```

---

### GPU Not Detected

**Check NVIDIA drivers:**
```bash
nvidia-smi  # Should show GPU info

# If not working, reinstall drivers
sudo apt update
sudo apt install -y nvidia-driver-525  # or latest version
sudo reboot
```

---

### Out of Memory

**Model too big for instance:**
```bash
# Check available memory
free -h

# Use smaller model or bigger instance
export GLASSBOX_MODEL=meta-llama/Llama-2-7b-hf  # Smaller
```

---

### HuggingFace Authentication Failed

**Re-authenticate:**
```bash
huggingface-cli logout
huggingface-cli login

# Make sure you accepted model license
# Visit: https://huggingface.co/meta-llama/Llama-2-70b-hf
```

---

## 📝 Files Created by Scripts

After running deployment scripts, you'll find:

- `cloud_connection.txt` - Lambda Labs connection info
- `cloud_connection_gcp.txt` - GCP connection details
- `cloud_connection_aws.txt` - AWS connection details
- `glassbox-key-*.pem` - AWS SSH key (keep safe!)

---

## 🎓 Next Steps

1. **Deploy to cloud:** Choose a provider and run the script
2. **Test connection:** Use `examples/remote_client_example.py`
3. **Run bigger models:** Try Llama 2 13B or 70B
4. **Scale up:** Add auto-scaling with Kubernetes (see `SCALING_CLOUD_GUIDE.md`)

---

## 📚 Additional Resources

- **Complete scaling guide:** `../SCALING_CLOUD_GUIDE.md`
- **Remote client examples:** `../examples/remote_client_example.py`
- **Docker setup:** `../Dockerfile` and `../docker-compose.yml`
- **Main documentation:** `../readme.md`

---

## ❓ FAQ

**Q: Which provider should I use?**
A: Lambda Labs for cheapest GPU ($1.29/hour), GCP for best ML features, AWS for most integrations.

**Q: Can I use CPU-only instances?**
A: Yes, but very slow. GPU highly recommended for models 7B+.

**Q: How do I stop paying?**
A: Stop/terminate your instances when not using them. Set billing alerts!

**Q: Can I share one instance for multiple users?**
A: Yes! The API server handles multiple concurrent requests.

**Q: Do I need to download models every time?**
A: No - models are cached in `/app/data/models` (Docker) or `~/.cache/huggingface` (direct).

---

**Need help?** Check the main documentation or open an issue!
