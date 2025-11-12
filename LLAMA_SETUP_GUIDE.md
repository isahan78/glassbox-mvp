# Llama 2 Setup Guide for Production

Complete guide to setting up Llama 2 7B for production use with GlassBox.

---

## 🚀 Quick Start (5 Steps)

### Step 1: Get HuggingFace Access

1. **Create HuggingFace Account**
   - Go to: https://huggingface.co/join
   - Sign up (free)

2. **Accept Llama 2 License**
   - Visit: https://huggingface.co/meta-llama/Llama-2-7b-hf
   - Click "Access repository"
   - Read and accept the license (usually instant approval)
   - Meta may ask for basic info (name, organization)

3. **Get Access Token**
   - Go to: https://huggingface.co/settings/tokens
   - Click "New token"
   - Name it: "glassbox-llama"
   - Type: "Read"
   - Copy the token (starts with `hf_...`)

---

### Step 2: Login to HuggingFace

```bash
# Install HuggingFace CLI (should already be installed)
pip install huggingface-hub

# Login with your token
huggingface-cli login

# Paste your token when prompted
# Token: hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**Alternative: Environment Variable**
```bash
# Add to your .env file
echo "HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx" >> .env

# Or export in terminal
export HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

### Step 3: Install Dependencies

```bash
# Make sure you have all required packages
pip install transformers>=4.31.0
pip install accelerate>=0.20.0
pip install sentencepiece>=0.1.99
pip install protobuf>=3.20.0
```

**Or from requirements.txt:**
```bash
pip install -r requirements.txt
```

---

### Step 4: Test Loading Llama 2

```python
from glassbox import ActivationTracer

print("Loading Llama 2 7B...")
print("This will download ~13GB on first run (one-time only)")

tracer = ActivationTracer(model_name="meta-llama/Llama-2-7b-hf")

print("\n✅ Llama 2 loaded successfully!")
print(f"Model: {tracer.model_name}")
print(f"Layers: {tracer.num_layers}")
print(f"Heads per layer: {tracer.num_heads}")
```

**Expected Output:**
```
Loading Llama 2 7B...
This will download ~13GB on first run (one-time only)

📦 Loading meta-llama/Llama-2-7b-hf (7B)...
   Expected: 32 layers, 32 heads
Downloading (on first run): ████████████████████ 100%
Loaded pretrained model meta-llama/Llama-2-7b-hf into HookedTransformer
✅ Loaded meta-llama/Llama-2-7b-hf
   Actual: 32 layers, 32 heads per layer
   Device: cpu
   Memory: ~14.0GB required

✅ Llama 2 loaded successfully!
Model: meta-llama/Llama-2-7b-hf
Layers: 32
Heads per layer: 32
```

---

### Step 5: Test with Decision Analysis

```python
from glassbox import ActivationTracer, DecisionAnalyzer

# Load model
tracer = ActivationTracer(model_name="meta-llama/Llama-2-7b-hf")
analyzer = DecisionAnalyzer(tracer)

# Test decision
prompt = "Q: Should we approve this loan application? A:"
result, probs = analyzer.analyze_choices(prompt, ["yes", "no"])

print(f"\nPrompt: {prompt}")
print(f"Decision: {result.output_text}")
print(f"P(yes) = {probs['yes']:.1%}")
print(f"P(no) = {probs['no']:.1%}")
```

---

## 📊 Llama 2 Models Comparison

| Model | Params | RAM Required | Speed | Best For |
|-------|--------|--------------|-------|----------|
| Llama-2-7b-hf | 7B | 14GB | Medium | ⭐ Production (recommended) |
| Llama-2-13b-hf | 13B | 26GB | Slow | High-quality analysis |
| Llama-2-7b-chat-hf | 7B | 14GB | Medium | Chat/instruction format |
| Llama-2-13b-chat-hf | 13B | 26GB | Slow | Chat/instruction format |

**Recommended for GlassBox:** `Llama-2-7b-hf` (base model, not chat)

**Why base, not chat?**
- Chat models are fine-tuned for multi-turn conversation
- Base models are better for single predictions
- For yes/no decisions, base model works best

---

## 💻 Hardware Requirements

### Minimum (Llama 2 7B)
- **RAM:** 16GB (system) + 14GB (model) = **30GB total**
- **Storage:** 15GB free space
- **CPU:** Modern multi-core processor

