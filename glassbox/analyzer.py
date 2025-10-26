"""
GlassBox Analyzer - Attribution analysis for traced results.

This module provides methods to rank attention heads and compute
token-level influence scores from captured attention patterns.
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple
import torch
import numpy as np


@dataclass
class HeadScore:
    """Represents a single attention head's contribution."""
    layer: int
    head: int
    score: float  # Range: [0, 1]
    top_attended_tokens: List[Tuple[str, float]]


class AttentionAnalyzer:
    """Analyze attention patterns to identify contributing heads."""
    
    def rank_attention_heads(
        self,
        attention_cache: Dict[str, torch.Tensor],
        tokens: List[str],
        target_token_idx: int = -1
    ) -> List[HeadScore]:
        """
        Rank attention heads by their focus on the target output token.
        
        Algorithm:
        1. For each attention head, extract attention weights at target position
        2. Compute mean attention weight to all input tokens
        3. Rank heads by this aggregated attention score
        
        Args:
            attention_cache: Dict of attention tensors by layer/head
            tokens: List of token strings for reference
            target_token_idx: Position of token to analyze (-1 = last)
            
        Returns:
            List of HeadScore objects, sorted by contribution (highest first)
        """
        head_scores = []
        
        for key, attn_tensor in attention_cache.items():
            # Parse key: "layer_X_head_Y"
            parts = key.split("_")
            layer_idx = int(parts[1])
            head_idx = int(parts[3])
            
            # Handle negative indexing
            if target_token_idx < 0:
                target_idx = attn_tensor.shape[0] + target_token_idx
            else:
                target_idx = target_token_idx
            
            # Ensure index is valid
            if target_idx >= attn_tensor.shape[0] or target_idx < 0:
                continue
            
            # Get attention from target token to all previous tokens
            # Shape: [seq_len]
            target_attention = attn_tensor[target_idx, :target_idx + 1]
            
            # Score = mean attention weight
            score = target_attention.mean().item()
            
            # Get top attended tokens
            top_k = min(5, len(target_attention))
            top_values, top_indices = torch.topk(target_attention, top_k)
            
            top_attended = [
                (tokens[idx.item()], val.item())
                for idx, val in zip(top_indices, top_values)
                if idx.item() < len(tokens)
            ]
            
            head_scores.append(HeadScore(
                layer=layer_idx,
                head=head_idx,
                score=score,
                top_attended_tokens=top_attended
            ))
        
        # Sort by score (highest first)
        return sorted(head_scores, key=lambda x: x.score, reverse=True)
    
    def compute_token_influence(
        self,
        attention_cache: Dict[str, torch.Tensor],
        tokens: List[str],
        target_token_idx: int = -1,
        top_n_heads: int = 10
    ) -> Dict[str, float]:
        """
        Compute aggregate influence score per input token.
        
        Algorithm:
        1. Take top N attention heads (by head score)
        2. For each head, get attention weights from target to each input token
        3. Average these weights across heads
        4. Normalize to [0, 1]
        
        Args:
            attention_cache: Dict of attention tensors
            tokens: List of token strings
            target_token_idx: Position to analyze (-1 = last)
            top_n_heads: Number of top heads to consider
            
        Returns:
            Dict mapping token_string -> influence_score
        """
        # First rank all heads
        ranked_heads = self.rank_attention_heads(
            attention_cache, 
            tokens, 
            target_token_idx
        )
        
        # Take top N
        top_heads = ranked_heads[:top_n_heads]
        
        # Handle negative indexing
        if target_token_idx < 0:
            # Get sequence length from first attention tensor
            first_tensor = next(iter(attention_cache.values()))
            target_idx = first_tensor.shape[0] + target_token_idx
        else:
            target_idx = target_token_idx
        
        # Accumulate attention weights per token
        token_scores = np.zeros(len(tokens))
        
        for head_score in top_heads:
            key = f"layer_{head_score.layer}_head_{head_score.head}"
            if key not in attention_cache:
                continue
            
            attn = attention_cache[key]
            
            # Get attention from target to all tokens
            if target_idx >= attn.shape[0]:
                continue
            
            target_attn = attn[target_idx, :target_idx + 1].numpy()
            
            # Add to accumulator (weighted by head score)
            valid_length = min(len(target_attn), len(token_scores))
            token_scores[:valid_length] += target_attn[:valid_length] * head_score.score
        
        # Normalize to [0, 1]
        if token_scores.max() > 0:
            token_scores = token_scores / token_scores.max()
        
        # Create dict mapping tokens to scores
        return {
            token: float(score)
            for token, score in zip(tokens, token_scores)
            if score > 0  # Only include non-zero scores
        }
    
    def get_top_contributing_tokens(
        self,
        token_influence: Dict[str, float],
        top_k: int = 10
    ) -> List[Tuple[str, float]]:
        """
        Get the top K most influential tokens.
        
        Args:
            token_influence: Dict from compute_token_influence
            top_k: Number of top tokens to return
            
        Returns:
            List of (token, score) tuples, sorted by score
        """
        sorted_tokens = sorted(
            token_influence.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_tokens[:top_k]


# Example usage
if __name__ == "__main__":
    from tracer import ActivationTracer, TracerConfig
    
    # Initialize tracer and analyzer
    tracer = ActivationTracer(model_name="gpt2-small")
    analyzer = AttentionAnalyzer()
    
    # Run trace
    prompt = "Should we approve this loan application?"
    config = TracerConfig(capture_layers=[5, 6, 7, 8, 9])
    result = tracer.trace(prompt, config)
    
    print(f"Analyzing: {prompt}")
    print(f"Output: {result.output_text}\n")
    
    # Rank attention heads
    top_heads = analyzer.rank_attention_heads(
        result.attention_cache,
        result.tokens,
        target_token_idx=-1
    )
    
    print("Top 5 Contributing Attention Heads:")
    for i, head in enumerate(top_heads[:5], 1):
        print(f"\n{i}. Layer {head.layer}, Head {head.head}")
        print(f"   Score: {head.score:.3f}")
        print(f"   Top attended tokens:")
        for token, weight in head.top_attended_tokens[:3]:
            print(f"     → '{token}': {weight:.3f}")
    
    # Compute token influence
    token_influence = analyzer.compute_token_influence(
        result.attention_cache,
        result.tokens,
        top_n_heads=10
    )
    
    print("\n\nToken Influence Scores:")
    top_tokens = analyzer.get_top_contributing_tokens(token_influence, top_k=7)
    for token, score in top_tokens:
        bar = "█" * int(score * 20)
        print(f"  '{token:15s}' {bar} {score:.3f}")
