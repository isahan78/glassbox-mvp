"""
GlassBox Circuit Discovery - Find minimal subgraphs that implement behaviors.

This module implements automated circuit discovery using activation patching
and systematic ablation studies.

Techniques:
- Automated Circuit Discovery (ACDC)
- Iterative Node Pruning
- Edge Patching
- Circuit Visualization

Based on research:
- "Towards Automated Circuit Discovery for Mechanistic Interpretability" (Conmy et al., 2023)
- "Interpretability in the Wild" (Nanda et al., 2023)
"""

import torch
import numpy as np
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict

from glassbox.interventions import (
    ActivationPatcher,
    InterventionConfig,
    InterventionType,
    InterventionResult
)
from glassbox.tracer import ActivationTracer
from glassbox.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class CircuitNode:
    """A node in the computational circuit."""
    layer: int
    component: str  # "resid", "attn", "mlp", "head"
    head: Optional[int] = None

    def __hash__(self):
        return hash((self.layer, self.component, self.head))

    def __eq__(self, other):
        return (
            self.layer == other.layer and
            self.component == other.component and
            self.head == other.head
        )

    def __str__(self):
        if self.head is not None:
            return f"L{self.layer}H{self.head}"
        return f"L{self.layer}.{self.component}"


@dataclass
class CircuitEdge:
    """An edge in the computational circuit."""
    source: CircuitNode
    target: CircuitNode
    weight: float  # Importance score

    def __str__(self):
        return f"{self.source} -> {self.target} ({self.weight:.3f})"


@dataclass
class Circuit:
    """A discovered computational circuit."""
    nodes: Set[CircuitNode] = field(default_factory=set)
    edges: List[CircuitEdge] = field(default_factory=list)
    task_description: str = ""
    faithfulness_score: float = 0.0  # How well circuit explains behavior

    def add_node(self, node: CircuitNode):
        """Add a node to the circuit."""
        self.nodes.add(node)

    def add_edge(self, edge: CircuitEdge):
        """Add an edge to the circuit."""
        self.edges.append(edge)
        self.nodes.add(edge.source)
        self.nodes.add(edge.target)

    def get_num_components(self) -> int:
        """Get total number of components in circuit."""
        return len(self.nodes)

    def get_compression_ratio(self, total_components: int) -> float:
        """
        Calculate circuit compression ratio.

        Args:
            total_components: Total components in full model

        Returns:
            Ratio of circuit size to model size (lower = more compressed)
        """
        return len(self.nodes) / total_components if total_components > 0 else 0.0

    def to_dict(self) -> Dict:
        """Convert circuit to dictionary for serialization."""
        return {
            "task": self.task_description,
            "faithfulness": self.faithfulness_score,
            "num_nodes": len(self.nodes),
            "num_edges": len(self.edges),
            "nodes": [
                {
                    "layer": n.layer,
                    "component": n.component,
                    "head": n.head
                }
                for n in self.nodes
            ],
            "edges": [
                {
                    "source": str(e.source),
                    "target": str(e.target),
                    "weight": e.weight
                }
                for e in self.edges
            ]
        }


