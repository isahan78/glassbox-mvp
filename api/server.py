"""
GlassBox API - FastAPI server for trace retrieval and generation.

Run with: uvicorn server:app --reload --port 8000
"""

from fastapi import FastAPI, HTTPException, Query, Security, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
from typing import Optional, List
from pathlib import Path
import sys
import os
import re
import time
import uuid
from contextlib import asynccontextmanager
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from glassbox.tracer import ActivationTracer, TracerConfig
from glassbox.serializer import TraceSerializer
from glassbox.decision_analyzer import DecisionAnalyzer
from glassbox.analyzer import AttentionAnalyzer
from glassbox.logging_config import setup_logging, get_logger
from glassbox.cache import get_trace_cache, get_analysis_cache
from glassbox.interventions import ActivationPatcher, InterventionConfig, InterventionType
from glassbox.circuits import CircuitDiscovery
from glassbox.sae import SparseAutoencoder, SAEConfig, SAETrainer, FeatureAnalyzer
from glassbox.feature_discovery import FeatureDiscoveryWorkflow
from glassbox.sae_circuits import SAECircuitDiscovery

# Setup logging
log_format = os.getenv("GLASSBOX_LOG_FORMAT", "simple")  # "simple" or "json"
log_level = os.getenv("GLASSBOX_LOG_LEVEL", "INFO")
logger = setup_logging(level=log_level, format_type=log_format, logger_name="glassbox.api")

# Setup rate limiting
limiter = Limiter(key_func=get_remote_address)


# Pydantic models for API
class TraceConfigRequest(BaseModel):
    """Configuration for trace generation."""
    capture_layers: Optional[List[int]] = None
    max_seq_length: int = Field(default=128, ge=32, le=512)


class TraceRequest(BaseModel):
    """Request to create a new trace."""
    prompt: str = Field(..., min_length=1, max_length=2000)
    config: Optional[TraceConfigRequest] = None


class TraceResponse(BaseModel):
    """Response for trace creation."""
    trace_id: str
    message: str
    url: str


class TraceListItem(BaseModel):
    """Metadata for a single trace in list view."""
    trace_id: str
    timestamp: str
    input_preview: str
    output: str


# API Key Configuration
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


async def verify_api_key(api_key: Optional[str] = Security(api_key_header)):
    """
    Verify API key for protected endpoints.

    If GLASSBOX_API_KEY environment variable is set, authentication is required.
    If not set, authentication is disabled (development mode).

    Args:
        api_key: API key from request header

    Raises:
        HTTPException: If authentication is enabled and key is invalid
    """
    required_key = os.getenv("GLASSBOX_API_KEY")

    # If no API key configured, allow all requests (development mode)
    if not required_key:
        return None

    # If API key is configured, validate it
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Include 'X-API-Key' header in your request.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if api_key != required_key:
        raise HTTPException(
            status_code=403,
            detail="Invalid API key",
        )

    return api_key


# Global components (initialized on startup)
tracer: Optional[ActivationTracer] = None
serializer: Optional[TraceSerializer] = None
decision_analyzer: Optional[DecisionAnalyzer] = None
attention_analyzer: Optional[AttentionAnalyzer] = None
activation_patcher: Optional[ActivationPatcher] = None
circuit_discovery: Optional[CircuitDiscovery] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize components on startup and cleanup on shutdown."""
    global tracer, serializer, decision_analyzer, attention_analyzer, activation_patcher, circuit_discovery
    # Startup
    logger.info("Initializing GlassBox components...")
    model_name = os.getenv("GLASSBOX_MODEL", "gpt2-small")
    logger.info("Loading model", extra={"model": model_name})

    try:
        tracer = ActivationTracer(model_name=model_name)
        serializer = TraceSerializer(output_dir="data/traces")
        decision_analyzer = DecisionAnalyzer(tracer)
        attention_analyzer = AttentionAnalyzer()
        activation_patcher = ActivationPatcher(tracer)
        circuit_discovery = CircuitDiscovery(tracer, threshold=0.1)
        logger.info("GlassBox API ready", extra={
            "model": model_name,
            "components": ["tracer", "serializer", "decision_analyzer", "attention_analyzer",
                          "activation_patcher", "circuit_discovery"]
        })
    except Exception as e:
        logger.error("Failed to initialize GlassBox components", exc_info=True, extra={"model": model_name})
        raise

    yield

    # Shutdown
    logger.info("Shutting down GlassBox API...")


# Initialize FastAPI app
app = FastAPI(
    title="GlassBox Trace API",
    description="API for generating and retrieving LLM interpretability traces",
    version="0.1.0",
    lifespan=lifespan
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure CORS - use environment variable for allowed origins
allowed_origins = os.getenv("GLASSBOX_CORS_ORIGINS", "http://localhost:3000,http://localhost:8501").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Middleware to log all HTTP requests with correlation IDs.

    Adds a unique request_id to each request for tracing across logs.
    """
    # Generate unique request ID
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    # Log incoming request
    start_time = time.time()
    logger.info("Incoming request", extra={
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path,
        "client": request.client.host if request.client else "unknown"
    })

    try:
        # Process request
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Log response
        logger.info("Request completed", extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 2)
        })

        # Add request ID to response headers for client-side tracing
        response.headers["X-Request-ID"] = request_id

        return response

    except Exception as e:
        # Log errors
        duration_ms = (time.time() - start_time) * 1000
        logger.error("Request failed", exc_info=True, extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "duration_ms": round(duration_ms, 2)
        })
        raise


