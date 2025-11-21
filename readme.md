# 🧠 GlassBox MVP

**Interpretable-by-design AI runtime that captures and visualizes how language models arrive at their outputs.**

[![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)](https://github.com/isahan78/glassbox-mvp)
[![Python](https://img.shields.io/badge/python-3.10+-green.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-orange.svg)](LICENSE)
[![Models](https://img.shields.io/badge/models-GPT--2%20%7C%20Llama%202%20%7C%20Mistral-purple.svg)](https://transformerlens.org)
[![Tests](https://github.com/isahan78/glassbox-mvp/workflows/Tests/badge.svg)](https://github.com/isahan78/glassbox-mvp/actions)
[![Production Ready](https://img.shields.io/badge/production%20ready-4.5%2F5-brightgreen.svg)](CRITICAL_FIXES_COMPLETED.md)

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

## 🚨 Production Ready (v0.1.0)

**Latest Update:** Enhanced interactive visualizations now available! 🎨

✅ **Interactive visualizations** using Plotly & NetworkX for circuit discovery, causal analysis, and activation spaces
✅ **3D activation projections** with PCA/t-SNE for exploring model representations
✅ **Enhanced circuit graphs** with draggable nodes and importance color-coding
✅ **Causal flow heatmaps** showing layer-by-layer information processing
✅ **62 automated tests** passing with GitHub Actions CI/CD
✅ **API authentication** with optional API key security
✅ **Production readiness: 4.5/5** ⭐⭐⭐⭐

[See what's new →](CRITICAL_FIXES_COMPLETED.md)

---

## ✨ Features

### Core Capabilities

✅ **Multi-Model Support**
- GPT-2 (Small, Medium, Large, XL)
- Llama 2 7B/13B (recommended!)
- Mistral 7B
- GPT-J 6B and more

✅ **Single & Multi-Token Generation** 🆕
- Single token prediction with full tracing
- Multi-token generation (up to 20 tokens)
- Per-token confidence analysis
- Full interpretability for each step

✅ **Decision Analysis** 🆕
- Analyze probabilities for specific choices (yes/no, approve/deny)
- Get top-k token predictions
- Natural language explanations
- Token influence visualization

✅ **Real-Time Analysis**
- Capture all 144 attention heads (GPT-2) or 1024 heads (Llama 2)
- Rank heads by contribution scores
- Compute token-level influence
- Visual token highlighting

✅ **Interactive Dashboard** 🆕
- Beautiful Streamlit interface with improved UX
- Confidence levels with context (High/Medium/Low)
- Visual token influence bars
- Attention heatmaps and charts
- Single & multi-token modes
- Model switching in UI
- Trace browsing and search
- **🔬 Advanced Analysis Page** (NEW!)
  - 🎯 Activation Patching - Interactive causal interventions
  - 📊 Causal Tracing - Layer-by-layer analysis with visualizations
  - 🔍 Circuit Discovery - Find minimal circuits for tasks
- **🧩 SAE Features Page** (NEW! 🔥)
  - 📊 Feature Discovery - Train SAEs and discover monosemantic features
  - 🔍 Feature Analysis - Analyze individual features in detail
  - 🔬 Feature Circuits - Circuit discovery based on interpretable features
- **🎨 Enhanced Interactive Visualizations** (NEW! 🔥)
  - **📊 Circuit Graphs** - Interactive NetworkX visualizations with hierarchical layouts
    - Drag nodes to explore circuit structure
    - Color-coded by importance scores
    - Hover tooltips with component details
    - Automatic compression ratio calculations
  - **🌡️ Causal Flow Analysis** - Multi-layer heatmaps and importance charts
    - Layer-by-layer causal effect visualization
    - Automatic critical layer identification
    - Comparative analysis across components
  - **🧩 SAE Feature Heatmaps** - Monosemantic feature activation patterns
    - Top-k feature visualization
    - Token-level activation strengths
    - Distribution analysis per feature
  - **🌐 3D Activation Space** - High-dimensional representation explorer
    - PCA and t-SNE dimensionality reduction
    - Interactive 3D scatter plots (rotate, zoom, pan)
    - Cluster analysis of prompt representations
    - Layer-specific activation patterns
  - **👁️ Multi-head Attention** - Enhanced attention pattern visualization
    - Side-by-side head comparison
    - Token-level attention heatmaps
    - Contribution score overlays

✅ **REST API** 🆕
- FastAPI endpoints with new features
- Decision analysis endpoints (`/analyze-choices`, `/top-tokens`)
- JSON trace artifacts
- Programmatic access
- Remote client library for cloud instances
- Auto-generated docs

✅ **Cloud Deployment** 🆕
- Deploy to Lambda Labs ($1.29/hour)
- Google Cloud Platform support
- AWS deployment scripts
- Docker & docker-compose
- Remote client for accessing cloud instances
- Auto-scaling guides

✅ **Production Infrastructure** 🆕🔥
- **Automated Testing** - 80+ tests (62 unit + 18 integration) with GitHub Actions CI/CD
- **API Authentication** - Optional API key security
- **Health Monitoring** - `/health` and `/ready` endpoints
- **Structured Logging** - JSON logging for production with request correlation IDs
- **Rate Limiting** - Protect API from abuse (10-100 requests/min per endpoint)
- **Performance Caching** - LRU caching for traces (100 entries) and analysis (200 entries)
- **Request Tracing** - Unique correlation IDs for distributed tracing
- **Type Safety** - Full type hints with `py.typed`
- **Security Documentation** - Comprehensive security policy
- **Contribution Guidelines** - Professional open-source practices

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
git clone https://github.com/glassbox-ai/glassbox-mvp.git
cd glassbox-mvp

# 2. Create virtual environment
python3.10 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install GlassBox
pip install -e .

# 5. Run tests to verify installation
./run_tests.sh
# Should see: ✅ All tests passed! (62 passed)
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

### 1. Decision Analysis (New!)

```python
from glassbox import ActivationTracer, DecisionAnalyzer

# Initialize with Llama 2 7B (or any supported model)
tracer = ActivationTracer(model_name="meta-llama/Llama-2-7b-hf")
analyzer = DecisionAnalyzer(tracer)

# Analyze decision with specific choices
result, probs = analyzer.analyze_choices(
    "Q: Should we approve this $100k loan? Credit: 750, Income: $85k. A:",
    ["yes", "no", "maybe"]
)

# Print results
print(f"Decision: {max(probs, key=probs.get)}")
print(f"\nProbabilities:")
for choice, prob in probs.items():
    print(f"  {choice}: {prob:.2%}")

# Output:
# Decision: yes
# Probabilities:
#   yes: 68.5%
#   no: 25.3%
#   maybe: 6.2%
```

### 2. Multi-Token Generation (New!)

```python
from glassbox import ActivationTracer, DecisionAnalyzer

tracer = ActivationTracer(model_name="meta-llama/Llama-2-7b-hf")
analyzer = DecisionAnalyzer(tracer)

# Generate multiple tokens with full tracing
full_text, traces = analyzer.generate_completion(
    "Q: Why should we approve this loan? A:",
    max_tokens=10
)

print(f"Generated: {full_text}")
print(f"\nPer-token confidence:")
for i, trace in enumerate(traces, 1):
    # Calculate confidence for each token
    import torch
    logits = trace.logits[0, -1]
    probs = torch.softmax(logits, dim=0)
    confidence = probs[logits.argmax()].item()
    print(f"  Token {i}: '{trace.output_text}' ({confidence:.1%})")
```

### 3. Basic Tracing

```python
from glassbox.tracer import ActivationTracer
from glassbox.analyzer import AttentionAnalyzer

# Initialize with your chosen model
tracer = ActivationTracer(model_name="gpt2-medium")  # or "meta-llama/Llama-2-7b-hf"
analyzer = AttentionAnalyzer(tracer)

# Run trace
prompt = "Should we approve this loan application?"
result = tracer.trace(prompt)

# Analyze attention
top_heads = analyzer.rank_attention_heads(result)

# Print results
print(f"Output: {result.output_text}")
print(f"Top contributing head: Layer {top_heads[0].layer}, Head {top_heads[0].head}")
print(f"Score: {top_heads[0].score:.3f}")
```

### 4. Remote Client (Cloud Instances)

```python
from glassbox import GlassBoxClient

# Connect to your cloud instance
client = GlassBoxClient("http://your-instance-ip:8000")

# Analyze decisions remotely (runs on cloud GPU!)
probs = client.analyze_choices(
    "Q: Approve $500k loan? Credit: 720, Income: $150k. A:",
    ["yes", "no"]
)

print(f"Approve: {probs['yes']:.2%}")
print(f"Deny: {probs['no']:.2%}")

# Get top predictions
top_tokens = client.get_top_tokens(
    "The capital of France is",
    top_k=5
)

for token, prob in top_tokens:
    print(f"  '{token}': {prob:.2%}")
```

### 5. Interactive Dashboard

```bash
# Start dashboard with Llama 2 7B
export GLASSBOX_MODEL=meta-llama/Llama-2-7b-hf
streamlit run dashboard/app.py
```

Then visit `http://localhost:8503`

**Features:**
- **Single & Multi-Token Modes** - Choose 1-20 tokens
- **Decision Summary** - Clear confidence levels (High/Medium/Low)
- **Visual Token Influence** - See which parts of input mattered most
- **Confidence Charts** - Per-token confidence visualization
- **Model Support** - GPT-2, Llama 2, Mistral
- **Trace Browser** - Search and explore saved traces
- **🔬 Advanced Analysis** (NEW!) - Mechanistic interpretability tools:
  - **Activation Patching** - Run causal interventions interactively
  - **Causal Tracing** - Visualize information flow across layers
  - **Circuit Discovery** - Find minimal circuits for specific tasks
- **🧩 SAE Features** (NEW! 🔥) - Monosemantic feature discovery:
  - **Feature Discovery** - Train Sparse Autoencoders on model activations
  - **Feature Analysis** - Understand what concepts each feature represents
  - **Feature Circuits** - Build interpretable circuits from monosemantic features

### 6. Advanced Mechanistic Interpretability (NEW! 🔥)

**Activation Patching** - Measure causal effects:
```python
from glassbox.interventions import ActivationPatcher, InterventionConfig, InterventionType

tracer = ActivationTracer("gpt2-small")
patcher = ActivationPatcher(tracer)

# Where does the model store "Eiffel Tower → Paris"?
result = patcher.patch_and_run(
    clean_input="The Eiffel Tower is in Paris",
    corrupted_input="The Eiffel Tower is in London",
    intervention=InterventionConfig(layer=8, component="resid")
)

print(f"Causal effect: {result.logit_diff:.3f}")  # Negative = restores correct behavior
```

**Causal Tracing** - Find critical layers:
```python
# Trace information flow across all layers
results = patcher.causal_trace(
    clean_input="The Eiffel Tower is in Paris",
    corrupted_input="The Eiffel Tower is in London",
    layers=list(range(12))
)

# Find most important layer
best_layer = min(results.items(), key=lambda x: x[1].logit_diff)
print(f"Most critical: {best_layer[0]}")
```

**Circuit Discovery** - Find minimal implementations:
```python
from glassbox.circuits import CircuitDiscovery

discovery = CircuitDiscovery(tracer, threshold=0.1)

circuit = discovery.discover_circuit(
    clean_input="The Eiffel Tower is in Paris",
    corrupted_input="The Eiffel Tower is in London",
    task_description="Geographic location recall"
)

print(f"Circuit uses {circuit.get_compression_ratio(36):.1%} of model")
print(f"Faithfulness: {circuit.faithfulness_score:.1%}")
print(discovery.visualize_circuit(circuit))
```

**All techniques available in the interactive dashboard!** 🎨

### 7. Sparse Autoencoder Features (NEW! 🔥)

**Monosemantic Feature Discovery** - Discover interpretable features:
```python
from glassbox.feature_discovery import FeatureDiscoveryWorkflow

# Initialize workflow
workflow = FeatureDiscoveryWorkflow(
    model_name="gpt2-small",
    layer=6  # Middle layer
)

# Prepare diverse training prompts
training_prompts = [
    "The Eiffel Tower is in Paris",
    "London is the capital of England",
    "Tokyo is the capital of Japan",
    # ... add 100-1000 diverse prompts for best results
]

# Run complete feature discovery workflow
results = workflow.run_full_workflow(
    training_prompts=training_prompts,
    analysis_prompts=training_prompts,
    expansion_factor=8,  # 768 → 6144 features
    num_training_steps=1000,
    output_dir="sae_results"
)

print(f"Discovered {results['num_features_discovered']} monosemantic features")
```

**Feature Analysis** - Understand what features represent:
```python
from glassbox.sae import FeatureAnalyzer

# Initialize analyzer with trained SAE
analyzer = FeatureAnalyzer(sae, tracer)

# Collect feature activations
analyzer.collect_activations(prompts=test_prompts, layer=6)

# Get top features
features = analyzer.get_top_features(k=20, min_activation_frequency=3)

# Analyze each feature
for feature in features:
    analysis = analyzer.analyze_feature(feature, generate_description=True)
    print(f"Feature {feature.feature_idx}: {analysis['description']}")
    print(f"  Activation strength: {feature.activation_strength:.3f}")
    print(f"  Top examples:")
    for ex in feature.top_activating_examples[:3]:
        print(f"    - {ex['token']} in '{ex['prompt'][:50]}'")
```

**Feature Circuits** - Build interpretable circuits from features:
```python
from glassbox.sae_circuits import SAECircuitDiscovery

# Train SAEs on multiple layers
sae_dict = {
    6: trained_sae_layer_6,
    8: trained_sae_layer_8,
    10: trained_sae_layer_10
}

# Initialize feature-based circuit discovery
discovery = SAECircuitDiscovery(tracer, sae_dict, threshold=0.1)

# Discover circuit based on SAE features
circuit = discovery.discover_feature_circuit(
    clean_input="The Eiffel Tower is in Paris",
    corrupted_input="The Eiffel Tower is in London",
    task_description="Geographic fact recall"
)

print(f"Feature circuit uses {circuit['num_features']} monosemantic features")
print(f"Compression: {circuit['compression_ratio']:.2%}")
print(discovery.explain_feature_circuit(circuit))
```

**Key Benefits:**
- 🎯 **Monosemantic** - Each feature represents a single concept
- 🔬 **Interpretable** - Understand what features do by analyzing activations
- 📊 **Sparse** - Only a few features activate per input
- 🔍 **Circuit Discovery** - Build circuits from interpretable features

**Research-backed implementation:**
- "Towards Monosemanticity" (Anthropic, 2023)
- "Sparse Autoencoders Find Highly Interpretable Features" (Cunningham et al., 2023)
- "Scaling Monosemanticity" (Anthropic, 2024)

**Available in the interactive dashboard!** Train SAEs and explore features visually 🎨

### 8. Enhanced Interactive Visualizations (NEW! 🔥)

**Publication-quality interactive visualizations for mechanistic interpretability.**

GlassBox provides five specialized visualizers built on Plotly and NetworkX for exploring model internals. All visualizations are interactive, exportable, and integrated into the dashboard.

#### Circuit Graph Visualization

```python
from glassbox.visualizations import CircuitVisualizer
from glassbox.circuits import CircuitDiscovery
from glassbox.tracer import ActivationTracer

# Initialize components
tracer = ActivationTracer()
discovery = CircuitDiscovery(tracer, threshold=0.1)
circuit_viz = CircuitVisualizer()

# Discover circuit
circuit = discovery.discover_circuit(
    clean_input="The Eiffel Tower is in Paris",
    corrupted_input="The Eiffel Tower is in London",
    task_description="Geographic fact recall",
    max_components=15
)

# Create interactive graph
fig = circuit_viz.create_interactive_graph(
    circuit,
    title="Geographic Fact Recall Circuit"
)

# Display or export
import streamlit as st
st.plotly_chart(fig, use_container_width=True)
# Or: fig.write_html("circuit.html")
```

**Features:**
- Hierarchical layout by layer depth
- Nodes draggable for custom arrangements
- Color-coded by importance scores
- Hover tooltips show component details
- Automatic compression metrics

#### Causal Flow Analysis

```python
from glassbox.visualizations import CausalFlowVisualizer
from glassbox.interventions import ActivationPatcher

# Initialize
patcher = ActivationPatcher(tracer)
causal_viz = CausalFlowVisualizer()

# Run causal trace across all layers
results = patcher.causal_trace(
    clean_input="Paris is in France",
    corrupted_input="Paris is in Germany",
    layers=list(range(24)),  # GPT-2 Medium
    components=["resid", "attn", "mlp"]
)

# Visualize layer importance
importance_fig = causal_viz.create_layer_importance_chart(results)
st.plotly_chart(importance_fig)

# Heatmap across layers and components
heatmap_fig = causal_viz.create_causal_heatmap(
    results,
    metric="logit_diff"
)
st.plotly_chart(heatmap_fig)
```

**Insights:**
- Identify critical layers automatically
- Compare component contributions
- Track information flow through model

#### 3D Activation Space Explorer

```python
from glassbox.visualizations import ActivationSpaceVisualizer

space_viz = ActivationSpaceVisualizer()

# Collect activations from multiple prompts
prompts = [
    "The Eiffel Tower is in Paris",
    "The Eiffel Tower is in London",
    "The Colosseum is in Rome",
    "Tokyo is the capital of Japan"
]

activations = []
for prompt in prompts:
    result = tracer.trace(prompt)
    # Extract layer 12 activations
    acts = result.activation_cache["layer_12_resid"][-1, :]
    activations.append(acts.numpy())

# Project to 3D
import numpy as np
activations_array = np.stack(activations)

fig = space_viz.create_3d_projection(
    activations_array,
    labels=prompts,
    method="pca"  # or "tsne"
)

st.plotly_chart(fig)
```

**Applications:**
- Cluster analysis of prompt representations
- Explore how model separates concepts
- Compare representations across layers
- Debug unexpected model behaviors

#### SAE Feature Activation Heatmaps

```python
from glassbox.visualizations import SAEFeatureVisualizer
from glassbox.sae import SparseAutoencoder

sae_viz = SAEFeatureVisualizer()

# After training SAE (see Section 7)
# Get feature activations
feature_activations = sae.encode(layer_activations)  # shape: (n_prompts, n_features)

# Visualize top features
heatmap = sae_viz.create_feature_activation_heatmap(
    feature_activations.numpy(),
    tokens=["The", "Eiffel", "Tower", "is", "in", "Paris"],
    top_k=20
)
st.plotly_chart(heatmap)

# Analyze specific feature
feature_dist = sae_viz.create_feature_distribution(
    feature_activations.numpy(),
    feature_idx=42
)
st.plotly_chart(feature_dist)
```

**Use Cases:**
- Identify which features activate for specific inputs
- Understand monosemantic feature meanings
- Debug SAE training quality

#### Visualization Features

✅ **Interactive Controls**
- Zoom, pan, rotate (3D)
- Hover for detailed information
- Click to select elements
- Drag nodes (circuit graphs)

✅ **Export Options**
- HTML (interactive, standalone)
- PNG (publication-ready)
- SVG (vector graphics)
- JSON (raw data)

✅ **Integration**
- Streamlit dashboard (built-in)
- Jupyter notebooks
- FastAPI endpoints
- Standalone HTML pages

✅ **Professional Quality**
- Publication-ready styling
- Customizable color schemes
- Annotation support
- Responsive layouts

#### Dashboard Integration

All visualizations are accessible in the **Streamlit dashboard**:

1. **🔬 Advanced Analysis** → Circuit Discovery
   - Interactive circuit graphs
   - Compression metrics
   - Component importance

2. **🔬 Advanced Analysis** → Causal Tracing
   - Layer importance charts
   - Multi-layer heatmaps
   - Critical layer identification

3. **🔬 Advanced Analysis** → Activation Space
   - 3D prompt clustering
   - PCA/t-SNE projections
   - Layer-specific views

4. **🧩 SAE Features** → Feature Discovery
   - Feature activation heatmaps
   - Top-k feature visualization
   - Distribution analysis

**Quick Start:**
```bash
streamlit run dashboard/app.py
# Navigate to Advanced Analysis or SAE Features tabs
```

### 9. REST API

```bash
# Start API server (development mode - no authentication)
uvicorn api.server:app --reload --port 8000

# Start API server (production mode - with authentication)
export GLASSBOX_API_KEY=$(openssl rand -hex 32)
uvicorn api.server:app --host 0.0.0.0 --port 8000

# View docs at http://localhost:8000/docs
```

**Production configuration (NEW!):**
```bash
# Configure logging (simple for dev, json for production)
export GLASSBOX_LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
export GLASSBOX_LOG_FORMAT=json # "simple" (colorful) or "json" (structured)

# Configure rate limiting (built-in, no setup required)
# - Heavy endpoints (trace generation): 10 requests/minute
# - Medium endpoints (analysis/delete): 20 requests/minute
# - Light endpoints (read-only): 100 requests/minute

# Performance caching is automatic
# - Trace cache: 100 entries, 60 min TTL
# - Analysis cache: 200 entries
# View cache stats: GET /cache/stats
# Clear cache: POST /cache/clear
```

**Health and monitoring (NEW!):**
```bash
# Simple health check
curl http://localhost:8000/health

# Readiness check (verifies model loaded)
curl http://localhost:8000/ready

# Cache statistics
curl http://localhost:8000/cache/stats

# API statistics
curl http://localhost:8000/stats

# Every response includes X-Request-ID header for correlation
curl -v http://localhost:8000/health | grep X-Request-ID
```

**Create a trace:**
```bash
# Without authentication (development mode)
curl -X POST http://localhost:8000/trace \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "The capital of France is",
    "config": {
      "capture_layers": [8, 9, 10],
      "max_seq_length": 128
    }
  }'

# With authentication (production mode)
curl -X POST http://localhost:8000/trace \
  -H "X-API-Key: your_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "The capital of France is",
    "config": {
      "capture_layers": [8, 9, 10],
      "max_seq_length": 128
    }
  }'
```

**Analyze choices (New!):**
```bash
curl -X POST http://localhost:8000/analyze-choices \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Q: Approve loan? A:",
    "choices": ["yes", "no"]
  }'
```

**Get top tokens (New!):**
```bash
curl -X POST http://localhost:8000/top-tokens \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "The capital of France is",
    "top_k": 5
  }'
```

**Get trace:**
```bash
curl http://localhost:8000/trace/20251025_143022_abc123
```

**Advanced Mechanistic Interpretability Endpoints (NEW! 🔥)**

**Activation Patching** - Measure causal effects:
```bash
curl -X POST http://localhost:8000/patch \
  -H "Content-Type: application/json" \
  -d '{
    "clean_input": "The Eiffel Tower is in Paris",
    "corrupted_input": "The Eiffel Tower is in London",
    "layer": 8,
    "component": "resid",
    "intervention_type": "PATCH"
  }'

# Returns: logit_diff, prob_diff, kl_divergence, intervention_magnitude
```

**Causal Tracing** - Find critical layers:
```bash
curl -X POST http://localhost:8000/causal-trace \
  -H "Content-Type: application/json" \
  -d '{
    "clean_input": "The Eiffel Tower is in Paris",
    "corrupted_input": "The Eiffel Tower is in London",
    "layers": [0, 4, 8, 11],
    "components": ["resid"]
  }'

# Returns: Results for each layer showing which layers matter most
```

**Circuit Discovery** - Find minimal circuits:
```bash
curl -X POST http://localhost:8000/discover-circuit \
  -H "Content-Type: application/json" \
  -d '{
    "clean_input": "The Eiffel Tower is in Paris",
    "corrupted_input": "The Eiffel Tower is in London",
    "task_description": "Geographic fact recall",
    "max_components": 10
  }'

# Returns: Circuit with nodes, edges, faithfulness score, compression ratio
```

**Train SAE** - Discover monosemantic features:
```bash
curl -X POST http://localhost:8000/train-sae \
  -H "Content-Type: application/json" \
  -d '{
    "layer": 6,
    "prompts": ["prompt1", "prompt2", "..."],
    "expansion_factor": 8,
    "num_training_steps": 500
  }'

# Returns: Checkpoint path, final loss, variance explained
```

**Discover Features** - Analyze SAE features:
```bash
curl -X POST http://localhost:8000/sae-features \
  -H "Content-Type: application/json" \
  -d '{
    "layer": 6,
    "checkpoint_path": "data/sae/layer_6_checkpoint.pt",
    "prompts": ["test1", "test2", "..."],
    "top_k": 20
  }'

# Returns: List of features with descriptions and examples
```

**Feature Circuits** - Interpretable circuit discovery:
```bash
curl -X POST http://localhost:8000/feature-circuit \
  -H "Content-Type: application/json" \
  -d '{
    "clean_input": "The Eiffel Tower is in Paris",
    "corrupted_input": "The Eiffel Tower is in London",
    "task_description": "Geographic fact recall",
    "sae_checkpoints": {
      "6": "data/sae/layer_6_checkpoint.pt",
      "8": "data/sae/layer_8_checkpoint.pt"
    }
  }'

# Returns: Feature-based circuit with interpretable nodes
```

**Rate Limits for Advanced Endpoints:**
- `/patch`: 10 requests/minute
- `/causal-trace`: 5 requests/minute
- `/discover-circuit`: 3 requests/minute
- `/train-sae`: 2 requests/minute
- `/sae-features`: 5 requests/minute
- `/feature-circuit`: 2 requests/minute

**View all endpoints:**
```bash
# Interactive API docs
open http://localhost:8000/docs

# Get examples
curl http://localhost:8000/examples
```

### 7. Cloud Deployment (New!)

**Quick Start - Lambda Labs (Cheapest):**
```bash
# Deploy to Lambda Labs GPU ($1.29/hour)
./cloud/deploy_lambda_labs.sh
```

**Or Google Cloud:**
```bash
./cloud/deploy_gcp.sh
```

**Or AWS:**
```bash
./cloud/deploy_aws.sh
```

**Then use remote client:**
```python
from glassbox import GlassBoxClient

client = GlassBoxClient("http://your-instance-ip:8000")
probs = client.analyze_choices("Q: Approve? A:", ["yes", "no"])
print(f"Yes: {probs['yes']:.2%}")
```

See [CLOUD_QUICKSTART.md](CLOUD_QUICKSTART.md) for details.

### 8. Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up

# Or build manually
docker build -t glassbox:latest .
docker run --gpus all -p 8000:8000 glassbox:latest
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

### Local Testing

```bash
# Easy way - use the test runner script
./run_tests.sh

# Run all tests with pytest
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=glassbox --cov-report=html --cov-report=term-missing

# Run specific test file
pytest tests/test_tracer.py -v

# Run fast tests only (skip slow integration tests)
./run_tests.sh --fast
```

### Automated Testing (CI/CD)

✅ **GitHub Actions** runs automatically on every push and pull request:
- Tests on Ubuntu and macOS
- Python 3.10 and 3.11
- Code quality checks (black, flake8, mypy)
- Security scanning (safety)

View test results: [GitHub Actions](https://github.com/isahan78/glassbox-mvp/actions)

**Test Coverage:**
- **62 tests** passing
- **>80% coverage** for core library
- All tests complete in ~46 seconds

---

## 📚 Documentation

### Quick Start Guides
- **[Cloud Quick Start](CLOUD_QUICKSTART.md)** 🆕 - Deploy to cloud in 15 minutes
- **[Llama Setup Guide](LLAMA_SETUP_GUIDE.md)** 🆕 - Complete Llama 2 setup
- **[Quick Start: Decisions](QUICK_START_DECISIONS.md)** 🆕 - Yes/no decision analysis
- **[Your Questions Answered](YOUR_QUESTIONS_ANSWERED.md)** 🆕 - FAQ

### Comprehensive Guides
- **[Scaling & Cloud Guide](SCALING_CLOUD_GUIDE.md)** 🆕 - Cloud architecture & deployment
- **[Model Storage Guide](MODEL_STORAGE_GUIDE.md)** 🆕 - External storage setup
- **[Model Requirements](MODEL_REQUIREMENTS.md)** 🆕 - Which models and why
- **[Cloud Deployment README](cloud/README.md)** 🆕 - Complete cloud guide

### Reference Documentation
- **[Architecture Guide](docs/ARCHITECTURE.md)** - System design and components
- **[API Reference](docs/API_REFERENCE.md)** - Complete API documentation
- **[Llama Quick Reference](LLAMA_QUICK_REFERENCE.md)** 🆕 - Cheat sheet
- **[Documentation Index](DOCUMENTATION_INDEX.md)** 🆕 - All docs organized
- **[Validation Methodology](docs/VALIDATION.md)** - How we validate interpretability

### Infrastructure & Operations 🆕🔥
- **[Security Policy](SECURITY.md)** 🆕 - Vulnerability reporting, authentication, deployment security
- **[Contributing Guide](CONTRIBUTING.md)** 🆕 - How to contribute, code style, PR process
- **[Critical Fixes Summary](CRITICAL_FIXES_COMPLETED.md)** 🆕 - Production readiness improvements
- **[Repository Analysis](REPO_ANALYSIS_AND_NEXT_STEPS.md)** 🆕 - Complete analysis & roadmap

### Code Examples
- **[Decision Analysis Example](examples/decision_analysis.py)** 🆕 - Working code
- **[Remote Client Example](examples/remote_client_example.py)** 🆕 - Cloud client usage

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
- ✅ **Sparse Autoencoder (SAE) integration** - COMPLETED! (Feature discovery, analysis, circuits)
- ✨ Feature dictionary
- ✨ Natural language explanations

### v0.4 - Production Ready (Weeks 19-24)
- ✅ **API authentication** - COMPLETED! (API key support)
- ✅ **Health checks** - COMPLETED! (/health, /ready endpoints)
- ✅ **CI/CD pipeline** - COMPLETED! (GitHub Actions)
- ✨ Multi-GPU support for large models
- ✨ PostgreSQL backend for traces
- ✨ Rate limiting
- ✨ Real-time streaming inference

### v0.5 - Enterprise (Weeks 25-30)
- ✨ EU AI Act compliance templates
- ✨ Comparative analysis (diff traces)
- ✨ Adversarial testing mode
- ✨ Custom model fine-tuning support

---

## 🤝 Contributing

We welcome contributions! GlassBox is an open-source project and we appreciate all contributions.

**Please read our [Contributing Guide](CONTRIBUTING.md) for:**
- Development setup instructions
- Code style guidelines
- Testing requirements
- Pull request process
- Git workflow

### Quick Start for Contributors

```bash
# 1. Fork and clone
git clone https://github.com/YOUR_USERNAME/glassbox-mvp.git
cd glassbox-mvp

# 2. Set up development environment
python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .

# 3. Run tests to verify setup
./run_tests.sh

# 4. Make your changes and test
# ... make changes ...
./run_tests.sh

# 5. Format and lint
black glassbox/ api/ dashboard/ tests/
mypy glassbox/

# 6. Commit and push
git checkout -b feature/my-feature
git commit -m "feat: add my feature"
git push origin feature/my-feature
```

**Security Issues:** See [SECURITY.md](SECURITY.md) for reporting vulnerabilities

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

- **GitHub Issues**: [github.com/glassbox-ai/glassbox-mvp/issues](https://github.com/glassbox-ai/glassbox-mvp/issues)
- **Discussions**: [github.com/glassbox-ai/glassbox-mvp/discussions](https://github.com/glassbox-ai/glassbox-mvp/discussions)
- **Email**: team@glassbox.ai
- **Documentation**: [github.com/glassbox-ai/glassbox-mvp#readme](https://github.com/glassbox-ai/glassbox-mvp#readme)

---

## ⭐ Star History

If you find GlassBox useful, please star the repo! It helps others discover the project.

---

## 🎉 Getting Started

### Option 1: Quick Test (2 minutes)
```bash
# Test with GPT-2
python glassbox/tracer.py gpt2-medium
```

### Option 2: Full Dashboard Experience (5 minutes)
```bash
# Run dashboard with Llama 2 7B
export GLASSBOX_MODEL=meta-llama/Llama-2-7b-hf
streamlit run dashboard/app.py
# Visit http://localhost:8503
```

### Option 3: Set Up Llama 2 (10 minutes)
```bash
# Automated setup
./setup_llama.sh
```

### Option 4: Deploy to Cloud (15 minutes)
```bash
# Deploy to Lambda Labs GPU
./cloud/deploy_lambda_labs.sh
```

### Option 5: Production API (1 minute)
```bash
# Start API server
export GLASSBOX_MODEL=meta-llama/Llama-2-7b-hf
uvicorn api.server:app --reload
# Visit http://localhost:8000/docs
```

**Ready to understand your models? Let's go! 🚀**

---

<div align="center">

**Made with ❤️ by the GlassBox team**

*Stop treating AI as a black box. Start understanding it.*

</div>
