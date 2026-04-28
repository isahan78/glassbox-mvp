"""
Steering vector computation and application.

This module implements activation steering — a technique from representation
engineering where we:
1. Compute a "steering vector" that represents a concept direction in
   activation space, by taking the mean activation difference between
   contrastive prompt pairs.
2. Add that vector to the model's residual stream during inference to
   shift its behavior toward (or away from) the concept.

Key distinction from activation patching:
- Patching REPLACES activations: output = alpha * new + (1-alpha) * old
- Steering ADDS to activations: output = original + alpha * vector
This makes steering a gentler, more controllable intervention.

References:
- Turner et al. (2023), "Activation Addition: Steering Language Models
  Without Optimization"
- Rimsky et al. (2023), "Steering Llama 2 via Contrastive Activation Addition"
"""

from contextlib import contextmanager
from typing import Dict, Optional, Tuple

import torch
from transformer_lens import HookedTransformer

from config import ExperimentConfig


def compute_steering_vectors(
    model: HookedTransformer,
    config: ExperimentConfig,
) -> Dict[int, torch.Tensor]:
    """
    Compute a steering vector at every layer from contrastive prompt pairs.

    For each layer, we:
    1. Run all positive prompts, grab residual stream at the LAST token position
       (that's where the next-token prediction happens in autoregressive models).
    2. Do the same for negative prompts.
    3. Steering vector = mean(positive) - mean(negative).

    This difference vector points in the direction that makes the model predict
    the target token instead of the foil token. Its magnitude varies by layer —
    layers where the model "processes" this concept will have larger, more
    meaningful vectors.

    Args:
        model: A TransformerLens HookedTransformer.
        config: Experiment config with contrastive pairs.

    Returns:
        Dict mapping layer index to steering vector tensor of shape [d_model].
    """
    n_layers = model.cfg.n_layers
    positive_prompts = config.positive_prompts
    negative_prompts = config.negative_prompts

    # We'll accumulate activations for each layer, then average.
    # Using lists first, then stack + mean, to handle variable sequence lengths.
    positive_acts = {layer: [] for layer in range(n_layers)}
    negative_acts = {layer: [] for layer in range(n_layers)}

    print(f"  Computing steering vectors from {config.num_pairs} contrastive pairs...")

    # Collect positive prompt activations
    for prompt in positive_prompts:
        tokens = model.to_tokens(prompt)
        _, cache = model.run_with_cache(tokens)

        for layer in range(n_layers):
            # hook_resid_post is the residual stream AFTER the layer's processing.
            # Shape: [batch=1, seq_len, d_model]
            # We grab the last token position [0, -1, :] because that's where
            # the model makes its next-token prediction.
            resid = cache[f"blocks.{layer}.hook_resid_post"][0, -1, :]
            positive_acts[layer].append(resid.detach())

    # Collect negative prompt activations
    for prompt in negative_prompts:
        tokens = model.to_tokens(prompt)
        _, cache = model.run_with_cache(tokens)

        for layer in range(n_layers):
            resid = cache[f"blocks.{layer}.hook_resid_post"][0, -1, :]
            negative_acts[layer].append(resid.detach())

    # Compute the steering vector at each layer: mean_positive - mean_negative
    steering_vectors = {}
    for layer in range(n_layers):
        mean_pos = torch.stack(positive_acts[layer]).mean(dim=0)  # [d_model]
        mean_neg = torch.stack(negative_acts[layer]).mean(dim=0)  # [d_model]
        steering_vectors[layer] = mean_pos - mean_neg

    print(f"  Done. Vector norms by layer: ", end="")
    norms = [f"L{l}={steering_vectors[l].norm():.2f}" for l in range(n_layers)]
    print(", ".join(norms))

    return steering_vectors


