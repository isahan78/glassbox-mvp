"""
GlassBox - Interpretable-by-design AI runtime for language models.

This package provides tools for capturing, analyzing, and visualizing
how language models arrive at their outputs.
"""

from glassbox.tracer import ActivationTracer, TracerConfig, TraceResult, TraceMetadata
from glassbox.analyzer import AttentionAnalyzer, HeadScore
from glassbox.serializer import TraceSerializer
from glassbox.decision_analyzer import DecisionAnalyzer
from glassbox.client import GlassBoxClient, AsyncGlassBoxClient, RemoteTraceResult, create_client

__version__ = "0.1.0"
__author__ = "GlassBox Team"
__email__ = "team@glassbox.ai"

__all__ = [
    # Tracer
    "ActivationTracer",
    "TracerConfig",
    "TraceResult",
    "TraceMetadata",
    # Analyzer
    "AttentionAnalyzer",
    "HeadScore",
    # Serializer
    "TraceSerializer",
    # Decision Analyzer
    "DecisionAnalyzer",
    # Remote Client
    "GlassBoxClient",
    "AsyncGlassBoxClient",
    "RemoteTraceResult",
    "create_client",
]
