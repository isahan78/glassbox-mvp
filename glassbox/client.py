"""
GlassBox Remote Client

Simple client library for interacting with remote GlassBox API servers.
Useful when running models on cloud infrastructure.
"""

import requests
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import json


@dataclass
class RemoteTraceResult:
    """Result from a remote trace operation."""
    trace_id: str
    output_text: str
    output_token: str
    output_logprob: float
    prompt: str
    model_name: str
    num_layers: int
    num_heads: int
    timestamp: str


class GlassBoxClient:
    """
    Client for interacting with remote GlassBox API servers.

    Example:
        # Connect to cloud instance
        client = GlassBoxClient("http://your-instance-ip:8000")

        # Trace a prompt
        result = client.trace("Q: Approve loan? A:")
        print(f"Prediction: {result.output_text}")

        # Analyze decision choices
        probs = client.analyze_choices(
            "Q: Should we approve this loan? A:",
            ["yes", "no"]
        )
        print(f"P(yes) = {probs['yes']:.2%}")
    """

    def __init__(self, base_url: str, api_key: Optional[str] = None):
        """
        Initialize GlassBox client.

        Args:
            base_url: Base URL of GlassBox API (e.g., "http://instance-ip:8000")
            api_key: Optional API key for authentication
        """
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()

        if api_key:
            self.session.headers['Authorization'] = f'Bearer {api_key}'

        # Test connection
        try:
            response = self.session.get(f"{self.base_url}/")
            response.raise_for_status()
        except requests.RequestException as e:
            raise ConnectionError(f"Could not connect to GlassBox API at {base_url}: {e}")

    def trace(self, prompt: str) -> RemoteTraceResult:
        """
        Trace a single prompt and get model prediction with internals.

        Args:
            prompt: Input prompt to trace

        Returns:
            RemoteTraceResult with trace data

        Raises:
            requests.HTTPError: If API request fails
        """
        response = self.session.post(
            f"{self.base_url}/trace",
            json={"prompt": prompt}
        )
        response.raise_for_status()

        data = response.json()
        return RemoteTraceResult(**data['result'])

    def analyze_choices(
        self,
        prompt: str,
        choices: List[str]
    ) -> Dict[str, float]:
        """
        Analyze probabilities for specific answer choices.

        Args:
            prompt: Input prompt (e.g., "Q: Approve? A:")
            choices: List of possible answers (e.g., ["yes", "no"])

        Returns:
            Dictionary mapping choices to probabilities

        Example:
            probs = client.analyze_choices(
                "Q: Is this safe? A:",
                ["yes", "no"]
            )
            print(f"P(yes) = {probs['yes']:.2%}")
        """
        response = self.session.post(
            f"{self.base_url}/analyze-choices",
            json={"prompt": prompt, "choices": choices}
        )
        response.raise_for_status()

        return response.json()['probabilities']

    def get_top_tokens(
        self,
        prompt: str,
        top_k: int = 10
    ) -> List[Tuple[str, float]]:
        """
        Get top-k most likely next tokens for a prompt.

        Args:
            prompt: Input prompt
            top_k: Number of top tokens to return

        Returns:
            List of (token, probability) tuples
        """
        response = self.session.post(
            f"{self.base_url}/top-tokens",
            json={"prompt": prompt, "top_k": top_k}
        )
        response.raise_for_status()

        return response.json()['top_tokens']

    def get_trace(self, trace_id: str) -> Dict[str, Any]:
        """
        Retrieve a previously saved trace by ID.

        Args:
            trace_id: Trace identifier

        Returns:
            Trace data dictionary
        """
        response = self.session.get(f"{self.base_url}/trace/{trace_id}")
        response.raise_for_status()

        return response.json()

    def analyze_attention(
        self,
        trace_id: str,
        top_n: int = 10
    ) -> Dict[str, Any]:
        """
        Analyze attention patterns for a trace.

        Args:
            trace_id: Trace identifier
            top_n: Number of top attention heads to return

        Returns:
            Attention analysis results
        """
        response = self.session.post(
            f"{self.base_url}/analyze",
            json={"trace_id": trace_id, "top_n": top_n}
        )
        response.raise_for_status()

        return response.json()

    def health_check(self) -> Dict[str, Any]:
        """
        Check API health and get server info.

        Returns:
            Server status information
        """
        response = self.session.get(f"{self.base_url}/")
        response.raise_for_status()

        return response.json()


class AsyncGlassBoxClient:
    """
    Async client for GlassBox API (for high-throughput applications).

    Requires: pip install httpx

    Example:
        import asyncio

        async def main():
            client = AsyncGlassBoxClient("http://your-instance-ip:8000")
            result = await client.trace("Q: Approve? A:")
            print(result.output_text)

        asyncio.run(main())
    """

    def __init__(self, base_url: str, api_key: Optional[str] = None):
        """Initialize async client."""
        try:
            import httpx
        except ImportError:
            raise ImportError(
                "AsyncGlassBoxClient requires httpx. "
                "Install with: pip install httpx"
            )

        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self._client = None

    async def __aenter__(self):
        """Async context manager entry."""
        import httpx

        headers = {}
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'

        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=30.0
        )

        # Test connection
        response = await self._client.get("/")
        response.raise_for_status()

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()

    async def trace(self, prompt: str) -> RemoteTraceResult:
        """Trace a prompt asynchronously."""
        response = await self._client.post(
            "/trace",
            json={"prompt": prompt}
        )
        response.raise_for_status()

        data = response.json()
        return RemoteTraceResult(**data['result'])

    async def analyze_choices(
        self,
        prompt: str,
        choices: List[str]
    ) -> Dict[str, float]:
        """Analyze choices asynchronously."""
        response = await self._client.post(
            "/analyze-choices",
            json={"prompt": prompt, "choices": choices}
        )
        response.raise_for_status()

        return response.json()['probabilities']

    async def get_top_tokens(
        self,
        prompt: str,
        top_k: int = 10
    ) -> List[Tuple[str, float]]:
        """Get top tokens asynchronously."""
        response = await self._client.post(
            "/top-tokens",
            json={"prompt": prompt, "top_k": top_k}
        )
        response.raise_for_status()

        return response.json()['top_tokens']


def create_client(
    base_url: str,
    api_key: Optional[str] = None,
    async_mode: bool = False
) -> GlassBoxClient:
    """
    Factory function to create GlassBox client.

    Args:
        base_url: API server URL
        api_key: Optional API key
        async_mode: If True, return async client

    Returns:
        GlassBoxClient or AsyncGlassBoxClient

    Example:
        # Sync client
        client = create_client("http://instance-ip:8000")

        # Async client
        async_client = create_client(
            "http://instance-ip:8000",
            async_mode=True
        )
    """
    if async_mode:
        return AsyncGlassBoxClient(base_url, api_key)
    else:
        return GlassBoxClient(base_url, api_key)


# Convenience exports
__all__ = [
    'GlassBoxClient',
    'AsyncGlassBoxClient',
    'RemoteTraceResult',
    'create_client'
]