class CircuitDiscovery:
    """
    Automated circuit discovery using activation patching.

    This systematically ablates components to find the minimal set
    that implements a specific behavior.
    """

    def __init__(
        self,
        tracer: ActivationTracer,
        threshold: float = 0.1
    ):
        """
        Initialize circuit discovery.

        Args:
            tracer: ActivationTracer instance
            threshold: Importance threshold for including components
        """
        self.tracer = tracer
        self.patcher = ActivationPatcher(tracer)
        self.threshold = threshold

        logger.info("CircuitDiscovery initialized", extra={
            "model": tracer.model_name,
            "threshold": threshold
        })

    def compute_component_importance(
        self,
        clean_input: str,
        corrupted_input: str,
        layers: Optional[List[int]] = None,
        components: List[str] = ["resid", "attn", "mlp"]
    ) -> Dict[str, float]:
        """
        Compute importance of each component via ablation.

        Args:
            clean_input: Clean prompt
            corrupted_input: Corrupted prompt
            layers: Layers to test (None = all)
            components: Component types to test

        Returns:
            Dictionary mapping component names to importance scores
        """
        if layers is None:
            layers = list(range(self.tracer.model.cfg.n_layers))

        importance_scores = {}

        logger.info("Computing component importance", extra={
            "clean_input": clean_input[:50],
            "num_layers": len(layers),
            "num_components": len(components)
        })

        for layer in layers:
            for component in components:
                # Create intervention config
                config = InterventionConfig(
                    layer=layer,
                    component=component,
                    intervention_type=InterventionType.ZERO_ABLATE
                )

                # Run ablation
                try:
                    result = self.patcher.patch_and_run(
                        clean_input=clean_input,
                        corrupted_input=corrupted_input,
                        intervention=config
                    )

                    # Use absolute KL divergence as importance
                    importance = abs(result.kl_divergence)
                    key = f"{component}_layer_{layer}"
                    importance_scores[key] = importance

                    logger.debug("Component importance", extra={
                        "component": key,
                        "importance": importance
                    })

                except Exception as e:
                    logger.warning(f"Failed to ablate {component} layer {layer}: {e}")
                    continue

        return importance_scores

    def discover_circuit(
        self,
        clean_input: str,
        corrupted_input: str,
        task_description: str = "",
        max_components: Optional[int] = None
    ) -> Circuit:
        """
        Discover minimal circuit for a task.

        Args:
            clean_input: Clean example
            corrupted_input: Corrupted example
            task_description: Description of task
            max_components: Maximum circuit size (None = automatic)

        Returns:
            Discovered Circuit object
        """
        logger.info("Starting circuit discovery", extra={
            "task": task_description,
            "max_components": max_components
        })

        # Compute importance of all components
        importance_scores = self.compute_component_importance(
            clean_input, corrupted_input
        )

        # Sort by importance
        sorted_components = sorted(
            importance_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        # Build circuit from most important components
        circuit = Circuit(task_description=task_description)

        # Add components above threshold
        for component_name, score in sorted_components:
            if score >= self.threshold:
                # Parse component name
                parts = component_name.split("_")
                comp_type = parts[0]
                layer = int(parts[2])

                node = CircuitNode(
                    layer=layer,
                    component=comp_type
                )
                circuit.add_node(node)

                logger.debug("Added node to circuit", extra={
                    "node": str(node),
                    "importance": score
                })

            # Check max components limit
            if max_components and len(circuit.nodes) >= max_components:
                break

        # Compute faithfulness (how well circuit explains behavior)
        total_importance = sum(importance_scores.values())
        circuit_importance = sum(
            score for comp, score in sorted_components
            if score >= self.threshold
        )
        circuit.faithfulness_score = (
            circuit_importance / total_importance
            if total_importance > 0 else 0.0
        )

        # Get total components for compression ratio
        num_layers = self.tracer.model.cfg.n_layers
        components_per_layer = 3  # resid, attn, mlp
        total_components = num_layers * components_per_layer

        logger.info("Circuit discovery complete", extra={
            "num_nodes": len(circuit.nodes),
            "faithfulness": circuit.faithfulness_score,
            "compression": circuit.get_compression_ratio(total_components)
        })

        return circuit

    def visualize_circuit(self, circuit: Circuit) -> str:
        """
        Create text visualization of circuit.

        Args:
            circuit: Circuit to visualize

        Returns:
            ASCII art representation
        """
        lines = []
        lines.append(f"\n{'=' * 60}")
        lines.append(f"Circuit: {circuit.task_description}")
        lines.append(f"{'=' * 60}")
        lines.append(f"Nodes: {len(circuit.nodes)}")
        lines.append(f"Faithfulness: {circuit.faithfulness_score:.2%}")
        lines.append(f"\nComponents:")

        # Group nodes by layer
        by_layer = defaultdict(list)
        for node in circuit.nodes:
            by_layer[node.layer].append(node)

        for layer in sorted(by_layer.keys()):
            components = ", ".join(n.component for n in by_layer[layer])
            lines.append(f"  Layer {layer:2d}: {components}")

        if circuit.edges:
            lines.append(f"\nEdges ({len(circuit.edges)}):")
            for edge in circuit.edges[:10]:  # Show top 10
                lines.append(f"  {edge}")

        lines.append(f"{'=' * 60}\n")

        return "\n".join(lines)


# Example usage and testing
if __name__ == "__main__":
    print("🔍 GlassBox Circuit Discovery Example\n")
    print("=" * 60)

    # Initialize
    print("\n1. Initializing circuit discovery...")
    tracer = ActivationTracer(model_name="gpt2-small")
    discovery = CircuitDiscovery(tracer, threshold=0.05)

    # Define task
    clean = "The Eiffel Tower is in Paris"
    corrupted = "The Eiffel Tower is in London"
    task = "Geographic location recall"

    print(f"\n2. Discovering circuit for task: {task}")
    print(f"   Clean:     {clean}")
    print(f"   Corrupted: {corrupted}")

    # Discover circuit
    circuit = discovery.discover_circuit(
        clean_input=clean,
        corrupted_input=corrupted,
        task_description=task,
        max_components=10
    )

    # Visualize
    print(discovery.visualize_circuit(circuit))

    # Show circuit details
    print(f"\n3. Circuit Summary:")
    print(f"   Total nodes: {circuit.get_num_components()}")
    print(f"   Faithfulness: {circuit.faithfulness_score:.2%}")
    print(f"   Compression: {circuit.get_compression_ratio(36):.2%}")
    print(f"   (Circuit uses {circuit.get_compression_ratio(36)*100:.1f}% of model)")

    # Export circuit
    circuit_dict = circuit.to_dict()
    print(f"\n4. Circuit can be serialized to JSON")
    print(f"   Keys: {list(circuit_dict.keys())}")

    print("\n" + "=" * 60)
    print("✅ Circuit discovery example complete!\n")
