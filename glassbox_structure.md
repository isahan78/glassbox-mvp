# 📁 GlassBox Project Structure

This document outlines the complete directory structure for the GlassBox MVP.

## Directory Tree

```
glassbox/
├── README.md                    # Main documentation
├── requirements.txt             # Python dependencies
├── setup.py                     # Package installation config
├── .gitignore                   # Git ignore patterns
├── LICENSE                      # MIT License
│
├── glassbox/                    # Core library package
│   ├── __init__.py             # Package initialization
│   ├── tracer.py               # Activation capture (provided)
│   ├── analyzer.py             # Attribution analysis (provided)
│   ├── serializer.py           # JSON generation (provided)
│   └── utils.py                # Helper functions
│
├── dashboard/                   # Streamlit UI
│   ├── app.py                  # Main dashboard (provided)
│   ├── components/             # Reusable UI components
│   │   ├── __init__.py
│   │   ├── trace_browser.py   # Trace list view
│   │   ├── attention_viz.py   # Visualization components
│   │   └── metrics_panel.py   # Performance metrics display
│   └── styles.css              # Custom styling
│
├── api/                         # FastAPI service
│   ├── __init__.py
│   ├── server.py               # REST endpoints (provided)
│   └── models.py               # Pydantic request/response models
│
├── data/                        # Storage directory
│   └── traces/                 # Trace JSON files
│       ├── 2025-10-14/         # Date-based subdirectories
│       │   ├── trace_173045_abc123.json
│       │   └── trace_173102_def456.json
│       └── 2025-10-15/
│
├── notebooks/                   # Jupyter notebooks
│   ├── 01_quickstart.ipynb     # Getting started guide (provided)
│   ├── 02_custom_analysis.ipynb # Advanced analysis examples
│   └── 03_validation_tests.ipynb # Interpretability validation
│
├── tests/                       # Unit tests
│   ├── __init__.py
│   ├── test_tracer.py          # Tracer tests (provided)
│   ├── test_analyzer.py        # Analyzer tests (provided)
│   ├── test_serializer.py      # Serializer tests
│   └── test_api.py             # API endpoint tests
│
├── docs/                        # Documentation
│   ├── ARCHITECTURE.md         # System architecture
│   ├── API_REFERENCE.md        # API documentation
│   ├── VALIDATION.md           # Validation methodology
│   └── images/                 # Diagrams and screenshots
│
└── benchmarks/                  # Performance benchmarks
    ├── run_benchmarks.py       # Benchmark suite
    └── results/                # Benchmark outputs
```

## File Descriptions

### Root Files

**README.md**
- Quick start guide
- Installation instructions
- Feature overview
- Usage examples

**requirements.txt** (provided)
- All Python dependencies
- Pinned versions for reproducibility

**setup.py** (provided)
- Package metadata
- Installation configuration
- Entry points for CLI tools

**.gitignore**
```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/

# Data
data/traces/
*.json

# IDE
.vscode/
.idea/
*.swp

# Notebooks
.ipynb_checkpoints/
```

### Core Library (`glassbox/`)

**`__init__.py`**
```python
"""GlassBox - Interpretable-by-design AI runtime."""

from .tracer import ActivationTracer, TracerConfig, TraceResult
from .analyzer import AttentionAnalyzer, HeadScore
from .serializer import TraceSerializer

__version__ = "0.1.0"
__all__ = [
    "ActivationTracer",
    "TracerConfig",
    "TraceResult",
    "AttentionAnalyzer",
    "HeadScore",
    "TraceSerializer",
]
```

**tracer.py** ✅ (provided)
- `ActivationTracer` class
- `TracerConfig` dataclass
- `TraceResult` dataclass
- Hook management for TransformerLens

**analyzer.py** ✅ (provided)
- `AttentionAnalyzer` class
- `HeadScore` dataclass
- Attention ranking algorithms
- Token influence computation

**serializer.py** ✅ (provided)
- `TraceSerializer` class
- JSON schema generation
- File storage management
- Trace loading/listing

**utils.py**
```python
"""Utility functions for GlassBox."""

import hashlib
from datetime import datetime
from typing import List

def generate_trace_id(prompt: str) -> str:
    """Generate unique trace ID."""
    timestamp = datetime.now()
    trace_hash = hashlib.md5(
        f"{prompt}{timestamp}".encode()
    ).hexdigest()[:6]
    return f"{timestamp.strftime('%Y%m%d_%H%M%S')}_{trace_hash}"

def format_token_display(token: str) -> str:
    """Format token for display (handle BPE artifacts)."""
    return token.replace("Ġ", " ").replace("Ċ", "\n")

def aggregate_bpe_tokens(tokens: List[str]) -> List[str]:
    """Combine BPE subword tokens into full words."""
    words = []
    current = ""
    for tok in tokens:
        if tok.startswith(" "):
            if current:
                words.append(current)
            current = tok.lstrip()
        else:
            current += tok
    if current:
        words.append(current)
    return words
```

### Dashboard (`dashboard/`)

**app.py** ✅ (provided)
- Main Streamlit application
- Page navigation
- Trace creation and browsing
- Visualization rendering