@app.get("/")
@limiter.limit("100/minute")
async def root(request: Request):
    """API root endpoint with basic info."""
    auth_enabled = bool(os.getenv("GLASSBOX_API_KEY"))
    return {
        "message": "GlassBox API v0.1.0",
        "status": "operational",
        "authentication": "enabled" if auth_enabled else "disabled (development mode)",
        "docs": "/docs",
        "version": "0.1.0"
    }


@app.get("/health")
@limiter.limit("100/minute")
async def health_check(request: Request):
    """
    Health check endpoint for monitoring and load balancers.

    Returns simple status to indicate API is responding.
    Does not check model loading or database connectivity.

    Returns:
        Status dictionary with HTTP 200 if healthy
    """
    return {
        "status": "healthy",
        "service": "glassbox-api",
        "version": "0.1.0"
    }


@app.get("/ready")
@limiter.limit("100/minute")
async def readiness_check(request: Request):
    """
    Readiness check endpoint for Kubernetes and orchestration systems.

    Checks if the API is ready to serve requests by verifying:
    - Model is loaded
    - Serializer is initialized
    - Decision analyzer is ready

    Returns:
        Status dictionary with HTTP 200 if ready, 503 if not ready
    """
    checks = {
        "model_loaded": tracer is not None,
        "serializer_ready": serializer is not None,
        "decision_analyzer_ready": decision_analyzer is not None,
        "attention_analyzer_ready": attention_analyzer is not None,
    }

    all_ready = all(checks.values())

    if not all_ready:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "not_ready",
                "checks": checks,
                "message": "API is initializing. Please wait."
            }
        )

    return {
        "status": "ready",
        "checks": checks,
        "service": "glassbox-api",
        "version": "0.1.0"
    }


@app.get("/traces", response_model=List[TraceListItem])
@limiter.limit("100/minute")
async def list_traces(
    request: Request,
    date: Optional[str] = Query(
        None,
        description="Filter by date (YYYY-MM-DD format)",
        regex=r"^\d{4}-\d{2}-\d{2}$"
    ),
    limit: int = Query(
        100,
        ge=1,
        le=500,
        description="Maximum number of traces to return"
    )
):
    """
    List available traces with optional filtering.
    
    Args:
        date: Optional date filter in YYYY-MM-DD format
        limit: Maximum number of results (default: 100, max: 500)
    
    Returns:
        List of trace metadata objects
    """
    try:
        traces = serializer.list_traces(date=date, limit=limit)
        
        return [
            TraceListItem(
                trace_id=t["trace_id"],
                timestamp=t["timestamp"],
                input_preview=t["input_preview"],
                output=t["output"]
            )
            for t in traces
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error listing traces: {str(e)}"
        )


def validate_trace_id(trace_id: str) -> str:
    """
    Validate trace_id format to prevent path traversal attacks.

    Expected format: YYYYMMDD_HHMMSS_xxxxxx (e.g., 20251025_143022_abc123)
    """
    if not re.match(r'^[0-9]{8}_[0-9]{6}_[a-f0-9]{6}$', trace_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid trace_id format. Expected: YYYYMMDD_HHMMSS_xxxxxx"
        )
    return trace_id


