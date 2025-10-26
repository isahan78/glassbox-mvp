"""
GlassBox Serializer - Converts trace results to structured JSON.

This module handles persistence of trace data to JSON files with
a standardized schema for audit trails and compliance.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
import hashlib
import torch

from glassbox.tracer import TraceResult
from glassbox.analyzer import AttentionAnalyzer


class TraceSerializer:
    """Converts analysis results into structured JSON artifacts."""
    
    def __init__(self, output_dir: str = "data/traces"):
        """
        Initialize serializer with output directory.
        
        Args:
            output_dir: Directory to store trace JSON files
        """
        self.output_dir = Path(output_dir)
        self.analyzer = AttentionAnalyzer()
    
    def serialize(
        self,
        trace_result: TraceResult,
        top_n_heads: int = 10,
        git_commit: str = "unknown"
    ) -> Dict[str, Any]:
        """
        Convert TraceResult to structured JSON-serializable dict.
        
        Args:
            trace_result: Result from ActivationTracer
            top_n_heads: Number of top heads to include
            git_commit: Git commit hash for reproducibility
            
        Returns:
            Dictionary conforming to GlassBox trace schema
        """
        # Generate trace ID
        timestamp = datetime.now()
        trace_hash = hashlib.md5(
            f"{trace_result.prompt}{timestamp}".encode()
        ).hexdigest()[:6]
        trace_id = f"{timestamp.strftime('%Y%m%d_%H%M%S')}_{trace_hash}"
        
        # Rank attention heads
        ranked_heads = self.analyzer.rank_attention_heads(
            trace_result.attention_cache,
            trace_result.tokens,
            target_token_idx=-1
        )
        
        # Compute token influence
        token_influence = self.analyzer.compute_token_influence(
            trace_result.attention_cache,
            trace_result.tokens,
            target_token_idx=-1,
            top_n_heads=top_n_heads
        )
        
        # Get output token details
        output_logit = trace_result.logits[0, -1]
        output_probs = torch.softmax(output_logit, dim=0)
        output_token_id = output_logit.argmax().item()
        output_prob = output_probs[output_token_id].item()
        
        # Build JSON structure conforming to spec
        trace_dict = {
            "trace_id": trace_id,
            "timestamp": trace_result.metadata.timestamp,
            "model": trace_result.metadata.model_name,
            "config": {
                "captured_layers": sorted(set(
                    int(k.split("_")[1]) 
                    for k in trace_result.attention_cache.keys()
                )),
                "max_seq_length": 512,
                "attribution_method": "attention_pattern"
            },
            "input": {
                "text": trace_result.prompt,
                "tokens": trace_result.tokens,
                "token_ids": trace_result.token_ids
            },
            "output": {
                "text": trace_result.output_text,
                "token": trace_result.output_text,
                "token_id": output_token_id,
                "token_position": len(trace_result.tokens) - 1,
                "logit_score": float(output_logit[output_token_id].item()),
                "probability": float(output_prob)
            },
            "attribution": {
                "top_attention_heads": [
                    {
                        "layer": head.layer,
                        "head": head.head,
                        "score": float(head.score),
                        "top_attended_tokens": [
                            {
                                "token": token,
                                "weight": float(weight)
                            }
                            for token, weight in head.top_attended_tokens
                        ]
                    }
                    for head in ranked_heads[:top_n_heads]
                ],
                "token_influence": {
                    token: float(score)
                    for token, score in token_influence.items()
                }
            },
            "performance": {
                "inference_time_ms": float(trace_result.metadata.inference_time_ms),
                "capture_overhead_ms": float(trace_result.metadata.capture_overhead_ms),
                "baseline_inference_ms": float(trace_result.metadata.baseline_inference_ms),
                "slowdown_factor": float(trace_result.metadata.slowdown_factor)
            },
            "metadata": {
                "git_commit": git_commit,
                "glassbox_version": trace_result.metadata.glassbox_version,
                "device": trace_result.metadata.device
            }
        }
        
        return trace_dict
    
    def save(
        self,
        trace_result: TraceResult,
        top_n_heads: int = 10,
        git_commit: str = "unknown"
    ) -> Path:
        """
        Serialize and save trace to JSON file.
        
        Args:
            trace_result: Result from ActivationTracer
            top_n_heads: Number of top heads to include
            git_commit: Git commit hash
            
        Returns:
            Path to saved JSON file
        """
        # Serialize to dict
        trace_dict = self.serialize(trace_result, top_n_heads, git_commit)
        
        # Create date-based subdirectory
        date_str = datetime.now().strftime("%Y-%m-%d")
        date_dir = self.output_dir / date_str
        date_dir.mkdir(parents=True, exist_ok=True)
        
        # Save to file
        filename = f"trace_{trace_dict['trace_id']}.json"
        filepath = date_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(trace_dict, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Saved trace to: {filepath}")
        return filepath
    
    def load(self, trace_id: str) -> Dict[str, Any]:
        """
        Load a trace by ID.
        
        Args:
            trace_id: Trace identifier (with or without date prefix)
            
        Returns:
            Trace dictionary
            
        Raises:
            FileNotFoundError: If trace not found
        """
        # Search for file in all date directories
        for date_dir in self.output_dir.iterdir():
            if not date_dir.is_dir():
                continue
            
            filepath = date_dir / f"trace_{trace_id}.json"
            if filepath.exists():
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
        
        raise FileNotFoundError(f"Trace '{trace_id}' not found in {self.output_dir}")
    
    def list_traces(
        self, 
        date: str = None, 
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List available traces with optional filtering.
        
        Args:
            date: Optional date filter (YYYY-MM-DD format)
            limit: Maximum number of traces to return (default: 100)
            
        Returns:
            List of trace metadata dictionaries with keys:
            - trace_id: Unique identifier
            - timestamp: ISO timestamp
            - input_preview: First 100 chars of input
            - output: Model output text
            - filepath: Full path to JSON file
        """
        traces = []
        
        # Create output directory if it doesn't exist
        if not self.output_dir.exists():
            self.output_dir.mkdir(parents=True, exist_ok=True)
            return traces
        
        # Determine which directories to search
        if date:
            dirs = [self.output_dir / date]
        else:
            dirs = sorted(
                [d for d in self.output_dir.iterdir() if d.is_dir()],
                reverse=True
            )
        
        for date_dir in dirs:
            if not date_dir.is_dir():
                continue
            
            # Get all trace files in this directory
            trace_files = sorted(
                date_dir.glob("trace_*.json"),
                reverse=True
            )
            
            for filepath in trace_files:
                if len(traces) >= limit:
                    break
                
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        trace = json.load(f)
                    
                    # Extract preview metadata
                    traces.append({
                        "trace_id": trace["trace_id"],
                        "timestamp": trace["timestamp"],
                        "input_preview": trace["input"]["text"][:100],
                        "output": trace["output"]["text"],
                        "filepath": str(filepath)
                    })
                except Exception as e:
                    print(f"⚠️  Error loading {filepath}: {e}")
                    continue
            
            if len(traces) >= limit:
                break
        
        return traces
    
    def delete(self, trace_id: str) -> bool:
        """
        Delete a trace by ID.
        
        Args:
            trace_id: Trace identifier
            
        Returns:
            True if deleted successfully, False otherwise
        """
        # Search for file
        for date_dir in self.output_dir.iterdir():
            if not date_dir.is_dir():
                continue
            
            filepath = date_dir / f"trace_{trace_id}.json"
            if filepath.exists():
                filepath.unlink()
                print(f"🗑️  Deleted trace: {trace_id}")
                return True
        
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about stored traces.
        
        Returns:
            Dictionary with trace statistics
        """
        all_traces = self.list_traces(limit=10000)
        
        # Count by date
        from collections import defaultdict
        date_counts = defaultdict(int)
        
        for trace in all_traces:
            date = trace['timestamp'][:10]
            date_counts[date] += 1
        
        return {
            "total_traces": len(all_traces),
            "traces_by_date": dict(sorted(date_counts.items())),
            "storage_directory": str(self.output_dir)
        }


# Example usage and testing
if __name__ == "__main__":
    from glassbox.tracer import ActivationTracer, TracerConfig
    
    print("🧠 GlassBox Serializer Example\n")
    print("=" * 60)
    
    # Initialize components
    print("\n1. Initializing components...")
    tracer = ActivationTracer(model_name="gpt2-small")
    serializer = TraceSerializer(output_dir="data/traces")
    
    # Run trace
    print("\n2. Running trace...")
    prompt = "Should we approve this loan application? Credit score: 750"
    config = TracerConfig(capture_layers=list(range(12)))
    result = tracer.trace(prompt, config)
    
    print(f"   Prompt: {prompt}")
    print(f"   Output: {result.output_text}")
    print(f"   Time: {result.metadata.inference_time_ms:.0f}ms")
    
    # Save trace
    print("\n3. Saving trace...")
    filepath = serializer.save(result, top_n_heads=10)
    
    # Extract trace ID
    trace_id = filepath.stem.replace("trace_", "")
    
    # Load it back
    print("\n4. Loading trace back...")
    loaded = serializer.load(trace_id)
    
    print(f"   Trace ID: {loaded['trace_id']}")
    print(f"   Model: {loaded['model']}")
    print(f"   Input tokens: {len(loaded['input']['tokens'])}")
    print(f"   Top heads captured: {len(loaded['attribution']['top_attention_heads'])}")
    
    # Show top head
    top_head = loaded['attribution']['top_attention_heads'][0]
    print(f"\n   Top attention head:")
    print(f"     Layer {top_head['layer']}, Head {top_head['head']}")
    print(f"     Score: {top_head['score']:.3f}")
    print(f"     Top attended tokens:")
    for token_info in top_head['top_attended_tokens'][:3]:
        print(f"       → '{token_info['token']}': {token_info['weight']:.3f}")
    
    # List all traces
    print("\n5. Listing all traces...")
    traces = serializer.list_traces(limit=5)
    print(f"   Found {len(traces)} trace(s):\n")
    
    for i, t in enumerate(traces, 1):
        print(f"   {i}. {t['trace_id']}")
        print(f"      Input: {t['input_preview'][:50]}...")
        print(f"      Output: {t['output']}")
        print()
    
    # Get statistics
    print("\n6. Storage statistics...")
    stats = serializer.get_stats()
    print(f"   Total traces: {stats['total_traces']}")
    print(f"   Storage location: {stats['storage_directory']}")
    
    print("\n" + "=" * 60)
    print("✅ Serializer test complete!\n")
