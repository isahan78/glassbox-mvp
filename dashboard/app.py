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
from glassbox.analyzer import AttentionAnalyzer
from glassbox.decision_analyzer import DecisionAnalyzer
from glassbox.interventions import ActivationPatcher, InterventionConfig, InterventionType
from glassbox.circuits import CircuitDiscovery
from glassbox.sae import SparseAutoencoder, SAEConfig, SAETrainer, FeatureAnalyzer
from glassbox.feature_discovery import FeatureDiscoveryWorkflow
from glassbox.sae_circuits import SAECircuitDiscovery
from glassbox.visualizations import (
    CircuitVisualizer,
    CausalFlowVisualizer,
    SAEFeatureVisualizer,
    ActivationSpaceVisualizer,
    AttentionVisualizer
)


# Helper function to display special characters
def format_output_token(token: str) -> str:
    """Format output token to show special characters clearly."""
    if not token:
        return "[EMPTY]"
    elif token == "\n":
        return "\\n (newline)"
    elif token == "\t":
        return "\\t (tab)"
    elif token == " ":
        return "[SPACE]"
    elif token.strip() == "":
        return f"[WHITESPACE: {repr(token)}]"
    else:
        return token


# Page config
st.set_page_config(
    page_title="GlassBox Dashboard",
    page_icon="🧠",
    layout="wide"
)

# Available models configuration
AVAILABLE_MODELS = {
    "GPT-2 Small (124M)": {
        "name": "gpt2-small",
        "size": "124M",
        "layers": 12,
        "heads": 12,
        "memory": "~2 GB",
        "speed": "Fast"
    },
    "GPT-2 Medium (355M)": {
        "name": "gpt2-medium",
        "size": "355M",
        "layers": 24,
        "heads": 16,
        "memory": "~3 GB",
        "speed": "Medium"
    },
    "GPT-2 Large (774M)": {
        "name": "gpt2-large",
        "size": "774M",
        "layers": 36,
        "heads": 20,
        "memory": "~5 GB",
        "speed": "Slower"
    },
    "GPT-2 XL (1.5B)": {
        "name": "gpt2-xl",
        "size": "1.5B",
        "layers": 48,
        "heads": 25,
        "memory": "~6 GB",
        "speed": "Slow"
    },
    "Llama 2 7B": {
        "name": "meta-llama/Llama-2-7b-hf",
        "size": "7B",
        "layers": 32,
        "heads": 32,
        "memory": "~14 GB",
        "speed": "Slow",
        "note": "Requires HuggingFace login"
    },
    "Llama 2 13B": {
        "name": "meta-llama/Llama-2-13b-hf",
        "size": "13B",
        "layers": 40,
        "heads": 40,
        "memory": "~26 GB",
        "speed": "Very Slow",
        "note": "Requires HuggingFace login"
    },
}

# Initialize components
@st.cache_resource
def get_tracer(model_name: str = "gpt2-medium"):
    """Initialize tracer (cached by model name)."""
    return ActivationTracer(model_name=model_name)

@st.cache_resource
def get_serializer():
    """Initialize serializer (cached)."""
    return TraceSerializer(output_dir="data/traces")

@st.cache_resource
def get_analyzer(model_name: str = "gpt2-medium"):
    """Initialize decision analyzer (cached by model name)."""
    tracer = get_tracer(model_name)
    return DecisionAnalyzer(tracer)


def get_selected_model():
    """Get the currently selected model name from session state."""
    if "selected_model" not in st.session_state:
        st.session_state.selected_model = "GPT-2 Medium (355M)"
    return AVAILABLE_MODELS[st.session_state.selected_model]["name"]


def get_model_max_layer():
    """Get the maximum layer index for the selected model."""
    if "selected_model" not in st.session_state:
        st.session_state.selected_model = "GPT-2 Medium (355M)"
    return AVAILABLE_MODELS[st.session_state.selected_model]["layers"] - 1


def main():
    st.title("🧠 GlassBox Dashboard")
    st.markdown("*Interpretable-by-design AI runtime for language models*")

    # Sidebar - Model Selection
    st.sidebar.title("Model Selection")

    # Model selector
    selected_display_name = st.sidebar.selectbox(
        "Choose Model",
        options=list(AVAILABLE_MODELS.keys()),
        index=list(AVAILABLE_MODELS.keys()).index(
            st.session_state.get("selected_model", "GPT-2 Medium (355M)")
        ),
        key="model_selector"
    )

    # Update session state if model changed
    if st.session_state.get("selected_model") != selected_display_name:
        st.session_state.selected_model = selected_display_name
        # Clear cached resources when model changes
        st.cache_resource.clear()
        st.rerun()

    # Get model info
    model_info = AVAILABLE_MODELS[selected_display_name]

    # Display model info
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Model Info:**")
    st.sidebar.markdown(f"- **Size:** {model_info['size']}")
    st.sidebar.markdown(f"- **Layers:** {model_info['layers']}")
    st.sidebar.markdown(f"- **Heads:** {model_info['heads']}")
    st.sidebar.markdown(f"- **Memory:** {model_info['memory']}")
    st.sidebar.markdown(f"- **Speed:** {model_info['speed']}")

    # Show note if exists (e.g., for Llama models)
    if "note" in model_info:
        st.sidebar.warning(f"⚠️ {model_info['note']}")

    st.sidebar.markdown("---")

    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Select View",
        ["🔍 New Trace", "📚 Trace Browser", "🔬 Advanced Analysis", "🧩 SAE Features", "ℹ️ About"]
    )

    if page == "🔍 New Trace":
        show_new_trace_page()
    elif page == "📚 Trace Browser":
        show_trace_browser_page()
    elif page == "🔬 Advanced Analysis":
        show_advanced_analysis_page()
    elif page == "🧩 SAE Features":
        show_sae_features_page()
    else:
        show_about_page()


