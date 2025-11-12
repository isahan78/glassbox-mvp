"""
GlassBox Tracer - Captures transformer internals during inference.

This module provides activation and attention capture for GPT-2 models
using the TransformerLens library.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Tuple, Dict
import torch
from transformer_lens import HookedTransformer
import time
from datetime import datetime

# Constants
BYTES_PER_FLOAT32 = 4
BYTES_TO_GB = 1024**3
DEFAULT_MAX_SEQ_LENGTH = 512


@dataclass
class TracerConfig:
    """Configuration for activation capture."""
    
    # Layer selection (None = all layers)
    capture_layers: Optional[List[int]] = None
    
    # Attention head selection (layer, head) tuples
    capture_heads: Optional[List[Tuple[int, int]]] = None
    
    # Memory optimization
    store_activations: bool = True
    max_seq_length: int = DEFAULT_MAX_SEQ_LENGTH
    
    # Output control
    include_gradients: bool = False


@dataclass
class TraceMetadata:
    """Metadata about the trace execution."""
    timestamp: str
    model_name: str
    device: str
    inference_time_ms: float
    capture_overhead_ms: float
    baseline_inference_ms: float
    slowdown_factor: float
    glassbox_version: str = "0.1.0"


@dataclass
class TraceResult:
    """Results from a traced inference run."""
    prompt: str
    output_text: str
    tokens: List[str]
    token_ids: List[int]
    logits: torch.Tensor
    attention_cache: Dict[str, torch.Tensor]
    activation_cache: Optional[Dict[str, torch.Tensor]]
    metadata: TraceMetadata


class ActivationTracer:
    """Captures model internals during forward pass."""
    
    # Supported model configurations
    SUPPORTED_MODELS = {
        # GPT-2 Family (Small, fast)
        "gpt2-small": {"size": "124M", "layers": 12, "heads": 12},
        "gpt2-medium": {"size": "355M", "layers": 24, "heads": 16},
        "gpt2-large": {"size": "774M", "layers": 36, "heads": 20},
        "gpt2-xl": {"size": "1.5B", "layers": 48, "heads": 25},
        
        # Llama 2 Family (Modern, instruction-following)
        "meta-llama/Llama-2-7b-hf": {"size": "7B", "layers": 32, "heads": 32},
        "meta-llama/Llama-2-13b-hf": {"size": "13B", "layers": 40, "heads": 40},
        
        # Mistral (Efficient, modern)
        "mistral-7b": {"size": "7B", "layers": 32, "heads": 32},
        
        # GPT-Neo/J (Open source alternatives)
        "EleutherAI/gpt-neo-1.3B": {"size": "1.3B", "layers": 24, "heads": 16},
        "EleutherAI/gpt-j-6B": {"size": "6B", "layers": 28, "heads": 16},
    }
    
    def __init__(self, model_name: str = "gpt2-medium", device: str = "cpu"):
        """
        Initialize the tracer with a specific model.
        
        Supported models (with 36GB RAM):
        - "gpt2-small" (124M) - Fast, basic
        - "gpt2-medium" (355M) - ⭐ Good balance
        - "gpt2-large" (774M) - Better quality
        - "gpt2-xl" (1.5B) - High quality
        - "meta-llama/Llama-2-7b-hf" (7B) - ⭐⭐ RECOMMENDED (modern, smart)
        - "mistral-7b" (7B) - Modern, efficient
        - "EleutherAI/gpt-j-6B" (6B) - Open source alternative
        
        Args:
            model_name: Model identifier
            device: Device to run on ('cpu', 'cuda', 'mps')
        """
        self.model_name = model_name
        self.device = device
        
        # Show model info
        if model_name in self.SUPPORTED_MODELS:
            info = self.SUPPORTED_MODELS[model_name]
            print(f"📦 Loading {model_name} ({info['size']})...")
            print(f"   Expected: {info['layers']} layers, {info['heads']} heads")
        else:
            print(f"⚠️  {model_name} not in supported list, attempting to load...")
        
        # Load model
        try:
            self.model = HookedTransformer.from_pretrained(
                model_name,
                device=device,
                fold_ln=False,  # Better for interpretability
                center_writing_weights=False,
                center_unembed=False,
            )
        except Exception as e:
            print(f"❌ Error loading {model_name}: {e}")
            print(f"💡 Tip: For Llama models, run 'huggingface-cli login' first")
            raise
        
        self.num_layers = self.model.cfg.n_layers
        self.num_heads = self.model.cfg.n_heads
        
        print(f"✅ Loaded {model_name}")
        print(f"   Actual: {self.num_layers} layers, {self.num_heads} heads per layer")
        print(f"   Device: {self.device}")
        
        # Memory estimate
        param_count = sum(p.numel() for p in self.model.parameters())
        memory_gb = (param_count * BYTES_PER_FLOAT32) / BYTES_TO_GB
        print(f"   Memory: ~{memory_gb:.1f}GB required")
    
    def trace(
        self, 
        prompt: str, 
        config: Optional[TracerConfig] = None
    ) -> TraceResult:
        """
        Run model inference with activation capture.
        
        Args:
            prompt: Input text to trace
            config: Configuration for capture (defaults to full capture)
            
        Returns:
            TraceResult containing all captured data
        """
        if config is None:
            config = TracerConfig()
        
        # Truncate if needed
        tokens = self.model.to_tokens(prompt)
        if tokens.shape[1] > config.max_seq_length:
            tokens = tokens[:, :config.max_seq_length]
            print(f"Warning: Truncated input to {config.max_seq_length} tokens")
        
        # Baseline inference timing
        baseline_start = time.time()
        with torch.no_grad():
            _ = self.model(tokens)
        baseline_time = (time.time() - baseline_start) * 1000
        
        # Traced inference
        trace_start = time.time()
        
        # Run with cache
        with torch.no_grad():
            logits, cache = self.model.run_with_cache(tokens)
        
        trace_time = (time.time() - trace_start) * 1000
        
        # Extract attention patterns
        attention_cache = self._extract_attention(cache, config)
        
        # Extract activations if requested
        activation_cache = None
        if config.store_activations:
            activation_cache = self._extract_activations(cache, config)
        
        # Get output token
        next_token_id = logits[0, -1].argmax().item()
        output_text = self.model.to_string(next_token_id)
        
        # Convert tokens to strings
        token_strings = [
            self.model.to_string(tok.item()) 
            for tok in tokens[0]
        ]
        
        # Build metadata
        metadata = TraceMetadata(
            timestamp=datetime.now().isoformat(),
            model_name=self.model_name,
            device=str(self.device),
            inference_time_ms=trace_time,
            capture_overhead_ms=trace_time - baseline_time,
            baseline_inference_ms=baseline_time,
            slowdown_factor=trace_time / baseline_time if baseline_time > 0 else 0
        )
        
        return TraceResult(
            prompt=prompt,
            output_text=output_text,
            tokens=token_strings,
            token_ids=tokens[0].tolist(),
            logits=logits,
            attention_cache=attention_cache,
            activation_cache=activation_cache,
            metadata=metadata
        )
    
    def _extract_attention(
        self, 
        cache, 
        config: TracerConfig
    ) -> Dict[str, torch.Tensor]:
        """Extract attention patterns from cache."""
        attention_cache = {}
        
        layers = config.capture_layers or range(self.num_layers)
        
        for layer in layers:
            if layer >= self.num_layers:
                continue
                
            # Get attention pattern for this layer
            # Shape: [batch, head, query_pos, key_pos]
            attn_pattern = cache[f"blocks.{layer}.attn.hook_pattern"]
            
            # Store each head separately
            for head in range(self.num_heads):
                # Check if we should capture this specific head
                if config.capture_heads is not None:
                    if (layer, head) not in config.capture_heads:
                        continue
                
                key = f"layer_{layer}_head_{head}"
                # Remove batch dimension: [query_pos, key_pos]
                attention_cache[key] = attn_pattern[0, head].cpu()
        
        return attention_cache
    
    def _extract_activations(
        self, 
        cache, 
        config: TracerConfig
    ) -> Dict[str, torch.Tensor]:
        """Extract layer activations from cache."""
        activation_cache = {}
        
        layers = config.capture_layers or range(self.num_layers)
        
        for layer in layers:
            if layer >= self.num_layers:
                continue
            
            # Residual stream after this layer
            key = f"layer_{layer}_resid"
            activation_cache[key] = cache[f"blocks.{layer}.hook_resid_post"][0].cpu()
        
        return activation_cache


# Example usage
if __name__ == "__main__":
    # Initialize tracer
    tracer = ActivationTracer(model_name="gpt2-small")
    
    # Configure capture (optional - focuses on middle layers)
    config = TracerConfig(
        capture_layers=[5, 6, 7, 8, 9],
        max_seq_length=128
    )
    
    # Run trace
    prompt = "Should we approve this loan application?"
    result = tracer.trace(prompt, config)
    
    # Print results
    print(f"\nPrompt: {result.prompt}")
    print(f"Output: {result.output_text}")
    print(f"Tokens: {len(result.tokens)}")
    print(f"Inference time: {result.metadata.inference_time_ms:.1f}ms")
    print(f"Slowdown: {result.metadata.slowdown_factor:.2f}x")
    print(f"Captured {len(result.attention_cache)} attention heads")