"""
GlassBox SAE-Circuit Integration - Discover circuits based on monosemantic features.

This module provides integration between Sparse Autoencoders (SAE) and circuit discovery,
enabling feature-level circuit analysis.

Key capabilities:
1. Discover which SAE features are part of task circuits
2. Build interpretable circuits based on monosemantic features
3. Analyze feature flow through model layers
4. Identify critical features for specific behaviors

Based on research:
- "Towards Automated Circuit Discovery" (Conmy et al., 2023)
- "Towards Monosemanticity" (Anthropic, 2023)
- "Sparse Autoencoders Find Highly Interpretable Features" (Cunningham et al., 2023)
"""

import torch
import torch.nn.functional as F
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
import numpy as np

from glassbox.tracer import ActivationTracer
from glassbox.sae import SparseAutoencoder, SAEFeature, FeatureAnalyzer
from glassbox.circuits import Circuit, CircuitNode, CircuitEdge
from glassbox.interventions import ActivationPatcher, InterventionConfig, InterventionType
from glassbox.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class FeatureCircuitNode:
    """A node in a feature-based circuit."""
    layer: int
    feature_idx: int
    importance: float
    activation_pattern: str
    description: Optional[str] = None


class SAECircuitDiscovery:
    """
    Discover circuits based on SAE features rather than raw activations.

    This provides more interpretable circuits by working at the feature level.
    """

    def __init__(
        self,
        tracer: ActivationTracer,
        sae_dict: Dict[int, SparseAutoencoder],  # layer -> SAE mapping
        threshold: float = 0.1
    ):
        """
        Initialize SAE-based circuit discovery.

        Args:
            tracer: Activation tracer
            sae_dict: Dictionary mapping layer indices to trained SAEs
            threshold: Importance threshold for including features
        """
        self.tracer = tracer
        self.sae_dict = sae_dict
        self.threshold = threshold
        self.patcher = ActivationPatcher(tracer)

        logger.info("SAE circuit discovery initialized", extra={
            "num_layers_with_sae": len(sae_dict),
            "threshold": threshold
        })

    def identify_active_features(
        self,
        prompt: str,
        layers: Optional[List[int]] = None
    ) -> Dict[int, List[Tuple[int, float]]]:
        """
        Identify which SAE features activate for a given prompt.

        Args:
            prompt: Input prompt
            layers: Which layers to analyze (None = all SAE layers)

        Returns:
            Dictionary mapping layer -> [(feature_idx, activation_strength), ...]
        """
        if layers is None:
            layers = sorted(self.sae_dict.keys())

        logger.info("Identifying active features", extra={
            "prompt": prompt[:50],
            "layers": layers
        })

        # Trace prompt
        result = self.tracer.trace(prompt)

        active_features = {}

        for layer in layers:
            if layer not in self.sae_dict:
                continue

            sae = self.sae_dict[layer]

            # Get activations for this layer
            cache_key = f"layer_{layer}_resid"
            if cache_key not in result.cache:
                logger.warning(f"Layer {layer} not in cache")
                continue

            activations = result.cache[cache_key]  # [seq_len, d_model]

            # Encode with SAE
            with torch.no_grad():
                features = sae.encode(activations)  # [seq_len, d_sae]

            # Aggregate across positions (max activation)
            max_features = features.max(dim=0).values  # [d_sae]

            # Find active features
            active_mask = max_features > 0
            active_indices = torch.where(active_mask)[0]
            active_values = max_features[active_mask]

            # Sort by activation strength
            sorted_indices = active_values.argsort(descending=True)
            active_features[layer] = [
                (int(active_indices[i]), float(active_values[i]))
                for i in sorted_indices
            ]

        logger.info("Active features identified", extra={
            "total_features": sum(len(v) for v in active_features.values())
        })

        return active_features

    def measure_feature_importance(
        self,
        clean_input: str,
        corrupted_input: str,
        layer: int,
        feature_idx: int
    ) -> float:
        """
        Measure importance of a specific SAE feature for a task.

        Uses ablation: zero out the feature and measure impact.

        Args:
            clean_input: Clean input text
            corrupted_input: Corrupted input text
            layer: Layer index
            feature_idx: Feature index in SAE

        Returns:
            Importance score (0-1)
        """
        if layer not in self.sae_dict:
            return 0.0

        sae = self.sae_dict[layer]

        # Get clean activations
        clean_result = self.tracer.trace(clean_input)
        corrupted_result = self.tracer.trace(corrupted_input)

        cache_key = f"layer_{layer}_resid"
        if cache_key not in clean_result.cache:
            return 0.0

        clean_act = clean_result.cache[cache_key]  # [seq_len, d_model]
        corrupted_act = corrupted_result.cache[cache_key]

        # Encode with SAE
        with torch.no_grad():
            clean_features = sae.encode(clean_act)  # [seq_len, d_sae]
            corrupted_features = sae.encode(corrupted_act)

            # Ablate the specific feature (set to zero)
            ablated_features = clean_features.clone()
            ablated_features[:, feature_idx] = 0

            # Decode back to activations
            clean_reconstructed = sae.decode(clean_features)
            ablated_reconstructed = sae.decode(ablated_features)

            # Measure impact of ablation
            feature_contribution = (clean_reconstructed - ablated_reconstructed).norm()
            total_norm = clean_reconstructed.norm()

            importance = (feature_contribution / (total_norm + 1e-8)).item()

        return min(importance, 1.0)

    def discover_feature_circuit(
        self,
        clean_input: str,
        corrupted_input: str,
        task_description: str,
        max_features_per_layer: int = 10
    ) -> Dict[str, Any]:
        """
        Discover circuit based on SAE features.

        Args:
            clean_input: Clean input text
            corrupted_input: Corrupted input text
            task_description: Description of task
            max_features_per_layer: Max features to include per layer

        Returns:
            Dictionary with feature circuit information
        """
        logger.info("Discovering feature circuit", extra={
            "task": task_description,
            "max_features_per_layer": max_features_per_layer
        })

        # Step 1: Identify active features in clean run
        clean_features = self.identify_active_features(clean_input)

        # Step 2: Measure importance of each feature
        important_features = {}

        for layer in sorted(clean_features.keys()):
            layer_important = []

            # Check top features for this layer
            for feat_idx, activation in clean_features[layer][:max_features_per_layer]:
                importance = self.measure_feature_importance(
                    clean_input,
                    corrupted_input,
                    layer,
                    feat_idx
                )

                if importance > self.threshold:
                    layer_important.append({
                        "feature_idx": feat_idx,
                        "importance": importance,
                        "activation": activation
                    })

            if layer_important:
                # Sort by importance
                layer_important.sort(key=lambda x: x["importance"], reverse=True)
                important_features[layer] = layer_important

        # Step 3: Build feature circuit
        circuit_nodes = []
        total_importance = 0

        for layer, features in important_features.items():
            for feat_info in features:
                node = FeatureCircuitNode(
                    layer=layer,
                    feature_idx=feat_info["feature_idx"],
                    importance=feat_info["importance"],
                    activation_pattern=f"Activates: {feat_info['activation']:.3f}"
                )
                circuit_nodes.append(node)
                total_importance += feat_info["importance"]

        # Compute statistics
        num_total_features = sum(
            self.sae_dict[layer].config.d_sae
            for layer in self.sae_dict.keys()
        )

        feature_circuit = {
            "task": task_description,
            "num_features": len(circuit_nodes),
            "num_layers": len(important_features),
            "total_importance": total_importance,
            "compression_ratio": len(circuit_nodes) / num_total_features,
            "features_by_layer": {
                layer: [
                    {
                        "feature_idx": node.feature_idx,
                        "importance": node.importance,
                        "activation_pattern": node.activation_pattern
                    }
                    for node in circuit_nodes if node.layer == layer
                ]
                for layer in sorted(important_features.keys())
            }
        }

        logger.info("Feature circuit discovered", extra={
            "num_features": len(circuit_nodes),
            "num_layers": len(important_features),
            "compression": f"{feature_circuit['compression_ratio']:.2%}"
        })

        return feature_circuit

    def explain_feature_circuit(
        self,
        feature_circuit: Dict[str, Any],
        feature_descriptions: Optional[Dict[Tuple[int, int], str]] = None
    ) -> str:
        """
        Generate human-readable explanation of feature circuit.

        Args:
            feature_circuit: Feature circuit from discover_feature_circuit()
            feature_descriptions: Optional mapping of (layer, feature_idx) -> description

        Returns:
            Formatted explanation string
        """
        explanation = []
        explanation.append("=" * 60)
        explanation.append(f"Feature Circuit: {feature_circuit['task']}")
        explanation.append("=" * 60)
        explanation.append(f"Features: {feature_circuit['num_features']}")
        explanation.append(f"Layers: {feature_circuit['num_layers']}")
        explanation.append(f"Compression: {feature_circuit['compression_ratio']:.2%}")
        explanation.append("")

        explanation.append("Critical Features by Layer:")
        explanation.append("")

        for layer in sorted(feature_circuit["features_by_layer"].keys()):
            features = feature_circuit["features_by_layer"][layer]
            explanation.append(f"Layer {layer}:")

            for feat in features[:5]:  # Top 5 per layer
                feat_idx = feat["feature_idx"]
                importance = feat["importance"]

                # Get description if available
                desc = ""
                if feature_descriptions and (layer, feat_idx) in feature_descriptions:
                    desc = f" - {feature_descriptions[(layer, feat_idx)]}"

                explanation.append(
                    f"  Feature {feat_idx}: importance={importance:.3f}{desc}"
                )

            explanation.append("")

        explanation.append("=" * 60)

        return "\n".join(explanation)

    def visualize_feature_flow(
        self,
        feature_circuit: Dict[str, Any]
    ) -> str:
        """
        Create ASCII visualization of feature flow through layers.

        Args:
            feature_circuit: Feature circuit to visualize

        Returns:
            ASCII art representation
        """
        viz = []
        viz.append("\nFeature Flow Diagram:")
        viz.append("")

        for layer in sorted(feature_circuit["features_by_layer"].keys()):
            features = feature_circuit["features_by_layer"][layer]
            num_features = len(features)

            # Layer header
            viz.append(f"Layer {layer} ({num_features} features)")

            # Feature bars (importance visualization)
            for feat in features[:5]:
                importance = feat["importance"]
                bar_length = int(importance * 40)
                bar = "█" * bar_length
                viz.append(f"  F{feat['feature_idx']:4d} |{bar:40s}| {importance:.3f}")

            if layer < max(feature_circuit["features_by_layer"].keys()):
                viz.append("     ↓")
                viz.append("")

        return "\n".join(viz)


