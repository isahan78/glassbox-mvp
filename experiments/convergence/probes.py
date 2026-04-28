"""
Probing methods: logit lens and attention analysis.

These are two independent ways to figure out which layer encodes a concept:

1. Logit lens — at each layer, project the residual stream into vocabulary
   space using the model's unembedding matrix. This reveals when the correct
   answer "crystallizes" during the forward pass. Introduced by nostalgebraist
   (2020), "interpreting GPT: the logit lens."

2. Attention analysis — compare attention patterns between a clean run and
   a steered run. Heads that change the most are the ones the steering vector
   "talks through" — they're mechanistically involved in processing the concept.
"""

from typing import Dict, List, Tuple

import torch
import torch.nn.functional as F
from transformer_lens import HookedTransformer

from config import ExperimentConfig
from steering import steering_hook


def logit_lens(
    model: HookedTransformer,
    prompt: str,
    config: ExperimentConfig,
) -> Dict[int, float]:
    """
    Apply the logit lens at every layer to track when the target token
    becomes the model's prediction.

    At each layer, we take the residual stream (the running "state" of the
    computation) and project it directly to vocabulary space using the
    model's unembedding matrix W_U. Then we look at the probability the
    model assigns to our target token at that layer.

    Early layers will be near-random. At some point, the probability jumps —
    that's the layer where the model "figures out" the answer.

    Since we loaded with fold_ln=False, the raw residual stream has NOT
    been layer-normed. We must apply the model's final layer norm (ln_final)
    before projecting through the unembedding matrix. Without this, the
    logits are wildly scaled and softmax collapses to near-zero for
    everything. This is the standard "logit lens" approach.

    Args:
        model: The HookedTransformer.
        prompt: Input text.
        config: Config with target_token.

    Returns:
        Dict mapping layer index to P(target_token) at that layer.
    """
    target_id = model.to_single_token(config.target_token)
    tokens = model.to_tokens(prompt)
    n_layers = model.cfg.n_layers

    # Single forward pass, cache everything.
    _, cache = model.run_with_cache(tokens)

    layer_probs = {}
    for layer in range(n_layers):
        # Get the residual stream at this layer, last token position.
        # Shape: [d_model]
        resid = cache[f"blocks.{layer}.hook_resid_post"][0, -1, :]

        # CRITICAL: Apply the final layer norm before unembedding.
        # The model normally does: logits = unembed(ln_final(resid_final)).
        # For the logit lens, we pretend this layer is the final one
        # and apply the same ln_final. Without this, the residual stream
        # magnitudes are wrong and softmax produces near-zero probabilities.
        resid_normed = model.ln_final(resid)

        # Project to vocabulary space using the unembedding matrix.
        # W_U shape: [d_model, vocab_size], b_U shape: [vocab_size]
        # This gives us "what would the model predict if computation
        # stopped at this layer?"
        logits_at_layer = resid_normed @ model.W_U + model.b_U  # [vocab_size]

        # Convert to probabilities via softmax.
        probs = F.softmax(logits_at_layer, dim=-1)

        # Extract probability of our target token.
        target_prob = probs[target_id].item()
        layer_probs[layer] = target_prob

    # Find where the biggest jump happens — that's where the concept
    # gets "written" into the residual stream.
    prob_values = list(layer_probs.values())
    deltas = [prob_values[i] - prob_values[i - 1] for i in range(1, len(prob_values))]
    peak_delta_layer = deltas.index(max(deltas)) + 1  # +1 because deltas start at layer 1
    print(f"  Logit lens: biggest probability jump at layer {peak_delta_layer}")
    print(f"  Target token probs: ", end="")
    for layer, prob in layer_probs.items():
        print(f"L{layer}={prob:.4f}", end=" ")
    print()

    return layer_probs


