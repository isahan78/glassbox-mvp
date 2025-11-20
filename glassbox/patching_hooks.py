"""
GlassBox Patching Hooks - Real-time activation intervention during inference.

This module implements PyTorch hooks to actually patch activations during
the forward pass, enabling true causal interventions.
"""

import torch
import torch.nn as nn
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass

from glassbox.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class PatchSpec:
    """Specification for a single activation patch."""
    layer_idx: int
    component: str  # "resid", "attn", "mlp", "head"
    head_idx: Optional[int] = None
    position: Optional[int] = None  # None = all positions
    replacement: Optional[torch.Tensor] = None  # Tensor to patch in


class ActivationPatchingHook:
    """
    PyTorch hook for patching activations during forward pass.

    This allows real-time intervention in model computations.
    """

    def __init__(
        self,
        patches: List[PatchSpec],
        intervention_alpha: float = 1.0
    ):
        """
        Initialize patching hook.

        Args:
            patches: List of patches to apply
            intervention_alpha: Strength of intervention (0=none, 1=full)
        """
        self.patches = {
            (p.layer_idx, p.component, p.head_idx): p
            for p in patches
        }
        self.alpha = intervention_alpha
        self.hook_handles = []

        logger.debug("Patching hook initialized", extra={
            "num_patches": len(patches),
            "alpha": intervention_alpha
        })

    def create_hook(self, patch: PatchSpec) -> Callable:
        """
        Create a hook function for a specific patch.

        Args:
            patch: Patch specification

        Returns:
            Hook function compatible with register_forward_hook
        """
        def hook_fn(module, input, output):
            """Hook function that patches activations."""
            if patch.replacement is None:
                return output

            # Apply patch
            if patch.position is not None:
                # Patch specific position
                patched = output.clone()
                patched[:, patch.position, :] = (
                    self.alpha * patch.replacement[:, patch.position, :] +
                    (1 - self.alpha) * output[:, patch.position, :]
                )
            else:
                # Patch all positions
                patched = (
                    self.alpha * patch.replacement +
                    (1 - self.alpha) * output
                )

            logger.debug("Applied patch", extra={
                "layer": patch.layer_idx,
                "component": patch.component,
                "position": patch.position,
                "magnitude": torch.norm(patched - output).item()
            })

            return patched

        return hook_fn

    def register_hooks(self, model: nn.Module) -> List:
        """
        Register all hooks on model.

        Args:
            model: TransformerLens model

        Returns:
            List of hook handles for cleanup
        """
        handles = []

        for (layer_idx, component, head_idx), patch in self.patches.items():
            # Get the module to hook
            if component == "resid":
                # Hook residual stream
                module = model.blocks[layer_idx]
            elif component == "attn":
                # Hook attention output
                module = model.blocks[layer_idx].attn
            elif component == "mlp":
                # Hook MLP output
                module = model.blocks[layer_idx].mlp
            elif component == "head":
                # Hook specific attention head
                # This requires more complex logic
                continue
            else:
                logger.warning(f"Unknown component: {component}")
                continue

            # Register hook
            hook_fn = self.create_hook(patch)
            handle = module.register_forward_hook(hook_fn)
            handles.append(handle)

            logger.debug("Registered hook", extra={
                "layer": layer_idx,
                "component": component
            })

        self.hook_handles = handles
        return handles

    def remove_hooks(self):
        """Remove all registered hooks."""
        for handle in self.hook_handles:
            handle.remove()
        self.hook_handles = []
        logger.debug("Removed all hooks", extra={
            "num_removed": len(self.hook_handles)
        })


class PatchingContext:
    """
    Context manager for safe activation patching.

    Example:
        with PatchingContext(model, patches) as ctx:
            output = model(input)
        # Hooks automatically removed
    """

    def __init__(
        self,
        model: nn.Module,
        patches: List[PatchSpec],
        alpha: float = 1.0
    ):
        """
        Initialize patching context.

        Args:
            model: Model to patch
            patches: List of patches to apply
            alpha: Intervention strength
        """
        self.model = model
        self.hook = ActivationPatchingHook(patches, alpha)

    def __enter__(self):
        """Register hooks."""
        self.hook.register_hooks(self.model)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Remove hooks."""
        self.hook.remove_hooks()
        return False


def apply_patching_intervention(
    model: nn.Module,
    input_ids: torch.Tensor,
    patches: List[PatchSpec],
    alpha: float = 1.0
) -> torch.Tensor:
    """
    Run model forward pass with patching interventions.

    Args:
        model: Model to run
        input_ids: Input token IDs
        patches: List of patches to apply
        alpha: Intervention strength

    Returns:
        Model output logits with patches applied
    """
    with PatchingContext(model, patches, alpha):
        logits = model(input_ids)

    return logits


# Example usage
if __name__ == "__main__":
    print("🔧 GlassBox Patching Hooks Example\n")
    print("=" * 60)

    from glassbox.tracer import ActivationTracer

    # Initialize tracer
    print("\n1. Loading model...")
    tracer = ActivationTracer("gpt2-small")

    # Run clean forward pass to get activations
    print("\n2. Running clean forward pass...")
    clean_prompt = "The Eiffel Tower is in Paris"
    clean_result = tracer.trace(clean_prompt)

    print(f"   Input: {clean_prompt}")
    print(f"   Output: {clean_result.output_text}")

    # Create patch specification
    print("\n3. Creating patch specification...")
    patch = PatchSpec(
        layer_idx=8,
        component="resid",
        replacement=clean_result.activation_cache["layer_8_resid"]
    )

    # Apply patch during corrupted run
    print("\n4. Running with patch...")
    corrupted_prompt = "The Eiffel Tower is in London"

    # Tokenize
    tokens = tracer.model.to_tokens(corrupted_prompt)

    # Run with patch
    with PatchingContext(tracer.model, [patch]):
        logits = tracer.model(tokens)

    # Decode output
    output_token_id = logits[0, -1].argmax().item()
    output_token = tracer.model.to_string(output_token_id)

    print(f"   Input: {corrupted_prompt}")
    print(f"   Output (with patch): {output_token}")

    print("\n" + "=" * 60)
    print("✅ Patching hooks example complete!\n")
