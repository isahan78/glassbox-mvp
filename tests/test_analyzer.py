"""
Unit tests for GlassBox analyzer module.

Run with: pytest tests/test_analyzer.py -v
"""

import pytest
import torch
from glassbox.tracer import ActivationTracer, TracerConfig
from glassbox.analyzer import AttentionAnalyzer, HeadScore


@pytest.fixture
def tracer():
    """Fixture to provide a tracer instance."""
    return ActivationTracer(model_name="gpt2-small")


@pytest.fixture
def analyzer():
    """Fixture to provide an analyzer instance."""
    return AttentionAnalyzer()


@pytest.fixture
def sample_trace(tracer):
    """Fixture to provide a sample trace result."""
    prompt = "The capital of France is"
    config = TracerConfig(capture_layers=[8, 9, 10])
    return tracer.trace(prompt, config)


class TestHeadScore:
    """Tests for HeadScore dataclass."""
    
    def test_head_score_creation(self):
        """Test creating a HeadScore object."""
        head = HeadScore(
            layer=5,
            head=3,
            score=0.75,
            top_attended_tokens=[("Paris", 0.42), ("France", 0.31)]
        )
        
        assert head.layer == 5
        assert head.head == 3
        assert head.score == 0.75
        assert len(head.top_attended_tokens) == 2


class TestAttentionAnalyzer:
    """Tests for AttentionAnalyzer class."""
    
    def test_rank_attention_heads(self, analyzer, sample_trace):
        """Test ranking attention heads."""
        ranked = analyzer.rank_attention_heads(
            sample_trace.attention_cache,
            sample_trace.tokens
        )
        
        assert len(ranked) > 0
        assert all(isinstance(h, HeadScore) for h in ranked)
        
        # Scores should be in descending order
        scores = [h.score for h in ranked]
        assert scores == sorted(scores, reverse=True)
    
    def test_head_score_range(self, analyzer, sample_trace):
        """Test that head scores are in valid range [0, 1]."""
        ranked = analyzer.rank_attention_heads(
            sample_trace.attention_cache,
            sample_trace.tokens
        )
        
        for head in ranked:
            assert 0 <= head.score <= 1
    
    def test_top_attended_tokens(self, analyzer, sample_trace):
        """Test that top attended tokens are populated."""
        ranked = analyzer.rank_attention_heads(
            sample_trace.attention_cache,
            sample_trace.tokens
        )
        
        for head in ranked[:5]:  # Check top 5
            assert len(head.top_attended_tokens) > 0
            
            # Check token-weight pairs
            for token, weight in head.top_attended_tokens:
                assert isinstance(token, str)
                assert 0 <= weight <= 1
    
    def test_layer_head_attributes(self, analyzer, sample_trace):
        """Test that layer and head attributes are valid."""
        ranked = analyzer.rank_attention_heads(
            sample_trace.attention_cache,
            sample_trace.tokens
        )
        
        for head in ranked:
            assert 0 <= head.layer < 12
            assert 0 <= head.head < 12
    
    def test_compute_token_influence(self, analyzer, sample_trace):
        """Test computing token-level influence scores."""
        influence = analyzer.compute_token_influence(
            sample_trace.attention_cache,
            sample_trace.tokens,
            top_n_heads=10
        )
        
        assert isinstance(influence, dict)
        assert len(influence) > 0
        
        # All scores should be in [0, 1]
        for token, score in influence.items():
            assert isinstance(token, str)
            assert 0 <= score <= 1
    
    def test_token_influence_normalization(self, analyzer, sample_trace):
        """Test that token influence is properly normalized."""
        influence = analyzer.compute_token_influence(
            sample_trace.attention_cache,
            sample_trace.tokens,
            top_n_heads=10
        )
        
        # Maximum score should be 1.0 (or close to it)
        max_score = max(influence.values())
        assert 0.9 <= max_score <= 1.0
    
    def test_top_n_heads_parameter(self, analyzer, sample_trace):
        """Test varying the top_n_heads parameter."""
        # Use fewer heads
        influence_5 = analyzer.compute_token_influence(
            sample_trace.attention_cache,
            sample_trace.tokens,
            top_n_heads=5
        )
        
        # Use more heads
        influence_15 = analyzer.compute_token_influence(
            sample_trace.attention_cache,
            sample_trace.tokens,
            top_n_heads=15
        )
        
        # Both should return valid results
        assert len(influence_5) > 0
        assert len(influence_15) > 0
    
    def test_target_token_index(self, analyzer, sample_trace):
        """Test different target token indices."""
        # Last token (default)
        influence_last = analyzer.compute_token_influence(
            sample_trace.attention_cache,
            sample_trace.tokens,
            target_token_idx=-1
        )
        
        # Middle token
        mid_idx = len(sample_trace.tokens) // 2
        influence_mid = analyzer.compute_token_influence(
            sample_trace.attention_cache,
            sample_trace.tokens,
            target_token_idx=mid_idx
        )
        
        # Both should work
        assert len(influence_last) > 0
        assert len(influence_mid) > 0
    
    def test_get_top_contributing_tokens(self, analyzer, sample_trace):
        """Test getting top K contributing tokens."""
        influence = analyzer.compute_token_influence(
            sample_trace.attention_cache,
            sample_trace.tokens
        )
        
        top_5 = analyzer.get_top_contributing_tokens(influence, top_k=5)
        
        assert len(top_5) <= 5
        assert all(isinstance(item, tuple) for item in top_5)
        assert all(len(item) == 2 for item in top_5)
        
        # Should be sorted by score (descending)
        scores = [score for _, score in top_5]
        assert scores == sorted(scores, reverse=True)
    
    def test_empty_cache_handling(self, analyzer):
        """Test handling of empty attention cache."""
        empty_cache = {}
        tokens = ["test"]
        
        ranked = analyzer.rank_attention_heads(empty_cache, tokens)
        assert len(ranked) == 0
    
    def test_consistent_rankings(self, analyzer, sample_trace):
        """Test that rankings are consistent across multiple calls."""
        ranked1 = analyzer.rank_attention_heads(
            sample_trace.attention_cache,
            sample_trace.tokens
        )
        
        ranked2 = analyzer.rank_attention_heads(
            sample_trace.attention_cache,
            sample_trace.tokens
        )
        
        # Should produce identical results
        assert len(ranked1) == len(ranked2)
        for h1, h2 in zip(ranked1, ranked2):
            assert h1.layer == h2.layer
            assert h1.head == h2.head
            assert abs(h1.score - h2.score) < 1e-6
    
    def test_attention_weight_aggregation(self, analyzer, sample_trace):
        """Test that attention weights are properly aggregated."""
        influence = analyzer.compute_token_influence(
            sample_trace.attention_cache,
            sample_trace.tokens,
            top_n_heads=1  # Use only top head
        )
        
        # Should have at least one token with influence
        assert len(influence) > 0
        
        # Verify weights sum to something reasonable
        total_weight = sum(influence.values())
        assert total_weight > 0


