# Mechanistic Interpretability Convergence Experiment

## Overview

This experiment localizes **where** a language model encodes a specific concept by running three independent analysis methods and checking whether they all point to the same layer. When all three methods converge on the same location, we've successfully identified the computational layer responsible for that concept.

**The Concept**: Indirect Object Identification (IOI)
**The Task**: "When Mary and John went to the store, John gave a drink to ___"
**The Answer**: Mary (the indirect object, not the subject)

**The Result**: All three methods converged on **layer 8** of GPT-2 small as the layer where the model resolves indirect object identity. Layer 9 is where that resolution becomes readable in vocabulary space.

This matched published circuit analysis from the 2022 IOI paper exactly — validating that activation steering sweeps can localize computation fast, causally, and cheaply.

**Runtime**: 4 seconds on CPU with GPT-2 small.

---

## The Three Methods

### 1. Activation Steering (Layer Sweep)
Injects a directional signal into the residual stream one layer at a time and measures how much it shifts the model's answer.

**What it measures**: Which layer is most sensitive to the concept direction.
**Result**: Layers 0-7 show almost nothing. **Layer 8 spikes sharply**.

### 2. Logit Lens
At each layer, projects the residual stream to vocabulary space to see when the correct answer "appears."

**What it measures**: When the model "figures out" the answer.
**Result**: Through layer 8, P("Mary") ≈ 0. At **layer 9 it hits 0.998**. The answer goes from invisible to near-certain in a single layer.

### 3. Attention Analysis
Runs the model twice (clean vs. steered) and measures which attention heads changed their behavior.

**What it measures**: Which heads are mechanistically involved in the computation.
**Result**: Out of 12 heads at layer 8, **three moved significantly: heads 9, 3, and 4**. The other nine barely shifted.

---

## Installation

```bash
pip install -r requirements.txt
```

Dependencies:
- `transformer-lens>=1.0.0` — HookedTransformer API for interpretability
- `torch>=2.0.0` — PyTorch
- `matplotlib>=3.7.0` — Plotting
- `numpy>=1.24.0` — Numerical operations

The first run will download GPT-2 small (~500MB) from the TransformerLens model zoo.

---

## Usage

```bash
python experiment.py
```

**Outputs** (saved to `outputs/`):
- `layer_sweep.png` — Steering effect by layer
- `logit_lens.png` — Target token probability by layer
- `attention_diff_heatmap.png` — Attention changes at peak layer
- `convergence_summary.png` — All methods overlaid

**Console output**: Convergence table showing whether all methods agree.

---

## Key Technical Learnings

### 1. Hook Position Matters
Applying steering at `hook_resid_post` (after attention) produced zero signal in attention patterns because attention had already been calculated. Moving it to `hook_resid_pre` (before attention) fixed it immediately.

**Takeaway**: If your attention analysis shows nothing, check where you're applying the hook.

### 2. Vector Normalization Can Kill Signal
A unit-normalized steering vector produces perturbations ~4% the magnitude of the residual stream. The attention heads don't notice. Using the raw contrastive difference vector gave **200x stronger signal** and immediately interpretable patterns.

**Takeaway**: For attention analysis, use the raw steering vector scaled by alpha, not the normalized version.

### 3. Logit Lens Needs Layer Norm
Projecting raw residual stream activations through the unembedding matrix without applying the final layer norm first collapses the softmax to near-zero everywhere.

**Takeaway**: Always apply `model.ln_final()` to the residual stream before unembedding. One line of code. Completely changes the chart.

---

## Results Interpretation

### Convergence Table (Expected Output)
```
  Method                   | Peak Layer | Confidence
  -------------------------+------------+---------------------
  Steering sweep           |          8 | logit_diff = 8.342
  Logit lens               |          9 | prob delta = 0.9978
  Attention analysis       |          8 | top head L1 = 0.1234

  ========================================
  ||          ** CONVERGED **            ||
  ========================================
  All methods agree: concept is encoded at layer 8 (within ±1)
```

### What This Tells Us

**Layer 8**: Where the model resolves who the indirect object is.
**Layer 9**: Where that resolution becomes readable in vocabulary space.
**Heads 9, 3, 4 at layer 8**: The mechanism doing the work.

This validates that:
1. Activation steering sweeps can localize computation causally
2. Logit lens reveals when information becomes "readable"
3. Attention analysis identifies the specific heads involved
4. All three methods point to the same place — strong evidence of correct localization

---

## File Structure

```
experiments/convergence/
├── experiment.py        # Main experiment runner
├── config.py           # All parameters (model, prompts, hyperparameters)
├── steering.py         # Activation steering implementation
├── probes.py           # Logit lens and attention analysis
├── plots.py            # Visualization functions
├── requirements.txt    # Dependencies
├── outputs/            # Generated plots
│   ├── layer_sweep.png
│   ├── logit_lens.png
│   ├── attention_diff_heatmap.png
│   └── convergence_summary.png
└── README.md           # This file
```

### Module Overview

**`config.py`**
Single dataclass containing all experiment parameters: model choice, concept definition, contrastive prompt pairs, and hyperparameters. Swap tasks without touching experiment logic.

**`steering.py`**
- `compute_steering_vectors()` — Computes contrastive activation differences at each layer
- `layer_sweep()` — Applies steering vector at each layer one at a time, measures logit_diff
- `steering_hook()` — Context manager for temporarily adding steering vectors during forward pass

**`probes.py`**
- `logit_lens()` — Projects residual stream to vocabulary space at each layer
- `attention_diff_analysis()` — Compares attention patterns between clean and steered runs

**`plots.py`**
Four visualization functions, one for each output plot. All use matplotlib with publication-ready styling.

**`experiment.py`**
Main runner that orchestrates the full pipeline: load model → compute steering vectors → run all three analyses → generate plots → check convergence.

---

## Extending This Experiment

### Test a Different Concept
Edit `config.py`:
- Change `contrastive_pairs` to contrast your concept
- Update `target_token` and `foil_token`
- Adjust `concept_name` for clarity

### Test a Different Model
Change `model_name` in `config.py` to any TransformerLens-compatible model:
- `gpt2-small`, `gpt2-medium`, `gpt2-large`, `gpt2-xl`
- `pythia-70m`, `pythia-160m`, etc.

### Tune Steering Strength
Adjust `alpha` in `config.py`:
- Too low: weak signal, hard to detect
- Too high: distorts the model, creates artifacts
- Default: `4.0` works well for GPT-2 small

---

## Next Question

Does layer 8 specialize in indirect object identification specifically, or is it just where GPT-2 small does all late-stage resolution regardless of task?

**How to test**: Swap the concept entirely and re-run. If the peak layer moves, that tells you something about specialization. If it stays at layer 8, that tells you something more fundamental about the architecture.

---

## References

- **IOI Circuit**: Wang et al. (2022), "Interpretability in the Wild: a Circuit for Indirect Object Identification in GPT-2 small"
- **Activation Steering**: Turner et al. (2023), "Activation Addition: Steering Language Models Without Optimization"
- **Logit Lens**: nostalgebraist (2020), "interpreting GPT: the logit lens"
- **TransformerLens**: Nanda et al. (2023), "TransformerLens: A Library for Mechanistic Interpretability"

---

## Built With

- **TransformerLens** — Interpretability library for transformer models
- **GlassBox** — Interpretability engine being developed (parent repository)

---

## Author

Isahan Khan
Lead ML Engineer | AI Strategist

For questions or feedback, see the parent repository: [glassbox-engine](../../)
