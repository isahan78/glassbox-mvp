"""
GlassBox Sparse Autoencoders (SAE) - Monosemantic Feature Discovery.

Sparse Autoencoders learn to decompose model activations into interpretable,
monosemantic features. Each SAE feature ideally represents a single concept
that the model uses.

Based on research:
- "Towards Monosemanticity" (Anthropic, 2023)
- "Sparse Autoencoders Find Highly Interpretable Features" (Cunningham et al., 2023)
- "Scaling Monosemanticity" (Anthropic, 2024)

Key concepts:
- L1 sparsity penalty encourages each feature to activate rarely
- Tied encoder/decoder weights for efficiency
- Dead neuron handling via resampling
- Feature activation dashboards
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import numpy as np
from pathlib import Path
import json

from glassbox.tracer import ActivationTracer, TraceResult
from glassbox.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class SAEConfig:
    """Configuration for Sparse Autoencoder."""

    # Architecture
    d_model: int                          # Input dimension (e.g., 768 for GPT-2 small)
    d_sae: int                            # SAE hidden dimension (typically 4-16x d_model)

    # Training
    l1_coefficient: float = 0.001         # L1 sparsity penalty strength
    learning_rate: float = 1e-4           # Adam learning rate
    batch_size: int = 256                 # Training batch size

    # Dead neuron handling
    dead_neuron_threshold: float = 1e-6   # Feature considered dead if avg activation below this
    resample_frequency: int = 25000       # Resample dead neurons every N steps

    # Architecture options
    tied_weights: bool = True             # Tie encoder and decoder weights (W_dec = W_enc^T)
    normalize_decoder: bool = True        # Normalize decoder weights to unit norm

    # Logging
    log_frequency: int = 100              # Log stats every N steps


class SparseAutoencoder(nn.Module):
    """
    Sparse Autoencoder for discovering monosemantic features.

    Architecture:
        x → ReLU(W_enc · x + b_enc) → sparse_features
        sparse_features → W_dec · sparse_features + b_dec → x_reconstructed

    Loss = ||x - x_reconstructed||^2 + l1_coefficient * ||sparse_features||_1
    """

    def __init__(self, config: SAEConfig):
        """
        Initialize SAE.

        Args:
            config: SAE configuration
        """
        super().__init__()
        self.config = config

        # Encoder: d_model → d_sae
        self.W_enc = nn.Parameter(
            torch.randn(config.d_sae, config.d_model) * 0.01
        )
        self.b_enc = nn.Parameter(torch.zeros(config.d_sae))

        # Decoder: d_sae → d_model
        if config.tied_weights:
            # W_dec is transpose of W_enc
            self.W_dec = None  # Computed dynamically
        else:
            self.W_dec = nn.Parameter(
                torch.randn(config.d_model, config.d_sae) * 0.01
            )

        self.b_dec = nn.Parameter(torch.zeros(config.d_model))

        # Track feature statistics for dead neuron detection
        self.register_buffer(
            "feature_activation_counts",
            torch.zeros(config.d_sae)
        )
        self.register_buffer(
            "total_activations",
            torch.tensor(0)
        )

        logger.info("SAE initialized", extra={
            "d_model": config.d_model,
            "d_sae": config.d_sae,
            "expansion_factor": config.d_sae / config.d_model,
            "tied_weights": config.tied_weights
        })

    def get_W_dec(self) -> torch.Tensor:
        """Get decoder weights (handles tied weights case)."""
        if self.config.tied_weights:
            W_dec = self.W_enc.T
        else:
            W_dec = self.W_dec

        # Normalize decoder weights if requested
        if self.config.normalize_decoder:
            W_dec = F.normalize(W_dec, dim=0)

        return W_dec

    def encode(self, x: torch.Tensor) -> torch.Tensor:
        """
        Encode input to sparse features.

        Args:
            x: Input activations [batch, d_model]

        Returns:
            Sparse feature activations [batch, d_sae]
        """
        # Linear projection + ReLU for sparsity
        features = F.relu(x @ self.W_enc.T + self.b_enc)

        # Track feature usage (for dead neuron detection)
        with torch.no_grad():
            self.feature_activation_counts += (features > 0).sum(dim=0).float()
            self.total_activations += x.shape[0]

        return features

    def decode(self, features: torch.Tensor) -> torch.Tensor:
        """
        Decode sparse features back to input space.

        Args:
            features: Sparse feature activations [batch, d_sae]

        Returns:
            Reconstructed activations [batch, d_model]
        """
        W_dec = self.get_W_dec()
        return features @ W_dec.T + self.b_dec

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Forward pass: encode and decode.

        Args:
            x: Input activations [batch, d_model]

        Returns:
            Tuple of (reconstructed, features, W_dec)
        """
        features = self.encode(x)
        reconstructed = self.decode(features)
        W_dec = self.get_W_dec()

        return reconstructed, features, W_dec

    def get_loss(
        self,
        x: torch.Tensor,
        reconstructed: torch.Tensor,
        features: torch.Tensor
    ) -> Tuple[torch.Tensor, Dict[str, float]]:
        """
        Compute SAE loss with L1 sparsity penalty.

        Args:
            x: Original activations
            reconstructed: Reconstructed activations
            features: Sparse features

        Returns:
            Tuple of (total_loss, loss_dict)
        """
        # Reconstruction loss (MSE)
        mse_loss = F.mse_loss(reconstructed, x)

        # L1 sparsity penalty
        l1_loss = features.abs().mean()

        # Total loss
        total_loss = mse_loss + self.config.l1_coefficient * l1_loss

        # Compute metrics
        with torch.no_grad():
            # L0 norm (average number of active features)
            l0 = (features > 0).float().sum(dim=1).mean()

            # Explained variance
            var_explained = 1 - (
                (x - reconstructed).pow(2).sum() /
                x.pow(2).sum()
            )

        loss_dict = {
            "total_loss": total_loss.item(),
            "mse_loss": mse_loss.item(),
            "l1_loss": l1_loss.item(),
            "l0_norm": l0.item(),
            "var_explained": var_explained.item()
        }

        return total_loss, loss_dict

    def get_dead_neurons(self) -> torch.Tensor:
        """
        Find dead neurons (features that never activate).

        Returns:
            Boolean tensor of shape [d_sae] indicating dead neurons
        """
        if self.total_activations == 0:
            return torch.zeros(self.config.d_sae, dtype=torch.bool)

        avg_activation = self.feature_activation_counts / self.total_activations
        dead = avg_activation < self.config.dead_neuron_threshold

        return dead

    def reset_dead_neurons(self, inputs: torch.Tensor):
        """
        Reset dead neurons by resampling from input distribution.

        Args:
            inputs: Sample of input activations to resample from
        """
        dead = self.get_dead_neurons()
        num_dead = dead.sum().item()

        if num_dead == 0:
            return

        logger.info(f"Resampling {num_dead} dead neurons", extra={
            "num_dead": num_dead,
            "pct_dead": num_dead / self.config.d_sae
        })

        # Sample random inputs
        sample_indices = torch.randint(0, inputs.shape[0], (num_dead,))
        samples = inputs[sample_indices]

        # Reset encoder weights to point at these samples
        with torch.no_grad():
            self.W_enc.data[dead] = samples * 0.1
            self.b_enc.data[dead] = 0.0

            # Reset activation counts
            self.feature_activation_counts[dead] = 0