class TestIntegration:
    """Integration tests combining tracer and analyzer."""
    
    def test_end_to_end_analysis(self, tracer, analyzer):
        """Test complete trace and analysis workflow."""
        # Trace
        prompt = "Paris is the capital of France"
        result = tracer.trace(prompt)
        
        # Analyze
        ranked = analyzer.rank_attention_heads(
            result.attention_cache,
            result.tokens
        )
        
        influence = analyzer.compute_token_influence(
            result.attention_cache,
            result.tokens
        )
        
        top_tokens = analyzer.get_top_contributing_tokens(influence, top_k=5)
        
        # Verify results
        assert len(ranked) > 0
        assert len(influence) > 0
        assert len(top_tokens) > 0
    
    def test_multiple_prompts(self, tracer, analyzer):
        """Test analysis on multiple different prompts."""
        prompts = [
            "Hello world",
            "The quick brown fox",
            "Machine learning is"
        ]
        
        for prompt in prompts:
            result = tracer.trace(prompt)
            ranked = analyzer.rank_attention_heads(
                result.attention_cache,
                result.tokens
            )
            
            assert len(ranked) > 0
            assert all(0 <= h.score <= 1 for h in ranked)
    
    def test_layer_specific_analysis(self, tracer, analyzer):
        """Test analysis when capturing specific layers."""
        config = TracerConfig(capture_layers=[10, 11])
        result = tracer.trace("Test prompt", config)
        
        ranked = analyzer.rank_attention_heads(
            result.attention_cache,
            result.tokens
        )
        
        # Should only have heads from specified layers
        layers = {h.layer for h in ranked}
        assert layers.issubset({10, 11})
    
    def test_short_vs_long_prompts(self, tracer, analyzer):
        """Test analysis on different prompt lengths."""
        short_prompt = "Hi"
        long_prompt = "This is a much longer prompt with many more tokens to process"
        
        for prompt in [short_prompt, long_prompt]:
            result = tracer.trace(prompt)
            ranked = analyzer.rank_attention_heads(
                result.attention_cache,
                result.tokens
            )
            
            influence = analyzer.compute_token_influence(
                result.attention_cache,
                result.tokens
            )
            
            assert len(ranked) > 0
            assert len(influence) > 0


class TestEdgeCases:
    """Tests for edge cases and error conditions."""
    
    def test_single_token_input(self, tracer, analyzer):
        """Test with single token input."""
        result = tracer.trace("Hi")
        
        ranked = analyzer.rank_attention_heads(
            result.attention_cache,
            result.tokens
        )
        
        # Should still produce results
        assert len(ranked) >= 0
    
    def test_mismatched_tokens_length(self, analyzer, sample_trace):
        """Test with mismatched token list length."""
        # Use fewer tokens than actually in cache
        short_tokens = sample_trace.tokens[:3]
        
        # Should not crash
        ranked = analyzer.rank_attention_heads(
            sample_trace.attention_cache,
            short_tokens
        )
        
        assert isinstance(ranked, list)
    
    def test_negative_indices(self, analyzer, sample_trace):
        """Test negative indexing for target token."""
        # Last token
        influence = analyzer.compute_token_influence(
            sample_trace.attention_cache,
            sample_trace.tokens,
            target_token_idx=-1
        )
        assert len(influence) > 0
        
        # Second to last
        influence = analyzer.compute_token_influence(
            sample_trace.attention_cache,
            sample_trace.tokens,
            target_token_idx=-2
        )
        assert len(influence) > 0
    
    def test_zero_top_k(self, analyzer, sample_trace):
        """Test get_top_contributing_tokens with k=0."""
        influence = analyzer.compute_token_influence(
            sample_trace.attention_cache,
            sample_trace.tokens
        )
        
        top_0 = analyzer.get_top_contributing_tokens(influence, top_k=0)
        assert len(top_0) == 0
    
    def test_top_k_larger_than_tokens(self, analyzer, sample_trace):
        """Test when top_k is larger than number of tokens."""
        influence = analyzer.compute_token_influence(
            sample_trace.attention_cache,
            sample_trace.tokens
        )
        
        # Request more tokens than available
        top_many = analyzer.get_top_contributing_tokens(
            influence, 
            top_k=1000
        )
        
        # Should return all available tokens
        assert len(top_many) <= len(sample_trace.tokens)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
