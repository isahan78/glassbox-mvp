# Model Storage & Custom Locations Guide

## ✅ Good News: You Have Enough RAM!

**Your RAM:** 36GB
**Llama 2 7B Needs:** ~30GB total
- System: ~16GB
- Model in memory: ~14GB
- **You have 6GB headroom!** ✅

---

## 📦 How Model Storage Works

### Two Different Storage Locations

1. **Disk Storage** (Permanent)
   - Where model files are saved
   - Default: `~/.cache/huggingface/hub/`
   - Size: ~13GB for Llama 2 7B
   - Only downloaded once

2. **RAM** (Temporary)
   - Where model loads when running
   - Size: ~14GB for Llama 2 7B
   - Only while model is active
   - Clears when you stop the program

**You can customize the disk location, but RAM usage is automatic.**

---

## 🗂️ Changing Model Cache Location

### Option 1: Environment Variable (Recommended)

```bash
# Set custom cache location
export HF_HOME=/path/to/your/storage/huggingface
export TRANSFORMERS_CACHE=/path/to/your/storage/models

# For example, use external drive:
export HF_HOME=/Volumes/ExternalDrive/ai-models/huggingface
export TRANSFORMERS_CACHE=/Volumes/ExternalDrive/ai-models/cache
```

**Make it permanent:**
```bash
# Add to ~/.bashrc or ~/.zshrc
echo 'export HF_HOME=/Volumes/ExternalDrive/ai-models/huggingface' >> ~/.zshrc
echo 'export TRANSFORMERS_CACHE=/Volumes/ExternalDrive/ai-models/cache' >> ~/.zshrc

# Reload
source ~/.zshrc
```

---

### Option 2: Symlink (Easy Alternative)

Move existing cache to external drive:

```bash
# 1. Stop any running models
pkill -f streamlit
pkill -f uvicorn

# 2. Move cache to external drive
mv ~/.cache/huggingface /Volumes/ExternalDrive/huggingface-cache

# 3. Create symlink
ln -s /Volumes/ExternalDrive/huggingface-cache ~/.cache/huggingface

# 4. Test it
ls -la ~/.cache/huggingface
# Should show: ~/.cache/huggingface -> /Volumes/ExternalDrive/huggingface-cache
```

**Advantages:**
- ✅ Transparent to all apps
- ✅ No environment variables needed
- ✅ Works system-wide

---

### Option 3: Custom Download Location

Download to specific location when loading:

```python
from transformers import AutoModelForCausalLM, AutoTokenizer
import os

# Set cache directory
cache_dir = "/Volumes/ExternalDrive/ai-models"

# Download/load model to custom location
model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-2-7b-hf",
    cache_dir=cache_dir
)

tokenizer = AutoTokenizer.from_pretrained(
    "meta-llama/Llama-2-7b-hf",
    cache_dir=cache_dir
)
```

**For GlassBox:**
```python
import os
os.environ['TRANSFORMERS_CACHE'] = '/Volumes/ExternalDrive/ai-models'

from glassbox import ActivationTracer
tracer = ActivationTracer(model_name="meta-llama/Llama-2-7b-hf")
```

---

## 💾 Storage Options

### Option A: External SSD/HDD (Recommended)

**Pros:**
- ✅ Fast access
- ✅ Easy to set up
- ✅ Portable

**Setup:**
```bash
# Create directory structure
mkdir -p /Volumes/ExternalDrive/ai-models/huggingface
mkdir -p /Volumes/ExternalDrive/ai-models/cache

# Set environment
export HF_HOME=/Volumes/ExternalDrive/ai-models/huggingface
export TRANSFORMERS_CACHE=/Volumes/ExternalDrive/ai-models/cache

# Download model
python -c "from glassbox import ActivationTracer; ActivationTracer('meta-llama/Llama-2-7b-hf')"
```

**Performance:**
- SSD: Same as internal (~15s load time)
- HDD: Slower load (~30-60s), but fine once loaded

---

### Option B: Network Storage (NAS)

**Pros:**
- ✅ Shared across multiple machines
- ✅ Centralized storage

**Cons:**
- ⚠️ Slower loading (network speed dependent)
- ⚠️ Requires network connection