@dataclass
class SAEFeature:
    """A discovered monosemantic feature."""
    feature_idx: int
    activation_frequency: float
    activation_strength: float
    top_activating_examples: List[Dict[str, Any]]  # List of {text, activation, position}
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "feature_idx": self.feature_idx,
            "activation_frequency": self.activation_frequency,
            "activation_strength": self.activation_strength,
            "top_activating_examples": self.top_activating_examples,
            "description": self.description
        }


class SAETrainer:
    """Trainer for Sparse Autoencoders."""

    def __init__(
        self,
        sae: SparseAutoencoder,
        config: SAEConfig,
        device: str = "cpu"
    ):
        """
        Initialize SAE trainer.

        Args:
            sae: Sparse autoencoder to train
            config: Training configuration
            device: Device to train on
        """
        self.sae = sae.to(device)
        self.config = config
        self.device = device

        # Optimizer
        self.optimizer = torch.optim.Adam(
            self.sae.parameters(),
            lr=config.learning_rate
        )

        self.step = 0
        self.loss_history = []

        logger.info("SAE trainer initialized", extra={
            "learning_rate": config.learning_rate,
            "device": device
        })

    def train_step(
        self,
        activations: torch.Tensor
    ) -> Dict[str, float]:
        """
        Single training step.

        Args:
            activations: Batch of activations [batch, d_model]

        Returns:
            Dictionary of loss values
        """
        activations = activations.to(self.device)

        # Forward pass
        reconstructed, features, W_dec = self.sae(activations)

        # Compute loss
        loss, loss_dict = self.sae.get_loss(activations, reconstructed, features)

        # Backward pass
        self.optimizer.zero_grad()
        loss.backward()

        # Gradient clipping
        torch.nn.utils.clip_grad_norm_(self.sae.parameters(), 1.0)

        self.optimizer.step()

        # Dead neuron resampling
        if self.step % self.config.resample_frequency == 0 and self.step > 0:
            self.sae.reset_dead_neurons(activations)

        self.step += 1
        self.loss_history.append(loss_dict)

        # Logging
        if self.step % self.config.log_frequency == 0:
            logger.info("Training step", extra={
                "step": self.step,
                **loss_dict
            })

        return loss_dict

    def save(self, path: str):
        """Save SAE checkpoint."""
        checkpoint = {
            "sae_state_dict": self.sae.state_dict(),
            "config": self.config,
            "step": self.step,
            "loss_history": self.loss_history
        }
        torch.save(checkpoint, path)
        logger.info("SAE checkpoint saved", extra={"path": path})

    def load(self, path: str):
        """Load SAE checkpoint."""
        checkpoint = torch.load(path, map_location=self.device)
        self.sae.load_state_dict(checkpoint["sae_state_dict"])
        self.step = checkpoint["step"]
        self.loss_history = checkpoint.get("loss_history", [])
        logger.info("SAE checkpoint loaded", extra={"path": path, "step": self.step})