def attention_diff_analysis(
    model: HookedTransformer,
    prompt: str,
    steering_vector: torch.Tensor,
    layer: int,
    config: ExperimentConfig,
) -> Dict[int, Dict]:
    """
    Compare attention patterns between a clean run and a steered run.

    We steer at the given layer (typically the peak layer from the sweep)
    and look at how each attention head's pattern changes. Heads that change
    a lot are mechanistically involved in processing the concept the steering
    vector represents.

    IMPORTANT: We steer on hook_resid_pre (the INPUT to the layer), not
    hook_resid_post (the output). If we steered on hook_resid_post, the
    steering vector would only affect DOWNSTREAM layers — it wouldn't
    change the attention patterns at the target layer itself, because
    attention has already been computed by then. By steering on the input,
    the attention heads at this layer see the modified residual stream
    and their patterns change accordingly.

    Why L1 difference? It measures the total redistribution of attention
    probability mass. If a head shifts 0.3 probability from one token to
    another, its L1 diff will be ~0.6 (lost from one place, gained at another).
    This is more interpretable than L2 for attention patterns.

    Args:
        model: The HookedTransformer.
        prompt: Input text.
        steering_vector: The steering vector to apply.
        layer: Which layer to steer at and analyze.
        config: Config with alpha.

    Returns:
        Dict mapping head_idx to:
            - "diff": L1 difference magnitude (float)
            - "clean_pattern": attention pattern without steering [seq, seq]
            - "steered_pattern": attention pattern with steering [seq, seq]
    """
    tokens = model.to_tokens(prompt)
    n_heads = model.cfg.n_heads

    # --- Clean run: no steering ---
    _, clean_cache = model.run_with_cache(tokens)

    # Attention pattern shape: [batch, n_heads, query_pos, key_pos]
    clean_attn = clean_cache[f"blocks.{layer}.attn.hook_pattern"][0]  # [n_heads, q, k]

    # --- Steered run: add steering vector BEFORE the layer ---
    # We use hook_resid_pre so the steering vector modifies the input to
    # this layer's attention computation. This is what makes the attention
    # patterns actually change.
    #
    # IMPORTANT: Unlike the layer sweep (which normalizes to unit norm),
    # here we use the RAW steering vector scaled by alpha. Why? The residual
    # stream at layer 8 has norm ~88. A unit-norm vector * alpha=4 is only
    # a 4.5% perturbation — enough to shift logits but too small to
    # meaningfully change attention patterns. The raw contrastive difference
    # vector has a natural magnitude that reflects how much the concept
    # actually matters at this layer, so it produces visible attention shifts.
    #
    # We also steer at ALL token positions, not just the last one. Attention
    # patterns depend on both queries and keys — if we only modify the last
    # position, only that position's queries change. By modifying all
    # positions, we also change the keys that other positions attend to,
    # producing much richer and more informative attention diffs.
    hook_name = f"blocks.{layer}.hook_resid_pre"

    scaled_vector = config.alpha * steering_vector

    def steer_fn(resid, hook):
        # Add to ALL positions so both queries and keys are affected.
        resid += scaled_vector.unsqueeze(0).unsqueeze(0)
        return resid

    with model.hooks(fwd_hooks=[(hook_name, steer_fn)]):
        _, steered_cache = model.run_with_cache(tokens)

    steered_attn = steered_cache[f"blocks.{layer}.attn.hook_pattern"][0]  # [n_heads, q, k]

    # --- Compute per-head L1 differences ---
    head_results = {}
    for head in range(n_heads):
        clean_pattern = clean_attn[head].detach()      # [query_pos, key_pos]
        steered_pattern = steered_attn[head].detach()   # [query_pos, key_pos]

        # L1 difference: total absolute change in attention weights.
        # We average over query positions to get a single scalar.
        l1_diff = (clean_pattern - steered_pattern).abs().mean().item()

        head_results[head] = {
            "diff": l1_diff,
            "clean_pattern": clean_pattern.cpu(),
            "steered_pattern": steered_pattern.cpu(),
        }

    # Rank heads by how much they changed.
    ranked = sorted(head_results.items(), key=lambda x: x[1]["diff"], reverse=True)
    print(f"  Attention diff at layer {layer}:")
    for head_idx, info in ranked[:5]:
        print(f"    Head {head_idx}: L1 diff = {info['diff']:.4f}")

    return head_results
