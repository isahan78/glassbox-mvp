# Model Requirements for GlassBox

## ❓ Do You Need Open-Source Models?

**YES** - GlassBox **ONLY works with open-source models** that you can run locally or have full access to.

## 🔍 Why Open-Source Models?

### What GlassBox Needs

To analyze how a model makes decisions, GlassBox needs access to:

1. **Internal Activations** - The hidden states between layers
2. **Attention Patterns** - Which tokens each attention head focuses on
3. **Layer Outputs** - The residual stream after each transformer block
4. **Model Weights** - To hook into the forward pass

### What You CAN'T Use

❌ **OpenAI API** (GPT-4, GPT-3.5, etc.)
- Only gives you final output text
- No access to internal activations
- API is a black box

❌ **Anthropic API** (Claude)
- Same issue - black box API
- No internal access

❌ **Google PaLM API**
- Same issue

❌ **Any Closed API Service**

**Why?** These services only return the final text output. You cannot see:
- What the attention heads are doing
- Which tokens influenced the prediction
- Internal layer activations

It's like asking "why did you make this decision?" and only getting the answer, not the reasoning.

---

## ✅ What You CAN Use

### Currently Supported Models

GlassBox uses **TransformerLens**, which supports:

#### 1. **GPT-2 Family** (Recommended for Testing)
```python
tracer = ActivationTracer(model_name="gpt2-small")   # 124M params, ~500MB
tracer = ActivationTracer(model_name="gpt2-medium")  # 355M params, ~1.5GB ⭐
tracer = ActivationTracer(model_name="gpt2-large")   # 774M params, ~3GB
tracer = ActivationTracer(model_name="gpt2-xl")      # 1.5B params, ~6GB
```

**Pros:**
- ✅ Fast to load
- ✅ Low memory usage
- ✅ Good for testing and demos
- ✅ No authentication needed

**Cons:**
- ❌ Not as capable as modern models
- ❌ Not instruction-tuned
- ❌ May give weird responses

---

#### 2. **Llama 2 Family** (Recommended for Production)
```python
tracer = ActivationTracer(model_name="meta-llama/Llama-2-7b-hf")   # 7B params, ~14GB ⭐⭐
tracer = ActivationTracer(model_name="meta-llama/Llama-2-13b-hf")  # 13B params, ~26GB
```

**Pros:**
- ✅ Modern, capable model
- ✅ Better reasoning
- ✅ More coherent outputs
- ✅ Good instruction following

**Cons:**
- ❌ Requires HuggingFace account & license acceptance
- ❌ Higher memory usage (14GB+)
- ❌ Slower inference

**Setup:**
```bash
# 1. Create HuggingFace account: https://huggingface.co/
# 2. Accept license: https://huggingface.co/meta-llama/Llama-2-7b-hf
# 3. Get token: https://huggingface.co/settings/tokens
# 4. Login:
huggingface-cli login
```

---

#### 3. **Mistral 7B**
```python
tracer = ActivationTracer(model_name="mistral-7b")  # 7B params, ~14GB
```

**Pros:**
- ✅ Modern architecture
- ✅ Efficient
- ✅ Good performance

---

#### 4. **GPT-J 6B**
```python
tracer = ActivationTracer(model_name="EleutherAI/gpt-j-6B")  # 6B params, ~12GB
```

---

#### 5. **GPT-Neo**
```python
tracer = ActivationTracer(model_name="EleutherAI/gpt-neo-1.3B")
tracer = ActivationTracer(model_name="EleutherAI/gpt-neo-2.7B")
```

---

## 🎯 Which Model Should You Use?

### For Testing / Development
**Use: GPT-2 Medium**
- Fast
- Low memory
- Good enough for testing

```python
tracer = ActivationTracer(model_name="gpt2-medium")
```

### For Demos / Presentations
**Use: GPT-2 Medium or Llama 2 7B**
- GPT-2 Medium: Faster, simpler setup
- Llama 2 7B: More impressive results, but slower

### For Production / Real Analysis
**Use: Llama 2 7B or 13B**
- Better quality decisions
- More interpretable attention patterns
- Modern architecture

```python
tracer = ActivationTracer(model_name="meta-llama/Llama-2-7b-hf")
```

---

## 💻 Hardware Requirements

### Minimum (GPT-2 Small/Medium)
- **RAM:** 4GB
- **CPU:** Any modern CPU
- **GPU:** Not required (but faster)

### Recommended (GPT-2 Large, Llama 2 7B)
- **RAM:** 16GB+
- **CPU:** Modern multi-core
- **GPU:** 8GB VRAM (optional but 5-10x faster)