class FeatureAnalyzer:
    """Analyzer for discovering and interpreting SAE features."""

    def __init__(
        self,
        sae: SparseAutoencoder,
        tracer: 'ActivationTracer',
        device: str = "cpu"
    ):
        """
        Initialize feature analyzer.

        Args:
            sae: Trained sparse autoencoder
            tracer: Activation tracer for collecting data
            device: Device to run on
        """
        self.sae = sae.to(device)
        self.sae.eval()
        self.tracer = tracer
        self.device = device

        # Storage for feature activations
        self.feature_examples = {}  # feature_idx -> List[example_dict]

        logger.info("Feature analyzer initialized", extra={
            "d_sae": sae.config.d_sae,
            "device": device
        })

    def collect_activations(
        self,
        prompts: List[str],
        layer: int,
        max_examples_per_feature: int = 10
    ):
        """
        Collect feature activations across prompts.

        Args:
            prompts: List of input prompts
            layer: Which layer to analyze
            max_examples_per_feature: Max examples to store per feature
        """
        logger.info("Collecting feature activations", extra={
            "num_prompts": len(prompts),
            "layer": layer,
            "max_examples": max_examples_per_feature
        })

        for prompt_idx, prompt in enumerate(prompts):
            # Trace prompt
            result = self.tracer.trace(prompt)

            # Get activations for this layer
            cache_key = f"layer_{layer}_resid"
            if result.activation_cache is None or cache_key not in result.activation_cache:
                logger.warning(f"Layer {layer} not in activation_cache", extra={
                    "available_keys": list(result.activation_cache.keys()) if result.activation_cache else []
                })
                continue

            activations = result.activation_cache[cache_key]  # [seq_len, d_model]

            # Encode with SAE
            with torch.no_grad():
                activations = activations.to(self.device)
                features = self.sae.encode(activations)  # [seq_len, d_sae]

            # Track top activating features for each position
            for pos in range(features.shape[0]):
                pos_features = features[pos]  # [d_sae]

                # Find active features (> 0)
                active_mask = pos_features > 0
                active_indices = torch.where(active_mask)[0]
                active_values = pos_features[active_mask]

                # Store examples for each active feature
                for feat_idx, activation in zip(active_indices.detach().cpu().numpy(),
                                                 active_values.detach().cpu().numpy()):
                    feat_idx = int(feat_idx)

                    if feat_idx not in self.feature_examples:
                        self.feature_examples[feat_idx] = []

                    # Add example
                    example = {
                        "prompt": prompt,
                        "position": pos,
                        "activation": float(activation),
                        "token": result.tokens[pos] if pos < len(result.tokens) else None
                    }

                    self.feature_examples[feat_idx].append(example)

                    # Keep only top examples
                    self.feature_examples[feat_idx] = sorted(
                        self.feature_examples[feat_idx],
                        key=lambda x: x["activation"],
                        reverse=True
                    )[:max_examples_per_feature]

            if (prompt_idx + 1) % 10 == 0:
                logger.info(f"Processed {prompt_idx + 1}/{len(prompts)} prompts", extra={
                    "features_discovered": len(self.feature_examples)
                })

    def get_top_features(
        self,
        k: int = 20,
        min_activation_frequency: int = 3
    ) -> List[SAEFeature]:
        """
        Get top k most interesting features.

        Args:
            k: Number of features to return
            min_activation_frequency: Minimum number of activations required

        Returns:
            List of SAEFeature objects
        """
        features = []

        for feat_idx, examples in self.feature_examples.items():
            if len(examples) < min_activation_frequency:
                continue

            # Compute statistics
            activation_frequency = len(examples)
            activation_strength = np.mean([ex["activation"] for ex in examples])

            feature = SAEFeature(
                feature_idx=feat_idx,
                activation_frequency=activation_frequency,
                activation_strength=float(activation_strength),
                top_activating_examples=examples
            )
            features.append(feature)

        # Sort by activation strength * frequency (importance)
        features.sort(
            key=lambda f: f.activation_strength * f.activation_frequency,
            reverse=True
        )

        logger.info("Extracted top features", extra={
            "total_features": len(features),
            "top_k": min(k, len(features))
        })

        return features[:k]

    def analyze_feature(
        self,
        feature: SAEFeature,
        generate_description: bool = False
    ) -> Dict[str, Any]:
        """
        Analyze a single feature in detail.

        Args:
            feature: Feature to analyze
            generate_description: Whether to auto-generate description

        Returns:
            Dictionary with analysis results
        """
        analysis = {
            "feature_idx": feature.feature_idx,
            "activation_frequency": feature.activation_frequency,
            "activation_strength": feature.activation_strength,
            "top_examples": feature.top_activating_examples[:5],
        }

        # Get decoder direction for this feature
        W_dec = self.sae.get_W_dec().detach()
        decoder_weights = W_dec[:, feature.feature_idx].cpu().numpy()

        analysis["decoder_norm"] = float(np.linalg.norm(decoder_weights))

        # Token analysis
        tokens = [ex["token"] for ex in feature.top_activating_examples if ex["token"]]
        if tokens:
            from collections import Counter
            token_counts = Counter(tokens)
            analysis["common_tokens"] = token_counts.most_common(5)

        # Auto-generate description if requested
        if generate_description:
            analysis["description"] = self._generate_description(feature)

        return analysis

    def _generate_description(self, feature: SAEFeature) -> str:
        """
        Generate natural language description of feature.

        Args:
            feature: Feature to describe

        Returns:
            Description string
        """
        # Extract common patterns from top examples
        examples = feature.top_activating_examples[:5]

        # Get tokens
        tokens = [ex["token"] for ex in examples if ex["token"]]

        if not tokens:
            return "Unknown feature pattern"

        from collections import Counter
        token_counts = Counter(tokens)
        most_common = token_counts.most_common(3)

        if len(most_common) == 1:
            return f"Activates on token: {most_common[0][0]}"
        elif len(most_common) > 1:
            token_list = ", ".join([t[0] for t in most_common])
            return f"Activates on tokens: {token_list}"
        else:
            return "Mixed feature pattern"

    def export_features(
        self,
        features: List[SAEFeature],
        path: str
    ):
        """
        Export features to JSON file.

        Args:
            features: List of features to export
            path: Output path
        """
        data = {
            "num_features": len(features),
            "sae_config": {
                "d_model": self.sae.config.d_model,
                "d_sae": self.sae.config.d_sae,
                "l1_coefficient": self.sae.config.l1_coefficient
            },
            "features": [f.to_dict() for f in features]
        }

        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)

        logger.info("Features exported", extra={
            "path": str(output_path),
            "num_features": len(features)
        })

    def get_feature_dashboard_data(
        self,
        feature_idx: int
    ) -> Dict[str, Any]:
        """
        Get data for feature dashboard visualization.

        Args:
            feature_idx: Feature index to visualize

        Returns:
            Dictionary with visualization data
        """
        if feature_idx not in self.feature_examples:
            return {"error": "Feature not found"}

        examples = self.feature_examples[feature_idx]

        # Create feature object
        feature = SAEFeature(
            feature_idx=feature_idx,
            activation_frequency=len(examples),
            activation_strength=float(np.mean([ex["activation"] for ex in examples])),
            top_activating_examples=examples
        )

        # Get detailed analysis
        analysis = self.analyze_feature(feature, generate_description=True)

        # Prepare visualization data
        dashboard_data = {
            "feature_idx": feature_idx,
            "description": analysis.get("description", "Unknown"),
            "stats": {
                "activation_frequency": feature.activation_frequency,
                "activation_strength": feature.activation_strength,
                "decoder_norm": analysis["decoder_norm"]
            },
            "top_examples": [
                {
                    "text": ex["prompt"],
                    "position": ex["position"],
                    "activation": ex["activation"],
                    "token": ex["token"]
                }
                for ex in examples[:10]
            ],
            "activation_distribution": [ex["activation"] for ex in examples],
            "common_tokens": analysis.get("common_tokens", [])
        }

        return dashboard_data