### Recommended (Llama 2 7B)
- **RAM:** 32GB or more
- **GPU:** 16GB VRAM (optional, but 10x faster)
- **Storage:** 20GB+ free space

### For GPU Acceleration
```python
# Use GPU if available
import torch

device = "cuda" if torch.cuda.is_available() else "cpu"
tracer = ActivationTracer(
    model_name="meta-llama/Llama-2-7b-hf",
    device=device
)

print(f"Running on: {device}")
# Running on: cuda  ← Much faster!
```

---

## 🔧 Production Configuration

### Option 1: Environment Variable (Recommended)

**In `.env` file:**
```bash
GLASSBOX_MODEL=meta-llama/Llama-2-7b-hf
HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**In code:**
```python
import os
from glassbox import ActivationTracer

model_name = os.getenv("GLASSBOX_MODEL", "gpt2-medium")
tracer = ActivationTracer(model_name=model_name)
```

**Start API server:**
```bash
# API will automatically use Llama 2
export GLASSBOX_MODEL=meta-llama/Llama-2-7b-hf
uvicorn api.server:app --reload
```

---

### Option 2: Direct Configuration

**In API (api/server.py):**
```python
# Modify the lifespan function
@asynccontextmanager
async def lifespan(app: FastAPI):
    global tracer, serializer
    print("Initializing GlassBox components...")

    # Use Llama 2 for production
    tracer = ActivationTracer(model_name="meta-llama/Llama-2-7b-hf")
    serializer = TraceSerializer(output_dir="data/traces")

    print("GlassBox API ready!")
    yield
    print("Shutting down...")
```

**In Dashboard (dashboard/app.py):**
```python
@st.cache_resource
def get_tracer():
    """Initialize tracer with Llama 2."""
    return ActivationTracer(model_name="meta-llama/Llama-2-7b-hf")
```

---

## 🎯 Prompt Engineering for Llama 2

Llama 2 works better with **structured prompts**:

### ✅ Good Prompts for Llama 2

```python
# Format 1: Q&A with clear structure
"Q: Should we approve this loan application?\nCredit Score: 750\nIncome: $80,000\nA:"

# Format 2: Instruction format
"[INST] Based on the following information, should we approve the loan? Credit: 750, Income: $80k [/INST]"

# Format 3: Simple Q&A
"Question: Approve this loan?\nAnswer:"

# Format 4: Completion style
"Loan decision (approve/deny):"
```

### ❌ Bad Prompts

```python
# Too vague
"What about this loan?"

# No structure
"loan approval decision credit 750 income 80k"

# Too conversational (better for chat models)
"Hey, can you help me decide if we should approve this loan?"
```

---

## 📈 Performance Comparison

### GPT-2 Medium vs Llama 2 7B

**Test: "Q: Should we approve this loan? A:"**

| Metric | GPT-2 Medium | Llama 2 7B |
|--------|--------------|------------|
| Load time | ~3 seconds | ~15 seconds |
| Inference | ~5 seconds | ~15 seconds (CPU) |
| Inference (GPU) | ~2 seconds | ~2 seconds |
| Memory | 1.5GB | 14GB |
| Quality | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Coherence | Sometimes odd | Very coherent |
| P(yes) accuracy | Varies | More reliable |

**Verdict:** Llama 2 is **slower but much better quality** for production.

---

## 🚨 Troubleshooting

### Issue 1: "Repository not found"

**Error:**
```
Repository meta-llama/Llama-2-7b-hf not found
```

**Solution:**
1. Make sure you accepted the license at https://huggingface.co/meta-llama/Llama-2-7b-hf
2. Wait 5-10 minutes after acceptance (approval is usually instant)
3. Make sure you're logged in: `huggingface-cli login`

---

### Issue 2: "Out of Memory"

**Error:**
```
RuntimeError: CUDA out of memory
```

**Solutions:**

**Option A: Use CPU**
```python
tracer = ActivationTracer(
    model_name="meta-llama/Llama-2-7b-hf",
    device="cpu"
)
```

**Option B: Use Smaller Model**
```python
# Try GPT-2 Large instead
tracer = ActivationTracer(model_name="gpt2-large")
```

**Option C: Increase System RAM**
- Close other applications
- Use a machine with 32GB+ RAM

---

### Issue 3: Slow Download

**Problem:** 13GB download taking forever

**Solutions:**
1. **Resume download if interrupted:**
   ```bash
   # Downloads are cached, just run again
   python -c "from glassbox import ActivationTracer; ActivationTracer('meta-llama/Llama-2-7b-hf')"
   ```

2. **Check download location:**
   ```bash
   # Models cached in:
   ~/.cache/huggingface/hub/
   ```

3. **Pre-download manually:**
   ```bash
   # Download ahead of time
   huggingface-cli download meta-llama/Llama-2-7b-hf
   ```

---

### Issue 4: Token Authentication Failed

**Error:**
```
Token is invalid
```

**Solution:**
1. Get new token: https://huggingface.co/settings/tokens
2. Make sure it's a "Read" token
3. Login again: `huggingface-cli login`

---

## 🔒 Production Deployment

### 1. Docker Setup

**Dockerfile:**
```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy code
COPY . .

