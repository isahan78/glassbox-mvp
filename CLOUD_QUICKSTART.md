# GlassBox Cloud Quick Start

**Get GlassBox running on cloud GPUs in under 15 minutes.**

---

## 🎯 Why Cloud?

Your local machine (36GB RAM) is perfect for **Llama 2 7B**. But for bigger models:

| Model | RAM | Your Machine | Solution |
|-------|-----|--------------|----------|
| Llama 2 7B | 30GB | ✅ Works | Local |
| Llama 2 13B | 52GB | ❌ Too big | Cloud |
| Llama 2 70B | 140GB | ❌ Too big | Cloud |

**This guide gets you to cloud fast.**

---

## ⚡ Fastest Path: Lambda Labs

**Cost:** $1.29/hour
**Time:** 10 minutes
**Best for:** Development & testing

### Step 1: Sign Up (2 minutes)

1. Go to https://lambdalabs.com/
2. Create account
3. Add payment method
4. Add SSH key:
   ```bash
   # Generate SSH key if you don't have one
   ssh-keygen -t rsa -b 4096

   # Copy your public key
   cat ~/.ssh/id_rsa.pub

   # Paste it at: https://cloud.lambdalabs.com/ssh-keys
   ```

### Step 2: Run Deployment Script (5 minutes)

```bash
cd glassbox_mvp
./cloud/deploy_lambda_labs.sh
```

