# 🧠 GlassBox MVP

**Interpretable-by-design AI runtime that captures and visualizes how language models arrive at their outputs.**

[![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)](https://github.com/yourorg/glassbox)
[![Python](https://img.shields.io/badge/python-3.10+-green.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-orange.svg)](LICENSE)
[![Models](https://img.shields.io/badge/models-GPT--2%20%7C%20Llama%202%20%7C%20Mistral-purple.svg)](https://transformerlens.org)

> *"Finally understand what your language model is thinking."*

---

## 🎯 What is GlassBox?

Modern LLMs are black boxes. **GlassBox** opens them up by:

- 🔍 **Capturing attention patterns** during inference
- 📊 **Ranking attention heads** by contribution
- 🎯 **Showing token influence** on outputs
- 📝 **Generating audit trails** for compliance
- 🎨 **Visualizing decisions** interactively

**Perfect for:** AI safety researchers, enterprise ML teams, and anyone who needs to understand *why* a model made a decision.

---

## ✨ Features

### Core Capabilities

✅ **Multi-Model Support**
- GPT-2 (Small, Medium, Large, XL)
- Llama 2 7B/13B (recommended!)
- Mistral 7B
- GPT-J 6B and more

✅ **Real-Time Analysis**
- Capture all 144 attention heads (GPT-2) or 1024 heads (Llama 2)
- Rank heads by contribution scores
- Compute token-level influence

✅ **Interactive Dashboard**
- Beautiful Streamlit interface
- Attention heatmaps and bar charts
- Model switching in UI
- Trace browsing and search

✅ **REST API**
- FastAPI endpoints
- JSON trace artifacts
- Programmatic access
- Auto-generated docs

✅ **Compliance Ready**
- Structured JSON traces
- Timestamped audit trails
- Performance metrics
- Reproducible results

---

## 🚀 Quick Start

### Installation (5 minutes)

```bash
# 1. Clone the repository
git clone https://github.com/yourorg/glassbox-mvp.git
cd glassbox-mvp

# 2. Create virtual environment
python3.10 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install GlassBox
pip install -e .

# 5. Test installation
python glassbox/tracer.py
```

### For Llama 2 (recommended with 36GB+ RAM)

```bash
# Get HuggingFace token from https://huggingface.co/settings/tokens
huggingface-cli login

# Accept license at https://huggingface.co/meta-llama/Llama-2-7b-hf
# Then test:
python glassbox/tracer.py meta-llama/Llama-2-7b-hf
```

See [LLAMA_SETUP.md](LLAMA_SETUP.md) for detailed setup.

---

## 📖 Usage Examples

### 1. Basic Tracing (Python)

```python
from glassbox.tracer import ActivationTracer
from glassbox.analyzer import AttentionAnalyzer

# Initialize with your chosen model
tracer = ActivationTracer(model_name="gpt2-medium")  # or "meta-llama/Llama-2-7b-hf"
analyzer = AttentionAnalyzer()

# Run trace
prompt = "Should we approve this loan application?"
result = tracer.trace(prompt)

# Analyze attention
top_heads = analyzer.rank_attention_heads(
    result.attention_cache,
    result.tokens
)

# Print results
print(f"Output: {result.output_text}")
print(f"Top contributing head: Layer {top_heads[0].layer}, Head {top_heads[0].head}")
print(f"Score: {top_heads[0].score:.3f}")
```

### 2. Interactive Dashboard

```bash
streamlit run dashboard/app.py
```

Then visit `http://localhost:8501`

**Features:**
- Create new traces with any prompt
- Select model from dropdown (GPT-2, Llama 2, Mistral)
- View attention head rankings
- Explore token influence heatmaps
- Browse saved traces

### 3. REST API

```bash
# Start API server
uvicorn api.server:app --reload --port 8000

# View docs at http://localhost:8000/docs
```

**Create a trace:**
```bash
curl -X POST http://localhost:8000/trace \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "The capital of France is",
    "config": {
      "capture_layers": [8, 9, 10],
      "max_seq_length": 128
    }
  }'
```

**Get trace:**
```bash
curl http://localhost:8000/trace/20251025_143022_abc123
```

### 4. Jupyter Notebook

```bash
jupyter notebook notebooks/01_quickstart.ipynb
```

---

## 📊 Example Output

### JSON Trace Structure

```json
{
  "trace_id": "20251025_143022_abc123",
  "model": "meta-llama/Llama-2-7b-hf",
  "input": {
    "text": "Should we approve this loan application?",
    "tokens": ["Should", "we", "approve", ...]
  },
  "output": {
    "text": "Yes",
    "probability": 0.73
  },
  "attribution": {
    "top_attention_heads": [
      {
        "layer": 15,
        "head": 8,
        "score": 0.84,
        "top_attended_tokens": [
          {"token": "loan", "weight": 0.52},
          {"token": "approve", "weight": 0.31}
        ]
      }
    ],
    "token_influence": {
      "loan": 0.71,
      "approve": 0.58,
      "application": 0.43
    }
  },
  "performance": {
    "inference_time_ms": 12450,
    "slowdown_factor": 4.2
  }
}
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────┐
│   Streamlit Dashboard               │
│   FastAPI REST API                  │
└─────────────┬───────────────────────┘
              │
┌─────────────▼───────────────────────┐
│   Trace Store (JSON files)          │
│   - Date-based organization         │
│   - Searchable metadata             │
└─────────────┬───────────────────────┘
              │
┌─────────────▼───────────────────────┐
│   GlassBox Core Library             │
│   ┌─────────────────────────────┐   │
│   │ Tracer (Hook Manager)       │   │
│   │ - Captures activations      │   │
│   │ - Records attention         │   │
│   └─────────────────────────────┘   │
│   ┌─────────────────────────────┐   │
│   │ Analyzer                    │   │
│   │ - Ranks attention heads     │   │
│   │ - Computes token influence  │   │
│   └─────────────────────────────┘   │
│   ┌─────────────────────────────┐   │
│   │ Serializer                  │   │
│   │ - Generates JSON traces     │   │
│   │ - Manages persistence       │   │
│   └─────────────────────────────┘   │
└─────────────┬───────────────────────┘
              │
┌─────────────▼───────────────────────┐
│   TransformerLens                   │
│   - Model loading                   │
│   - Hook registration               │
│   - Activation capture              │
└─────────────────────────────────────┘
```

---

## 📈 Performance

Tested on MacBook Pro M1 and standard VMs:

| Model | Params | Inference Time | Memory | Slowdown |
|-------|--------|----------------|--------|----------|
| GPT-2 Small | 124M | ~3s | 2GB | 3-4x |
| GPT-2 Medium | 355M | ~5s | 3GB | 3-5x |
| GPT-2 Large | 774M | ~8s | 5GB | 4-6x |
| **Llama 2 7B** | **7B** | **~15s** | **14GB** | **4-5x** |
| Mistral 7B | 7B | ~12s | 14GB | 3-4x |

*Times for short prompts (~10 tokens) on CPU. GPU speeds up 5-10x.*

---

## 🎓 Use Cases

### AI Safety Research
- Study attention patterns and circuits
- Identify failure modes
- Validate interpretability hypotheses
- Compare models systematically

### Enterprise ML
- Generate compliance audit trails
- Debug unexpected behaviors
- Trace decisions for regulated industries
- Build trust with stakeholders

### Education & Demos
- Show how transformers work internally
- Create interactive explanations
- Teach mechanistic interpretability
- Impress technical audiences

---

## ⚙️ Configuration

### Model Selection

```python
# Fast iteration (355M params)
tracer = ActivationTracer(model_name="gpt2-medium")

# Best quality (7B params) ⭐ RECOMMENDED
tracer = ActivationTracer(model_name="meta-llama/Llama-2-7b-hf")

# Efficient alternative (7B params)
tracer = ActivationTracer(model_name="mistral-7b")
```

### Capture Configuration

```python
from glassbox.tracer import TracerConfig

config = TracerConfig(
    capture_layers=[10, 11, 12],  # Focus on final layers
    max_seq_length=256,            # Limit input length
    store_activations=True         # Save full activations
)

result = tracer.trace(prompt, config)
```

### Prompt Engineering

**For GPT-2:**
```python
# Completion-style works best
"The capital of France is"
"Q: What is 2+2? A:"
```

**For Llama 2 / Mistral:**
```python
# Instruction-style works best
"Q: Should we approve this loan? A:"
"[INST] Analyze this situation [/INST]"
"Question: What is the capital of France? Answer:"
```

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest --cov=glassbox tests/

# Run specific test file
pytest tests/test_tracer.py -v

# Run validation tests
jupyter notebook notebooks/03_validation_tests.ipynb
```

**Test Coverage:** >80% for core library

---

## 📚 Documentation

- **[Architecture Guide](docs/ARCHITECTURE.md)** - System design and components
- **[API Reference](docs/API_REFERENCE.md)** - Complete API documentation
- **[Llama Setup](LLAMA_SETUP.md)** - Setup guide for Llama 2 models
- **[Validation Methodology](docs/VALIDATION.md)** - How we validate interpretability

---

## ⚠️ Limitations

### Methodological
- ⚠️ **Attention ≠ Causation** - High attention suggests but doesn't prove influence
- ⚠️ **Aggregation Loss** - Averaging across heads loses fine-grained detail
- ⚠️ **Positional Confounds** - Position-based patterns can obscure semantics

### Technical
- ⚠️ **Model Coverage** - Best support for GPT-2 and Llama architectures
- ⚠️ **Sequence Length** - Limited to 512 tokens (memory constraints)
- ⚠️ **Single GPU** - No multi-GPU support yet (v3.0 coming soon)
- ⚠️ **CPU Performance** - Slower on CPU (use GPU when possible)

### Compliance
- ⚠️ **Not Legal Advice** - Provides technical artifacts, not compliance certification
- ⚠️ **Expert Required** - Outputs require ML expertise to interpret
- ⚠️ **No Counterfactuals** - Cannot prove "model would decide differently if..."

---

## 🛣️ Roadmap

### v0.2 - Causal Validation (Weeks 8-12)
- ✨ Activation patching for causal testing
- ✨ Ablation studies
- ✨ Gradient-based attribution

### v0.3 - Feature Interpretability (Weeks 13-18)
- ✨ Sparse Autoencoder (SAE) integration
- ✨ Feature dictionary
- ✨ Natural language explanations

### v0.4 - Production Ready (Weeks 19-24)
- ✨ Multi-GPU support for large models
- ✨ PostgreSQL backend for traces
- ✨ API authentication & rate limiting
- ✨ Real-time streaming inference

### v0.5 - Enterprise (Weeks 25-30)
- ✨ EU AI Act compliance templates
- ✨ Comparative analysis (diff traces)
- ✨ Adversarial testing mode
- ✨ Custom model fine-tuning support

---

## 🤝 Contributing

We welcome contributions! Here's how:

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Make your changes**
   - Add tests for new features
   - Update documentation
   - Follow code style (run `black glassbox/`)
4. **Commit and push**
   ```bash
   git commit -m "Add amazing feature"
   git push origin feature/amazing-feature
   ```
5. **Open a Pull Request**

### Development Setup

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Format code
black glassbox/ dashboard/ api/ tests/

# Type checking
mypy glassbox/

# Run tests
pytest tests/ -v
```

---

## 🙏 Acknowledgments

Built with amazing open source tools:

- **[TransformerLens](https://github.com/neelnanda-io/TransformerLens)** by Neel Nanda - Core interpretability library
- **[Streamlit](https://streamlit.io)** - Interactive dashboard framework
- **[FastAPI](https://fastapi.tiangolo.com)** - Modern Python API framework
- **[Plotly](https://plotly.com)** - Interactive visualizations

Research inspired by:
- **[Anthropic's Transformer Circuits](https://transformer-circuits.pub)** - Mechanistic interpretability foundations
- **[A Mathematical Framework for Transformer Circuits](https://transformer-circuits.pub/2021/framework/index.html)**
- **[In-Context Learning and Induction Heads](https://transformer-circuits.pub/2022/in-context-learning-and-induction-heads/index.html)**

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

**Commercial use permitted.** Attribution appreciated but not required.

---

## 📧 Support & Contact

- **GitHub Issues**: [github.com/yourorg/glassbox-mvp/issues](https://github.com/yourorg/glassbox-mvp/issues)
- **Discussions**: [github.com/yourorg/glassbox-mvp/discussions](https://github.com/yourorg/glassbox-mvp/discussions)
- **Email**: team@glassbox.ai
- **Twitter**: [@glassboxai](https://twitter.com/glassboxai)

---

## ⭐ Star History

If you find GlassBox useful, please star the repo! It helps others discover the project.

---

## 🎉 Getting Started

```bash
# Quick test (takes 2 minutes)
python glassbox/tracer.py gpt2-medium

# Full experience (takes 5 minutes)
streamlit run dashboard/app.py

# Production API (takes 1 minute)
uvicorn api.server:app --reload
```

**Ready to understand your models? Let's go! 🚀**

---

<div align="center">

**Made with ❤️ by the GlassBox team**

*Stop treating AI as a black box. Start understanding it.*

</div>