@app.get("/trace/{trace_id}")
@limiter.limit("100/minute")
async def get_trace(request: Request, trace_id: str):
    """
    Retrieve full trace JSON by ID.

    Args:
        trace_id: Trace identifier (timestamp_hash format: YYYYMMDD_HHMMSS_xxxxxx)

    Returns:
        Complete trace object with all analysis data
    """
    trace_id = validate_trace_id(trace_id)

    try:
        trace = serializer.load(trace_id)
        return trace
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Trace '{trace_id}' not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error loading trace: {str(e)}"
        )


@app.post("/trace", response_model=TraceResponse)
@limiter.limit("10/minute")
async def create_trace(
    request: Request,
    trace_request: TraceRequest,
    api_key: Optional[str] = Depends(verify_api_key)
):
    """
    Generate a new trace for a given prompt.

    Args:
        trace_request: TraceRequest with prompt and optional config

    Returns:
        TraceResponse with trace_id and retrieval URL
    """
    try:
        # Build config
        if trace_request.config:
            config = TracerConfig(
                capture_layers=trace_request.config.capture_layers,
                max_seq_length=trace_request.config.max_seq_length
            )
        else:
            config = TracerConfig()

        # Run trace
        result = tracer.trace(trace_request.prompt, config)
        
        # Save trace
        filepath = serializer.save(result)
        
        # Extract trace_id from filename
        trace_id = filepath.stem.replace("trace_", "")
        
        return TraceResponse(
            trace_id=trace_id,
            message="Trace generated successfully",
            url=f"/trace/{trace_id}"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating trace: {str(e)}"
        )


@app.get("/stats")
@limiter.limit("100/minute")
async def get_stats(request: Request):
    """
    Get API statistics.

    Returns:
        Statistics about traces and system status
    """
    try:
        # Count total traces
        all_traces = serializer.list_traces(limit=10000)

        # Get date distribution
        from collections import defaultdict
        date_counts = defaultdict(int)
        for trace in all_traces:
            date = trace['timestamp'][:10]
            date_counts[date] += 1

        return {
            "total_traces": len(all_traces),
            "traces_by_date": dict(sorted(date_counts.items())),
            "model": "gpt2-small",
            "api_version": "0.1.0"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving stats: {str(e)}"
        )


@app.get("/cache/stats")
@limiter.limit("100/minute")
async def get_cache_stats(request: Request):
    """
    Get cache performance statistics.

    Returns:
        Cache metrics including hit rates, sizes, and hot traces
    """
    try:
        trace_cache = get_trace_cache()
        analysis_cache = get_analysis_cache()

        return {
            "trace_cache": trace_cache.get_stats(),
            "analysis_cache": analysis_cache.get_stats()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving cache stats: {str(e)}"
        )


@app.post("/cache/clear")
@limiter.limit("5/minute")
async def clear_cache(
    request: Request,
    api_key: Optional[str] = Depends(verify_api_key)
):
    """
    Clear all cache entries (requires authentication).

    Returns:
        Confirmation message with cleared entry counts
    """
    try:
        trace_cache = get_trace_cache()
        analysis_cache = get_analysis_cache()

        # Get stats before clearing
        trace_count = len(trace_cache._cache)
        analysis_count = len(analysis_cache._cache)

        # Clear caches
        trace_cache.clear()
        analysis_cache.clear()

        logger.info("Cache cleared via API", extra={
            "trace_entries_cleared": trace_count,
            "analysis_entries_cleared": analysis_count
        })

        return {
            "message": "Cache cleared successfully",
            "trace_entries_cleared": trace_count,
            "analysis_entries_cleared": analysis_count
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error clearing cache: {str(e)}"
        )


@app.delete("/trace/{trace_id}")
@limiter.limit("20/minute")
async def delete_trace(
    request: Request,
    trace_id: str,
    api_key: Optional[str] = Depends(verify_api_key)
):
    """
    Delete a trace by ID.

    Args:
        trace_id: Trace identifier (timestamp_hash format: YYYYMMDD_HHMMSS_xxxxxx)

    Returns:
        Confirmation message
    """
    trace_id = validate_trace_id(trace_id)

    try:
        # Use serializer's delete method instead of duplicating logic
        success = serializer.delete(trace_id)

        if success:
            return {
                "message": f"Trace {trace_id} deleted successfully"
            }
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Trace '{trace_id}' not found"
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting trace: {str(e)}"
        )


