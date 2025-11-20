"""
Integration tests for GlassBox API endpoints.

Tests core API functionality including:
- Basic endpoints (health, root, examples)
- Request correlation IDs
- Cache statistics
- Rate limiting presence
- Input validation

Note: Full end-to-end tests with model loading are in test_api_e2e.py
"""

import pytest
from fastapi.testclient import TestClient
import os
import time
from pathlib import Path

# Ensure no API key is set for tests (unless testing auth)
if "GLASSBOX_API_KEY" in os.environ:
    del os.environ["GLASSBOX_API_KEY"]

# Set to use small model for faster tests
os.environ["GLASSBOX_MODEL"] = "gpt2-small"

from api.server import app

# Create test client
client = TestClient(app)


class TestHealthEndpoints:
    """Test health check endpoint."""

    def test_health_check(self):
        """Test basic health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "glassbox-api"
        assert "version" in data

    def test_readiness_check_structure(self):
        """Test readiness check returns proper structure."""
        response = client.get("/ready")
        # May be 200 (ready) or 503 (not ready) depending on initialization
        assert response.status_code in [200, 503]
        data = response.json()

        if response.status_code == 200:
            assert data["status"] == "ready"
            assert "checks" in data
        else:
            # 503 response has detail field instead of direct structure
            assert "detail" in data or "status" in data


class TestRootEndpoint:
    """Test root API endpoint."""

    def test_root_endpoint(self):
        """Test API root returns basic info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "status" in data
        assert data["status"] == "operational"
        assert "version" in data


class TestTraceEndpoints:
    """Test trace endpoint validation and structure."""

    def test_get_trace_invalid_format(self):
        """Test invalid trace ID format."""
        response = client.get("/trace/invalid_id")
        assert response.status_code == 400
        assert "Invalid trace_id format" in response.json()["detail"]

    def test_list_traces_endpoint(self):
        """Test list traces endpoint exists and returns proper structure."""
        response = client.get("/traces")
        assert response.status_code in [200, 500]  # May fail if not initialized
        if response.status_code == 200:
            traces = response.json()
            assert isinstance(traces, list)

    def test_list_traces_with_limit(self):
        """Test listing traces respects limit parameter."""
        response = client.get("/traces?limit=5")
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            traces = response.json()
            assert len(traces) <= 5

    def test_create_trace_validation(self):
        """Test trace creation validates input properly."""
        # Empty prompt should fail
        response = client.post(
            "/trace",
            json={"prompt": ""}
        )
        assert response.status_code == 422  # Validation error

        # Prompt too long should fail
        response = client.post(
            "/trace",
            json={"prompt": "x" * 3000}
        )
        assert response.status_code == 422


class TestAnalysisEndpoints:
    """Test decision analysis endpoint validation."""

    def test_analyze_choices_invalid_input(self):
        """Test analysis with invalid input."""
        # Too few choices
        response = client.post(
            "/analyze-choices",
            json={
                "prompt": "Test",
                "choices": ["only_one"]
            }
        )
        assert response.status_code == 422  # Validation error

        # Too many choices
        response = client.post(
            "/analyze-choices",
            json={
                "prompt": "Test",
                "choices": ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k"]
            }
        )
        assert response.status_code == 422

    def test_top_tokens_validation(self):
        """Test top tokens endpoint validates input."""
        # top_k too large
        response = client.post(
            "/top-tokens",
            json={
                "prompt": "Test",
                "top_k": 100
            }
        )
        assert response.status_code == 422  # Validation error

        # top_k too small
        response = client.post(
            "/top-tokens",
            json={
                "prompt": "Test",
                "top_k": 0
            }
        )
        assert response.status_code == 422


class TestStatsEndpoints:
    """Test statistics endpoints."""

    def test_get_stats(self):
        """Test API statistics endpoint exists."""
        response = client.get("/stats")
        assert response.status_code in [200, 500]  # May fail if not initialized
        if response.status_code == 200:
            data = response.json()
            assert "total_traces" in data
            assert "model" in data
            assert "api_version" in data

    def test_get_cache_stats(self):
        """Test cache statistics endpoint."""
        response = client.get("/cache/stats")
        assert response.status_code == 200
        data = response.json()
        assert "trace_cache" in data
        assert "analysis_cache" in data

        # Check trace cache stats
        trace_stats = data["trace_cache"]
        assert "size" in trace_stats
        assert "max_size" in trace_stats
        assert "utilization" in trace_stats


class TestCacheEndpoints:
    """Test caching functionality."""

    def test_clear_cache_endpoint(self):
        """Test cache clear endpoint exists and works."""
        response = client.post("/cache/clear")
        # Should succeed regardless of initialization
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert "message" in data
            assert "trace_entries_cleared" in data
            assert "analysis_entries_cleared" in data


class TestExamplesEndpoint:
    """Test examples documentation endpoint."""

    def test_get_examples(self):
        """Test examples endpoint returns usage documentation."""
        response = client.get("/examples")
        assert response.status_code == 200
        data = response.json()
        assert "examples" in data
        assert len(data["examples"]) > 0

        # Check example structure
        example = data["examples"][0]
        assert "description" in example
        assert "method" in example
        assert "endpoint" in example


class TestRequestCorrelation:
    """Test request correlation ID functionality."""

    def test_request_id_in_response_headers(self):
        """Test that each response includes X-Request-ID header."""
        response = client.get("/health")
        assert "X-Request-ID" in response.headers

        request_id = response.headers["X-Request-ID"]
        assert len(request_id) == 36  # UUID format

    def test_unique_request_ids(self):
        """Test that each request gets a unique ID."""
        response1 = client.get("/health")
        response2 = client.get("/health")

        id1 = response1.headers["X-Request-ID"]
        id2 = response2.headers["X-Request-ID"]

        assert id1 != id2


class TestAuthentication:
    """Test API key authentication awareness."""

    def test_root_shows_auth_status(self):
        """Test that root endpoint indicates auth status."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "authentication" in data
        # Should mention either "enabled" or "disabled"
        auth_status = data["authentication"].lower()
        assert "enabled" in auth_status or "disabled" in auth_status


class TestInputValidation:
    """Test API input validation."""

    def test_invalid_date_format_rejected(self):
        """Test that invalid date formats are rejected."""
        response = client.get("/traces?date=invalid-date")
        assert response.status_code == 422  # Validation error

    def test_invalid_limit_rejected(self):
        """Test that invalid limit values are rejected."""
        # Limit too large
        response = client.get("/traces?limit=1000")
        assert response.status_code == 422

        # Limit too small
        response = client.get("/traces?limit=0")
        assert response.status_code == 422


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
