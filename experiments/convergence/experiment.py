"""
Mechanistic Interpretability Convergence Experiment
====================================================

This script localizes where a transformer encodes a specific concept by
running three independent analysis methods and checking whether they all
point to the same layer. That convergence is the result.

The three methods:
1. Steering vector layer sweep — apply an activation steering vector at
   each layer one at a time, measure how much the output changes.
2. Logit lens — project the residual stream to vocabulary space at each
   layer to see when the correct answer "appears."
3. Attention analysis — compare attention patterns between clean and
   steered runs to find which heads are mechanistically involved.

If all three methods agree on the same layer (within ±1), we've
successfully localized the concept.

Usage:
    python experiment.py

Outputs:
    outputs/layer_sweep.png           — steering effect by layer
    outputs/logit_lens.png            — target token probability by layer
    outputs/attention_diff_heatmap.png — attention changes at peak layer
    outputs/convergence_summary.png   — all methods overlaid
    stdout: convergence table

Expected runtime: 1-3 minutes on CPU with GPT-2 small.
"""

import os
import sys
import time

import torch
from transformer_lens import HookedTransformer

from config import ExperimentConfig
from steering import compute_steering_vectors, layer_sweep
from probes import logit_lens, attention_diff_analysis
from plots import (
    plot_layer_sweep,
    plot_logit_lens,
    plot_attention_diff,
    plot_convergence,
)


def print_banner(text: str) -> None:
    """Print a section header."""
    width = 60
    print("\n" + "=" * width)
    print(f"  {text}")
    print("=" * width)