# Example usage
if __name__ == "__main__":
    print("🧩 GlassBox Sparse Autoencoder Example\n")
    print("=" * 60)

    # Initialize SAE
    print("\n1. Initializing SAE...")
    config = SAEConfig(
        d_model=768,      # GPT-2 small hidden dimension
        d_sae=768 * 8,    # 8x expansion (typical for SAEs)
        l1_coefficient=0.001,
        learning_rate=1e-4
    )

    sae = SparseAutoencoder(config)
    print(f"   d_model: {config.d_model}")
    print(f"   d_sae: {config.d_sae} ({config.d_sae/config.d_model:.1f}x expansion)")
    print(f"   Parameters: {sum(p.numel() for p in sae.parameters()):,}")

    # Generate sample data
    print("\n2. Testing forward pass...")
    batch_size = 32
    x = torch.randn(batch_size, config.d_model)

    reconstructed, features, W_dec = sae(x)
    loss, loss_dict = sae.get_loss(x, reconstructed, features)

    print(f"   Input shape: {x.shape}")
    print(f"   Features shape: {features.shape}")
    print(f"   Reconstructed shape: {reconstructed.shape}")
    print(f"   Active features per sample: {loss_dict['l0_norm']:.1f}")
    print(f"   Reconstruction loss: {loss_dict['mse_loss']:.4f}")
    print(f"   Variance explained: {loss_dict['var_explained']:.2%}")

    # Test training
    print("\n3. Testing training step...")
    trainer = SAETrainer(sae, config)

    for i in range(5):
        x = torch.randn(batch_size, config.d_model)
        loss_dict = trainer.train_step(x)

    print(f"   Training steps completed: {trainer.step}")
    print(f"   Final loss: {loss_dict['total_loss']:.4f}")

    # Check for dead neurons
    print("\n4. Checking neuron health...")
    dead = sae.get_dead_neurons()
    print(f"   Dead neurons: {dead.sum().item()} / {config.d_sae}")
    print(f"   ({dead.float().mean().item():.1%} of features)")

    # Test feature extraction (requires tracer - optional demo)
    print("\n5. Feature extraction demo...")
    print("   (To run feature extraction, use FeatureAnalyzer with real model)")
    print("   Example workflow:")
    print("   - Initialize: analyzer = FeatureAnalyzer(sae, tracer)")
    print("   - Collect: analyzer.collect_activations(prompts, layer=6)")
    print("   - Analyze: features = analyzer.get_top_features(k=20)")
    print("   - Export: analyzer.export_features(features, 'features.json')")

    print("\n" + "=" * 60)
    print("✅ SAE example complete!\n")
    print("Next steps:")
    print("1. Train SAE on real model activations")
    print("2. Discover monosemantic features")
    print("3. Integrate with circuit discovery")
    print("4. Visualize in dashboard")