**components/trace_browser.py**
```python
"""Trace browser component."""

import streamlit as st
from glassbox_serializer import TraceSerializer

def render_trace_list(serializer: TraceSerializer, date: str = None):
    """Render list of traces with filtering."""
    traces = serializer.list_traces(date=date)
    
    for trace in traces:
        with st.expander(f"{trace['trace_id']}: {trace['input_preview'][:50]}"):
            st.write(f"Output: {trace['output']}")
            if st.button("View Details", key=trace['trace_id']):
                return trace['trace_id']
    return None
```

**components/attention_viz.py**
```python
"""Attention visualization components."""

import plotly.graph_objects as go
import streamlit as st

def render_attention_heatmap(attention_matrix, tokens):
    """Render attention pattern as heatmap."""
    fig = go.Figure(data=go.Heatmap(
        z=attention_matrix,
        x=tokens,
        y=tokens,
        colorscale='Reds'
    ))
    st.plotly_chart(fig)

def render_head_ranking(heads_df):
    """Render attention head ranking chart."""
    import plotly.express as px
    fig = px.bar(heads_df, x='score', y='head', orientation='h')
    st.plotly_chart(fig)
```

### API (`api/`)

**server.py** ✅ (provided)
- FastAPI application
- REST endpoints
- Request/response models
- Error handling

**models.py**
```python
"""Pydantic models for API."""

from pydantic import BaseModel, Field
from typing import Optional, List

class TraceCreateRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    capture_layers: Optional[List[int]] = None
    max_seq_length: int = Field(128, ge=32, le=512)

class TraceResponse(BaseModel):
    trace_id: str
    url: str
    message: str
```

### Tests (`tests/`)

**test_tracer.py** ✅ (provided)
- Tracer initialization tests
- Configuration tests
- Capture functionality tests
- Performance tests

**test_analyzer.py** ✅ (provided)
- Head ranking tests
- Token influence tests
- Edge case tests
- Integration tests

**test_serializer.py**
```python
"""Tests for serializer module."""

import pytest
from glassbox_serializer import TraceSerializer
from glassbox_tracer import ActivationTracer

def test_save_and_load():
    tracer = ActivationTracer()
    serializer = TraceSerializer()
    
    result = tracer.trace("Test")
    filepath = serializer.save(result)
    
    trace_id = filepath.stem.replace("trace_", "")
    loaded = serializer.load(trace_id)
    
    assert loaded['input']['text'] == "Test"
```

### Notebooks (`notebooks/`)

**01_quickstart.ipynb** ✅ (provided)
- Installation verification
- Basic usage examples
- End-to-end workflow
- Visualization examples

**02_custom_analysis.ipynb**
- Custom attribution methods
- Layer-specific analysis
- Multi-prompt comparisons
- Advanced visualization

**03_validation_tests.ipynb**
- Indirect Object Identification
- Positional attention patterns
- Semantic resolution tests
- Known circuit validation

### Documentation (`docs/`)

**ARCHITECTURE.md**
- System design overview
- Component interactions
- Data flow diagrams
- Technology stack

**API_REFERENCE.md**
- Complete API documentation
- Endpoint specifications
- Request/response examples
- Authentication (future)

**VALIDATION.md**
- Interpretability validation methodology
- Test case descriptions
- Results and analysis
- Limitations discussion

## Setup Instructions

### 1. Create Directory Structure

```bash
mkdir -p glassbox/{glassbox,dashboard/components,api,data/traces,notebooks,tests,docs,benchmarks}
cd glassbox
```

### 2. Create Files

Copy the provided artifacts into their respective locations:

```bash
# Core library
cp tracer.py glassbox/
cp analyzer.py glassbox/
cp serializer.py glassbox/

# Dashboard
cp dashboard_app.py dashboard/app.py

# API
cp api_server.py api/server.py

# Tests
cp test_tracer.py tests/
cp test_analyzer.py tests/

# Notebooks
cp quickstart.ipynb notebooks/01_quickstart.ipynb

# Root files
cp requirements.txt .
cp setup.py .
```

### 3. Initialize Git

```bash
git init
echo "__pycache__/
*.pyc
venv/
data/traces/
.ipynb_checkpoints/" > .gitignore
git add .
git commit -m "Initial GlassBox MVP implementation"
```

### 4. Install Package

```bash
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

### 5. Verify Installation

```bash
# Run tests
pytest tests/ -v

# Start dashboard
streamlit run dashboard/app.py

# Start API
uvicorn api.server:app --reload
```

## Next Steps

1. **Create remaining files**:
   - Component modules in `dashboard/components/`
   - Additional notebooks
   - Documentation files

2. **Add example traces**:
   ```bash
   python -c "from glassbox_tracer import ActivationTracer; \
              from glassbox_serializer import TraceSerializer; \
              t = ActivationTracer(); \
              s = TraceSerializer(); \
              s.save(t.trace('Hello world'))"
   ```

3. **Run validation tests**:
   - Execute `03_validation_tests.ipynb`
   - Verify IOI, positional, and semantic patterns

4. **Deploy locally**:
   - Launch dashboard and API
   - Test end-to-end workflow
   - Generate sample traces

## Development Workflow

```bash
# 1. Make changes to code
vim glassbox/tracer.py

# 2. Run tests
pytest tests/ -v

# 3. Format code
black glassbox/ dashboard/ api/ tests/

# 4. Type check
mypy glassbox/

# 5. Test in notebook
jupyter notebook notebooks/01_quickstart.ipynb

# 6. Commit changes
git add .
git commit -m "Feature: Add X"
```

---

**🎉 Your GlassBox MVP is ready to build!**