**Setup:**
```bash
# Mount NAS
mkdir -p /mnt/nas
mount -t nfs nas.local:/ai-models /mnt/nas

# Set environment
export HF_HOME=/mnt/nas/huggingface
export TRANSFORMERS_CACHE=/mnt/nas/cache

# Download
python -c "from glassbox import ActivationTracer; ActivationTracer('meta-llama/Llama-2-7b-hf')"
```

---

### Option C: Cloud Storage (Advanced)

Mount cloud storage locally:

**Using rclone:**
```bash
# Install rclone
brew install rclone  # macOS
# or: apt install rclone  # Linux

# Configure cloud storage (e.g., Google Drive, S3)
rclone config

# Mount cloud storage
mkdir -p ~/cloud-models
rclone mount gdrive:ai-models ~/cloud-models --daemon

# Use it
export HF_HOME=~/cloud-models/huggingface
python -c "from glassbox import ActivationTracer; ActivationTracer('meta-llama/Llama-2-7b-hf')"
```

**Performance:**
- ⚠️ Very slow first load (downloads from cloud)
- ⚠️ Requires internet
- ✅ Good for backup/sharing

---

## 📍 Current Cache Location

### Check Where Models Are Stored

```bash
# Check default cache location
echo $HF_HOME
echo $TRANSFORMERS_CACHE

# If empty, defaults to:
echo ~/.cache/huggingface

# List downloaded models
ls -lh ~/.cache/huggingface/hub/

# Check size
du -sh ~/.cache/huggingface/
```

---

## 🔄 Moving Existing Models

### If you already downloaded Llama 2 and want to move it:

```bash
# 1. Check current location
ls -lh ~/.cache/huggingface/hub/

# 2. Stop running processes
pkill -f streamlit
pkill -f uvicorn

# 3. Move to new location
mv ~/.cache/huggingface /Volumes/ExternalDrive/huggingface-cache

# 4. Create symlink
ln -s /Volumes/ExternalDrive/huggingface-cache ~/.cache/huggingface

# 5. Verify
ls -la ~/.cache/ | grep huggingface
# Should show: huggingface -> /Volumes/ExternalDrive/huggingface-cache

# 6. Test
python -c "from glassbox import ActivationTracer; t = ActivationTracer('meta-llama/Llama-2-7b-hf'); print('✅ Works!')"
```

---

## 🚀 Performance Comparison

### Loading Speed by Storage Type

| Storage Type | Load Time | Notes |
|--------------|-----------|-------|
| Internal SSD | ~10-15s | Fastest |
| External SSD (USB 3.0+) | ~15-20s | Nearly same as internal |
| External HDD | ~30-60s | Slower, but OK once loaded |
| Network Storage (1Gbps) | ~45-90s | Depends on network |
| Cloud Storage | ~5-30 min | Very slow, not recommended |

**Once loaded into RAM, performance is identical!**

---

## 💡 Best Practices

### For Your Setup (36GB RAM)

**Recommended:**
1. **Use external SSD** if you need space
2. **Symlink approach** for transparency
3. **Keep models on SSD** (not HDD) for fast loading

**Example Setup:**
```bash
# 1. Create directory on external SSD
mkdir -p /Volumes/MySSD/ai-models

# 2. Move cache
mv ~/.cache/huggingface /Volumes/MySSD/ai-models/huggingface

# 3. Create symlink
ln -s /Volumes/MySSD/ai-models/huggingface ~/.cache/huggingface

# 4. Done! Everything works transparently
```

---

## 🔧 Configuration for Production

### .env File Setup

```bash
# .env file
GLASSBOX_MODEL=meta-llama/Llama-2-7b-hf
HF_HOME=/Volumes/MySSD/ai-models/huggingface
TRANSFORMERS_CACHE=/Volumes/MySSD/ai-models/cache
HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Startup Script

```bash
#!/bin/bash
# start_glassbox.sh

# Set environment
export HF_HOME=/Volumes/MySSD/ai-models/huggingface
export TRANSFORMERS_CACHE=/Volumes/MySSD/ai-models/cache
export GLASSBOX_MODEL=meta-llama/Llama-2-7b-hf

