"""
GlassBox Dashboard - Interactive Streamlit interface for trace exploration.

Run with: streamlit run app.py
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from pathlib import Path
import json
from datetime import datetime
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from glassbox.tracer import ActivationTracer, TracerConfig
from glassbox.serializer import TraceSerializer


# Page config
st.set_page_config(
    page_title="GlassBox Dashboard",
    page_icon="🧠",
    layout="wide"
)

# Initialize components
@st.cache_resource
def get_tracer():
    """Initialize tracer (cached)."""
    return ActivationTracer(model_name="gpt2-medium")

@st.cache_resource
def get_serializer():
    """Initialize serializer (cached)."""
    return TraceSerializer(output_dir="data/traces")


def main():
    st.title("🧠 GlassBox Dashboard")
    st.markdown("*Interpretable-by-design AI runtime for language models*")
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Select View",
        ["🔍 New Trace", "📚 Trace Browser", "ℹ️ About"]
    )
    
    if page == "🔍 New Trace":
        show_new_trace_page()
    elif page == "📚 Trace Browser":
        show_trace_browser_page()
    else:
        show_about_page()


def show_new_trace_page():
    """Page for creating new traces."""
    st.header("Create New Trace")
    
    # Input form
    with st.form("trace_form"):
        prompt = st.text_area(
            "Enter prompt to trace:",
            value="Should we approve this loan application?",
            height=100
        )
        
        col1, col2 = st.columns(2)
        with col1:
            capture_all = st.checkbox("Capture all layers", value=True)
            if not capture_all:
                layer_range = st.slider(
                    "Layer range",
                    0, 11, (5, 9)
                )
        
        with col2:
            max_length = st.number_input(
                "Max sequence length",
                min_value=32,
                max_value=512,
                value=128
            )
        
        submit = st.form_submit_button("🚀 Generate Trace", type="primary")
    
    if submit and prompt:
        with st.spinner("Running inference and capturing activations..."):
            # Configure
            if capture_all:
                config = TracerConfig(max_seq_length=max_length)
            else:
                config = TracerConfig(
                    capture_layers=list(range(layer_range[0], layer_range[1] + 1)),
                    max_seq_length=max_length
                )
            
            # Trace
            tracer = get_tracer()
            result = tracer.trace(prompt, config)
            
            # Save
            serializer = get_serializer()
            filepath = serializer.save(result)
            
            st.success(f"✅ Trace generated successfully!")
            
            # Display results
            display_trace_results(result, serializer.serialize(result))


def show_trace_browser_page():
    """Page for browsing existing traces."""
    st.header("Trace Browser")
    
    serializer = get_serializer()
    
    # Filters
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        date_filter = st.date_input("Filter by date", value=None)
    with col2:
        search = st.text_input("Search in prompts")
    with col3:
        limit = st.number_input("Limit", 10, 100, 50)
    
    # Get traces
    date_str = date_filter.strftime("%Y-%m-%d") if date_filter else None
    traces = serializer.list_traces(date=date_str, limit=limit)
    
    # Apply search filter
    if search:
        traces = [
            t for t in traces 
            if search.lower() in t['input_preview'].lower()
        ]
    
    if not traces:
        st.info("No traces found. Create your first trace in the '🔍 New Trace' tab!")
        return
    
    # Display trace list
    st.subheader(f"Found {len(traces)} trace(s)")
    
    for trace_meta in traces:
        with st.expander(
            f"**{trace_meta['trace_id']}** - {trace_meta['input_preview'][:60]}..."
        ):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.text_area(
                    "Input",
                    trace_meta['input_preview'],
                    height=80,
                    disabled=True,
                    key=f"input_{trace_meta['trace_id']}"
                )
            
            with col2:
                st.metric("Output", trace_meta['output'])
                st.caption(f"Time: {trace_meta['timestamp']}")
            
            if st.button("View Full Analysis", key=f"btn_{trace_meta['trace_id']}"):
                # Load full trace
                full_trace = serializer.load(trace_meta['trace_id'])
                display_full_trace(full_trace)


def display_trace_results(result, trace_dict):
    """Display analysis results for a new trace."""
    
    # Overview metrics
    st.subheader("📊 Trace Overview")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Output Token", result.output_text)
    with col2:
        st.metric("Confidence", f"{trace_dict['output']['probability']:.1%}")
    with col3:
        st.metric("Inference Time", f"{result.metadata.inference_time_ms:.0f}ms")
    with col4:
        st.metric("Slowdown", f"{result.metadata.slowdown_factor:.1f}x")
    
    # Input/Output
    st.subheader("💬 Input → Output")
    col1, col2 = st.columns(2)
    with col1:
        st.text_area("Input", result.prompt, height=100, disabled=True)
    with col2:
        st.text_area("Output", result.output_text, height=100, disabled=True)
    
    # Display full analysis
    display_full_trace(trace_dict)


def display_full_trace(trace_dict):
    """Display complete trace analysis."""
    
    # Top Attention Heads
    st.subheader("🎯 Top Contributing Attention Heads")
    
    heads_data = []
    for head in trace_dict['attribution']['top_attention_heads']:
        heads_data.append({
            'Head': f"Layer {head['layer']}, Head {head['head']}",
            'Layer': head['layer'],
            'Head ID': head['head'],
            'Score': head['score']
        })
    
    heads_df = pd.DataFrame(heads_data)
    
    # Bar chart
    fig = px.bar(
        heads_df,
        x='Score',
        y='Head',
        orientation='h',
        title='Attention Head Contribution Scores',
        color='Score',
        color_continuous_scale='Reds'
    )
    fig.update_layout(
        yaxis={'categoryorder': 'total ascending'},
        height=400
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Detailed head analysis
    st.subheader("🔍 Detailed Head Analysis")
    selected_head_idx = st.selectbox(
        "Select head to examine",
        range(len(trace_dict['attribution']['top_attention_heads'])),
        format_func=lambda i: f"Layer {trace_dict['attribution']['top_attention_heads'][i]['layer']}, "
                              f"Head {trace_dict['attribution']['top_attention_heads'][i]['head']} "
                              f"(score: {trace_dict['attribution']['top_attention_heads'][i]['score']:.3f})"
    )
    
    selected_head = trace_dict['attribution']['top_attention_heads'][selected_head_idx]
    
    st.markdown(f"**Layer {selected_head['layer']}, Head {selected_head['head']}** - Score: `{selected_head['score']:.3f}`")
    
    # Show top attended tokens
    attended_tokens = selected_head['top_attended_tokens']
    if attended_tokens:
        st.markdown("**Top attended tokens:**")
        for token_info in attended_tokens:
            token = token_info['token']
            weight = token_info['weight']
            bar_length = int(weight * 30)
            st.markdown(f"  `{token:20s}` {'█' * bar_length} {weight:.3f}")
    
    # Token Influence Heatmap
    st.subheader("🌡️ Token-Level Influence")
    
    token_influence = trace_dict['attribution']['token_influence']
    
    if token_influence:
        # Create sorted data for visualization
        sorted_tokens = sorted(
            token_influence.items(),
            key=lambda x: x[1],
            reverse=True
        )[:15]  # Top 15 tokens
        
        tokens, scores = zip(*sorted_tokens)
        
        # Bar chart
        influence_df = pd.DataFrame({
            'Token': tokens,
            'Influence': scores
        })
        
        fig = px.bar(
            influence_df,
            x='Influence',
            y='Token',
            orientation='h',
            title='Token Influence on Output',
            color='Influence',
            color_continuous_scale='Blues'
        )
        fig.update_layout(
            yaxis={'categoryorder': 'total ascending'},
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Heatmap visualization
        st.markdown("**Influence Heatmap**")
        
        # Prepare data for heatmap
        influence_values = [token_influence.get(t, 0) for t in trace_dict['input']['tokens']]
        
        fig = go.Figure(data=go.Heatmap(
            z=[influence_values],
            x=trace_dict['input']['tokens'],
            y=['Output'],
            colorscale='Reds',
            text=[[f"{v:.2f}" for v in influence_values]],
            texttemplate='%{text}',
            textfont={"size": 10},
            hoverongaps=False
        ))
        
        fig.update_layout(
            title='Token Influence Across Input Sequence',
            height=200,
            xaxis_title='Input Tokens',
            yaxis_title=''
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Performance Metrics
    st.subheader("⚡ Performance Metrics")
    
    perf = trace_dict['performance']
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Time", f"{perf['inference_time_ms']:.0f}ms")
    with col2:
        st.metric("Baseline Time", f"{perf['baseline_inference_ms']:.0f}ms")
    with col3:
        st.metric("Capture Overhead", f"{perf['capture_overhead_ms']:.0f}ms")
    with col4:
        st.metric("Slowdown Factor", f"{perf['slowdown_factor']:.2f}x")
    
    # Raw data
    with st.expander("📄 View Raw JSON"):
        st.json(trace_dict)


def show_about_page():
    """About page with system information."""
    st.header("About GlassBox")
    
    st.markdown("""
    ## 🧠 What is GlassBox?
    
    GlassBox is an **interpretable-by-design AI runtime** that captures and visualizes 
    how language models arrive at their outputs.
    
    ### Key Features
    
    - **🔍 Attention Capture**: Records internal attention patterns during inference
    - **📊 Head Ranking**: Identifies which attention heads contribute most to outputs
    - **🎯 Token Attribution**: Shows which input tokens influenced the output
    - **📝 Audit Trails**: Generates structured JSON traces for compliance
    - **📈 Interactive Viz**: Explore model decisions through visualizations
    
    ### How It Works
    
    1. **Intercept**: Hook into transformer layers during forward pass
    2. **Capture**: Store attention weights and activation patterns
    3. **Analyze**: Rank attention heads by contribution scores
    4. **Visualize**: Present findings through interactive dashboard
    
    ### Current Model
    
    - **Model**: GPT-2 Small (124M parameters)
    - **Architecture**: 12 layers, 12 attention heads per layer
    - **Context**: Up to 512 tokens
    
    ### Attribution Method
    
    This MVP uses **attention pattern analysis**:
    - Computes mean attention weight from output token to input tokens
    - Ranks heads by aggregated attention scores
    - Aggregates across top heads for token-level influence
    
    ⚠️ **Important**: Attention scores show correlation, not proven causation.
    High attention suggests potential influence but doesn't guarantee causal impact.
    
    ### Use Cases
    
    - **AI Safety Research**: Study model circuits and failure modes
    - **Enterprise ML**: Generate audit trails for regulated deployments
    - **Debugging**: Trace unexpected model behaviors to input features
    
    ### Limitations
    
    - Only supports GPT-2 architecture
    - Limited to 512 tokens
    - Attention ≠ causation (causal validation coming in v0.2)
    - Requires ML expertise to interpret results
    
    ### Version
    
    **GlassBox v0.1.0 MVP**
    
    Built with TransformerLens, Streamlit, and Plotly
    """)
    
    st.divider()
    
    st.subheader("📚 Resources")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **Documentation**
        - [Architecture Overview](#)
        - [API Reference](#)
        - [Validation Tests](#)
        """)
    
    with col2:
        st.markdown("""
        **Research**
        - [Transformer Circuits](https://transformer-circuits.pub)
        - [TransformerLens](https://transformerlens.org)
        - [Mechanistic Interpretability](https://distill.pub)
        """)


if __name__ == "__main__":
    main()