### For Llama 2 13B+
- **RAM:** 32GB+
- **GPU:** 16GB+ VRAM recommended

---

## 🚀 Can You Use Custom Models?

**YES** - if they're compatible with TransformerLens!

TransformerLens supports models with these architectures:
- GPT-2 / GPT-Neo / GPT-J
- Llama / Llama 2
- Mistral
- OPT
- BLOOM
- And others

To use a custom model:

```python
# If it's on HuggingFace and compatible:
tracer = ActivationTracer(model_name="organization/model-name")

# Example with a fine-tuned model:
tracer = ActivationTracer(model_name="your-org/your-finetuned-llama-2")
```

---

## 📊 Quality Comparison

| Model | Size | Speed | Quality | Memory | Setup Complexity |
|-------|------|-------|---------|--------|------------------|
| GPT-2 Small | 124M | ⚡⚡⚡ | ⭐⭐ | 500MB | Easy |
| GPT-2 Medium | 355M | ⚡⚡ | ⭐⭐⭐ | 1.5GB | Easy |
| GPT-2 Large | 774M | ⚡ | ⭐⭐⭐ | 3GB | Easy |
| Llama 2 7B | 7B | ⚡ | ⭐⭐⭐⭐⭐ | 14GB | Medium |
| Llama 2 13B | 13B | 🐌 | ⭐⭐⭐⭐⭐ | 26GB | Medium |

---

## ⚠️ Important Limitations

### 1. No Closed APIs
You **CANNOT** use:
- OpenAI (GPT-4, ChatGPT)
- Anthropic (Claude)
- Google (PaLM, Gemini)
- Cohere

**Why?** No access to internal activations.

### 2. Local Execution Required
Models run **on your hardware**, not in the cloud (unless you set up your own cloud instance).

### 3. Slower Than API Calls
- API call to GPT-4: ~1-2 seconds
- GlassBox with GPT-2: ~3-5 seconds
- GlassBox with Llama 2: ~10-20 seconds (CPU)

**Why?** We're capturing ALL internal activations, which is slower.

### 4. Limited Context Length
- GPT-2: Max 1024 tokens
- Llama 2: Max 4096 tokens (but slower)

---

## 🔐 Privacy Benefit

**HUGE ADVANTAGE:** Your data never leaves your machine!

With closed APIs:
- Your prompts are sent to external servers
- Data may be logged
- Privacy concerns for sensitive data

With GlassBox:
- Everything runs locally
- No data sent anywhere
- Perfect for sensitive/confidential data
- Compliance-friendly (HIPAA, GDPR, etc.)

---

## 🎓 Summary

### You NEED Open-Source Models Because:

1. ✅ **Access to Internals** - See attention patterns and activations
2. ✅ **Privacy** - Data stays local
3. ✅ **Cost** - No API fees after initial download
4. ✅ **Reproducibility** - Same model, same results
5. ✅ **Compliance** - Meet regulatory requirements

### You CAN'T Use Closed APIs Because:

1. ❌ No internal access
2. ❌ Black box behavior
3. ❌ Cannot see attention
4. ❌ Cannot trace decisions
5. ❌ Not interpretable with GlassBox

---

## 🚀 Quick Start Recommendations

### Beginner / Testing
```bash
# Fastest setup, lowest memory
python -c "from glassbox import ActivationTracer; tracer = ActivationTracer('gpt2-medium')"
```

### Production / Real Analysis
```bash
# Best quality, requires HuggingFace login
huggingface-cli login
python -c "from glassbox import ActivationTracer; tracer = ActivationTracer('meta-llama/Llama-2-7b-hf')"
```

### Custom Fine-Tuned Model
```bash
# If you have a custom fine-tuned Llama/GPT model
python -c "from glassbox import ActivationTracer; tracer = ActivationTracer('your-org/your-model')"
```

---

## ❓ FAQ

**Q: Can I use GPT-4 with GlassBox?**
A: No. GPT-4 is a closed API with no internal access.

**Q: What about Claude or Gemini?**
A: Same issue - no internal access.

**Q: Can I use my own fine-tuned model?**
A: Yes! As long as it's based on a supported architecture (GPT-2, Llama, etc.)

**Q: Is internet required?**
A: Only for initial model download. After that, everything runs offline.

**Q: Can I run this in the cloud?**
A: Yes! Set up a VM with enough RAM and run GlassBox there.

**Q: What about smaller/faster models?**
A: Distilled models (DistilGPT-2, etc.) work if TransformerLens supports them.

---

**Need help choosing a model? Start with `gpt2-medium` for testing, then upgrade to `Llama-2-7b-hf` for production!**