@contextmanager
def steering_hook(
    model: HookedTransformer,
    steering_vector: torch.Tensor,
    layer: int,
    alpha: float,
    position: Optional[int] = None,
):
    """
    Context manager that temporarily adds a steering vector to the residual
    stream at a specific layer during the forward pass.

    This uses TransformerLens's hook system rather than raw PyTorch hooks,
    which is cleaner and integrates with TransformerLens's cache system.

    The hook does: residual_stream += alpha * steering_vector
    This is an ADDITIVE intervention — we're nudging the model's internal
    representations, not replacing them.

    Args:
        model: The HookedTransformer.
        steering_vector: Direction to steer toward, shape [d_model].
        layer: Which layer to intervene at.
        alpha: Steering strength. Positive = toward concept, negative = away.
        position: Token position to steer at. None = last position only
                  (the prediction position for autoregressive models).

    Yields:
        None. The hook is active inside the context block.
    """
    # Normalize the steering vector to unit norm, then scale by alpha.
    # This way, alpha directly controls the L2 magnitude of the perturbation,
    # making it comparable across layers and experiments.
    direction = steering_vector / (steering_vector.norm() + 1e-8)
    scaled_vector = alpha * direction

    # Define the hook function. TransformerLens hooks receive
    # (activation_tensor, hook_object) and return the modified tensor.
    def hook_fn(resid, hook):
        # resid shape: [batch, seq_len, d_model]
        if position is not None:
            resid[:, position, :] += scaled_vector
        else:
            # Default: steer only at the last token position.
            # This is where the next-token prediction happens.
            resid[:, -1, :] += scaled_vector
        return resid

    # TransformerLens hook name for the residual stream after layer processing.
    hook_name = f"blocks.{layer}.hook_resid_post"

    # Use TransformerLens's built-in hook context manager.
    # This automatically registers and removes the hook.
    fwd_hooks = [(hook_name, hook_fn)]
    with model.hooks(fwd_hooks=fwd_hooks):
        yield


def run_with_steering(
    model: HookedTransformer,
    prompt: str,
    steering_vector: torch.Tensor,
    layer: int,
    alpha: float,
) -> torch.Tensor:
    """
    Run a forward pass with a steering vector applied at one layer.

    Args:
        model: The HookedTransformer.
        prompt: Input text.
        steering_vector: Direction to steer, shape [d_model].
        layer: Which layer to add the vector at.
        alpha: Steering strength.

    Returns:
        Logits tensor, shape [batch=1, seq_len, vocab_size].
    """
    tokens = model.to_tokens(prompt)

    with steering_hook(model, steering_vector, layer, alpha):
        logits = model(tokens)

    return logits


def layer_sweep(
    model: HookedTransformer,
    config: ExperimentConfig,
    steering_vectors: Dict[int, torch.Tensor],
    prompt: str,
) -> Dict[int, float]:
    """
    Sweep the steering vector across all layers, one at a time.

    For each layer:
    1. Apply the steering vector ONLY at that layer.
    2. Run inference.
    3. Record logit_diff = logit(target_token) - logit(foil_token)
       at the last token position.

    The layer where logit_diff is highest is where the model is most
    sensitive to this concept — i.e., where the concept is "encoded."

    Args:
        model: The HookedTransformer.
        config: Experiment config with target/foil tokens and alpha.
        steering_vectors: Dict of {layer: vector} from compute_steering_vectors.
        prompt: The prompt to run inference on.

    Returns:
        Dict mapping layer index to logit_diff (float).
    """
    # Get token IDs for the target and foil tokens.
    target_id = model.to_single_token(config.target_token)
    foil_id = model.to_single_token(config.foil_token)

    n_layers = model.cfg.n_layers
    layer_diffs = {}

    # Also compute the baseline (no steering) for reference.
    baseline_logits = model(model.to_tokens(prompt))
    baseline_diff = (
        baseline_logits[0, -1, target_id] - baseline_logits[0, -1, foil_id]
    ).item()
    print(f"  Baseline logit_diff (no steering): {baseline_diff:.3f}")

    for layer in range(n_layers):
        logits = run_with_steering(
            model, prompt, steering_vectors[layer], layer, config.alpha
        )

        # logit_diff: how much the model prefers target over foil.
        # Higher = steering at this layer is more effective at pushing
        # the model toward the target answer.
        target_logit = logits[0, -1, target_id].item()
        foil_logit = logits[0, -1, foil_id].item()
        diff = target_logit - foil_logit

        layer_diffs[layer] = diff

    # Report the peak layer
    peak_layer = max(layer_diffs, key=layer_diffs.get)
    print(f"  Peak steering layer: {peak_layer} (logit_diff = {layer_diffs[peak_layer]:.3f})")

    return layer_diffs
