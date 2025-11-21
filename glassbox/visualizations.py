"""
GlassBox Enhanced Visualizations - Interactive visualizations for circuits, features, and attention.

This module provides advanced interactive visualizations using Plotly for:
- Interactive circuit graphs
- Animated causal flow
- SAE feature heatmaps
- 3D activation projections
- Enhanced attention visualizations
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np
from typing import List, Dict, Optional, Any, Tuple
import networkx as nx
from dataclasses import dataclass

from glassbox.circuits import Circuit, CircuitNode
from glassbox.logging_config import get_logger

logger = get_logger(__name__)


class CircuitVisualizer:
    """Create interactive circuit graph visualizations."""

    def __init__(self):
        """Initialize circuit visualizer."""
        logger.info("CircuitVisualizer initialized")

    def create_interactive_graph(
        self,
        circuit: Circuit,
        title: Optional[str] = None
    ) -> go.Figure:
        """
        Create interactive circuit graph using Plotly.

        Args:
            circuit: Circuit to visualize
            title: Optional title for the graph

        Returns:
            Plotly figure with interactive graph
        """
        # Create NetworkX graph
        G = nx.DiGraph()

        # Add nodes
        node_labels = {}
        node_colors = []
        node_sizes = []

        for node in circuit.nodes:
            node_id = f"L{node.layer}_{node.component}"
            G.add_node(node_id, layer=node.layer, component=node.component)
            node_labels[node_id] = f"Layer {node.layer}\n{node.component}"

            # Color by importance
            importance = node.importance if hasattr(node, 'importance') else 0.5
            node_colors.append(importance)
            node_sizes.append(20 + importance * 30)

        # Add edges
        for edge in circuit.edges:
            source_id = f"L{edge.source_layer}_{edge.source_component}"
            target_id = f"L{edge.target_layer}_{edge.target_component}"
            if source_id in G and target_id in G:
                G.add_edge(source_id, target_id, weight=edge.weight)

        # Use hierarchical layout (by layer)
        pos = {}
        layers = {}
        for node_id, data in G.nodes(data=True):
            layer = data['layer']
            if layer not in layers:
                layers[layer] = []
            layers[layer].append(node_id)

        for layer, nodes in layers.items():
            for i, node_id in enumerate(nodes):
                x = i - len(nodes) / 2
                y = -layer  # Negative so layer 0 is at top
                pos[node_id] = (x, y)

        # Create edge traces
        edge_trace = []
        for edge in G.edges(data=True):
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]

            edge_trace.append(
                go.Scatter(
                    x=[x0, x1, None],
                    y=[y0, y1, None],
                    mode='lines',
                    line=dict(width=1, color='rgba(125, 125, 125, 0.5)'),
                    hoverinfo='none',
                    showlegend=False
                )
            )

        # Create node trace
        node_x = []
        node_y = []
        node_text = []
        node_importance = []

        for node_id in G.nodes():
            x, y = pos[node_id]
            node_x.append(x)
            node_y.append(y)
            node_text.append(node_labels[node_id])

            # Find importance
            importance = 0.5
            for circuit_node in circuit.nodes:
                if f"L{circuit_node.layer}_{circuit_node.component}" == node_id:
                    importance = circuit_node.importance if hasattr(circuit_node, 'importance') else 0.5
                    break
            node_importance.append(importance)

        node_trace = go.Scatter(
            x=node_x,
            y=node_y,
            mode='markers+text',
            text=node_text,
            textposition="top center",
            marker=dict(
                size=[20 + imp * 30 for imp in node_importance],
                color=node_importance,
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(
                    title="Importance",
                    thickness=15,
                    len=0.5
                ),
                line=dict(width=2, color='white')
            ),
            hovertemplate='<b>%{text}</b><br>Importance: %{marker.color:.3f}<extra></extra>',
            showlegend=False
        )

        # Create figure
        fig = go.Figure(data=edge_trace + [node_trace])

        fig.update_layout(
            title=title or f"Circuit: {circuit.task}",
            showlegend=False,
            hovermode='closest',
            margin=dict(b=20, l=5, r=5, t=40),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            plot_bgcolor='rgba(0,0,0,0)',
            height=600
        )

        logger.info("Created interactive circuit graph", extra={
            "num_nodes": len(circuit.nodes),
            "num_edges": len(circuit.edges)
        })

        return fig


class CausalFlowVisualizer:
    """Create animated causal flow visualizations."""

    def __init__(self):
        """Initialize causal flow visualizer."""
        logger.info("CausalFlowVisualizer initialized")

    def create_causal_heatmap(
        self,
        causal_results: Dict[str, Any],
        metric: str = "logit_diff"
    ) -> go.Figure:
        """
        Create heatmap of causal effects across layers.

        Args:
            causal_results: Results from causal tracing
            metric: Which metric to visualize

        Returns:
            Plotly heatmap figure
        """
        # Parse results into matrix
        layers = set()
        components = set()

        for layer_name in causal_results.keys():
            # Parse layer_name like "resid_layer_8"
            parts = layer_name.split('_')
            if len(parts) >= 3:
                component = parts[0]
                layer = int(parts[-1])
                layers.add(layer)
                components.add(component)

        layers = sorted(list(layers))
        components = sorted(list(components))

        # Create matrix
        matrix = np.zeros((len(components), len(layers)))

        for i, component in enumerate(components):
            for j, layer in enumerate(layers):
                key = f"{component}_layer_{layer}"
                if key in causal_results:
                    result = causal_results[key]
                    if hasattr(result, metric):
                        matrix[i, j] = getattr(result, metric)

        # Create heatmap
        fig = go.Figure(data=go.Heatmap(
            z=matrix,
            x=layers,
            y=components,
            colorscale='RdBu',
            zmid=0,
            text=np.round(matrix, 3),
            texttemplate='%{text}',
            textfont={"size": 10},
            colorbar=dict(title=metric.replace('_', ' ').title())
        ))

        fig.update_layout(
            title=f"Causal Effects: {metric.replace('_', ' ').title()}",
            xaxis_title="Layer",
            yaxis_title="Component",
            height=400
        )

        logger.info("Created causal heatmap", extra={
            "num_layers": len(layers),
            "num_components": len(components),
            "metric": metric
        })

        return fig

    def create_layer_importance_chart(
        self,
        causal_results: Dict[str, Any]
    ) -> go.Figure:
        """
        Create bar chart of layer importance.

        Args:
            causal_results: Results from causal tracing

        Returns:
            Plotly bar chart
        """
        # Aggregate by layer
        layer_effects = {}

        for layer_name, result in causal_results.items():
            parts = layer_name.split('_')
            if len(parts) >= 3:
                layer = int(parts[-1])
                effect = abs(result.logit_diff) if hasattr(result, 'logit_diff') else 0

                if layer not in layer_effects:
                    layer_effects[layer] = []
                layer_effects[layer].append(effect)

        # Average effects per layer
        layers = sorted(layer_effects.keys())
        avg_effects = [np.mean(layer_effects[layer]) for layer in layers]

        fig = go.Figure(data=[
            go.Bar(
                x=layers,
                y=avg_effects,
                marker_color=avg_effects,
                marker_colorscale='Viridis',
                text=[f"{e:.3f}" for e in avg_effects],
                textposition='auto'
            )
        ])

        fig.update_layout(
            title="Layer Importance (Average Causal Effect)",
            xaxis_title="Layer",
            yaxis_title="Average |Logit Diff|",
            height=400,
            showlegend=False
        )

        return fig


class SAEFeatureVisualizer:
    """Visualize SAE features and activations."""

    def __init__(self):
        """Initialize SAE feature visualizer."""
        logger.info("SAEFeatureVisualizer initialized")

    def create_feature_activation_heatmap(
        self,
        activations: np.ndarray,
        tokens: List[str],
        top_k: int = 20
    ) -> go.Figure:
        """
        Create heatmap of feature activations across tokens.

        Args:
            activations: Feature activations [seq_len, d_sae]
            tokens: List of tokens
            top_k: Number of top features to show

        Returns:
            Plotly heatmap figure
        """
        # Find top-k most active features
        feature_maxes = activations.max(axis=0)
        top_features = np.argsort(feature_maxes)[-top_k:][::-1]

        # Extract activations for top features
        top_activations = activations[:, top_features].T  # [top_k, seq_len]

        fig = go.Figure(data=go.Heatmap(
            z=top_activations,
            x=tokens,
            y=[f"Feature {i}" for i in top_features],
            colorscale='Viridis',
            colorbar=dict(title="Activation")
        ))

        fig.update_layout(
            title=f"Top {top_k} Feature Activations",
            xaxis_title="Token",
            yaxis_title="Feature",
            height=500
        )

        logger.info("Created feature activation heatmap", extra={
            "num_features": top_k,
            "num_tokens": len(tokens)
        })

        return fig

    def create_feature_distribution(
        self,
        activations: np.ndarray,
        feature_idx: int
    ) -> go.Figure:
        """
        Create distribution plot for a specific feature.

        Args:
            activations: Feature activations [seq_len, d_sae]
            feature_idx: Index of feature to visualize

        Returns:
            Plotly histogram figure
        """
        feature_acts = activations[:, feature_idx]

        # Remove zeros for better visualization
        nonzero_acts = feature_acts[feature_acts > 0]

        fig = go.Figure()

        # All activations
        fig.add_trace(go.Histogram(
            x=feature_acts,
            name='All Activations',
            opacity=0.6,
            nbinsx=50
        ))

        # Non-zero only
        if len(nonzero_acts) > 0:
            fig.add_trace(go.Histogram(
                x=nonzero_acts,
                name='Non-zero Only',
                opacity=0.6,
                nbinsx=50
            ))

        fig.update_layout(
            title=f"Feature {feature_idx} Activation Distribution",
            xaxis_title="Activation Strength",
            yaxis_title="Count",
            barmode='overlay',
            height=400
        )

        return fig


class ActivationSpaceVisualizer:
    """Create 3D visualizations of activation spaces."""

    def __init__(self):
        """Initialize activation space visualizer."""
        logger.info("ActivationSpaceVisualizer initialized")

    def create_3d_projection(
        self,
        activations: np.ndarray,
        labels: Optional[List[str]] = None,
        method: str = "pca"
    ) -> go.Figure:
        """
        Create 3D projection of activation space.

        Args:
            activations: Activations to visualize [n_samples, d_model]
            labels: Optional labels for each point
            method: Dimensionality reduction method ("pca" or "tsne")

        Returns:
            Plotly 3D scatter plot
        """
        from sklearn.decomposition import PCA

        # Reduce to 3D
        if method == "pca":
            reducer = PCA(n_components=3)
            reduced = reducer.fit_transform(activations)
            explained_var = reducer.explained_variance_ratio_
            title_suffix = f" (PCA: {sum(explained_var):.1%} variance explained)"
        else:
            # Could add t-SNE here
            reducer = PCA(n_components=3)
            reduced = reducer.fit_transform(activations)
            title_suffix = ""

        # Create 3D scatter
        if labels is None:
            labels = [f"Point {i}" for i in range(len(activations))]

        fig = go.Figure(data=[go.Scatter3d(
            x=reduced[:, 0],
            y=reduced[:, 1],
            z=reduced[:, 2],
            mode='markers',
            marker=dict(
                size=5,
                color=np.arange(len(activations)),
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(title="Sample Index")
            ),
            text=labels,
            hovertemplate='<b>%{text}</b><br>X: %{x:.3f}<br>Y: %{y:.3f}<br>Z: %{z:.3f}<extra></extra>'
        )])

        fig.update_layout(
            title=f"3D Activation Space Projection{title_suffix}",
            scene=dict(
                xaxis_title="PC1" if method == "pca" else "Dim1",
                yaxis_title="PC2" if method == "pca" else "Dim2",
                zaxis_title="PC3" if method == "pca" else "Dim3"
            ),
            height=600
        )

        logger.info("Created 3D activation projection", extra={
            "num_samples": len(activations),
            "method": method
        })

        return fig


class AttentionVisualizer:
    """Enhanced attention visualizations."""

    def __init__(self):
        """Initialize attention visualizer."""
        logger.info("AttentionVisualizer initialized")

    def create_attention_heatmap(
        self,
        attention_weights: np.ndarray,
        tokens: List[str],
        layer: int,
        head: int
    ) -> go.Figure:
        """
        Create enhanced attention heatmap.

        Args:
            attention_weights: Attention weights [seq_len, seq_len]
            tokens: List of tokens
            layer: Layer index
            head: Head index

        Returns:
            Plotly heatmap figure
        """
        fig = go.Figure(data=go.Heatmap(
            z=attention_weights,
            x=tokens,
            y=tokens,
            colorscale='Blues',
            colorbar=dict(title="Attention"),
            text=np.round(attention_weights, 3),
            texttemplate='%{text}',
            textfont={"size": 8}
        ))

        fig.update_layout(
            title=f"Attention Pattern - Layer {layer}, Head {head}",
            xaxis_title="Key (Attending To)",
            yaxis_title="Query (Attending From)",
            height=500,
            xaxis={'side': 'bottom'},
            yaxis={'side': 'left'}
        )

        logger.info("Created attention heatmap", extra={
            "layer": layer,
            "head": head,
            "seq_len": len(tokens)
        })

        return fig

    def create_multi_head_comparison(
        self,
        attention_weights: List[np.ndarray],
        tokens: List[str],
        layer: int,
        num_heads: int = 4
    ) -> go.Figure:
        """
        Create subplot comparing multiple attention heads.

        Args:
            attention_weights: List of attention matrices, one per head
            tokens: List of tokens
            layer: Layer index
            num_heads: Number of heads to show

        Returns:
            Plotly figure with subplots
        """
        num_heads = min(num_heads, len(attention_weights))

        fig = make_subplots(
            rows=2,
            cols=2,
            subplot_titles=[f"Head {i}" for i in range(num_heads)],
            vertical_spacing=0.1,
            horizontal_spacing=0.1
        )

        for i in range(num_heads):
            row = i // 2 + 1
            col = i % 2 + 1

            fig.add_trace(
                go.Heatmap(
                    z=attention_weights[i],
                    x=tokens,
                    y=tokens,
                    colorscale='Blues',
                    showscale=(i == num_heads - 1),
                    colorbar=dict(title="Attention", x=1.1) if i == num_heads - 1 else None
                ),
                row=row,
                col=col
            )

        fig.update_layout(
            title=f"Attention Heads Comparison - Layer {layer}",
            height=700
        )

        return fig


# Example usage
if __name__ == "__main__":
    print("🎨 GlassBox Enhanced Visualizations\n")
    print("=" * 60)

    print("\n1. Available Visualizers:")
    print("   - CircuitVisualizer: Interactive circuit graphs")
    print("   - CausalFlowVisualizer: Causal flow heatmaps and animations")
    print("   - SAEFeatureVisualizer: Feature activation heatmaps")
    print("   - ActivationSpaceVisualizer: 3D activation projections")
    print("   - AttentionVisualizer: Enhanced attention heatmaps")

    print("\n2. Usage Example:")
    print("   circuit_viz = CircuitVisualizer()")
    print("   fig = circuit_viz.create_interactive_graph(circuit)")
    print("   fig.show()  # In Jupyter")
    print("   # Or in Streamlit: st.plotly_chart(fig)")

    print("\n3. Integration:")
    print("   All visualizations return Plotly figures")
    print("   Can be displayed in:")
    print("   - Streamlit (st.plotly_chart)")
    print("   - Jupyter (fig.show)")
    print("   - Saved as HTML (fig.write_html)")

    print("\n" + "=" * 60)
    print("✅ Visualizations module ready!\n")