# Start API
uvicorn api.server:app --host 0.0.0.0 --port 8000
```

---

## 📊 Disk Space Requirements

### What You Need

| Component | Size | Location |
|-----------|------|----------|
| **Model Files** | 13GB | Disk (cache) |
| **GlassBox Code** | <100MB | Your project folder |
| **Dependencies** | ~2GB | Python packages |
| **Trace Data** | Varies | `data/traces/` |
| **Total** | ~15-20GB | Disk |

**Plus RAM:**
- Model in memory: 14GB
- System: 16GB
- **Total RAM:** 30GB

**Your 36GB RAM:** ✅ Perfect!

---

## 🛠️ Advanced: Shared Model Across Multiple Machines

### Option 1: NFS Share

**Server (has models):**
```bash
# Install NFS server
sudo apt install nfs-kernel-server

# Configure exports
echo "/path/to/models *(ro,sync,no_subtree_check)" | sudo tee -a /etc/exports

# Restart NFS
sudo systemctl restart nfs-kernel-server
```

**Clients:**
```bash
# Mount models
sudo mount server.local:/path/to/models /mnt/shared-models

# Use them
export HF_HOME=/mnt/shared-models/huggingface
python -c "from glassbox import ActivationTracer; ActivationTracer('meta-llama/Llama-2-7b-hf')"
```

---

### Option 2: Model Server (Remote Inference)

For very limited disk space, run model on a separate server:

**Server Side:**
```python
# server_model.py
from fastapi import FastAPI
from glassbox import ActivationTracer
import uvicorn

app = FastAPI()
tracer = ActivationTracer(model_name="meta-llama/Llama-2-7b-hf")

@app.post("/predict")
def predict(prompt: str):
    result = tracer.trace(prompt)
    return {"output": result.output_text}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9000)
```

**Client Side:**
```python
import requests

response = requests.post(
    "http://model-server:9000/predict",
    json={"prompt": "Q: Approve? A:"}
)
print(response.json())
```

**Note:** This loses interpretability! Only do this if you have no choice.

---

## ⚠️ Common Issues

### Issue 1: "No space left on device"

**Check space:**
```bash
df -h
```

**Solutions:**
1. Use external drive
2. Clean old models: `rm -rf ~/.cache/huggingface/hub/models--*old-model*`
3. Move cache: See symlink method above

---

### Issue 2: "Permission denied"

**Fix permissions:**
```bash
# Make sure you own the directory
sudo chown -R $USER:$USER /Volumes/ExternalDrive/ai-models

# Make it writable
chmod -R u+w /Volumes/ExternalDrive/ai-models
```

---

### Issue 3: External drive unmounted

**Auto-mount on startup:**

**macOS:**
```bash
# Add to /etc/fstab or use Disk Utility to enable auto-mount
```

**Linux:**
```bash
# Add to /etc/fstab
echo "UUID=xxx /mnt/models ext4 defaults 0 2" | sudo tee -a /etc/fstab
```

---

## ✅ Quick Setup for Your 36GB RAM

Since you have enough RAM, here's the simplest approach:

### If You Have Disk Space:
```bash
# Just use defaults - you're all set!
./setup_llama.sh
```

### If You Need to Save Internal Disk Space:
```bash
# Use external SSD
export HF_HOME=/Volumes/ExternalSSD/ai-models
./setup_llama.sh
```

---

## 📋 Summary

### Your Situation:
- ✅ **RAM:** 36GB (enough for Llama 2 7B!)
- ❓ **Disk:** May want to use external storage

### Recommended Setup:
```bash
# If using external drive:
mkdir -p /Volumes/MySSD/ai-models
export HF_HOME=/Volumes/MySSD/ai-models
export TRANSFORMERS_CACHE=/Volumes/MySSD/ai-models/cache

# Download
./setup_llama.sh

# Models stored on external drive, loaded to your 36GB RAM ✅
```

### Storage Locations:
- **Model files (disk):** External SSD (~13GB)
- **Model in memory (RAM):** Your 36GB RAM (~14GB used)
- **Best of both worlds!**

---

**You're all set! Your 36GB RAM is perfect for Llama 2.** 🎉