def show_new_trace_page():
    """Page for creating new traces."""
    st.header("Create New Trace")

    # Input form
    with st.form("trace_form"):
        prompt = st.text_area(
            "Enter prompt to trace:",
            value="Q: Should we approve this loan application? A:",
            height=100
        )

        # Generation mode
        st.subheader("Generation Mode")
        generation_mode = st.radio(
            "Select mode:",
            ["Single Token (Fast)", "Multi-Token (Slower, detailed)"],
            help="Single token predicts one token. Multi-token generates a completion with full tracing for each token."
        )

        multi_token = generation_mode == "Multi-Token (Slower, detailed)"

        if multi_token:
            max_tokens = st.slider(
                "Tokens to generate",
                min_value=1,
                max_value=20,
                value=5,
                help="⚠️ Each token is traced individually. 10 tokens = ~10x slower than single token."
            )
            st.warning(f"⚠️ Generating {max_tokens} tokens will take approximately {max_tokens * 2}-{max_tokens * 5} seconds with full tracing.")
        else:
            st.info("ℹ️ **Single token mode:** Predicts the next token with detailed analysis of how the model arrives at that prediction.")

        # Get model info for dynamic layer range
        model_info = AVAILABLE_MODELS[st.session_state.get("selected_model", "GPT-2 Medium (355M)")]
        max_layer = model_info["layers"] - 1

        col1, col2 = st.columns(2)
        with col1:
            capture_all = st.checkbox("Capture all layers", value=True)
            if not capture_all:
                default_start = max(0, max_layer // 2 - 2)
                default_end = min(max_layer, max_layer // 2 + 2)
                layer_range = st.slider(
                    "Layer range",
                    0, max_layer, (default_start, default_end)
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
        try:
            # Configure
            if capture_all:
                config = TracerConfig(max_seq_length=max_length)
            else:
                config = TracerConfig(
                    capture_layers=list(range(layer_range[0], layer_range[1] + 1)),
                    max_seq_length=max_length
                )

            if multi_token:
                # Multi-token generation
                with st.spinner(f"Generating {max_tokens} tokens with full tracing... This may take a while..."):
                    analyzer = get_analyzer(get_selected_model())
                    full_text, traces = analyzer.generate_completion(
                        prompt,
                        max_tokens=max_tokens
                    )

                    st.success(f"✅ Generated {len(traces)} tokens successfully!")

                    # Display multi-token results
                    display_multi_token_results(prompt, full_text, traces)

            else:
                # Single token trace
                with st.spinner("Running inference and capturing activations..."):
                    tracer = get_tracer(get_selected_model())
                    result = tracer.trace(prompt, config)

                    # Save
                    serializer = get_serializer()
                    filepath = serializer.save(result)

                    st.success(f"✅ Trace generated successfully!")

                    # Display results
                    display_trace_results(result, serializer.serialize(result))

        except Exception as e:
            st.error(f"❌ Error generating trace: {str(e)}")
            with st.expander("Show detailed error"):
                st.exception(e)


def display_multi_token_results(prompt, full_text, traces):
    """Display results for multi-token generation."""

    # Calculate overall metrics
    total_time = sum(t.metadata.inference_time_ms for t in traces)
    avg_time = total_time / len(traces) if traces else 0

    # Calculate average confidence
    import torch
    confidences = []
    for trace in traces:
        output_logit = trace.logits[0, -1]
        output_probs = torch.softmax(output_logit, dim=0)
        output_token_id = output_logit.argmax().item()
        token_prob = output_probs[output_token_id].item()
        confidences.append(token_prob)

    avg_confidence = sum(confidences) / len(confidences) if confidences else 0
    generated_text = full_text[len(prompt):]

    # Decision Summary
    st.subheader("🎯 Generation Summary")

    col1, col2 = st.columns([2, 3])
    with col1:
        st.metric("Generated Text", f"{len(traces)} tokens")
        st.text_area("Output", generated_text, height=100, disabled=True)

    with col2:
        if avg_confidence > 0.7:
            st.success(f"🟢 Average Confidence: {avg_confidence:.1%}")
            st.caption("✓ Model was confident in its generation")
        elif avg_confidence > 0.4:
            st.warning(f"🟡 Average Confidence: {avg_confidence:.1%}")
            st.caption("⚠ Generation has moderate uncertainty")
        else:
            st.error(f"🔴 Average Confidence: {avg_confidence:.1%}")
            st.caption("⚠️ Model was uncertain about this generation")

        st.metric("Total Time", f"{total_time/1000:.1f}s")
        st.metric("Speed", f"{avg_time:.0f}ms/token")

    # Token-by-token confidence visualization
    st.subheader("📊 Confidence Per Token")

    # Create a bar chart of confidence
    import pandas as pd
    token_data = []
    for i, (trace, conf) in enumerate(zip(traces, confidences), 1):
        token_data.append({
            'Position': i,
            'Token': format_output_token(trace.output_text),
            'Confidence': conf * 100
        })

    df = pd.DataFrame(token_data)
    import plotly.express as px
    fig = px.bar(
        df,
        x='Position',
        y='Confidence',
        hover_data=['Token'],
        title='Confidence Level for Each Generated Token',
        color='Confidence',
        color_continuous_scale='RdYlGn',
        range_color=[0, 100]
    )
    fig.update_layout(yaxis_title="Confidence (%)", xaxis_title="Token Position")
    st.plotly_chart(fig, use_container_width=True)

    # Show full completion
    st.subheader("📝 Complete Text")
    st.text_area("Full Output", full_text, height=150, disabled=True)

    # Token-by-token breakdown (collapsed by default)
    with st.expander("🔍 Detailed Token-by-Token Analysis", expanded=False):
        st.caption("Click on each token to see detailed attention analysis")

        for i, (trace, conf) in enumerate(zip(traces, confidences), 1):
            formatted_token = format_output_token(trace.output_text)

            with st.expander(f"Token {i}: '{formatted_token}' ({conf:.1%} confidence)"):
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric("Token", formatted_token)
                    if formatted_token != trace.output_text:
                        st.caption(f"Raw: {repr(trace.output_text)}")

                with col2:
                    if conf > 0.7:
                        st.success(f"🟢 {conf:.1%}")
                    elif conf > 0.4:
                        st.warning(f"🟡 {conf:.1%}")
                    else:
                        st.error(f"🔴 {conf:.1%}")

                with col3:
                    st.metric("Time", f"{trace.metadata.inference_time_ms:.0f}ms")

                # Show attention analysis for this token
                serializer = get_serializer()
                trace_dict = serializer.serialize(trace)

                # Token influence for this step
                token_influence = trace_dict['attribution']['token_influence']
                if token_influence:
                    st.markdown("**Key influences for this token:**")
                    top_3 = sorted(token_influence.items(), key=lambda x: x[1], reverse=True)[:3]
                    for token, influence in top_3:
                        st.markdown(f"• `{token}` - {influence:.1%}")

                # Technical details
                with st.expander("Advanced: Attention Heads"):
                    st.markdown("**Top 5 Attention Heads:**")
                    for j, head in enumerate(trace_dict['attribution']['top_attention_heads'][:5], 1):
                        st.markdown(f"{j}. Layer {head['layer']}, Head {head['head']} - Score: {head['score']:.3f}")

    # Save option
    st.divider()
    if st.button("💾 Save All Traces"):
        serializer = get_serializer()
        saved_ids = []
        for i, trace in enumerate(traces):
            filepath = serializer.save(trace)
            trace_id = filepath.stem.replace("trace_", "")
            saved_ids.append(trace_id)

        st.success(f"✅ Saved {len(saved_ids)} traces to disk")
        with st.expander("View Trace IDs"):
            for trace_id in saved_ids:
                st.code(trace_id)


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
                formatted_output = format_output_token(trace_meta['output'])
                st.metric("Output", formatted_output)
                st.caption(f"Time: {trace_meta['timestamp']}")
            
            if st.button("View Full Analysis", key=f"btn_{trace_meta['trace_id']}"):
                try:
                    # Load full trace
                    full_trace = serializer.load(trace_meta['trace_id'])
                    display_full_trace(full_trace)
                except Exception as e:
                    st.error(f"❌ Error loading trace: {str(e)}")
                    with st.expander("Show detailed error"):
                        st.exception(e)


def display_trace_results(result, trace_dict):
    """Display analysis results for a new trace."""

    # Decision Summary (Priority 1)
    st.subheader("🎯 Decision Summary")

    confidence = trace_dict['output']['probability']
    formatted_output = format_output_token(result.output_text)

    # Confidence with context
    col1, col2 = st.columns([2, 3])
    with col1:
        st.metric("Prediction", formatted_output)
        if formatted_output != result.output_text:
            st.caption(f"Raw: {repr(result.output_text)}")

    with col2:
        if confidence > 0.7:
            st.success(f"🟢 High Confidence: {confidence:.1%}")
            st.caption("✓ The model is very sure about this prediction")
        elif confidence > 0.4:
            st.warning(f"🟡 Moderate Confidence: {confidence:.1%}")
            st.caption("⚠ Worth reviewing - model is somewhat uncertain")
        else:
            st.error(f"🔴 Low Confidence: {confidence:.1%}")
            st.caption("⚠️ Manual review strongly recommended")

    # Key factors (Priority 2)
    st.subheader("📊 Key Influencing Factors")

    token_influence = trace_dict['attribution']['token_influence']
    if token_influence:
        # Get top 5 most influential tokens
        top_tokens = sorted(
            token_influence.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        st.markdown("**The model focused primarily on these parts of your input:**")

        for token, influence in top_tokens:
            # Create a visual bar
            bar_length = int(influence * 50)
            bar = "█" * bar_length + "░" * (50 - bar_length)

            # Color based on influence level
            if influence > 0.15:
                st.markdown(f"🟢 **`{token}`** {bar} **{influence:.1%}**")
            elif influence > 0.08:
                st.markdown(f"🟡 `{token}` {bar} {influence:.1%}")
            else:
                st.markdown(f"⚪ `{token}` {bar} {influence:.1%}")

        # Show reasoning
        st.info(f"💭 **Model Reasoning:** The prediction '{formatted_output}' was primarily influenced by the tokens shown above, with '{top_tokens[0][0]}' having the strongest impact ({top_tokens[0][1]:.1%}).")
    else:
        st.warning("No token influence data available for this trace.")

    # Input visualization with highlighting
    st.subheader("💬 Input Analysis")

    # Show input with token highlighting
    tokens = trace_dict['input']['tokens']
    col1, col2 = st.columns([3, 1])

    with col1:
        st.text_area("Input", result.prompt, height=100, disabled=True)

        # Create highlighted version
        if token_influence:
            st.markdown("**Token Influence Visualization:**")
            highlighted_text = ""
            for token in tokens:
                influence = token_influence.get(token, 0)
                if influence > 0.15:
                    highlighted_text += f"**[{token}]** "  # High influence
                elif influence > 0.08:
                    highlighted_text += f"*{token}* "  # Medium influence
                else:
                    highlighted_text += f"{token} "  # Low influence

            st.markdown(highlighted_text)
            st.caption("**Bold** = High influence, *Italic* = Medium influence")

    with col2:
        st.metric("Tokens", len(tokens))
        st.metric("Inference Time", f"{result.metadata.inference_time_ms:.0f}ms")
        st.metric("Slowdown", f"{result.metadata.slowdown_factor:.1f}x")

    # Collapse technical details
    with st.expander("🔧 Advanced: Technical Details", expanded=False):
        st.caption("For ML experts and researchers")
        display_full_trace(trace_dict)


def display_full_trace(trace_dict):
    """Display complete trace analysis."""

    # Initialize attention visualizer
    attn_viz = AttentionVisualizer()

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
    """)

    # Dynamic model info
    model_info = AVAILABLE_MODELS[st.session_state.get("selected_model", "GPT-2 Medium (355M)")]
    st.markdown(f"""
    - **Model**: {st.session_state.get("selected_model", "GPT-2 Medium (355M)")} ({model_info['size']} parameters)
    - **Architecture**: {model_info['layers']} layers, {model_info['heads']} attention heads per layer
    - **Memory**: {model_info['memory']}
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

    - Supports GPT-2 family and Llama 2 models
    - Limited to 512 tokens
    - Attention ≠ causation (causal validation coming in v0.2)
    - Requires ML expertise to interpret results
    - Larger models require more memory and are slower
    
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


def show_advanced_analysis_page():
    """Page for advanced mechanistic interpretability analysis."""
    st.header("🔬 Advanced Mechanistic Analysis")
    st.markdown("*Causal interventions and circuit discovery tools*")

    # Create tabs for different analyses
    tab1, tab2, tab3, tab4 = st.tabs([
        "🎯 Activation Patching",
        "📊 Causal Tracing",
        "🔍 Circuit Discovery",
        "🌐 Activation Space"
    ])

    with tab1:
        show_activation_patching()

    with tab2:
        show_causal_tracing()

    with tab3:
        show_circuit_discovery()

    with tab4:
        show_activation_space()


def show_activation_patching():
    """Show activation patching interface."""
    st.subheader("Activation Patching")
    st.markdown("""
    **What is it?** Replace activations from a "clean" run into a "corrupted" run to measure causal effects.

    This helps answer: *Which layers/components are responsible for specific behaviors?*
    """)

    col1, col2 = st.columns(2)

    with col1:
        clean_input = st.text_input(
            "Clean Input (correct behavior)",
            value="The Eiffel Tower is in Paris",
            help="The prompt with correct/desired output"
        )

    with col2:
        corrupted_input = st.text_input(
            "Corrupted Input (counterfactual)",
            value="The Eiffel Tower is in London",
            help="The prompt with incorrect/undesired output"
        )

    # Intervention configuration
    st.markdown("#### Intervention Configuration")
    col1, col2, col3 = st.columns(3)

    with col1:
        max_layer = get_model_max_layer()
        default_layer = min(8, max_layer)
        layer = st.slider("Layer to patch", 0, max_layer, default_layer, help="Which layer to intervene at")

    with col2:
        component = st.selectbox(
            "Component",
            ["resid", "attn", "mlp"],
            help="Which component to patch"
        )

    with col3:
        intervention_type = st.selectbox(
            "Intervention Type",
            ["PATCH", "ZERO_ABLATE", "MEAN_ABLATE"],
            help="How to modify activations"
        )

    if st.button("Run Patching Experiment", type="primary"):
        with st.spinner("Running experiment..."):
            try:
                # Initialize patcher
                tracer = get_tracer(get_selected_model())
                patcher = ActivationPatcher(tracer)

                # Map intervention type string to enum
                intervention_map = {
                    "PATCH": InterventionType.PATCH,
                    "ZERO_ABLATE": InterventionType.ZERO_ABLATE,
                    "MEAN_ABLATE": InterventionType.MEAN_ABLATE
                }

                # Run experiment
                result = patcher.patch_and_run(
                    clean_input=clean_input,
                    corrupted_input=corrupted_input,
                    intervention=InterventionConfig(
                        layer=layer,
                        component=component,
                        intervention_type=intervention_map[intervention_type]
                    )
                )

                # Display results
                st.success("Experiment complete!")

                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric(
                        "Logit Diff",
                        f"{result.logit_diff:.3f}",
                        help="Change in target token logit (negative = intervention restores clean behavior)"
                    )

                with col2:
                    st.metric(
                        "KL Divergence",
                        f"{result.kl_divergence:.3f}",
                        help="Difference between output distributions"
                    )

                with col3:
                    st.metric(
                        "Intervention Magnitude",
                        f"{result.intervention_magnitude:.1f}",
                        help="L2 norm of intervention"
                    )

                # Show outputs
                st.markdown("#### Outputs")
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("**Clean Output:**")
                    st.code(result.clean_output)

                with col2:
                    st.markdown("**Intervened Output:**")
                    st.code(result.intervened_output)

                # Interpretation
                st.markdown("#### Interpretation")
                if result.logit_diff < -0.5:
                    st.info(f"🎯 **Strong causal effect**: Layer {layer} {component} is critical for this behavior. The intervention successfully restored clean-like output.")
                elif result.logit_diff < 0:
                    st.info(f"📊 **Moderate effect**: Layer {layer} {component} has some influence on this behavior.")
                else:
                    st.info(f"❌ **Weak effect**: Layer {layer} {component} doesn't strongly affect this behavior.")

            except Exception as e:
                st.error(f"Error running experiment: {str(e)}")


def show_causal_tracing():
    """Show causal tracing interface."""
    st.subheader("Causal Tracing")
    st.markdown("""
    **What is it?** Systematically patch each layer to find where information is processed.

    This creates a "causal heatmap" showing which layers matter for specific outputs.
    """)

    col1, col2 = st.columns(2)

    with col1:
        clean_input = st.text_input(
            "Clean Input",
            value="The Eiffel Tower is in Paris",
            key="ct_clean"
        )

    with col2:
        corrupted_input = st.text_input(
            "Corrupted Input",
            value="The Eiffel Tower is in London",
            key="ct_corrupt"
        )

    max_layer = get_model_max_layer()
    # Create reasonable default layers to trace (spread across model)
    default_trace_layers = [0, max_layer // 4, max_layer // 2, max_layer]
    layers_to_trace = st.multiselect(
        "Layers to trace",
        options=list(range(max_layer + 1)),
        default=default_trace_layers,
        help="Select which layers to analyze (fewer = faster)"
    )

    if st.button("Run Causal Trace", type="primary"):
        with st.spinner(f"Tracing {len(layers_to_trace)} layers..."):
            try:
                # Initialize patcher
                tracer = get_tracer(get_selected_model())
                patcher = ActivationPatcher(tracer)

                # Run causal trace
                results = patcher.causal_trace(
                    clean_input=clean_input,
                    corrupted_input=corrupted_input,
                    layers=layers_to_trace,
                    components=["resid"]
                )

                # Create dataframe for visualization
                data = []
                for key, result in results.items():
                    layer = int(key.split("_")[-1])
                    data.append({
                        "Layer": layer,
                        "Logit Diff": result.logit_diff,
                        "KL Divergence": result.kl_divergence
                    })

                df = pd.DataFrame(data).sort_values("Layer")

                # Display results
                st.success("Causal trace complete!")

                # Use enhanced visualizations
                causal_viz = CausalFlowVisualizer()

                # Layer importance chart
                try:
                    importance_fig = causal_viz.create_layer_importance_chart(results)
                    st.plotly_chart(importance_fig, use_container_width=True)
                except Exception as e:
                    st.warning(f"Could not create importance chart: {str(e)}")
                    # Fallback to original visualization
                    fig = go.Figure()
                    fig.add_trace(go.Bar(
                        x=df["Layer"],
                        y=df["Logit Diff"],
                        name="Logit Diff",
                        marker_color=['red' if x < -0.5 else 'orange' if x < 0 else 'green' for x in df["Logit Diff"]]
                    ))
                    fig.update_layout(
                        title="Causal Effect by Layer",
                        xaxis_title="Layer",
                        yaxis_title="Logit Difference",
                        height=400
                    )
                    st.plotly_chart(fig, use_container_width=True)

                # Causal heatmap
                try:
                    heatmap_fig = causal_viz.create_causal_heatmap(results, metric="logit_diff")
                    st.plotly_chart(heatmap_fig, use_container_width=True)
                except Exception as e:
                    st.warning(f"Could not create causal heatmap: {str(e)}")

                # Show table
                st.dataframe(df, use_container_width=True)

                # Find most important layer
                most_important = df.loc[df["Logit Diff"].abs().idxmax()]
                st.info(f"🎯 **Most critical layer**: Layer {int(most_important['Layer'])} (logit diff = {most_important['Logit Diff']:.3f})")

            except Exception as e:
                st.error(f"Error running causal trace: {str(e)}")


def show_circuit_discovery():
    """Show circuit discovery interface."""
    st.subheader("Circuit Discovery")
    st.markdown("""
    **What is it?** Find the minimal set of components that implement a specific behavior.

    This reveals the "algorithmic circuit" the model uses for a task.
    """)

    col1, col2 = st.columns(2)

    with col1:
        clean_input = st.text_input(
            "Clean Input",
            value="The Eiffel Tower is in Paris",
            key="cd_clean"
        )

    with col2:
        corrupted_input = st.text_input(
            "Corrupted Input",
            value="The Eiffel Tower is in London",
            key="cd_corrupt"
        )

    task_description = st.text_input(
        "Task Description",
        value="Geographic location recall",
        help="Describe what task this circuit implements"
    )

    col1, col2 = st.columns(2)

    with col1:
        threshold = st.slider(
            "Importance Threshold",
            0.0, 1.0, 0.1, 0.05,
            help="Only include components above this importance score"
        )

    with col2:
        max_components = st.number_input(
            "Max Components",
            min_value=1, max_value=36, value=10,
            help="Limit circuit size (smaller = more compressed)"
        )

    if st.button("Discover Circuit", type="primary"):
        with st.spinner("Discovering circuit... (this may take a minute)"):
            try:
                # Initialize discovery
                tracer = get_tracer(get_selected_model())
                discovery = CircuitDiscovery(tracer, threshold=threshold)

                # Discover circuit
                circuit = discovery.discover_circuit(
                    clean_input=clean_input,
                    corrupted_input=corrupted_input,
                    task_description=task_description,
                    max_components=max_components
                )

                # Display results
                st.success("Circuit discovered!")

                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric(
                        "Circuit Size",
                        f"{circuit.get_num_components()} nodes",
                        help="Number of components in circuit"
                    )

                with col2:
                    st.metric(
                        "Faithfulness",
                        f"{circuit.faithfulness_score:.1%}",
                        help="How well circuit explains behavior"
                    )

                with col3:
                    compression = circuit.get_compression_ratio(36)
                    st.metric(
                        "Compression",
                        f"{compression:.1%}",
                        help="Circuit size / Model size"
                    )

                # Visualize circuit
                st.markdown("#### Circuit Visualization")

                # Interactive graph visualization
                circuit_visualizer = CircuitVisualizer()
                try:
                    circuit_fig = circuit_visualizer.create_interactive_graph(
                        circuit,
                        title=f"{task_description} Circuit"
                    )
                    st.plotly_chart(circuit_fig, use_container_width=True)
                except Exception as e:
                    st.warning(f"Could not create interactive graph: {str(e)}")
                    # Fallback to text visualization
                    circuit_viz = discovery.visualize_circuit(circuit)
                    st.code(circuit_viz, language="text")

                # Show circuit data
                st.markdown("#### Circuit Data")
                with st.expander("View circuit JSON"):
                    st.json(circuit.to_dict())

                # Interpretation
                st.markdown("#### Interpretation")
                if compression < 0.3:
                    st.success(f"🎯 **Highly compressed circuit**: This task uses only {compression*100:.1f}% of the model. The behavior is implemented by a small, localized circuit.")
                elif compression < 0.6:
                    st.info(f"📊 **Moderate compression**: This task uses {compression*100:.1f}% of the model. The behavior involves multiple components.")
                else:
                    st.warning(f"⚠️ **Low compression**: This task uses {compression*100:.1f}% of the model. The behavior may be distributed across many components.")

            except Exception as e:
                st.error(f"Error discovering circuit: {str(e)}")


def show_activation_space():
    """Show 3D activation space visualization."""
    st.subheader("3D Activation Space Visualization")
    st.markdown("""
    **What is it?** Visualize high-dimensional model activations in 3D using dimensionality reduction.

    This helps answer: *How do different inputs cluster in the model's internal representation space?*
    """)

    # Input prompts
    st.markdown("#### Configure Visualization")

    with st.form("activation_space_form"):
        prompts_text = st.text_area(
            "Enter prompts to visualize (one per line):",
            value="The Eiffel Tower is in Paris\nThe Eiffel Tower is in London\nThe Colosseum is in Rome\nThe Colosseum is in Paris\nThe Great Wall is in China\nTokyo is the capital of Japan",
            height=150,
            help="Enter different prompts to see how they cluster in activation space"
        )

        col1, col2 = st.columns(2)
        with col1:
            # Get model info to determine max layer
            tracer = get_tracer(get_selected_model())
            max_layer = tracer.model.cfg.n_layers - 1
            default_layer = max_layer // 2

            layer = st.slider(
                "Layer to visualize",
                0, max_layer, default_layer,
                help="Which transformer layer to extract activations from"
            )

        with col2:
            method = st.selectbox(
                "Projection method",
                ["pca", "tsne"],
                help="PCA is faster, t-SNE may reveal more structure"
            )

        visualize_btn = st.form_submit_button("🌐 Visualize Activation Space", type="primary")

    if visualize_btn:
        prompts = [p.strip() for p in prompts_text.split('\n') if p.strip()]

        if len(prompts) < 3:
            st.error("Please provide at least 3 prompts for meaningful visualization")
        else:
            with st.spinner(f"Computing activations for {len(prompts)} prompts..."):
                try:
                    import torch
                    import numpy as np

                    # Get tracer
                    tracer = get_tracer(get_selected_model())

                    # Collect activations
                    all_activations = []
                    labels = []

                    for i, prompt in enumerate(prompts):
                        # Run trace to get activations
                        with torch.no_grad():
                            result = tracer.trace(prompt)

                            # Get layer activations (use last token)
                            layer_key = f"layer_{layer}_resid"
                            if result.activation_cache and layer_key in result.activation_cache:
                                # Get residual stream activation at last token position
                                acts = result.activation_cache[layer_key][-1, :]  # Last token
                                all_activations.append(acts.numpy() if hasattr(acts, 'numpy') else acts)
                                labels.append(f"{i+1}. {prompt[:40]}...")
                            else:
                                st.warning(f"Layer {layer} activations not found for prompt {i+1}. Available keys: {list(result.activation_cache.keys()) if result.activation_cache else 'None'}")

                    if len(all_activations) < 3:
                        st.error("Not enough valid activations collected. Try different prompts.")
                    else:
                        # Stack activations
                        activations_array = np.stack(all_activations)

                        st.success(f"✅ Collected activations from {len(all_activations)} prompts")
                        st.info(f"Activation dimensions: {activations_array.shape}")

                        # Create 3D projection
                        space_viz = ActivationSpaceVisualizer()

                        fig = space_viz.create_3d_projection(
                            activations_array,
                            labels=labels,
                            method=method
                        )

                        st.plotly_chart(fig, use_container_width=True)

                        # Interpretation
                        st.markdown("#### Interpretation")
                        st.markdown("""
                        **How to read this visualization:**
                        - Each point represents one prompt's activation at the selected layer
                        - Points close together = similar internal representations
                        - Points far apart = different internal representations
                        - Rotate/zoom to explore the structure

                        **What to look for:**
                        - Do similar prompts cluster together?
                        - Are there distinct groups?
                        - How does the model separate different concepts?
                        """)

                        # Show variance explained (for PCA)
                        if method == "pca":
                            st.info("💡 **PCA Tip**: The axes represent the top 3 principal components. Larger spreads along an axis indicate more important features.")
                        else:
                            st.info("💡 **t-SNE Tip**: t-SNE emphasizes local structure. Clusters are meaningful, but distances between clusters are not.")

                except Exception as e:
                    st.error(f"Error creating visualization: {str(e)}")
                    import traceback
                    with st.expander("Show error details"):
                        st.code(traceback.format_exc())


def show_sae_features_page():
    """Page for Sparse Autoencoder feature discovery."""
    st.header("🧩 Sparse Autoencoder Features")
    st.markdown("Discover monosemantic features using Sparse Autoencoders (SAEs)")

    tab1, tab2, tab3 = st.tabs([
        "📊 Feature Discovery",
        "🔍 Feature Analysis",
        "🔬 Feature Circuits"
    ])

    # Tab 1: Feature Discovery
    with tab1:
        st.subheader("Discover Monosemantic Features")

        st.markdown("""
        **What are Sparse Autoencoders?**

        SAEs decompose model activations into sparse, interpretable features. Each feature
        ideally represents a single concept ("monosemantic").

        **Workflow:**
        1. Collect activations from diverse prompts
        2. Train SAE to reconstruct activations sparsely
        3. Discover which features activate for which concepts
        """)

        with st.form("sae_discovery_form"):
            st.markdown("**Training Configuration:**")

            max_layer = get_model_max_layer()
            col1, col2 = st.columns(2)
            with col1:
                layer = st.number_input(
                    "Layer to analyze:",
                    min_value=0,
                    max_value=max_layer,
                    value=min(6, max_layer),
                    help="Which transformer layer to extract features from"
                )
                expansion_factor = st.number_input(
                    "Expansion factor:",
                    min_value=2,
                    max_value=16,
                    value=8,
                    help="SAE hidden dimension = d_model × expansion_factor"
                )

            with col2:
                num_training_steps = st.number_input(
                    "Training steps:",
                    min_value=100,
                    max_value=5000,
                    value=500,
                    help="Number of SAE training steps"
                )
                l1_coefficient = st.number_input(
                    "L1 sparsity penalty:",
                    min_value=0.0001,
                    max_value=0.01,
                    value=0.001,
                    format="%.4f",
                    help="Strength of sparsity constraint"
                )

            training_prompts = st.text_area(
                "Training prompts (one per line):",
                value="The Eiffel Tower is in Paris\nLondon is the capital of England\nTokyo is the capital of Japan\nRome is the capital of Italy\nBerlin is the capital of Germany\nThe Great Wall is in China",
                height=150,
                help="Diverse prompts for collecting training data"
            )

            submitted = st.form_submit_button("🚀 Run Feature Discovery")

        if submitted:
            prompts = [p.strip() for p in training_prompts.split('\n') if p.strip()]

            if len(prompts) < 3:
                st.error("Please provide at least 3 training prompts")
            else:
                with st.spinner("Running feature discovery workflow..."):
                    try:
                        # Initialize workflow
                        workflow = FeatureDiscoveryWorkflow(
                            model_name=get_tracer(get_selected_model()).model_name,
                            layer=layer
                        )

                        # Collect training data
                        st.info("Step 1/4: Collecting activations...")
                        training_data = workflow.collect_training_data(prompts, max_samples=2000)

                        # Train SAE
                        st.info("Step 2/4: Training SAE...")
                        progress_bar = st.progress(0)
                        sae, training_stats = workflow.train_sae(
                            training_data,
                            expansion_factor=expansion_factor,
                            l1_coefficient=l1_coefficient,
                            num_steps=num_training_steps
                        )
                        progress_bar.progress(100)

                        # Discover features
                        st.info("Step 3/4: Discovering features...")
                        features = workflow.discover_features(prompts, top_k=20)

                        # Analyze features
                        st.info("Step 4/4: Analyzing features...")
                        analyses = workflow.analyze_features(features)

                        st.success("✅ Feature discovery complete!")

                        # Display results
                        st.markdown("### Training Results")

                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Final Loss", f"{training_stats['loss_history'][-1]:.4f}")
                        with col2:
                            st.metric("Active Features", f"{training_stats['l0_history'][-1]:.0f}")
                        with col3:
                            st.metric("Variance Explained", f"{training_stats['var_explained_history'][-1]:.1%}")
                        with col4:
                            st.metric("Dead Neurons", f"{training_stats['num_dead_neurons']}")

                        # Training plots
                        st.markdown("### Training Progress")

                        fig_loss = go.Figure()
                        fig_loss.add_trace(go.Scatter(
                            y=training_stats['loss_history'],
                            mode='lines',
                            name='Total Loss'
                        ))
                        fig_loss.update_layout(
                            title="Training Loss",
                            xaxis_title="Step",
                            yaxis_title="Loss",
                            height=300
                        )
                        st.plotly_chart(fig_loss, use_container_width=True)

                        # Features discovered
                        st.markdown("### Discovered Features")
                        st.markdown(f"Found **{len(features)}** monosemantic features")

                        # Visualize top features
                        sae_viz = SAEFeatureVisualizer()

                        # Store in session state for other tabs
                        st.session_state.sae_trained = True
                        st.session_state.sae_model = sae
                        st.session_state.sae_layer = layer
                        st.session_state.sae_features = features
                        st.session_state.sae_analyses = analyses

                        # Create activation heatmap for top features
                        try:
                            # Collect activations for visualization
                            import numpy as np
                            import torch

                            # Get activations for prompts
                            tracer = get_tracer(get_selected_model())
                            all_activations = []
                            all_tokens = []

                            for prompt in prompts[:5]:  # Use first 5 prompts for viz
                                # Run through model to get activations
                                with torch.no_grad():
                                    result = tracer.trace(prompt)
                                    # Get layer activations
                                    layer_key = f"layer_{layer}_resid"
                                    if result.activation_cache and layer_key in result.activation_cache:
                                        acts = result.activation_cache[layer_key][-1, :]  # Last token
                                        # Get SAE features
                                        features_acts = sae.encode(acts.unsqueeze(0))
                                        all_activations.append(features_acts[0].detach().cpu().numpy())
                                        all_tokens.append(result.output_text)

                            if all_activations:
                                activations_array = np.stack(all_activations)
                                heatmap_fig = sae_viz.create_feature_activation_heatmap(
                                    activations_array,
                                    all_tokens,
                                    top_k=20
                                )
                                st.plotly_chart(heatmap_fig, use_container_width=True)
                        except Exception as e:
                            st.warning(f"Could not create feature heatmap: {str(e)}")

                        for i, feature in enumerate(features[:10]):  # Show top 10
                            with st.expander(f"Feature {feature.feature_idx} - Activation: {feature.activation_strength:.3f}"):
                                analysis = analyses[i]

                                st.markdown(f"**Description:** {analysis.get('description', 'Unknown')}")
                                st.markdown(f"**Activation frequency:** {feature.activation_frequency}")
                                st.markdown(f"**Decoder norm:** {analysis.get('decoder_norm', 0):.3f}")

                                # Top examples
                                st.markdown("**Top activating examples:**")
                                for ex in feature.top_activating_examples[:5]:
                                    st.markdown(f"- `{ex['token']}` in: \"{ex['prompt'][:60]}...\" (activation: {ex['activation']:.3f})")

                    except Exception as e:
                        st.error(f"Error: {str(e)}")
                        import traceback
                        st.code(traceback.format_exc())

    # Tab 2: Feature Analysis
    with tab2:
        st.subheader("Analyze Individual Features")

        st.markdown("""
        Analyze specific SAE features to understand what concepts they represent.
        """)

        # Check if SAE has been trained
        if not st.session_state.get("sae_trained", False):
            st.warning("⚠️ No SAE trained yet. Please run Feature Discovery first in the Discovery tab.")
        else:
            st.success(f"✅ SAE available for layer {st.session_state.sae_layer}")

            with st.form("feature_analysis_form"):
                prompt = st.text_input(
                    "Prompt to analyze:",
                    value="The Eiffel Tower is in Paris"
                )

                top_k_features = st.number_input("Top features to show:", min_value=5, max_value=50, value=20, key="top_k")

                analyze_btn = st.form_submit_button("🔍 Analyze Features")

            if analyze_btn:
                with st.spinner("Analyzing features..."):
                    try:
                        import torch
                        tracer = get_tracer(get_selected_model())
                        sae = st.session_state.sae_model
                        layer = st.session_state.sae_layer

                        # Get activations for prompt
                        result = tracer.trace(prompt)
                        layer_key = f"layer_{layer}_resid"

                        if result.activation_cache and layer_key in result.activation_cache:
                            acts = result.activation_cache[layer_key]

                            # Encode with SAE
                            with torch.no_grad():
                                features = sae.encode(acts)

                            # Get top activating features
                            max_features = features.max(dim=0).values
                            top_indices = max_features.argsort(descending=True)[:top_k_features]

                            st.markdown(f"### Top {top_k_features} Active Features for: \"{prompt}\"")

                            for i, idx in enumerate(top_indices):
                                idx = int(idx)
                                activation = float(max_features[idx])
                                if activation > 0:
                                    st.markdown(f"**Feature {idx}**: activation = {activation:.3f}")
                        else:
                            st.error(f"Could not get activations for layer {layer}")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")

    # Tab 3: Feature Circuits
    with tab3:
        st.subheader("Feature-Based Circuit Discovery")

        st.markdown("""
        Discover circuits based on SAE features instead of raw activations.
        This provides more interpretable circuits where each node is a monosemantic feature.
        """)

        # Check if SAE has been trained
        if not st.session_state.get("sae_trained", False):
            st.warning("⚠️ No SAE trained yet. Please run Feature Discovery first in the Discovery tab.")
        else:
            st.success(f"✅ SAE available for layer {st.session_state.sae_layer}")

            with st.form("feature_circuit_form"):
                col1, col2 = st.columns(2)

                with col1:
                    clean_input = st.text_input(
                        "Clean input:",
                        value="The Eiffel Tower is in Paris"
                    )

                with col2:
                    corrupted_input = st.text_input(
                        "Corrupted input:",
                        value="The Eiffel Tower is in London"
                    )

                task_description = st.text_input(
                    "Task description:",
                    value="Geographic fact recall"
                )

                discover_circuit_btn = st.form_submit_button("🔬 Discover Feature Circuit")

            if discover_circuit_btn:
                with st.spinner("Analyzing feature differences..."):
                    try:
                        import torch
                        tracer = get_tracer(get_selected_model())
                        sae = st.session_state.sae_model
                        layer = st.session_state.sae_layer

                        # Get activations for both prompts
                        clean_result = tracer.trace(clean_input)
                        corrupted_result = tracer.trace(corrupted_input)
                        layer_key = f"layer_{layer}_resid"

                        if (clean_result.activation_cache and layer_key in clean_result.activation_cache and
                            corrupted_result.activation_cache and layer_key in corrupted_result.activation_cache):

                            clean_acts = clean_result.activation_cache[layer_key]
                            corrupted_acts = corrupted_result.activation_cache[layer_key]

                            # Encode with SAE
                            with torch.no_grad():
                                clean_features = sae.encode(clean_acts)
                                corrupted_features = sae.encode(corrupted_acts)

                            # Find features that differ most
                            clean_max = clean_features.max(dim=0).values
                            corrupted_max = corrupted_features.max(dim=0).values
                            diff = (clean_max - corrupted_max).abs()

                            top_diff_indices = diff.argsort(descending=True)[:20]

                            st.markdown(f"### Features Most Different Between Inputs")
                            st.markdown(f"**Clean:** {clean_input}")
                            st.markdown(f"**Corrupted:** {corrupted_input}")
                            st.markdown("---")

                            for idx in top_diff_indices:
                                idx = int(idx)
                                clean_val = float(clean_max[idx])
                                corrupted_val = float(corrupted_max[idx])
                                difference = float(diff[idx])
                                if difference > 0.01:
                                    direction = "↑" if clean_val > corrupted_val else "↓"
                                    st.markdown(f"**Feature {idx}**: clean={clean_val:.3f}, corrupted={corrupted_val:.3f} ({direction} {difference:.3f})")
                        else:
                            st.error(f"Could not get activations for layer {layer}")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")

        st.markdown("""
        **Benefits of feature-level circuits:**
        - More interpretable than raw activation circuits
        - Each feature represents a single concept
        - Easier to understand model behavior
        - Can manually inspect what features do
        """)


def cli_main():
    """Entry point for console script."""
    import sys
    sys.argv = ["streamlit", "run", __file__]
    from streamlit.web import cli as stcli
    sys.exit(stcli.main())


if __name__ == "__main__":
    main()