# Example usage
if __name__ == "__main__":
    print("🔬 GlassBox SAE-Circuit Integration Example\n")
    print("=" * 60)

    print("\n1. Initializing...")
    print("   This example shows how SAE features integrate with circuits")
    print("   In practice, you would:")
    print("   - Train SAEs on multiple layers")
    print("   - Discover feature circuits for tasks")
    print("   - Analyze which features implement behaviors")

    print("\n2. Typical workflow:")
    print("   # Train SAEs for each layer")
    print("   sae_dict = {")
    print("       6: trained_sae_layer_6,")
    print("       8: trained_sae_layer_8,")
    print("       10: trained_sae_layer_10")
    print("   }")
    print("")
    print("   # Initialize discovery")
    print("   discovery = SAECircuitDiscovery(tracer, sae_dict)")
    print("")
    print("   # Discover feature circuit")
    print("   circuit = discovery.discover_feature_circuit(")
    print("       clean_input='The Eiffel Tower is in Paris',")
    print("       corrupted_input='The Eiffel Tower is in London',")
    print("       task_description='Geographic fact recall'")
    print("   )")
    print("")
    print("   # Explain circuit")
    print("   explanation = discovery.explain_feature_circuit(circuit)")
    print("   print(explanation)")

    print("\n3. Benefits of feature-level circuits:")
    print("   ✓ More interpretable than raw activation circuits")
    print("   ✓ Each feature is monosemantic (single concept)")
    print("   ✓ Easier to understand why model behaves certain way")
    print("   ✓ Can manually inspect feature activations")

    print("\n" + "=" * 60)
    print("✅ SAE-Circuit integration example complete!\n")
    print("Next: Add visualizations to dashboard")