class AnalyzeChoicesRequest(BaseModel):
    """Request to analyze decision choices."""
    prompt: str = Field(..., min_length=1, max_length=2000)
    choices: List[str] = Field(..., min_items=2, max_items=10)


@app.post("/analyze-choices")
@limiter.limit("10/minute")
async def analyze_choices(
    request: Request,
    analyze_request: AnalyzeChoicesRequest,
    api_key: Optional[str] = Depends(verify_api_key)
):
    """
    Analyze probabilities for specific answer choices.

    Args:
        analyze_request: AnalyzeChoicesRequest with prompt and list of choices

    Returns:
        Dictionary with result and probabilities for each choice

    Example:
        POST /analyze-choices
        {
            "prompt": "Q: Approve loan? A:",
            "choices": ["yes", "no"]
        }

        Response:
        {
            "result": {...},
            "probabilities": {"yes": 0.65, "no": 0.35}
        }
    """
    try:
        result, probs = decision_analyzer.analyze_choices(
            analyze_request.prompt,
            analyze_request.choices
        )

        # Save trace
        trace_id = serializer.save(result).stem.replace("trace_", "")

        return {
            "result": {
                "trace_id": trace_id,
                "output_text": result.output_text,
                "prompt": result.prompt,
                "model_name": result.metadata.model_name,
                "timestamp": result.metadata.timestamp
            },
            "probabilities": probs
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing choices: {str(e)}"
        )


class TopTokensRequest(BaseModel):
    """Request to get top-k token predictions."""
    prompt: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(default=10, ge=1, le=50)


@app.post("/top-tokens")
@limiter.limit("10/minute")
async def get_top_tokens_endpoint(
    request: Request,
    tokens_request: TopTokensRequest,
    api_key: Optional[str] = Depends(verify_api_key)
):
    """
    Get top-k most likely next tokens for a prompt.

    Args:
        tokens_request: TopTokensRequest with prompt and top_k

    Returns:
        List of (token, probability) tuples

    Example:
        POST /top-tokens
        {
            "prompt": "The capital of France is",
            "top_k": 5
        }

        Response:
        {
            "top_tokens": [
                [" Paris", 0.92],
                [" paris", 0.03],
                ...
            ]
        }
    """
    try:
        # First trace the prompt
        result = tracer.trace(tokens_request.prompt)

        # Get top tokens
        top_tokens = decision_analyzer.get_top_tokens(result, top_k=tokens_request.top_k)

        # Save trace
        trace_id = serializer.save(result).stem.replace("trace_", "")

        return {
            "trace_id": trace_id,
            "top_tokens": top_tokens
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting top tokens: {str(e)}"
        )


class AnalyzeAttentionRequest(BaseModel):
    """Request to analyze attention patterns for a trace."""
    trace_id: str
    top_n: int = Field(default=10, ge=1, le=50)


@app.post("/analyze")
@limiter.limit("20/minute")
async def analyze_attention_endpoint(
    request: Request,
    attention_request: AnalyzeAttentionRequest,
    api_key: Optional[str] = Depends(verify_api_key)
):
    """
    Analyze attention patterns for a previously generated trace.

    Args:
        attention_request: AnalyzeAttentionRequest with trace_id and top_n

    Returns:
        Attention analysis results with top attention heads

    Example:
        POST /analyze
        {
            "trace_id": "20251014_173045_abc123",
            "top_n": 10
        }
    """
    trace_id = validate_trace_id(attention_request.trace_id)

    try:
        # Load trace
        trace_data = serializer.load(trace_id)

        # Use the attention heads from the stored trace directly
        top_heads_data = trace_data.get('attribution', {}).get('top_attention_heads', [])

        # Limit to requested number
        top_heads = top_heads_data[:attention_request.top_n]

        # Format response
        return {
            "trace_id": trace_id,
            "top_heads": [
                {
                    "layer": head.get("layer"),
                    "head": head.get("head"),
                    "score": head.get("score"),
                    "top_attended_tokens": head.get("top_attended_tokens", [])
                }
                for head in top_heads
            ],
            "num_heads_analyzed": len(top_heads_data),
            "analysis_method": "attention_to_output"
        }
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Trace '{trace_id}' not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing attention: {str(e)}"
        )


# ========================================
# Advanced Mechanistic Interpretability Endpoints
# ========================================

