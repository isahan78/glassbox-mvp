# Getting Llama 2 for Production - Complete Guide

## 🎯 TL;DR - Fastest Way

```bash
# 1. Get HuggingFace account & accept license (5 min)
# Visit: https://huggingface.co/meta-llama/Llama-2-7b-hf

# 2. Login
huggingface-cli login

# 3. Run automated setup
./setup_llama.sh

# Done! ✅
```

---

## 📚 What I Created For You

I've created **comprehensive documentation** to help you set up Llama 2:

### 1. **LLAMA_SETUP_GUIDE.md** (Complete Guide)
- Step-by-step setup instructions
- Hardware requirements
- Troubleshooting guide
- Production deployment
- Docker setup
- Cloud deployment
- Performance benchmarks

### 2. **LLAMA_QUICK_REFERENCE.md** (Cheat Sheet)
- Quick commands
- Common issues & fixes
- Configuration examples
- Time estimates
- Pro tips

### 3. **setup_llama.sh** (Automated Setup)
- One-command installation
- Checks dependencies
- Downloads model
- Tests everything
- Shows next steps

---

## 🚀 Three Ways to Get Started

### Option A: Automated (Easiest)

```bash
# Just run this:
./setup_llama.sh
```

**What it does:**
- ✅ Checks if you're logged in
- ✅ Installs dependencies
- ✅ Downloads Llama 2 (13GB)
- ✅ Tests the model
- ✅ Shows you what to do next

---

### Option B: Manual (Step-by-Step)

#### Step 1: Get HuggingFace Access
```bash
# 1. Create account: https://huggingface.co/join
# 2. Accept license: https://huggingface.co/meta-llama/Llama-2-7b-hf
#    (Click "Access repository", instant approval)
# 3. Get token: https://huggingface.co/settings/tokens
#    (Create "Read" token, copy it)
```

#### Step 2: Login
```bash
huggingface-cli login
# Paste your token (starts with hf_...)
```

#### Step 3: Install Dependencies
```bash
pip install transformers>=4.31.0
pip install accelerate>=0.20.0
pip install sentencepiece>=0.1.99
pip install protobuf>=3.20.0
```

#### Step 4: Test It
```python
from glassbox import ActivationTracer

print("Loading Llama 2 7B...")
tracer = ActivationTracer(model_name="meta-llama/Llama-2-7b-hf")
print("✅ Success!")
```

---

### Option C: Quick Test (Before Downloading)

Want to verify everything works before downloading 13GB?

```bash
# Test with GPT-2 first (instant download)
python -c "
from glassbox import ActivationTracer
tracer = ActivationTracer('gpt2-medium')
print('✅ GlassBox works! Ready for Llama.')
"

# Then proceed with Llama setup
```

---

## 💻 Hardware Check

**Before downloading, make sure you have:**

✅ **RAM:** 16GB system + 14GB for model = **30GB total**
✅ **Storage:** 15GB free space
✅ **CPU:** Any modern multi-core processor
🔲 **GPU:** Optional but 10x faster (16GB VRAM recommended)

**Check your RAM:**
```bash
# macOS
sysctl hw.memsize | awk '{print $2/1024/1024/1024 " GB"}'

# Linux
free -h | grep Mem | awk '{print $2}'
```

If you don't have enough RAM, **use GPT-2** instead:
```python
# Still great for testing and development!
tracer = ActivationTracer(model_name="gpt2-medium")
```

---

## ⏱️ What to Expect

### First Time Setup Timeline

1. **HuggingFace account:** 2 minutes
2. **Accept license:** 1 minute (instant approval)
3. **Get token & login:** 2 minutes
4. **Download model:** 10-30 minutes (depends on internet)
5. **Test loading:** 10-20 seconds

**Total:** ~15-35 minutes (mostly waiting for download)

### After Setup

- **Loading model:** 10-20 seconds
- **Inference (CPU):** 10-20 seconds per trace
- **Inference (GPU):** 2-3 seconds per trace

---

## 🎯 Production Usage

### For API Server

```bash
# In .env file
GLASSBOX_MODEL=meta-llama/Llama-2-7b-hf

# Start server
uvicorn api.server:app --host 0.0.0.0 --port 8000
```

### For Dashboard

```bash
# In .env file
GLASSBOX_MODEL=meta-llama/Llama-2-7b-hf

# Start dashboard
streamlit run dashboard/app.py
```

### In Python Code