# Set environment
ENV GLASSBOX_MODEL=meta-llama/Llama-2-7b-hf
ENV HF_TOKEN=your_token_here

# Pre-download model (optional)
RUN python -c "from glassbox import ActivationTracer; ActivationTracer('meta-llama/Llama-2-7b-hf')"

# Run API
CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Build & Run:**
```bash
docker build -t glassbox-llama .
docker run -p 8000:8000 -e HF_TOKEN=$HF_TOKEN glassbox-llama
```

---

### 2. Cloud Deployment (AWS/GCP/Azure)

**Requirements:**
- Instance: 32GB RAM minimum
- Storage: 20GB+
- Example AWS: `r5.xlarge` (32GB RAM)
- Example GCP: `n1-highmem-4` (26GB RAM)

**Setup:**
```bash
# SSH into your instance
ssh user@your-server

# Install dependencies
git clone your-repo
cd glassbox_mvp
pip install -r requirements.txt

# Login to HuggingFace
huggingface-cli login

# Start API
export GLASSBOX_MODEL=meta-llama/Llama-2-7b-hf
uvicorn api.server:app --host 0.0.0.0 --port 8000
```

---

### 3. Monitoring & Health Checks

**Check if model is loaded:**
```bash
curl http://localhost:8000/
# Should return: {"model": "meta-llama/Llama-2-7b-hf", ...}
```

**Test inference:**
```bash
curl -X POST http://localhost:8000/trace \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Q: Test? A:"}'
```

---

## 📊 Cost Analysis

### Running Llama 2 Locally vs API

**Local (One-time cost):**
- Hardware: $0 (use existing) or ~$2000 for GPU workstation
- Model: Free (open source)
- Ongoing: Just electricity (~$5/month)

**API (OpenAI GPT-4):**
- Per 1K tokens: ~$0.03
- 100K requests/month: ~$3000/month
- Cannot see internal activations ❌

**Verdict:** Local Llama 2 pays for itself quickly if you need interpretability!

---

## ✅ Production Checklist

Before deploying Llama 2 to production:

- [ ] HuggingFace account created
- [ ] Llama 2 license accepted
- [ ] Token generated and tested
- [ ] `huggingface-cli login` completed
- [ ] Model downloads successfully
- [ ] Test inference works
- [ ] Enough RAM (32GB+)
- [ ] Environment variables configured
- [ ] Error handling tested
- [ ] Monitoring set up
- [ ] Backup plan if OOM (fallback to GPT-2?)

---

## 🎓 Summary

### To Get Llama 2 for Production:

1. **Account Setup** (5 min)
   - Create HuggingFace account
   - Accept Llama 2 license
   - Get access token

2. **Installation** (2 min)
   ```bash
   huggingface-cli login
   pip install -r requirements.txt
   ```

3. **Configuration** (1 min)
   ```bash
   export GLASSBOX_MODEL=meta-llama/Llama-2-7b-hf
   ```

4. **First Load** (10-20 min)
   - Downloads ~13GB (one-time)
   - Subsequent loads are instant

5. **Deploy** (5 min)
   ```bash
   uvicorn api.server:app --host 0.0.0.0 --port 8000
   ```

### Recommended Production Setup:
```bash
# .env file
GLASSBOX_MODEL=meta-llama/Llama-2-7b-hf
HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GLASSBOX_PORT=8000
GLASSBOX_HOST=0.0.0.0
```

**Total Time:** ~30 minutes for first setup
**Cost:** Free (model is open source)
**Quality:** Much better than GPT-2 for production

---

**Need help? Check the troubleshooting section or ask!** 🚀