**The script will:**
1. Guide you to launch an instance
2. Test SSH connection
3. Deploy GlassBox automatically
4. Set up HuggingFace (you'll need to login once)
5. Give you connection details

### Step 3: Launch Instance (2 minutes)

When prompted by the script:

1. Go to https://cloud.lambdalabs.com/instances
2. Click "Launch instance"
3. Select **"1x A100 (80GB)"** - $1.29/hour
4. Choose closest region
5. Click "Launch instance"
6. Copy the instance IP
7. Paste IP into the script

### Step 4: Start API Server (1 minute)

```bash
# Connect to instance
ssh ubuntu@YOUR_INSTANCE_IP

# Navigate to code
cd glassbox_mvp

# Set model (70B for production, 7B for testing)
export GLASSBOX_MODEL=meta-llama/Llama-2-70b-hf

# Start server
uvicorn api.server:app --host 0.0.0.0 --port 8000 &
```

### Step 5: Test From Your Machine

```bash
# Test API
curl http://YOUR_INSTANCE_IP:8000/

# Should return:
# {"message": "GlassBox API v0.1.0", "status": "operational", ...}
```

---

## 🐍 Using Your Cloud Instance

### From Python

```python
from glassbox import GlassBoxClient

# Connect to your cloud instance
client = GlassBoxClient("http://YOUR_INSTANCE_IP:8000")

# Analyze decisions (running on Llama 70B in the cloud!)
probs = client.analyze_choices(
    "Q: Should we approve this $500k loan? Credit score: 720, Income: $150k. A:",
    ["yes", "no"]
)

print(f"Approve: {probs['yes']:.2%}")
print(f"Deny: {probs['no']:.2%}")
```

### From Command Line

```bash
# Analyze a decision
curl -X POST http://YOUR_INSTANCE_IP:8000/analyze-choices \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Q: Is this transaction fraudulent? A:",
    "choices": ["yes", "no"]
  }'

# Get top predictions
curl -X POST http://YOUR_INSTANCE_IP:8000/top-tokens \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "The capital of France is",
    "top_k": 5
  }'
```

---

## 💰 Cost Management

### Stop When Not Using

```bash
# From Lambda Labs dashboard
# Click instance → "Terminate"

# Cost: $0/hour when stopped
```

### Estimated Monthly Costs

| Usage | Hours/Month | Cost |
|-------|-------------|------|
| **Testing** (2h/day) | 60 | $77 |
| **Development** (8h/day) | 240 | $310 |
| **Production** (24/7) | 720 | $929 |

**💡 Pro tip:** Only run when needed!

---

## 🚀 Alternative: Google Cloud (More Features)

**Cost:** $0.70-3.00/hour
**Time:** 15 minutes
**Best for:** Enterprise & auto-scaling

### Prerequisites

```bash
# Install gcloud CLI
brew install google-cloud-sdk  # macOS
# or: apt install google-cloud-sdk  # Linux

# Login
gcloud auth login
```

### Deploy

```bash
./cloud/deploy_gcp.sh
```

Follow prompts to:
- Select/create project
- Choose instance type (A100, V100, or T4)
- Choose region
- Enable spot instances for 60-91% savings

**Connection details saved to:** `cloud_connection_gcp.txt`

---

## 🏗️ Alternative: AWS (Most Integrations)

**Cost:** $0.50-32/hour
**Time:** 15 minutes
**Best for:** Full AWS ecosystem

### Prerequisites

```bash
# Install AWS CLI
brew install awscli  # macOS

# Configure
aws configure
```

### Deploy

```bash
./cloud/deploy_aws.sh
```

Follow prompts to:
- Select region
- Choose instance (p3.2xlarge, g4dn.xlarge, etc.)
- Create security groups
- Enable spot instances for 70-90% savings

**SSH key saved to:** `glassbox-key-*.pem` (keep safe!)

---

## 🐳 Docker Deployment

### Local Testing

```bash
# Build
docker build -t glassbox:latest .

# Run with GPU
docker run --gpus all -p 8000:8000 \
  -e GLASSBOX_MODEL=meta-llama/Llama-2-70b-hf \
  -e HF_TOKEN=your_token \
  glassbox:latest

# Or use docker-compose
docker-compose up
```

### Push to Cloud

**Google Cloud:**
```bash
docker tag glassbox gcr.io/your-project/glassbox
docker push gcr.io/your-project/glassbox
gcloud run deploy glassbox-api --image gcr.io/your-project/glassbox
```

**AWS ECR:**
```bash
docker tag glassbox YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/glassbox
docker push YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/glassbox
```

---

## 📊 Model Size Guide

Choose the right model for your needs:

| Model | Cloud Instance | Cost/Hour | Quality | Use Case |
|-------|---------------|-----------|---------|----------|
| **Llama 2 7B** | 1x T4 | $0.50 | Good | Testing |
| **Llama 2 13B** | 1x A100 | $1.29 | Better | Development |
| **Llama 2 70B** | 4x A100 | $5.16 | Best | Production |

**Switch models easily:**
```bash
# On your cloud instance
export GLASSBOX_MODEL=meta-llama/Llama-2-70b-hf  # 70B
export GLASSBOX_MODEL=meta-llama/Llama-2-13b-hf  # 13B
export GLASSBOX_MODEL=meta-llama/Llama-2-7b-hf   # 7B

# Restart API
pkill uvicorn
uvicorn api.server:app --host 0.0.0.0 --port 8000 &
```

---

## 🔧 Troubleshooting

### Can't Connect

```bash
# Check instance is running
ping YOUR_INSTANCE_IP

# Test port
telnet YOUR_INSTANCE_IP 8000

# Check firewall (GCP)
gcloud compute firewall-rules list

# Check security group (AWS)
aws ec2 describe-security-groups
```

### Out of Memory

```bash
# Check available RAM
free -h

# Use smaller model
export GLASSBOX_MODEL=meta-llama/Llama-2-7b-hf

# Or upgrade instance
```

### HuggingFace Auth Failed

```bash
# Re-login
huggingface-cli logout
huggingface-cli login

# Make sure you accepted model license
# Visit: https://huggingface.co/meta-llama/Llama-2-70b-hf
```

---

## 📚 Next Steps

1. **Start local:** Use Llama 2 7B on your 36GB RAM machine
   ```bash
   ./setup_llama.sh
   ```

2. **Test cloud:** Deploy Lambda Labs for bigger models
   ```bash
   ./cloud/deploy_lambda_labs.sh
   ```

3. **Scale up:** Try Llama 2 70B for production quality

4. **Automate:** Set up auto-scaling with Kubernetes (see `SCALING_CLOUD_GUIDE.md`)

---

## 🎓 Full Documentation

- **Complete cloud guide:** `SCALING_CLOUD_GUIDE.md`
- **Cloud deployment details:** `cloud/README.md`
- **Remote client examples:** `examples/remote_client_example.py`
- **Model requirements:** `MODEL_REQUIREMENTS.md`
- **Main docs:** `readme.md`

---

## ✅ Summary

### Lambda Labs (Recommended)
```bash
./cloud/deploy_lambda_labs.sh
# → $1.29/hour, easiest setup
```

### Google Cloud (Enterprise)
```bash
./cloud/deploy_gcp.sh
# → $0.70-3/hour, auto-scaling
```

### AWS (Full Features)
```bash
./cloud/deploy_aws.sh
# → $0.50-32/hour, most integrations
```

---

**Questions? Check the docs or open an issue!**

🚀 **Get started:** `./cloud/deploy_lambda_labs.sh`