class PatchRequest(BaseModel):
    """Request for activation patching experiment."""
    clean_input: str = Field(..., min_length=1, max_length=2000)
    corrupted_input: str = Field(..., min_length=1, max_length=2000)
    layer: int = Field(..., ge=0, le=31)
    component: str = Field(default="resid", pattern="^(resid|attn|mlp)$")
    intervention_type: str = Field(default="PATCH", pattern="^(PATCH|ZERO_ABLATE|MEAN_ABLATE|NOISE|RESAMPLE)$")
    target_token: Optional[str] = None


@app.post("/patch")
@limiter.limit("10/minute")
async def patch_activation(
    request: Request,
    patch_request: PatchRequest,
    api_key: Optional[str] = Depends(verify_api_key)
):
    """
    Run activation patching experiment.

    Patches activations from clean run into corrupted run to measure causal effect.

    Args:
        patch_request: PatchRequest with clean/corrupted inputs and intervention config

    Returns:
        Patching results with causal metrics

    Example:
        POST /patch
        {
            "clean_input": "The Eiffel Tower is in Paris",
            "corrupted_input": "The Eiffel Tower is in London",
            "layer": 8,
            "component": "resid"
        }

        Response:
        {
            "logit_diff": -2.34,
            "prob_diff": 0.15,
            "kl_divergence": 0.42,
            "intervention_magnitude": 1.23
        }
    """
    try:
        # Map string intervention type to enum
        intervention_type_map = {
            "PATCH": InterventionType.PATCH,
            "ZERO_ABLATE": InterventionType.ZERO_ABLATE,
            "MEAN_ABLATE": InterventionType.MEAN_ABLATE,
            "NOISE": InterventionType.NOISE,
            "RESAMPLE": InterventionType.RESAMPLE
        }

        intervention = InterventionConfig(
            layer=patch_request.layer,
            component=patch_request.component,
            intervention_type=intervention_type_map[patch_request.intervention_type]
        )

        result = activation_patcher.patch_and_run(
            clean_input=patch_request.clean_input,
            corrupted_input=patch_request.corrupted_input,
            intervention=intervention,
            target_token=patch_request.target_token
        )

        return {
            "logit_diff": result.logit_diff,
            "prob_diff": result.prob_diff,
            "kl_divergence": result.kl_divergence,
            "intervention_magnitude": result.intervention_magnitude,
            "clean_output": result.clean_output,
            "intervened_output": result.intervened_output
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error in patching experiment: {str(e)}"
        )


class CausalTraceRequest(BaseModel):
    """Request for causal tracing across layers."""
    clean_input: str = Field(..., min_length=1, max_length=2000)
    corrupted_input: str = Field(..., min_length=1, max_length=2000)
    layers: Optional[List[int]] = None
    components: List[str] = Field(default=["resid"], max_items=3)


@app.post("/causal-trace")
@limiter.limit("5/minute")
async def run_causal_trace(
    request: Request,
    trace_request: CausalTraceRequest,
    api_key: Optional[str] = Depends(verify_api_key)
):
    """
    Run causal tracing across layers.

    Systematically patches each layer to find where information is processed.

    Args:
        trace_request: CausalTraceRequest with inputs and layer configuration

    Returns:
        Dictionary mapping layer names to intervention results

    Example:
        POST /causal-trace
        {
            "clean_input": "The Eiffel Tower is in Paris",
            "corrupted_input": "The Eiffel Tower is in London",
            "layers": [0, 4, 8, 11],
            "components": ["resid"]
        }
    """
    try:
        results = activation_patcher.causal_trace(
            clean_input=trace_request.clean_input,
            corrupted_input=trace_request.corrupted_input,
            layers=trace_request.layers,
            components=trace_request.components
        )

        # Convert results to JSON-serializable format
        return {
            layer_name: {
                "logit_diff": result.logit_diff,
                "prob_diff": result.prob_diff,
                "kl_divergence": result.kl_divergence,
                "intervention_magnitude": result.intervention_magnitude
            }
            for layer_name, result in results.items()
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error in causal tracing: {str(e)}"
        )


class CircuitDiscoveryRequest(BaseModel):
    """Request for circuit discovery."""
    clean_input: str = Field(..., min_length=1, max_length=2000)
    corrupted_input: str = Field(..., min_length=1, max_length=2000)
    task_description: str = Field(..., min_length=1, max_length=200)
    max_components: int = Field(default=10, ge=1, le=50)


