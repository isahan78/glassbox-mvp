"""
GlassBox Feature Discovery - End-to-end workflows for discovering monosemantic features.

This module provides high-level workflows for:
1. Training SAEs on model activations
2. Discovering monosemantic features
3. Interpreting and analyzing features
4. Integrating features with circuit discovery

Based on research:
- "Towards Monosemanticity" (Anthropic, 2023)
- "Sparse Autoencoders Find Highly Interpretable Features" (Cunningham et al., 2023)
- "Scaling Monosemanticity" (Anthropic, 2024)
"""

import torch
from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path
import json

from glassbox.tracer import ActivationTracer
from glassbox.sae import SparseAutoencoder, SAEConfig, SAETrainer, FeatureAnalyzer, SAEFeature
from glassbox.logging_config import get_logger

logger = get_logger(__name__)


class FeatureDiscoveryWorkflow:
    """
    End-to-end workflow for discovering monosemantic features.

    Workflow:
    1. Collect activations from model on diverse prompts
    2. Train SAE to decompose activations into sparse features
    3. Analyze features to find monosemantic patterns
    4. Export and visualize discovered features
    """

    def __init__(
        self,
        model_name: str = "gpt2-small",
        layer: int = 6,
        device: str = "cpu"
    ):
        """
        Initialize feature discovery workflow.

        Args:
            model_name: Name of model to analyze
            layer: Which layer to analyze
            device: Device to run on
        """
        self.model_name = model_name
        self.layer = layer
        self.device = device

        # Initialize tracer
        self.tracer = ActivationTracer(model_name)

        # Get model dimension
        self.d_model = self.tracer.model.cfg.d_model

        # SAE will be initialized during training
        self.sae = None
        self.analyzer = None

        logger.info("Feature discovery workflow initialized", extra={
            "model": model_name,
            "layer": layer,
            "d_model": self.d_model
        })

    def collect_training_data(
        self,
        prompts: List[str],
        max_samples: int = 10000
    ) -> torch.Tensor:
        """
        Collect activation data for SAE training.

        Args:
            prompts: List of prompts to trace
            max_samples: Maximum number of activation vectors to collect

        Returns:
            Tensor of activations [num_samples, d_model]
        """
        logger.info("Collecting training data", extra={
            "num_prompts": len(prompts),
            "layer": self.layer,
            "max_samples": max_samples
        })

        activations_list = []
        cache_key = f"layer_{self.layer}_resid"

        for prompt_idx, prompt in enumerate(prompts):
            # Trace prompt
            result = self.tracer.trace(prompt)

            # Get activations for this layer
            if cache_key not in result.cache:
                logger.warning(f"Layer {self.layer} not found in cache")
                continue

            activations = result.cache[cache_key]  # [seq_len, d_model]
            activations_list.append(activations)

            # Check if we have enough samples
            total_samples = sum(a.shape[0] for a in activations_list)
            if total_samples >= max_samples:
                logger.info(f"Collected {total_samples} samples, stopping early")
                break

            if (prompt_idx + 1) % 10 == 0:
                logger.info(f"Processed {prompt_idx + 1}/{len(prompts)} prompts", extra={
                    "samples_collected": total_samples
                })

        # Concatenate all activations
        all_activations = torch.cat(activations_list, dim=0)

        # Subsample if needed
        if all_activations.shape[0] > max_samples:
            indices = torch.randperm(all_activations.shape[0])[:max_samples]
            all_activations = all_activations[indices]

        logger.info("Data collection complete", extra={
            "num_samples": all_activations.shape[0],
            "shape": list(all_activations.shape)
        })

        return all_activations

    def train_sae(
        self,
        training_data: torch.Tensor,
        expansion_factor: int = 8,
        l1_coefficient: float = 0.001,
        num_steps: int = 1000,
        batch_size: int = 256
    ) -> Tuple[SparseAutoencoder, Dict[str, Any]]:
        """
        Train sparse autoencoder on collected activations.

        Args:
            training_data: Activation data [num_samples, d_model]
            expansion_factor: SAE expansion (d_sae = expansion_factor * d_model)
            l1_coefficient: L1 sparsity penalty
            num_steps: Number of training steps
            batch_size: Batch size

        Returns:
            Tuple of (trained_sae, training_stats)
        """
        logger.info("Training SAE", extra={
            "expansion_factor": expansion_factor,
            "l1_coefficient": l1_coefficient,
            "num_steps": num_steps
        })

        # Create SAE config
        config = SAEConfig(
            d_model=self.d_model,
            d_sae=self.d_model * expansion_factor,
            l1_coefficient=l1_coefficient,
            batch_size=batch_size,
            learning_rate=1e-4
        )

        # Initialize SAE and trainer
        sae = SparseAutoencoder(config)
        trainer = SAETrainer(sae, config, device=self.device)

        # Training loop
        training_stats = {
            "loss_history": [],
            "l0_history": [],
            "var_explained_history": []
        }

        for step in range(num_steps):
            # Sample batch
            indices = torch.randperm(training_data.shape[0])[:batch_size]
            batch = training_data[indices]

            # Training step
            loss_dict = trainer.train_step(batch)

            # Record stats
            training_stats["loss_history"].append(loss_dict["total_loss"])
            training_stats["l0_history"].append(loss_dict["l0_norm"])
            training_stats["var_explained_history"].append(loss_dict["var_explained"])

            # Log progress
            if (step + 1) % 100 == 0:
                logger.info(f"Step {step + 1}/{num_steps}", extra={
                    "loss": loss_dict["total_loss"],
                    "l0": loss_dict["l0_norm"],
                    "var_explained": loss_dict["var_explained"]
                })

        # Check dead neurons
        dead = sae.get_dead_neurons()
        training_stats["num_dead_neurons"] = dead.sum().item()
        training_stats["pct_dead"] = dead.float().mean().item()

        logger.info("SAE training complete", extra={
            "final_loss": training_stats["loss_history"][-1],
            "dead_neurons": training_stats["num_dead_neurons"]
        })

        self.sae = sae
        return sae, training_stats

    def discover_features(
        self,
        prompts: List[str],
        top_k: int = 20,
        min_activation_frequency: int = 3
    ) -> List[SAEFeature]:
        """
        Discover monosemantic features using trained SAE.

        Args:
            prompts: List of prompts to analyze
            top_k: Number of top features to return
            min_activation_frequency: Minimum activations required

        Returns:
            List of discovered features
        """
        if self.sae is None:
            raise ValueError("Must train SAE first using train_sae()")

        logger.info("Discovering monosemantic features", extra={
            "num_prompts": len(prompts),
            "top_k": top_k
        })

        # Initialize analyzer
        self.analyzer = FeatureAnalyzer(self.sae, self.tracer, device=self.device)

        # Collect activations
        self.analyzer.collect_activations(
            prompts=prompts,
            layer=self.layer,
            max_examples_per_feature=10
        )

        # Get top features
        features = self.analyzer.get_top_features(
            k=top_k,
            min_activation_frequency=min_activation_frequency
        )

        logger.info("Feature discovery complete", extra={
            "features_discovered": len(features)
        })

        return features

    def analyze_features(
        self,
        features: List[SAEFeature],
        generate_descriptions: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Analyze discovered features in detail.

        Args:
            features: List of features to analyze
            generate_descriptions: Whether to generate descriptions

        Returns:
            List of feature analysis dictionaries
        """
        if self.analyzer is None:
            raise ValueError("Must discover features first using discover_features()")

        logger.info("Analyzing features", extra={
            "num_features": len(features)
        })

        analyses = []
        for feature in features:
            analysis = self.analyzer.analyze_feature(
                feature,
                generate_description=generate_descriptions
            )
            analyses.append(analysis)

        return analyses

    def export_results(
        self,
        features: List[SAEFeature],
        output_dir: str = "sae_results"
    ):
        """
        Export discovered features and SAE checkpoint.

        Args:
            features: Features to export
            output_dir: Output directory
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Export features
        if self.analyzer is not None:
            feature_path = output_path / "features.json"
            self.analyzer.export_features(features, str(feature_path))

        # Export SAE checkpoint (create temporary trainer)
        if self.sae is not None:
            sae_path = output_path / "sae_checkpoint.pt"
            trainer = SAETrainer(self.sae, self.sae.config, device=self.device)
            trainer.save(str(sae_path))

        # Export metadata
        metadata = {
            "model": self.model_name,
            "layer": self.layer,
            "d_model": self.d_model,
            "num_features": len(features),
            "config": {
                "d_sae": self.sae.config.d_sae if self.sae else None,
                "l1_coefficient": self.sae.config.l1_coefficient if self.sae else None
            }
        }

        metadata_path = output_path / "metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        logger.info("Results exported", extra={
            "output_dir": str(output_path),
            "num_features": len(features)
        })

    def run_full_workflow(
        self,
        training_prompts: List[str],
        analysis_prompts: List[str],
        expansion_factor: int = 8,
        num_training_steps: int = 1000,
        output_dir: str = "sae_results"
    ) -> Dict[str, Any]:
        """
        Run complete feature discovery workflow.

        Args:
            training_prompts: Prompts for SAE training
            analysis_prompts: Prompts for feature analysis
            expansion_factor: SAE expansion factor
            num_training_steps: Number of training steps
            output_dir: Output directory

        Returns:
            Dictionary with results
        """
        logger.info("Starting full feature discovery workflow")

        # Step 1: Collect training data
        training_data = self.collect_training_data(training_prompts)

        # Step 2: Train SAE
        sae, training_stats = self.train_sae(
            training_data,
            expansion_factor=expansion_factor,
            num_steps=num_training_steps
        )

        # Step 3: Discover features
        features = self.discover_features(analysis_prompts)

        # Step 4: Analyze features
        analyses = self.analyze_features(features)

        # Step 5: Export results
        self.export_results(features, output_dir)

        results = {
            "training_stats": training_stats,
            "num_features_discovered": len(features),
            "features": [f.to_dict() for f in features],
            "analyses": analyses,
            "output_dir": output_dir
        }

        logger.info("Full workflow complete", extra={
            "features_discovered": len(features),
            "output_dir": output_dir
        })

        return results


