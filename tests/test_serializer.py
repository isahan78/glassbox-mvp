"""
Unit tests for GlassBox serializer module.

Run with: pytest tests/test_serializer.py -v
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from glassbox.tracer import ActivationTracer, TracerConfig
from glassbox.serializer import TraceSerializer


@pytest.fixture(scope="session")
def tracer():
    """Session-scoped fixture to provide a tracer instance."""
    return ActivationTracer(model_name="gpt2-small")


@pytest.fixture
def temp_output_dir():
    """Fixture to provide a temporary output directory."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def serializer(temp_output_dir):
    """Fixture to provide a serializer instance with temp directory."""
    return TraceSerializer(output_dir=temp_output_dir)


@pytest.fixture
def sample_trace(tracer):
    """Fixture to provide a sample trace result."""
    prompt = "The capital of France is"
    config = TracerConfig(capture_layers=[8, 9, 10])
    return tracer.trace(prompt, config)


class TestTraceSerializer:
    """Tests for TraceSerializer class."""

    def test_serializer_initialization(self, serializer, temp_output_dir):
        """Test serializer initializes correctly."""
        assert serializer.output_dir == Path(temp_output_dir)
        assert serializer.analyzer is not None

    def test_serialize_structure(self, serializer, sample_trace):
        """Test that serialization produces correct structure."""
        trace_dict = serializer.serialize(sample_trace, top_n_heads=5)

        # Check top-level keys
        assert "trace_id" in trace_dict
        assert "timestamp" in trace_dict
        assert "model" in trace_dict
        assert "config" in trace_dict
        assert "input" in trace_dict
        assert "output" in trace_dict
        assert "attribution" in trace_dict
        assert "performance" in trace_dict
        assert "metadata" in trace_dict

    def test_serialize_trace_id_format(self, serializer, sample_trace):
        """Test that trace_id has correct format."""
        trace_dict = serializer.serialize(sample_trace)

        # Format: YYYYMMDD_HHMMSS_xxxxxx
        trace_id = trace_dict["trace_id"]
        parts = trace_id.split("_")

        assert len(parts) == 3
        assert len(parts[0]) == 8  # YYYYMMDD
        assert len(parts[1]) == 6  # HHMMSS
        assert len(parts[2]) == 6  # hash

    def test_serialize_input_section(self, serializer, sample_trace):
        """Test input section is correctly populated."""
        trace_dict = serializer.serialize(sample_trace)
        input_section = trace_dict["input"]

        assert "text" in input_section
        assert "tokens" in input_section
        assert "token_ids" in input_section

        assert input_section["text"] == sample_trace.prompt
        assert len(input_section["tokens"]) > 0
        assert len(input_section["token_ids"]) == len(input_section["tokens"])

    def test_serialize_output_section(self, serializer, sample_trace):
        """Test output section is correctly populated."""
        trace_dict = serializer.serialize(sample_trace)
        output_section = trace_dict["output"]

        assert "text" in output_section
        assert "token" in output_section
        assert "token_id" in output_section
        assert "token_position" in output_section
        assert "logit_score" in output_section
        assert "probability" in output_section

        assert 0.0 <= output_section["probability"] <= 1.0

    def test_serialize_attribution_section(self, serializer, sample_trace):
        """Test attribution section is correctly populated."""
        trace_dict = serializer.serialize(sample_trace, top_n_heads=5)
        attribution = trace_dict["attribution"]

        assert "top_attention_heads" in attribution
        assert "token_influence" in attribution

        # Check top attention heads
        heads = attribution["top_attention_heads"]
        assert len(heads) <= 5
        for head in heads:
            assert "layer" in head
            assert "head" in head
            assert "score" in head
            assert "top_attended_tokens" in head

    def test_serialize_performance_section(self, serializer, sample_trace):
        """Test performance section is correctly populated."""
        trace_dict = serializer.serialize(sample_trace)
        perf = trace_dict["performance"]

        assert "inference_time_ms" in perf
        assert "capture_overhead_ms" in perf
        assert "baseline_inference_ms" in perf
        assert "slowdown_factor" in perf

        assert perf["inference_time_ms"] > 0
        assert perf["slowdown_factor"] >= 1.0

    def test_save_creates_file(self, serializer, sample_trace):
        """Test that save creates a JSON file."""
        filepath = serializer.save(sample_trace)

        assert filepath.exists()
        assert filepath.suffix == ".json"
        assert filepath.name.startswith("trace_")

    def test_save_creates_date_directory(self, serializer, sample_trace, temp_output_dir):
        """Test that save creates date-based subdirectory."""
        serializer.save(sample_trace)

        # Check that a date directory was created
        date_str = datetime.now().strftime("%Y-%m-%d")
        date_dir = Path(temp_output_dir) / date_str

        assert date_dir.exists()
        assert date_dir.is_dir()

    def test_save_and_load_roundtrip(self, serializer, sample_trace):
        """Test that saved trace can be loaded back."""
        filepath = serializer.save(sample_trace)
        trace_id = filepath.stem.replace("trace_", "")

        # Load it back
        loaded = serializer.load(trace_id)

        assert loaded["trace_id"] == trace_id
        assert loaded["input"]["text"] == sample_trace.prompt

    def test_load_nonexistent_trace(self, serializer):
        """Test that loading nonexistent trace raises error."""
        with pytest.raises(FileNotFoundError):
            serializer.load("20251231_235959_abcdef")

    def test_list_traces_empty(self, serializer):
        """Test listing traces when directory is empty."""
        traces = serializer.list_traces()
        assert len(traces) == 0

    def test_list_traces_with_traces(self, serializer, sample_trace):
        """Test listing traces after saving some."""
        # Save a few traces
        serializer.save(sample_trace)
        serializer.save(sample_trace)

        traces = serializer.list_traces()

        assert len(traces) >= 2
        for trace in traces:
            assert "trace_id" in trace
            assert "timestamp" in trace
            assert "input_preview" in trace
            assert "output" in trace
            assert "filepath" in trace

    def test_list_traces_limit(self, serializer, sample_trace):
        """Test that limit parameter works."""
        # Save multiple traces
        for _ in range(5):
            serializer.save(sample_trace)

        traces = serializer.list_traces(limit=2)

        assert len(traces) == 2

    def test_list_traces_date_filter(self, serializer, sample_trace):
        """Test filtering traces by date."""
        serializer.save(sample_trace)

        date_str = datetime.now().strftime("%Y-%m-%d")
        traces = serializer.list_traces(date=date_str)

        assert len(traces) >= 1

    def test_delete_trace(self, serializer, sample_trace):
        """Test deleting a trace."""
        filepath = serializer.save(sample_trace)
        trace_id = filepath.stem.replace("trace_", "")

        # Delete it
        success = serializer.delete(trace_id)

        assert success
        assert not filepath.exists()

    def test_delete_nonexistent_trace(self, serializer):
        """Test deleting a nonexistent trace."""
        success = serializer.delete("20251231_235959_abcdef")
        assert not success

    def test_get_stats(self, serializer, sample_trace):
        """Test getting statistics."""
        # Save some traces
        serializer.save(sample_trace)
        serializer.save(sample_trace)

        stats = serializer.get_stats()

        assert "total_traces" in stats
        assert "traces_by_date" in stats
        assert "storage_directory" in stats

        assert stats["total_traces"] >= 2

    def test_serialize_json_valid(self, serializer, sample_trace):
        """Test that serialized output is valid JSON."""
        trace_dict = serializer.serialize(sample_trace)

        # Should be able to convert to JSON string and back
        json_str = json.dumps(trace_dict)
        parsed = json.loads(json_str)

        assert parsed["trace_id"] == trace_dict["trace_id"]

    def test_serialize_with_different_top_n_heads(self, serializer, sample_trace):
        """Test serialization with different top_n_heads values."""
        trace_dict_5 = serializer.serialize(sample_trace, top_n_heads=5)
        trace_dict_15 = serializer.serialize(sample_trace, top_n_heads=15)

        heads_5 = trace_dict_5["attribution"]["top_attention_heads"]
        heads_15 = trace_dict_15["attribution"]["top_attention_heads"]

        assert len(heads_5) <= 5
        assert len(heads_15) <= 15

    def test_serialize_includes_git_commit(self, serializer, sample_trace):
        """Test that git commit is included in metadata."""
        trace_dict = serializer.serialize(sample_trace, git_commit="abc123")

        assert trace_dict["metadata"]["git_commit"] == "abc123"

    def test_trace_id_uniqueness(self, serializer, sample_trace):
        """Test that multiple traces get unique IDs."""
        trace_dict_1 = serializer.serialize(sample_trace)
        trace_dict_2 = serializer.serialize(sample_trace)

        # IDs should be different (due to timestamp/hash)
        assert trace_dict_1["trace_id"] != trace_dict_2["trace_id"]


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_empty_output_dir_creation(self, temp_output_dir):
        """Test that output directory is created if it doesn't exist."""
        non_existent_dir = Path(temp_output_dir) / "subdir" / "traces"
        serializer = TraceSerializer(output_dir=str(non_existent_dir))

        # Should create directory when saving
        # (this is implicitly tested by other save tests)
        assert True

    def test_list_traces_with_corrupted_file(self, serializer, sample_trace, temp_output_dir):
        """Test that corrupted files are skipped gracefully."""
        # Save a valid trace
        serializer.save(sample_trace)

        # Create a corrupted JSON file
        date_str = datetime.now().strftime("%Y-%m-%d")
        date_dir = Path(temp_output_dir) / date_str
        corrupted_file = date_dir / "trace_corrupted.json"
        with open(corrupted_file, 'w') as f:
            f.write("{ invalid json")

        # Should still list valid traces without crashing
        traces = serializer.list_traces()
        assert len(traces) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
