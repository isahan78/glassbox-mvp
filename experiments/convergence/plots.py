"""
Plotting functions for the convergence experiment.

Generates four PNG files:
1. layer_sweep.png — logit diff by layer (which layer is most sensitive to steering?)
2. logit_lens.png — target token probability by layer (when does the answer appear?)
3. attention_diff_heatmap.png — attention pattern changes at the peak layer
4. convergence_summary.png — all methods on one chart to show convergence

All plots use matplotlib with a clean, publication-ready style.
"""

import os
from typing import Dict, List, Optional

import matplotlib.pyplot as plt
import numpy as np


def _ensure_output_dir(output_dir: str) -> None:
    """Create output directory if it doesn't exist."""
    os.makedirs(output_dir, exist_ok=True)


def _normalize_to_01(values: List[float]) -> List[float]:
    """Min-max normalize a list of values to [0, 1]."""
    v_min = min(values)
    v_max = max(values)
    if v_max == v_min:
        return [0.5] * len(values)
    return [(v - v_min) / (v_max - v_min) for v in values]


def plot_layer_sweep(
    layer_diffs: Dict[int, float],
    output_dir: str,
) -> int:
    """
    Plot logit_diff vs layer — shows which layer is most sensitive to
    activation steering.

    The peak of this curve is where the model "cares most" about the
    steering vector, indicating the concept is encoded there.

    Args:
        layer_diffs: Dict mapping layer index to logit_diff.
        output_dir: Where to save the plot.

    Returns:
        The peak layer index (for downstream use).
    """
    _ensure_output_dir(output_dir)

    layers = sorted(layer_diffs.keys())
    diffs = [layer_diffs[l] for l in layers]
    peak_layer = layers[np.argmax(diffs)]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(layers, diffs, "o-", color="#2196F3", linewidth=2, markersize=6)

    # Mark the peak layer with a vertical dashed line.
    ax.axvline(
        x=peak_layer, color="#F44336", linestyle="--", linewidth=1.5,
        label=f"Peak: layer {peak_layer} (logit_diff={layer_diffs[peak_layer]:.2f})"
    )

    ax.set_xlabel("Layer", fontsize=12)
    ax.set_ylabel("Logit Diff (target - foil)", fontsize=12)
    ax.set_title("Steering Vector Layer Sweep", fontsize=14)
    ax.set_xticks(layers)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    filepath = os.path.join(output_dir, "layer_sweep.png")
    plt.savefig(filepath, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {filepath}")

    return peak_layer


def plot_logit_lens(
    layer_probs: Dict[int, float],
    target_token: str,
    output_dir: str,
) -> int:
    """
    Plot target token probability vs layer — shows when the correct
    answer "crystallizes" during the forward pass.

    Early layers will show near-zero probability. At some layer, the
    probability jumps — that's where the model "figures out" the answer.

    Args:
        layer_probs: Dict mapping layer index to P(target_token).
        target_token: The token name (for the plot title).
        output_dir: Where to save.

    Returns:
        The layer with the biggest probability jump.
    """
    _ensure_output_dir(output_dir)

    layers = sorted(layer_probs.keys())
    probs = [layer_probs[l] for l in layers]

    # Find the layer with the biggest jump in probability.
    deltas = [probs[i] - probs[i - 1] for i in range(1, len(probs))]
    peak_delta_layer = layers[np.argmax(deltas) + 1]  # +1 offset for delta indexing

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(layers, probs, "s-", color="#4CAF50", linewidth=2, markersize=6)

    # Fill under the curve for visual emphasis.
    ax.fill_between(layers, probs, alpha=0.15, color="#4CAF50")

    ax.axvline(
        x=peak_delta_layer, color="#F44336", linestyle="--", linewidth=1.5,
        label=f"Biggest jump: layer {peak_delta_layer}"
    )

    ax.set_xlabel("Layer", fontsize=12)
    ax.set_ylabel(f"P('{target_token.strip()}')", fontsize=12)
    ax.set_title("Logit Lens: Target Token Probability by Layer", fontsize=14)
    ax.set_xticks(layers)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.set_ylim(bottom=0)

    plt.tight_layout()
    filepath = os.path.join(output_dir, "logit_lens.png")
    plt.savefig(filepath, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {filepath}")

    return peak_delta_layer


def plot_attention_diff(
    head_results: Dict[int, Dict],
    layer: int,
    tokens: List[str],
    output_dir: str,
    top_k: int = 3,
) -> int:
    """
    Plot attention pattern differences for the top-K most affected heads.

    For each head, we show the difference heatmap: steered_pattern - clean_pattern.
    Red = attention increased, blue = attention decreased. This reveals how
    the steering vector reroutes information flow through the attention mechanism.

    Args:
        head_results: Dict from attention_diff_analysis, keyed by head index.
        layer: Which layer these heads are in.
        tokens: List of token strings for axis labels.
        output_dir: Where to save.
        top_k: Number of top heads to plot.

    Returns:
        The head index with the largest attention difference.
    """
    _ensure_output_dir(output_dir)

    # Rank heads by L1 diff and take top-K.
    ranked = sorted(head_results.items(), key=lambda x: x[1]["diff"], reverse=True)
    top_heads = ranked[:top_k]

    # Truncate token labels if too long (for readability).
    max_tokens = 20
    display_tokens = tokens[:max_tokens] if len(tokens) > max_tokens else tokens
    n_display = len(display_tokens)

    fig, axes = plt.subplots(1, top_k, figsize=(6 * top_k, 5))
    if top_k == 1:
        axes = [axes]

    for idx, (head_idx, info) in enumerate(top_heads):
        clean = info["clean_pattern"][:n_display, :n_display].numpy()
        steered = info["steered_pattern"][:n_display, :n_display].numpy()
        diff = steered - clean

        # Use a diverging colormap: blue (decreased) to red (increased).
        vmax = max(abs(diff.min()), abs(diff.max()), 0.01)
        im = axes[idx].imshow(
            diff, cmap="RdBu_r", vmin=-vmax, vmax=vmax, aspect="auto"
        )

        axes[idx].set_title(
            f"Head {head_idx} (L1={info['diff']:.4f})", fontsize=11
        )
        axes[idx].set_xlabel("Key position", fontsize=9)
        if idx == 0:
            axes[idx].set_ylabel("Query position", fontsize=9)

        # Add token labels if few enough tokens to be readable.
        if n_display <= 15:
            axes[idx].set_xticks(range(n_display))
            axes[idx].set_xticklabels(display_tokens, rotation=45, ha="right", fontsize=7)
            axes[idx].set_yticks(range(n_display))
            axes[idx].set_yticklabels(display_tokens, fontsize=7)

        plt.colorbar(im, ax=axes[idx], fraction=0.046, pad=0.04)

    fig.suptitle(
        f"Attention Pattern Differences at Layer {layer} (Steered - Clean)",
        fontsize=13,
    )
    plt.tight_layout()
    filepath = os.path.join(output_dir, "attention_diff_heatmap.png")
    plt.savefig(filepath, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {filepath}")

    return top_heads[0][0]  # Return the most-changed head index


def plot_convergence(
    layer_diffs: Dict[int, float],
    layer_probs: Dict[int, float],
    head_diffs_by_layer: Optional[Dict[int, float]],
    peak_layer: int,
    output_dir: str,
) -> None:
    """
    All three method curves on one chart to visualize convergence.

    Each method's values are normalized to [0, 1] so they're comparable.
    A vertical line marks the peak layer. If the curves all peak at the
    same layer, the methods have converged — we've localized the concept.

    Args:
        layer_diffs: Steering sweep logit diffs by layer.
        layer_probs: Logit lens probabilities by layer.
        head_diffs_by_layer: Optional per-layer attention diff magnitudes.
        peak_layer: The identified peak layer.
        output_dir: Where to save.
    """
    _ensure_output_dir(output_dir)

    layers = sorted(layer_diffs.keys())

    # Normalize each method to [0, 1] for fair comparison.
    sweep_norm = _normalize_to_01([layer_diffs[l] for l in layers])
    lens_norm = _normalize_to_01([layer_probs[l] for l in layers])

    fig, ax = plt.subplots(figsize=(10, 5))

    ax.plot(
        layers, sweep_norm, "o-",
        color="#2196F3", linewidth=2, markersize=5, label="Steering Sweep"
    )
    ax.plot(
        layers, lens_norm, "s-",
        color="#4CAF50", linewidth=2, markersize=5, label="Logit Lens"
    )

    # If we have per-layer attention diffs, plot those too.
    if head_diffs_by_layer:
        attn_values = [head_diffs_by_layer.get(l, 0) for l in layers]
        attn_norm = _normalize_to_01(attn_values)
        ax.plot(
            layers, attn_norm, "^-",
            color="#FF9800", linewidth=2, markersize=5, label="Attention Diff"
        )

    # Mark the convergence point.
    ax.axvline(
        x=peak_layer, color="#F44336", linestyle="--", linewidth=2,
        label=f"Peak layer: {peak_layer}"
    )

    ax.set_xlabel("Layer", fontsize=12)
    ax.set_ylabel("Normalized Signal (0-1)", fontsize=12)
    ax.set_title("Convergence: All Methods on One Chart", fontsize=14)
    ax.set_xticks(layers)
    ax.legend(fontsize=10, loc="upper left")
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    filepath = os.path.join(output_dir, "convergence_summary.png")
    plt.savefig(filepath, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {filepath}")
