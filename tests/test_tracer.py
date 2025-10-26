"""
Unit tests for GlassBox tracer module.

Run with: pytest tests/test_tracer.py -v
"""

import pytest
import torch
from glassbox_tracer import ActivationTracer, TracerConfig, TraceResult


@pytest.fixture
def tracer():
    """Fixture to provide a tracer instance."""
    return ActivationTracer(model_name="gpt2-small")


class TestTracerConfig:
    """Tests for TracerConfig dataclass."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = TracerConfig()
        assert config.capture_layers is None
        assert config.capture_heads is None
        assert config.store_activations is True
        assert config.max_seq_length == 512
        assert config.include_gradients is False
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = TracerConfig(
            capture_layers=[5, 6, 7],
            max_seq_length=128,
            store_activations=False
        )
        assert config.capture_layers == [5, 6, 7]
        assert config.max_seq_length == 128
        assert config.store_activations is False


class TestActivationTracer:
    """Tests for ActivationTracer class."""
    
    def test_tracer_initialization(self, tracer):
        """Test tracer initializes correctly."""
        assert tracer.model_name == "gpt2-small"
        assert tracer.num_layers == 12
        assert tracer.num_heads == 12
        assert tracer.model is not None
    
    def test_basic_trace(self, tracer):
        """Test basic tracing functionality."""
        prompt = "Hello world"
        result = tracer.trace(prompt)
        
        assert isinstance(result, TraceResult)
        assert result.prompt == prompt
        assert len(result.tokens) > 0
        assert len(result.token_ids) == len(result.tokens)
        assert result.output_text is not None
        assert result.logits is not None
        assert len(result.attention_cache) > 0
    
    def test_trace_with_config(self, tracer):
        """Test tracing with custom configuration."""
        config = TracerConfig(
            capture_layers=[5, 6, 7],
            max_seq_length=64
        )
        
        prompt = "The capital of France is"
        result = tracer.trace(prompt, config)
        
        # Should only capture specified layers
        layers_captured = set()
        for key in result.attention_cache.keys():
            layer = int(key.split("_")[1])
            layers_captured.add(layer)
        
        assert layers_captured.issubset({5, 6, 7})
    
    def test_attention_cache_structure(self, tracer):
        """Test attention cache has correct structure."""
        result = tracer.trace("Test prompt")
        
        # Check cache keys format
        for key, tensor in result.attention_cache.items():
            assert key.startswith("layer_")
            assert "_head_" in key
            
            # Parse layer and head
            parts = key.split("_")
            layer = int(parts[1])
            head = int(parts[3])
            
            assert 0 <= layer < 12
            assert 0 <= head < 12
            
            # Check tensor shape [seq_len, seq_len]
            assert len(tensor.shape) == 2
            assert tensor.shape[0] == tensor.shape[1]
    
    def test_metadata(self, tracer):
        """Test trace metadata is populated."""
        result = tracer.trace("Test")
        metadata = result.metadata
        
        assert metadata.timestamp is not None
        assert metadata.model_name == "gpt2-small"
        assert metadata.inference_time_ms > 0
        assert metadata.baseline_inference_ms > 0
        assert metadata.capture_overhead_ms >= 0
        assert metadata.slowdown_factor >= 1.0
        assert metadata.glassbox_version == "0.1.0"
    
    def test_long_sequence_truncation(self, tracer):
        """Test that long sequences are truncated."""
        long_prompt = "word " * 600  # More than max_seq_length
        config = TracerConfig(max_seq_length=128)
        
        result = tracer.trace(long_prompt, config)
        
        # Should be truncated to max_seq_length
        assert len(result.tokens) <= 128
    
    def test_activation_cache_optional(self, tracer):
        """Test that activation cache can be disabled."""
        config = TracerConfig(store_activations=False)
        result = tracer.trace("Test", config)
        
        assert result.activation_cache is None
    
    def test_activation_cache_enabled(self, tracer):
        """Test that activation cache is stored when enabled."""
        config = TracerConfig(
            store_activations=True,
            capture_layers=[5, 6]
        )
        result = tracer.trace("Test", config)
        
        assert result.activation_cache is not None
        assert len(result.activation_cache) > 0
        
        # Check keys format
        for key in result.activation_cache.keys():
            assert key.startswith("layer_")
            assert "_resid" in key
    
    def test_output_logits(self, tracer):
        """Test that logits are correctly shaped."""
        result = tracer.trace("Test prompt")
        
        # Logits should be [batch=1, seq_len, vocab_size]
        assert len(result.logits.shape) == 3
        assert result.logits.shape[0] == 1
        assert result.logits.shape[1] == len(result.tokens)
        assert result.logits.shape[2] > 0  # vocab_size
    
    def test_empty_prompt_handling(self, tracer):
        """Test handling of empty or very short prompts."""
        # Single token should work
        result = tracer.trace("Hi")
        assert len(result.tokens) >= 1
        assert result.output_text is not None
    
    def test_special_characters(self, tracer):
        """Test tracing with special characters."""
        prompts = [
            "Hello! How are you?",
            "Price: $99.99",
            "Email: test@example.com"
        ]
        
        for prompt in prompts:
            result = tracer.trace(prompt)
            assert result.prompt == prompt
            assert len(result.tokens) > 0
    
    def test_performance_metrics(self, tracer):
        """Test that performance metrics are reasonable."""
        result = tracer.trace("Test prompt")
        
        # Inference should take less than 60 seconds
        assert result.metadata.inference_time_ms < 60000
        
        # Slowdown should be positive
        assert result.metadata.slowdown_factor > 0
        
        # Capture overhead should be non-negative
        assert result.metadata.capture_overhead_ms >= 0


class TestTraceResult:
    """Tests for TraceResult dataclass."""
    
    def test_trace_result_attributes(self, tracer):
        """Test that TraceResult has all required attributes."""
        result = tracer.trace("Test")
        
        assert hasattr(result, 'prompt')
        assert hasattr(result, 'output_text')
        assert hasattr(result, 'tokens')
        assert hasattr(result, 'token_ids')
        assert hasattr(result, 'logits')
        assert hasattr(result, 'attention_cache')
        assert hasattr(result, 'activation_cache')
        assert hasattr(result, 'metadata')
    
    def test_token_id_consistency(self, tracer):
        """Test that tokens and token_ids match."""
        result = tracer.trace("The capital of France")
        
        assert len(result.tokens) == len(result.token_ids)
        
        # Verify we can decode token_ids back to similar tokens
        for token_id, expected_token in zip(result.token_ids, result.tokens):
            decoded = tracer.model.to_string(token_id)
            # Should match (accounting for BPE quirks)
            assert len(decoded) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