@app.post("/discover-circuit")
@limiter.limit("3/minute")
async def discover_circuit(
    request: Request,
    circuit_request: CircuitDiscoveryRequest,
    api_key: Optional[str] = Depends(verify_api_key)
):
    """
    Discover minimal circuit for a task.

    Finds the minimal subgraph of components that implements a behavior.

    Args:
        circuit_request: CircuitDiscoveryRequest with task specification

    Returns:
        Circuit with nodes, edges, and metrics

    Example:
        POST /discover-circuit
        {
            "clean_input": "The Eiffel Tower is in Paris",
            "corrupted_input": "The Eiffel Tower is in London",
            "task_description": "Geographic fact recall",
            "max_components": 10
        }
    """
    try:
        circuit = circuit_discovery.discover_circuit(
            clean_input=circuit_request.clean_input,
            corrupted_input=circuit_request.corrupted_input,
            task_description=circuit_request.task_description,
            max_components=circuit_request.max_components
        )

        # Get total number of layers for compression ratio
        num_total_components = tracer.model.cfg.n_layers * 3  # resid, attn, mlp per layer

        return {
            "task": circuit.task_description,
            "num_components": circuit.get_num_components(),
            "faithfulness_score": circuit.faithfulness_score,
            "compression_ratio": circuit.get_compression_ratio(num_total_components),
            "nodes": [
                {
                    "layer": node.layer,
                    "component": node.component,
                    "head": node.head
                }
                for node in circuit.nodes
            ],
            "visualization": circuit_discovery.visualize_circuit(circuit)
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error in circuit discovery: {str(e)}"
        )


class SAETrainRequest(BaseModel):
    """Request to train SAE on a layer."""
    layer: int = Field(..., ge=0, le=31)
    prompts: List[str] = Field(..., min_items=10, max_items=1000)
    expansion_factor: int = Field(default=8, ge=2, le=16)
    l1_coefficient: float = Field(default=0.001, ge=0.0001, le=0.01)
    num_training_steps: int = Field(default=500, ge=100, le=5000)


@app.post("/train-sae")
@limiter.limit("2/minute")
async def train_sae(
    request: Request,
    sae_request: SAETrainRequest,
    api_key: Optional[str] = Depends(verify_api_key)
):
    """
    Train Sparse Autoencoder on a layer.

    Trains SAE to discover monosemantic features in layer activations.

    Args:
        sae_request: SAETrainRequest with training configuration

    Returns:
        Training results and SAE checkpoint path

    Example:
        POST /train-sae
        {
            "layer": 6,
            "prompts": ["prompt1", "prompt2", ...],
            "expansion_factor": 8,
            "num_training_steps": 500
        }
    """
    try:
        # Initialize workflow
        workflow = FeatureDiscoveryWorkflow(
            model_name=tracer.model_name,
            layer=sae_request.layer
        )

        # Collect training data
        training_data = workflow.collect_training_data(
            sae_request.prompts,
            max_samples=2000
        )

        # Train SAE
        sae, training_stats = workflow.train_sae(
            training_data,
            expansion_factor=sae_request.expansion_factor,
            l1_coefficient=sae_request.l1_coefficient,
            num_steps=sae_request.num_training_steps
        )

        # Save SAE checkpoint
        checkpoint_path = f"data/sae/layer_{sae_request.layer}_checkpoint.pt"
        Path(checkpoint_path).parent.mkdir(parents=True, exist_ok=True)
        trainer = SAETrainer(sae, sae.config)
        trainer.save(checkpoint_path)

        return {
            "message": "SAE training complete",
            "layer": sae_request.layer,
            "checkpoint_path": checkpoint_path,
            "final_loss": training_stats["loss_history"][-1],
            "final_l0": training_stats["l0_history"][-1],
            "variance_explained": training_stats["var_explained_history"][-1],
            "dead_neurons": training_stats["num_dead_neurons"],
            "d_sae": sae.config.d_sae
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error training SAE: {str(e)}"
        )


class SAEFeaturesRequest(BaseModel):
    """Request to discover SAE features."""
    layer: int = Field(..., ge=0, le=31)
    checkpoint_path: str = Field(..., min_length=1)
    prompts: List[str] = Field(..., min_items=5, max_items=500)
    top_k: int = Field(default=20, ge=1, le=100)