```python
from glassbox import ActivationTracer, DecisionAnalyzer

# Production setup
tracer = ActivationTracer(model_name="meta-llama/Llama-2-7b-hf")
analyzer = DecisionAnalyzer(tracer)

# Use it
result, probs = analyzer.analyze_choices(
    "Q: Should we approve this loan? A:",
    ["yes", "no"]
)

print(f"Decision: {result.output_text}")
print(f"Confidence: {probs['yes']:.1%} yes, {probs['no']:.1%} no")
```

---

## 🔒 Why Llama 2 for Production?

### vs GPT-2
| Aspect | GPT-2 Medium | Llama 2 7B |
|--------|--------------|------------|
| Quality | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Coherence | Sometimes odd | Very coherent |
| Reliability | Varies | Consistent |
| Modern | 2019 | 2023 |

### vs GPT-4 API
| Aspect | GPT-4 API | Llama 2 Local |
|--------|-----------|---------------|
| Quality | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Interpretability** | ❌ None | ✅ Full |
| **Privacy** | ❌ Cloud | ✅ Local |
| **Cost** | $$$ per call | Free |
| **Audit Trail** | ❌ No | ✅ Yes |

**Winner for GlassBox:** Llama 2 (only option that gives you internal access)

---

## 🐛 Common Issues

### "Repository not found"
**Fix:** Accept the license at https://huggingface.co/meta-llama/Llama-2-7b-hf

### "Out of memory"
**Fix:** Close other apps or use GPT-2 instead

### "Slow download"
**Fix:** Wait it out, downloads to cache (only once)

### "Token invalid"
**Fix:** Generate new token, run `huggingface-cli login` again

---

## 📖 Next Steps After Setup

Once Llama 2 is installed:

1. **Test it:**
   ```python
   from glassbox import ActivationTracer, DecisionAnalyzer

   tracer = ActivationTracer("meta-llama/Llama-2-7b-hf")
   analyzer = DecisionAnalyzer(tracer)

   result, probs = analyzer.analyze_choices(
       "Q: Approve this loan? A:",
       ["yes", "no"]
   )

   print(result.output_text, probs)
   ```

2. **Read the guides:**
   - `QUICK_START_DECISIONS.md` - How to use it
   - `YOUR_QUESTIONS_ANSWERED.md` - FAQ
   - `MODEL_REQUIREMENTS.md` - Deep dive

3. **Run examples:**
   ```bash
   cd examples
   python decision_analysis.py
   ```

4. **Deploy:**
   - Local: `uvicorn api.server:app`
   - Dashboard: `streamlit run dashboard/app.py`
   - Docker: See `LLAMA_SETUP_GUIDE.md`

---

## 💡 Pro Tips

1. **Download overnight** if slow internet
2. **Start with GPT-2** to test your code
3. **Use GPU** if available (10x faster)
4. **Cache location:** `~/.cache/huggingface/hub/`
5. **Only download once** - subsequent loads are instant
6. **Monitor RAM usage** during first load
7. **Set GLASSBOX_MODEL** env var for easy switching

---

## 🎓 Summary

### To Get Llama 2 for Production:

**Quick Version:**
```bash
./setup_llama.sh
```

**Manual Version:**
```bash
# 1. Get account & accept license (5 min)
# 2. Login
huggingface-cli login

# 3. Load model (downloads 13GB first time)
python -c "from glassbox import ActivationTracer; ActivationTracer('meta-llama/Llama-2-7b-hf')"
```

**Total Time:** 15-35 minutes (mostly download wait)
**Cost:** FREE (open source)
**Quality:** Production-ready ⭐⭐⭐⭐⭐

---

## 📞 Need Help?

1. **Check troubleshooting:** `LLAMA_SETUP_GUIDE.md`
2. **Quick reference:** `LLAMA_QUICK_REFERENCE.md`
3. **Run setup script:** `./setup_llama.sh`
4. **Ask me!**

---

## ✅ Pre-Flight Checklist

Before starting, make sure you have:

- [ ] 30GB+ RAM (16GB system + 14GB for model)
- [ ] 15GB free disk space
- [ ] Stable internet (for 13GB download)
- [ ] Python 3.10+ installed
- [ ] Virtual environment activated
- [ ] Time to wait for download (10-30 min)

**All set? Run `./setup_llama.sh` and let it do the work!** 🚀

---

**Quick Start Command:**
```bash
./setup_llama.sh && echo "✅ Ready for production with Llama 2!"
```
