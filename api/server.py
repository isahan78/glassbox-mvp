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

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from glassbox_tracer import ActivationTracer, TracerConfig
from glassbox_serializer import TraceSerializer


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


# Initialize FastAPI app
app = FastAPI(
    title="GlassBox Trace API",
    description="API for generating and retrieving LLM interpretability traces",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global components (initialized on startup)
tracer: Optional[ActivationTracer] = None
serializer: Optional[TraceSerializer] = None


@app.on_event("startup")
async def startup_event():
    """Initialize components on startup."""
    global tracer, serializer
    print("Initializing GlassBox components...")
    tracer = ActivationTracer(model_name="gpt2-small")
    serializer = TraceSerializer(output_dir="data/traces")
    print("GlassBox API ready!")


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


@app.get("/trace/{trace_id}")
async def get_trace(trace_id: str):
    """
    Retrieve full trace JSON by ID.
    
    Args:
        trace_id: Trace identifier (timestamp_hash format)
    
    Returns:
        Complete trace object with all analysis data
    """
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
        trace_id: Trace identifier
    
    Returns:
        Confirmation message
    """
    try:
        # Find and delete file
        output_dir = Path("data/traces")
        
        for date_dir in output_dir.iterdir():
            if not date_dir.is_dir():
                continue
            
            filepath = date_dir / f"trace_{trace_id}.json"
            if filepath.exists():
                filepath.unlink()
                return {
                    "message": f"Trace {trace_id} deleted successfully"
                }
        
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