@app.post("/sae-features")
@limiter.limit("5/minute")
async def discover_sae_features(
    request: Request,
    features_request: SAEFeaturesRequest,
    api_key: Optional[str] = Depends(verify_api_key)
):
    """
    Discover monosemantic features using trained SAE.

    Analyzes prompts to find which features activate and what they represent.

    Args:
        features_request: SAEFeaturesRequest with checkpoint and prompts

    Returns:
        List of discovered features with descriptions and examples

    Example:
        POST /sae-features
        {
            "layer": 6,
            "checkpoint_path": "data/sae/layer_6_checkpoint.pt",
            "prompts": ["prompt1", "prompt2", ...],
            "top_k": 20
        }
    """
    try:
        # Load SAE checkpoint
        import torch
        checkpoint = torch.load(features_request.checkpoint_path, map_location="cpu")

        # Recreate SAE
        sae = SparseAutoencoder(checkpoint["config"])
        sae.load_state_dict(checkpoint["sae_state_dict"])

        # Initialize analyzer
        analyzer = FeatureAnalyzer(sae, tracer)

        # Collect activations
        analyzer.collect_activations(
            prompts=features_request.prompts,
            layer=features_request.layer,
            max_examples_per_feature=10
        )

        # Get top features
        features = analyzer.get_top_features(
            k=features_request.top_k,
            min_activation_frequency=3
        )

        # Analyze each feature
        feature_results = []
        for feature in features:
            analysis = analyzer.analyze_feature(feature, generate_description=True)
            feature_results.append({
                "feature_idx": feature.feature_idx,
                "activation_frequency": feature.activation_frequency,
                "activation_strength": feature.activation_strength,
                "description": analysis.get("description", "Unknown"),
                "top_examples": [
                    {
                        "token": ex["token"],
                        "prompt": ex["prompt"][:100],
                        "activation": ex["activation"]
                    }
                    for ex in feature.top_activating_examples[:5]
                ],
                "common_tokens": analysis.get("common_tokens", [])
            })

        return {
            "layer": features_request.layer,
            "num_features": len(feature_results),
            "features": feature_results
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error discovering features: {str(e)}"
        )


class FeatureCircuitRequest(BaseModel):
    """Request for feature-based circuit discovery."""
    clean_input: str = Field(..., min_length=1, max_length=2000)
    corrupted_input: str = Field(..., min_length=1, max_length=2000)
    task_description: str = Field(..., min_length=1, max_length=200)
    sae_checkpoints: dict[int, str] = Field(..., min_items=1, max_items=5)  # layer -> checkpoint_path
    max_features_per_layer: int = Field(default=10, ge=1, le=20)


@app.post("/feature-circuit")
@limiter.limit("2/minute")
async def discover_feature_circuit(
    request: Request,
    circuit_request: FeatureCircuitRequest,
    api_key: Optional[str] = Depends(verify_api_key)
):
    """
    Discover circuit based on SAE features.

    More interpretable than raw activation circuits - each node is a monosemantic feature.

    Args:
        circuit_request: FeatureCircuitRequest with SAE checkpoints

    Returns:
        Feature circuit with interpretable nodes

    Example:
        POST /feature-circuit
        {
            "clean_input": "The Eiffel Tower is in Paris",
            "corrupted_input": "The Eiffel Tower is in London",
            "task_description": "Geographic fact recall",
            "sae_checkpoints": {
                "6": "data/sae/layer_6_checkpoint.pt",
                "8": "data/sae/layer_8_checkpoint.pt"
            },
            "max_features_per_layer": 10
        }
    """
    try:
        import torch

        # Load SAEs for each layer
        sae_dict = {}
        for layer_str, checkpoint_path in circuit_request.sae_checkpoints.items():
            layer = int(layer_str)
            checkpoint = torch.load(checkpoint_path, map_location="cpu")
            sae = SparseAutoencoder(checkpoint["config"])
            sae.load_state_dict(checkpoint["sae_state_dict"])
            sae_dict[layer] = sae

        # Initialize feature circuit discovery
        feature_discovery = SAECircuitDiscovery(tracer, sae_dict, threshold=0.1)

        # Discover feature circuit
        feature_circuit = feature_discovery.discover_feature_circuit(
            clean_input=circuit_request.clean_input,
            corrupted_input=circuit_request.corrupted_input,
            task_description=circuit_request.task_description,
            max_features_per_layer=circuit_request.max_features_per_layer
        )

        # Generate explanation
        explanation = feature_discovery.explain_feature_circuit(feature_circuit)

        return {
            "task": feature_circuit["task"],
            "num_features": feature_circuit["num_features"],
            "num_layers": feature_circuit["num_layers"],
            "total_importance": feature_circuit["total_importance"],
            "compression_ratio": feature_circuit["compression_ratio"],
            "features_by_layer": feature_circuit["features_by_layer"],
            "explanation": explanation,
            "visualization": feature_discovery.visualize_feature_flow(feature_circuit)
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error in feature circuit discovery: {str(e)}"
        )


