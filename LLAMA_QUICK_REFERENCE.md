# Llama 2 - Quick Reference Card

## 🚀 One-Command Setup

```bash
./setup_llama.sh
```

That's it! The script will:
- Check if you're logged in
- Install dependencies
- Download Llama 2 (13GB, one-time)
- Test the model
- Show next steps

---

## 📋 Manual Setup (If Preferred)

### Step 1: Get Access
```bash
# 1. Create account: https://huggingface.co/join
# 2. Accept license: https://huggingface.co/meta-llama/Llama-2-7b-hf
# 3. Get token: https://huggingface.co/settings/tokens

# 4. Login
huggingface-cli login
# Paste your token when prompted
```

### Step 2: Install Dependencies
```bash
pip install transformers accelerate sentencepiece protobuf
```

### Step 3: Load Model
```python
from glassbox import ActivationTracer

tracer = ActivationTracer(model_name="meta-llama/Llama-2-7b-hf")
```

---

## 💻 Usage Examples

### Basic Decision Analysis
```python
from glassbox import ActivationTracer, DecisionAnalyzer

tracer = ActivationTracer(model_name="meta-llama/Llama-2-7b-hf")
analyzer = DecisionAnalyzer(tracer)

result, probs = analyzer.analyze_choices(
    "Q: Approve this loan? A:",
    ["yes", "no"]
)

print(f"Decision: {result.output_text}")
print(f"P(yes)={probs['yes']:.1%}, P(no)={probs['no']:.1%}")
```

### With Attention Analysis
```python
from glassbox import ActivationTracer, DecisionAnalyzer, AttentionAnalyzer

tracer = ActivationTracer(model_name="meta-llama/Llama-2-7b-hf")
decision_analyzer = DecisionAnalyzer(tracer)
attention_analyzer = AttentionAnalyzer()

# Get decision
result, probs = decision_analyzer.analyze_choices(
    "Q: Credit 750, income $80k, approve? A:",
    ["yes", "no"]
)

# Analyze why
top_heads = attention_analyzer.rank_attention_heads(
    result.attention_cache,
    result.tokens
)

print(f"Decision: {result.output_text}")
print(f"Top head: Layer {top_heads[0].layer}, Head {top_heads[0].head}")
```

---

## ⚙️ Configuration

### Environment Variables (.env)
```bash
GLASSBOX_MODEL=meta-llama/Llama-2-7b-hf
HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GLASSBOX_PORT=8000
```

### Use in API
```bash
export GLASSBOX_MODEL=meta-llama/Llama-2-7b-hf
uvicorn api.server:app --reload
```

### Use in Dashboard
```bash
export GLASSBOX_MODEL=meta-llama/Llama-2-7b-hf
streamlit run dashboard/app.py
```

---

## 🐛 Common Issues & Fixes

| Issue | Fix |
|-------|-----|
| "Repository not found" | Accept license at https://huggingface.co/meta-llama/Llama-2-7b-hf |
| "Token invalid" | Run `huggingface-cli login` with fresh token |
| "Out of memory" | Use `device="cpu"` or get 32GB+ RAM |
| Slow download | Just wait, downloads to `~/.cache/huggingface/` |

---

## 📊 Quick Comparison

| Aspect | GPT-2 Medium | Llama 2 7B |
|--------|--------------|------------|
| **Setup** | Instant | 5 min + download |
| **Quality** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Speed (CPU)** | ~5s | ~15s |
| **Memory** | 1.5GB | 14GB |
| **Use Case** | Testing | Production |

---

## 🎯 Quick Commands

```bash
# Check if logged in
huggingface-cli whoami

# Download model manually
huggingface-cli download meta-llama/Llama-2-7b-hf

# Test model
python -c "from glassbox import ActivationTracer; ActivationTracer('meta-llama/Llama-2-7b-hf')"

# Run with Llama
export GLASSBOX_MODEL=meta-llama/Llama-2-7b-hf
uvicorn api.server:app

# Check cache location
ls ~/.cache/huggingface/hub/
```

---

## 📖 Full Documentation

- **Complete Guide:** `LLAMA_SETUP_GUIDE.md`
- **Decision Analysis:** `QUICK_START_DECISIONS.md`
- **Model Requirements:** `MODEL_REQUIREMENTS.md`
- **All Questions:** `YOUR_QUESTIONS_ANSWERED.md`

---

## ⏱️ Time Estimates

- **Account setup:** 5 minutes
- **First download:** 10-30 minutes (13GB)
- **Model loading:** 10-20 seconds
- **Inference (CPU):** 10-20 seconds per trace
- **Inference (GPU):** 2-3 seconds per trace

---

## 💡 Pro Tips

1. **Download overnight** - 13GB can take time
2. **Use GPU if available** - 10x faster inference
3. **Cache is reused** - Only download once
4. **Start with GPT-2** - Test your code first
5. **Monitor RAM** - Need 30GB+ total

---

**Need help? Read `LLAMA_SETUP_GUIDE.md` for detailed instructions!**
