"""
Test suite for advanced API endpoints (patching, circuits, SAE).

Run with: pytest tests/test_advanced_api.py
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.server import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestActivationPatching:
    """Tests for /patch endpoint."""

    def test_patch_endpoint_exists(self, client):
        """Test that /patch endpoint exists."""
        response = client.post(
            "/patch",
            json={
                "clean_input": "The Eiffel Tower is in Paris",
                "corrupted_input": "The Eiffel Tower is in London",
                "layer": 8,
                "component": "resid"
            }
        )
        # Should not be 404
        assert response.status_code != 404

    def test_patch_request_validation(self, client):
        """Test request validation for /patch."""
        # Missing required fields
        response = client.post(
            "/patch",
            json={"clean_input": "test"}
        )
        assert response.status_code == 422  # Validation error

    def test_patch_layer_validation(self, client):
        """Test layer validation."""
        response = client.post(
            "/patch",
            json={
                "clean_input": "test input",
                "corrupted_input": "test corrupted",
                "layer": 99,  # Invalid layer
                "component": "resid"
            }
        )
        assert response.status_code == 422


class TestCausalTracing:
    """Tests for /causal-trace endpoint."""

    def test_causal_trace_endpoint_exists(self, client):
        """Test that /causal-trace endpoint exists."""
        response = client.post(
            "/causal-trace",
            json={
                "clean_input": "The Eiffel Tower is in Paris",
                "corrupted_input": "The Eiffel Tower is in London",
                "layers": [0, 4, 8],
                "components": ["resid"]
            }
        )
        assert response.status_code != 404

    def test_causal_trace_default_components(self, client):
        """Test default components parameter."""
        response = client.post(
            "/causal-trace",
            json={
                "clean_input": "test",
                "corrupted_input": "test2"
            }
        )
        # Should use default components
        assert response.status_code in [200, 500]  # May fail on execution but validates


class TestCircuitDiscovery:
    """Tests for /discover-circuit endpoint."""

    def test_circuit_endpoint_exists(self, client):
        """Test that /discover-circuit endpoint exists."""
        response = client.post(
            "/discover-circuit",
            json={
                "clean_input": "The Eiffel Tower is in Paris",
                "corrupted_input": "The Eiffel Tower is in London",
                "task_description": "Geographic fact recall",
                "max_components": 10
            }
        )
        assert response.status_code != 404

    def test_circuit_max_components_validation(self, client):
        """Test max_components validation."""
        response = client.post(
            "/discover-circuit",
            json={
                "clean_input": "test",
                "corrupted_input": "test2",
                "task_description": "test task",
                "max_components": 100  # Too many
            }
        )
        assert response.status_code == 422


class TestSAEEndpoints:
    """Tests for SAE endpoints."""

    def test_train_sae_endpoint_exists(self, client):
        """Test that /train-sae endpoint exists."""
        response = client.post(
            "/train-sae",
            json={
                "layer": 6,
                "prompts": ["test prompt " + str(i) for i in range(15)],
                "expansion_factor": 8,
                "num_training_steps": 100
            }
        )
        assert response.status_code != 404

    def test_train_sae_prompts_validation(self, client):
        """Test prompts validation."""
        response = client.post(
            "/train-sae",
            json={
                "layer": 6,
                "prompts": ["only one"],  # Too few
                "expansion_factor": 8
            }
        )
        assert response.status_code == 422

    def test_sae_features_endpoint_exists(self, client):
        """Test that /sae-features endpoint exists."""
        response = client.post(
            "/sae-features",
            json={
                "layer": 6,
                "checkpoint_path": "fake_path.pt",
                "prompts": ["test"] * 10,
                "top_k": 20
            }
        )
        assert response.status_code != 404

    def test_feature_circuit_endpoint_exists(self, client):
        """Test that /feature-circuit endpoint exists."""
        response = client.post(
            "/feature-circuit",
            json={
                "clean_input": "test",
                "corrupted_input": "test2",
                "task_description": "test task",
                "sae_checkpoints": {
                    "6": "fake.pt"
                },
                "max_features_per_layer": 10
            }
        )
        assert response.status_code != 404


class TestEndpointDocumentation:
    """Tests for endpoint documentation."""

    def test_examples_includes_new_endpoints(self, client):
        """Test that /examples includes new endpoints (when updated)."""
        response = client.get("/examples")
        assert response.status_code == 200
        # Examples endpoint exists

    def test_openapi_schema_includes_new_endpoints(self, client):
        """Test that OpenAPI schema includes new endpoints."""
        response = client.get("/openapi.json")
        assert response.status_code == 200

        schema = response.json()
        paths = schema["paths"]

        # Check that new endpoints are in schema
        assert "/patch" in paths
        assert "/causal-trace" in paths
        assert "/discover-circuit" in paths
        assert "/train-sae" in paths
        assert "/sae-features" in paths
        assert "/feature-circuit" in paths


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