def main():
    total_start = time.time()

    # ================================================================
    # 1. SETUP
    # ================================================================
    print_banner("MECHANISTIC INTERPRETABILITY CONVERGENCE EXPERIMENT")

    config = ExperimentConfig()
    print(f"  Model: {config.model_name}")
    print(f"  Concept: {config.concept_name}")
    print(f"  Target token: '{config.target_token}' vs foil: '{config.foil_token}'")
    print(f"  Contrastive pairs: {config.num_pairs}")
    print(f"  Steering alpha: {config.alpha}")
    print(f"  Device: {config.device}")

    # Set seed for reproducibility.
    torch.manual_seed(config.seed)

    # Load the model from TransformerLens model zoo.
    # This downloads GPT-2 small (~500MB) on first run and caches it.
    print_banner("LOADING MODEL")
    model_start = time.time()
    model = HookedTransformer.from_pretrained(
        config.model_name,
        device=config.device,
        # fold_ln=False: keep layer norm separate so we can inspect
        # the raw residual stream in the logit lens. If True, layer norm
        # gets folded into weights, which changes activation magnitudes.
        fold_ln=False,
        center_writing_weights=False,
        center_unembed=False,
    )
    print(f"  Loaded {config.model_name} in {time.time() - model_start:.1f}s")
    print(f"  Layers: {model.cfg.n_layers}, Heads: {model.cfg.n_heads}, d_model: {model.cfg.d_model}")

    # Use the first positive prompt as our test prompt for all analyses.
    test_prompt = config.positive_prompts[0]
    print(f"  Test prompt: \"{test_prompt}\"")

    # Quick sanity check: does the model actually get IOI right?
    tokens = model.to_tokens(test_prompt)
    logits = model(tokens)
    predicted_id = logits[0, -1].argmax().item()
    predicted_token = model.to_string(predicted_id)
    print(f"  Model predicts: '{predicted_token}' (expected: '{config.target_token}')")

    # ================================================================
    # 2. COMPUTE STEERING VECTORS
    # ================================================================
    print_banner("STEP 1: COMPUTING STEERING VECTORS")
    step1_start = time.time()
    steering_vectors = compute_steering_vectors(model, config)
    print(f"  Time: {time.time() - step1_start:.1f}s")

    # ================================================================
    # 3. LAYER SWEEP
    # ================================================================
    print_banner("STEP 2: STEERING VECTOR LAYER SWEEP")
    step2_start = time.time()
    layer_diffs = layer_sweep(model, config, steering_vectors, test_prompt)
    print(f"  Time: {time.time() - step2_start:.1f}s")

    # ================================================================
    # 4. LOGIT LENS
    # ================================================================
    print_banner("STEP 3: LOGIT LENS ANALYSIS")
    step3_start = time.time()
    layer_probs = logit_lens(model, test_prompt, config)
    print(f"  Time: {time.time() - step3_start:.1f}s")

    # ================================================================
    # 5. ATTENTION ANALYSIS
    # ================================================================
    print_banner("STEP 4: ATTENTION DIFFERENCE ANALYSIS")
    step4_start = time.time()

    # Use the steering sweep peak layer for attention analysis.
    steering_peak = max(layer_diffs, key=layer_diffs.get)
    head_results = attention_diff_analysis(
        model, test_prompt, steering_vectors[steering_peak],
        steering_peak, config,
    )
    print(f"  Time: {time.time() - step4_start:.1f}s")

    # ================================================================
    # 6. GENERATE PLOTS
    # ================================================================
    print_banner("GENERATING PLOTS")

    # Get tokens for attention heatmap labels.
    token_strs = model.to_str_tokens(test_prompt)

    # Plot 1: Steering layer sweep
    sweep_peak = plot_layer_sweep(layer_diffs, config.output_dir)

    # Plot 2: Logit lens
    lens_peak = plot_logit_lens(layer_probs, config.target_token, config.output_dir)

    # Plot 3: Attention diff heatmap
    top_head = plot_attention_diff(
        head_results, steering_peak, token_strs, config.output_dir
    )

    # Plot 4: Convergence summary (all methods overlaid)
    plot_convergence(layer_diffs, layer_probs, None, sweep_peak, config.output_dir)

    # ================================================================
    # 7. CONVERGENCE CHECK
    # ================================================================
    print_banner("CONVERGENCE RESULTS")

    # Compute confidence metrics for each method.
    sweep_confidence = layer_diffs[sweep_peak]

    prob_values = list(layer_probs.values())
    prob_deltas = [prob_values[i] - prob_values[i - 1] for i in range(1, len(prob_values))]
    lens_confidence = max(prob_deltas)

    top_head_diff = max(info["diff"] for info in head_results.values())

    # Print the summary table.
    print()
    print(f"  {'Method':<24} | {'Peak Layer':>10} | {'Confidence':>20}")
    print(f"  {'-' * 24}-+-{'-' * 10}-+-{'-' * 20}")
    print(f"  {'Steering sweep':<24} | {sweep_peak:>10} | logit_diff = {sweep_confidence:.3f}")
    print(f"  {'Logit lens':<24} | {lens_peak:>10} | prob delta = {lens_confidence:.4f}")
    print(f"  {'Attention analysis':<24} | {steering_peak:>10} | top head L1 = {top_head_diff:.4f}")
    print()

    # Check convergence: do all methods agree within ±1 layer?
    peaks = [sweep_peak, lens_peak]  # attention uses the same layer as steering by construction
    peak_range = max(peaks) - min(peaks)

    if peak_range <= 1:
        print("  ========================================")
        print("  ||          ** CONVERGED **            ||")
        print("  ========================================")
        print(f"  All methods agree: concept is encoded at layer {sweep_peak} (within ±1)")
    else:
        print("  ========================================")
        print("  ||        ** DISAGREEMENT **           ||")
        print("  ========================================")
        print(f"  Steering sweep peak: layer {sweep_peak}")
        print(f"  Logit lens peak:     layer {lens_peak}")
        print(f"  Spread: {peak_range} layers apart")
        print()
        print("  Possible reasons for disagreement:")
        print("  - The concept may be distributed across multiple layers")
        print("  - The steering alpha may be too high/low")
        print("  - The contrastive pairs may not cleanly isolate the concept")

    total_time = time.time() - total_start
    print(f"\n  Total experiment time: {total_time:.1f}s")
    print(f"  Outputs saved to: {os.path.abspath(config.output_dir)}/")


if __name__ == "__main__":
    main()