# Example usage
if __name__ == "__main__":
    print("🔍 GlassBox Feature Discovery Example\n")
    print("=" * 60)

    # Sample prompts (in practice, use hundreds/thousands of diverse prompts)
    training_prompts = [
        "The Eiffel Tower is in Paris",
        "The capital of France is Paris",
        "London is the capital of England",
        "The Statue of Liberty is in New York",
        "Tokyo is the capital of Japan",
        "The Great Wall is in China",
        "Rome is the capital of Italy",
        "Berlin is the capital of Germany"
    ]

    analysis_prompts = training_prompts + [
        "Paris is a beautiful city",
        "I love visiting London",
        "Tokyo has amazing food"
    ]

    print("\n1. Initializing workflow...")
    workflow = FeatureDiscoveryWorkflow(
        model_name="gpt2-small",
        layer=6,
        device="cpu"
    )
    print(f"   Model: gpt2-small")
    print(f"   Layer: 6 (middle layer)")
    print(f"   d_model: {workflow.d_model}")

    print("\n2. Running full workflow...")
    print("   (This is a minimal example - real usage needs more prompts)")
    print("   - Collecting activations...")
    print("   - Training SAE...")
    print("   - Discovering features...")
    print("   - Analyzing patterns...")

    # Note: This is a demo - uncomment to run full workflow
    # results = workflow.run_full_workflow(
    #     training_prompts=training_prompts,
    #     analysis_prompts=analysis_prompts,
    #     expansion_factor=8,
    #     num_training_steps=100,  # Use 1000+ for real training
    #     output_dir="sae_results"
    # )
    #
    # print(f"\n   Features discovered: {results['num_features_discovered']}")
    # print(f"   Results saved to: {results['output_dir']}")

    print("\n" + "=" * 60)
    print("✅ Feature discovery example complete!\n")
    print("To run full workflow:")
    print("1. Prepare diverse training prompts (100-1000+)")
    print("2. Run: results = workflow.run_full_workflow(...)")
    print("3. Analyze discovered features")
    print("4. Integrate with circuit discovery")
