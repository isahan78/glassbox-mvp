"""
GlassBox API - FastAPI server for trace retrieval and generation.

Run with: uvicorn server:app --reload --port 8000
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List
from pathlib import Path
import sys
import os
import re
from contextlib import asynccontextmanager

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from glassbox.tracer import ActivationTracer, TracerConfig
from glassbox.serializer import TraceSerializer
from glassbox.decision_analyzer import DecisionAnalyzer
from glassbox.analyzer import AttentionAnalyzer


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


# Global components (initialized on startup)
tracer: Optional[ActivationTracer] = None
serializer: Optional[TraceSerializer] = None
decision_analyzer: Optional[DecisionAnalyzer] = None
attention_analyzer: Optional[AttentionAnalyzer] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize components on startup and cleanup on shutdown."""
    global tracer, serializer, decision_analyzer, attention_analyzer
    # Startup
    print("Initializing GlassBox components...")
    model_name = os.getenv("GLASSBOX_MODEL", "gpt2-small")
    print(f"Loading model: {model_name}")
    tracer = ActivationTracer(model_name=model_name)
    serializer = TraceSerializer(output_dir="data/traces")
    decision_analyzer = DecisionAnalyzer(tracer)
    attention_analyzer = AttentionAnalyzer(tracer)
    print("GlassBox API ready!")
    yield
    # Shutdown
    print("Shutting down GlassBox API...")


# Initialize FastAPI app
app = FastAPI(
    title="GlassBox Trace API",
    description="API for generating and retrieving LLM interpretability traces",
    version="0.1.0",
    lifespan=lifespan
)

# Configure CORS - use environment variable for allowed origins
allowed_origins = os.getenv("GLASSBOX_CORS_ORIGINS", "http://localhost:3000,http://localhost:8501").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """API health check."""
    return {
        "message": "GlassBox API v0.1.0",
        "status": "operational",
        "model": "gpt2-small",
        "docs": "/docs"
    }


@app.get("/traces", response_model=List[TraceListItem])
async def list_traces(
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
async def get_trace(trace_id: str):
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
async def create_trace(request: TraceRequest):
    """
    Generate a new trace for a given prompt.
    
    Args:
        request: TraceRequest with prompt and optional config
    
    Returns:
        TraceResponse with trace_id and retrieval URL
    """
    try:
        # Build config
        if request.config:
            config = TracerConfig(
                capture_layers=request.config.capture_layers,
                max_seq_length=request.config.max_seq_length
            )
        else:
            config = TracerConfig()
        
        # Run trace
        result = tracer.trace(request.prompt, config)
        
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
async def get_stats():
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


@app.delete("/trace/{trace_id}")
async def delete_trace(trace_id: str):
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
async def analyze_choices(request: AnalyzeChoicesRequest):
    """
    Analyze probabilities for specific answer choices.

    Args:
        request: AnalyzeChoicesRequest with prompt and list of choices

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
            request.prompt,
            request.choices
        )

        # Save trace
        trace_id = serializer.save(result).stem.replace("trace_", "")

        return {
            "result": {
                "trace_id": trace_id,
                "output_text": result.output_text,
                "output_token": result.output_token,
                "output_logprob": result.output_logprob,
                "prompt": result.prompt,
                "model_name": result.model_name,
                "num_layers": result.num_layers,
                "num_heads": result.num_heads,
                "timestamp": result.timestamp
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
async def get_top_tokens_endpoint(request: TopTokensRequest):
    """
    Get top-k most likely next tokens for a prompt.

    Args:
        request: TopTokensRequest with prompt and top_k

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
        result = tracer.trace(request.prompt)

        # Get top tokens
        top_tokens = decision_analyzer.get_top_tokens(result, top_k=request.top_k)

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
async def analyze_attention_endpoint(request: AnalyzeAttentionRequest):
    """
    Analyze attention patterns for a previously generated trace.

    Args:
        request: AnalyzeAttentionRequest with trace_id and top_n

    Returns:
        Attention analysis results with top attention heads

    Example:
        POST /analyze
        {
            "trace_id": "20251014_173045_abc123",
            "top_n": 10
        }
    """
    trace_id = validate_trace_id(request.trace_id)

    try:
        # Load trace
        trace_data = serializer.load(trace_id)

        # Reconstruct TraceResult (simplified - just need the key fields)
        from glassbox.tracer import TraceResult
        result = TraceResult(
            output_text=trace_data['output_text'],
            output_token=trace_data['output_token'],
            output_logprob=trace_data['output_logprob'],
            activations=trace_data['activations'],
            attention_patterns=trace_data['attention_patterns'],
            input_ids=trace_data['input_ids'],
            input_tokens=trace_data['input_tokens']
        )

        # Analyze attention
        head_scores = attention_analyzer.rank_attention_heads(result)
        top_heads = head_scores[:request.top_n]

        # Format response
        return {
            "trace_id": trace_id,
            "top_heads": [
                {
                    "layer": head.layer,
                    "head": head.head,
                    "score": head.score,
                    "pattern": head.pattern,
                    "description": head.description
                }
                for head in top_heads
            ],
            "num_heads_analyzed": len(head_scores),
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


# Example usage and documentation
@app.get("/examples")
async def get_examples():
    """
    Get example API usage.
    
    Returns:
        Example requests and responses
    """
    return {
        "examples": [
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
            },
            {
                "description": "List traces by date",
                "method": "GET",
                "endpoint": "/traces?date=2025-10-14"
            }
        ],
        "curl_examples": [
            "curl -X POST http://localhost:8000/trace -H 'Content-Type: application/json' -d '{\"prompt\": \"Hello world\"}'",
            "curl http://localhost:8000/traces",
            "curl http://localhost:8000/trace/20251014_173045_abc123"
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