# Example usage and documentation
@app.get("/examples")
@limiter.limit("100/minute")
async def get_examples(request: Request):
    """
    Get example API usage.
    
    Returns:
        Example requests and responses
    """
    return {
        "basic_examples": [
            {
                "description": "Create a new trace",
                "method": "POST",
                "endpoint": "/trace",
                "body": {
                    "prompt": "Should we approve this loan application?",
                    "config": {
                        "capture_layers": [5, 6, 7, 8, 9],
                        "max_seq_length": 128
                    }
                }
            },
            {
                "description": "List all traces",
                "method": "GET",
                "endpoint": "/traces?limit=50"
            },
            {
                "description": "Get specific trace",
                "method": "GET",
                "endpoint": "/trace/20251014_173045_abc123"
            }
        ],
        "advanced_examples": [
            {
                "description": "Run activation patching experiment",
                "method": "POST",
                "endpoint": "/patch",
                "body": {
                    "clean_input": "The Eiffel Tower is in Paris",
                    "corrupted_input": "The Eiffel Tower is in London",
                    "layer": 8,
                    "component": "resid",
                    "intervention_type": "PATCH"
                }
            },
            {
                "description": "Run causal tracing across layers",
                "method": "POST",
                "endpoint": "/causal-trace",
                "body": {
                    "clean_input": "The Eiffel Tower is in Paris",
                    "corrupted_input": "The Eiffel Tower is in London",
                    "layers": [0, 4, 8, 11],
                    "components": ["resid"]
                }
            },
            {
                "description": "Discover minimal circuit for a task",
                "method": "POST",
                "endpoint": "/discover-circuit",
                "body": {
                    "clean_input": "The Eiffel Tower is in Paris",
                    "corrupted_input": "The Eiffel Tower is in London",
                    "task_description": "Geographic fact recall",
                    "max_components": 10
                }
            },
            {
                "description": "Train SAE on a layer",
                "method": "POST",
                "endpoint": "/train-sae",
                "body": {
                    "layer": 6,
                    "prompts": ["The Eiffel Tower is in Paris", "London is in England", "..."],
                    "expansion_factor": 8,
                    "num_training_steps": 500
                }
            },
            {
                "description": "Discover SAE features",
                "method": "POST",
                "endpoint": "/sae-features",
                "body": {
                    "layer": 6,
                    "checkpoint_path": "data/sae/layer_6_checkpoint.pt",
                    "prompts": ["test prompts..."],
                    "top_k": 20
                }
            },
            {
                "description": "Discover feature-based circuit",
                "method": "POST",
                "endpoint": "/feature-circuit",
                "body": {
                    "clean_input": "The Eiffel Tower is in Paris",
                    "corrupted_input": "The Eiffel Tower is in London",
                    "task_description": "Geographic fact recall",
                    "sae_checkpoints": {
                        "6": "data/sae/layer_6_checkpoint.pt",
                        "8": "data/sae/layer_8_checkpoint.pt"
                    },
                    "max_features_per_layer": 10
                }
            }
        ],
        "curl_examples": [
            "# Basic trace",
            "curl -X POST http://localhost:8000/trace -H 'Content-Type: application/json' -d '{\"prompt\": \"Hello world\"}'",
            "",
            "# Activation patching",
            "curl -X POST http://localhost:8000/patch -H 'Content-Type: application/json' -d '{\"clean_input\": \"The Eiffel Tower is in Paris\", \"corrupted_input\": \"The Eiffel Tower is in London\", \"layer\": 8, \"component\": \"resid\"}'",
            "",
            "# Causal tracing",
            "curl -X POST http://localhost:8000/causal-trace -H 'Content-Type: application/json' -d '{\"clean_input\": \"test\", \"corrupted_input\": \"test2\", \"layers\": [0, 4, 8]}'"
        ]
    }


def main():
    """Entry point for console script."""
    import uvicorn
    port = int(os.getenv("GLASSBOX_PORT", "8000"))
    host = os.getenv("GLASSBOX_HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
