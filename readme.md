# GlassBox

**Mechanistic Interpretability Platform for Production AI Systems**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-93%20passing-brightgreen.svg)](https://github.com/isahan78/glassbox-engine/actions)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Coverage](https://img.shields.io/badge/coverage-80%25+-yellow.svg)](https://github.com/isahan78/glassbox-engine)

GlassBox provides real-time interpretability for transformer-based language models. Built on [TransformerLens](https://github.com/neelnanda-io/TransformerLens), it enables researchers and enterprises to understand, audit, and explain AI decision-making at the mechanistic level.

---

## Overview

Modern language models are increasingly deployed in high-stakes domains—financial services, healthcare, legal, and HR. Regulatory frameworks like the EU AI Act now require explainability for automated decision systems. GlassBox addresses this need by providing:

- **Activation Tracing** — Capture attention patterns and internal states during inference
- **Causal Analysis** — Identify which model components drive specific behaviors
- **Feature Discovery** — Extract interpretable features using Sparse Autoencoders
- **Circuit Mapping** — Find minimal computational subgraphs for specific tasks
- **Audit Trails** — Generate structured, timestamped records for compliance

---

## Key Features

### Interpretability Methods

| Method | Description | Use Case |
|--------|-------------|----------|
| **Attention Analysis** | Rank attention heads by contribution, compute token-level influence | Understanding which inputs matter |
| **Activation Patching** | Measure causal effects by transplanting activations between runs | Identifying critical components |
| **Causal Tracing** | Systematic layer-by-layer analysis of information flow | Locating where facts are stored |
| **Circuit Discovery** | Find minimal component sets that implement behaviors | Reverse-engineering model algorithms |
| **Sparse Autoencoders** | Decompose activations into monosemantic features | Extracting interpretable concepts |

### Production Infrastructure

- **REST API** — FastAPI with authentication, rate limiting, and OpenAPI documentation
- **Interactive Dashboard** — Streamlit interface with real-time visualizations
- **Cloud Deployment** — Scripts for AWS, GCP, and Lambda Labs
- **CI/CD Pipeline** — GitHub Actions with automated testing and security scanning
- **Structured Logging** — JSON logs with request correlation IDs

### Supported Models

| Model | Parameters | Memory | Status |
|-------|-----------|--------|--------|
| GPT-2 (Small/Medium/Large/XL) | 124M–1.5B | 2–6 GB | Fully supported |
| Llama 2 (7B/13B) | 7–13B | 14–26 GB | Fully supported |
| Mistral 7B | 7B | 14 GB | Fully supported |
| GPT-J 6B | 6B | 12 GB | Supported |

---

## Quick Start

### Installation

```bash
git clone https://github.com/isahan78/glassbox-engine.git
cd glassbox-engine

python3.10 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
pip install -e .

# Verify installation
./run_tests.sh
```

### Basic Usage

```python
from glassbox import ActivationTracer, DecisionAnalyzer

# Initialize with model
tracer = ActivationTracer(model_name="gpt2-medium")
analyzer = DecisionAnalyzer(tracer)

# Analyze a decision
result, probabilities = analyzer.analyze_choices(
    prompt="Q: Should we approve this loan application? Credit: 750, Income: $85k. A:",
    choices=["yes", "no", "maybe"]
)

print(f"Decision: {max(probabilities, key=probabilities.get)}")
print(f"Confidence: {max(probabilities.values()):.1%}")
```

### Launch Dashboard

```bash
streamlit run dashboard/app.py
# Open http://localhost:8503
```

### Start API Server

```bash
uvicorn api.server:app --port 8000
# Documentation at http://localhost:8000/docs
```

---

## Technical Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                        User Interfaces                         │
│  ┌─────────────────────┐    ┌─────────────────────────────┐   │
│  │  Streamlit Dashboard │    │  FastAPI REST Server        │   │
│  │  - Trace Explorer    │    │  - /trace, /analyze         │   │
│  │  - Visualizations    │    │  - /patch, /causal-trace    │   │
│  │  - SAE Features      │    │  - /discover-circuit        │   │
│  └─────────────────────┘    └─────────────────────────────┘   │
└───────────────────────────────┬────────────────────────────────┘
                                │
┌───────────────────────────────▼────────────────────────────────┐
│                       GlassBox Core                            │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐ │
│  │ Tracer       │  │ Analyzer     │  │ Interventions         │ │
│  │ - Hook mgmt  │  │ - Attention  │  │ - Activation patching │ │
│  │ - Caching    │  │ - Attribution│  │ - Ablation studies    │ │
│  └──────────────┘  └──────────────┘  └───────────────────────┘ │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐ │
│  │ SAE          │  │ Circuits     │  │ Visualizations        │ │
│  │ - Training   │  │ - Discovery  │  │ - Plotly/NetworkX     │ │
│  │ - Features   │  │ - Mapping    │  │ - 3D projections      │ │
│  └──────────────┘  └──────────────┘  └───────────────────────┘ │
└───────────────────────────────┬────────────────────────────────┘
                                │
┌───────────────────────────────▼────────────────────────────────┐
│                      TransformerLens                           │
│            Mechanistic interpretability library                │
│                  (Hook registration, caching)                  │
└────────────────────────────────────────────────────────────────┘
```

---

## Core Capabilities

### 1. Activation Patching

Measure the causal effect of specific model components:

```python
from glassbox.interventions import ActivationPatcher, InterventionConfig

patcher = ActivationPatcher(tracer)

result = patcher.patch_and_run(
    clean_input="The Eiffel Tower is in Paris",
    corrupted_input="The Eiffel Tower is in London",
    intervention=InterventionConfig(layer=8, component="resid")
)

print(f"Causal effect (logit diff): {result.logit_diff:.3f}")
print(f"KL divergence: {result.kl_divergence:.3f}")
```

### 2. Circuit Discovery

Identify minimal computational subgraphs:

```python
from glassbox.circuits import CircuitDiscovery

discovery = CircuitDiscovery(tracer, threshold=0.1)

circuit = discovery.discover_circuit(
    clean_input="The Eiffel Tower is in Paris",
    corrupted_input="The Eiffel Tower is in London",
    task_description="Geographic fact recall",
    max_components=15
)

print(f"Circuit size: {circuit.get_num_components()} components")
print(f"Compression: {circuit.get_compression_ratio(96):.1%} of model")
print(f"Faithfulness: {circuit.faithfulness_score:.1%}")
```

### 3. Sparse Autoencoder Features

Extract interpretable, monosemantic features:

```python
from glassbox.feature_discovery import FeatureDiscoveryWorkflow

workflow = FeatureDiscoveryWorkflow(model_name="gpt2-medium", layer=6)

# Train SAE on diverse prompts
results = workflow.run_full_workflow(
    training_prompts=prompts,
    expansion_factor=8,
    num_training_steps=1000
)

print(f"Discovered {results['num_features_discovered']} interpretable features")
```

### 4. Interactive Visualizations

All visualizations are interactive (Plotly) and publication-ready:

- **Circuit Graphs** — NetworkX-based with hierarchical layouts
- **Causal Heatmaps** — Layer × component effect matrices
- **3D Activation Space** — PCA/t-SNE projections of representations
- **Feature Activation Maps** — Token-level SAE feature patterns

---

## API Reference

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/trace` | POST | Generate activation trace for prompt |
| `/analyze-choices` | POST | Compare probabilities across choices |
| `/top-tokens` | POST | Get top-k predicted tokens |
| `/patch` | POST | Run activation patching experiment |
| `/causal-trace` | POST | Trace information flow across layers |
| `/discover-circuit` | POST | Find minimal circuit for behavior |
| `/train-sae` | POST | Train sparse autoencoder |
| `/health` | GET | Health check |
| `/ready` | GET | Readiness check (model loaded) |

### Example Request

```bash
curl -X POST http://localhost:8000/analyze-choices \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Q: Approve this loan? A:",
    "choices": ["yes", "no"]
  }'
```

Full API documentation available at `/docs` when server is running.

---

## Performance

Benchmarks on Apple M1 Pro (CPU):

| Model | Trace Time | Memory | Overhead |
|-------|-----------|--------|----------|
| GPT-2 Small | ~2s | 2 GB | 3–4× |
| GPT-2 Medium | ~4s | 3 GB | 3–5× |
| Llama 2 7B | ~15s | 14 GB | 4–5× |

GPU acceleration provides 5–10× speedup.

---

## Research Foundation

GlassBox implements methods from recent mechanistic interpretability research:

- **Activation Patching**: [Locating and Editing Factual Associations](https://arxiv.org/abs/2202.05262) (Meng et al., 2022)
- **Circuit Analysis**: [A Mathematical Framework for Transformer Circuits](https://transformer-circuits.pub/2021/framework/index.html) (Anthropic, 2021)
- **Sparse Autoencoders**: [Towards Monosemanticity](https://transformer-circuits.pub/2023/monosemantic-features/index.html) (Anthropic, 2023)
- **Causal Tracing**: [Causal Mediation Analysis](https://arxiv.org/abs/2004.12265) (Vig et al., 2020)

---

## Use Cases

**AI Safety Research**
- Study failure modes and unexpected behaviors
- Validate interpretability hypotheses
- Compare circuit structures across models

**Enterprise Compliance**
- Generate audit trails for regulated industries
- Document decision factors for EU AI Act
- Provide explanations for stakeholder review

**Model Development**
- Debug unexpected model outputs
- Understand feature representations
- Optimize model architecture

---

## Project Structure

```
glassbox-engine/
├── glassbox/           # Core library
│   ├── tracer.py       # Activation capture
│   ├── analyzer.py     # Attention analysis
│   ├── interventions.py# Patching & ablation
│   ├── circuits.py     # Circuit discovery
│   ├── sae.py          # Sparse autoencoders
│   └── visualizations.py
├── api/                # REST API
│   └── server.py
├── dashboard/          # Streamlit UI
│   └── app.py
├── tests/              # Test suite (93 tests)
├── docs/               # Documentation
└── cloud/              # Deployment scripts
```

---

## Development

### Running Tests

```bash
./run_tests.sh              # All tests
pytest tests/ -v            # Verbose output
pytest tests/ --cov=glassbox # With coverage
```

### Code Quality

```bash
black glassbox/ api/ tests/ # Format
mypy glassbox/              # Type check
flake8 glassbox/            # Lint
```

---

## Roadmap

| Version | Timeline | Features |
|---------|----------|----------|
| v0.1 | Now | Core interpretability, dashboard, API |
| v0.2 | Q1 2025 | Multi-GPU support, PostgreSQL backend |
| v0.3 | Q2 2025 | EU AI Act templates, SOC2 compliance |
| v0.4 | Q3 2025 | Real-time streaming, model comparison |
| v0.5 | Q4 2025 | Enterprise edition, on-prem deployment |

---

## Contributing

We welcome contributions. Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

1. Fork the repository
2. Create a feature branch
3. Run tests (`./run_tests.sh`)
4. Submit a pull request

---

## License

MIT License. See [LICENSE](LICENSE) for details.

---

## Citation

If you use GlassBox in research, please cite:

```bibtex
@software{glassbox2024,
  title={GlassBox: Mechanistic Interpretability Platform},
  author={GlassBox Team},
  year={2024},
  url={https://github.com/isahan78/glassbox-engine}
}
```

---

## Contact

- **Issues**: [GitHub Issues](https://github.com/isahan78/glassbox-engine/issues)
- **Discussions**: [GitHub Discussions](https://github.com/isahan78/glassbox-engine/discussions)

---

<div align="center">

**Understanding AI, one activation at a time.**

</div>
