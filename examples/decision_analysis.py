"""
Example: Using GlassBox for Yes/No Decision Analysis

This example shows how to:
1. Get yes/no probabilities for decisions
2. Analyze which attention heads contributed to the decision
3. Generate multi-token completions with tracing
"""

import sys
sys.path.insert(0, '..')

from glassbox.tracer import ActivationTracer
from glassbox.analyzer import AttentionAnalyzer
from glassbox.decision_analyzer import DecisionAnalyzer


def example_1_yes_no_probabilities():
    """Example 1: Analyze yes/no probabilities."""
    print("\n" + "="*60)
    print("EXAMPLE 1: Yes/No Decision Probabilities")
    print("="*60)

    tracer = ActivationTracer(model_name="gpt2-medium")
    analyzer = DecisionAnalyzer(tracer)

    # Different loan scenarios
    scenarios = [
        "Q: Credit score 750, income $80k, approve loan? A:",
        "Q: Credit score 450, income $30k, approve loan? A:",
        "Q: Credit score 680, income $50k, approve loan? A:",
    ]

    for prompt in scenarios:
        result, probs = analyzer.analyze_choices(prompt, ["yes", "no"])

        print(f"\nScenario: {prompt}")
        print(f"Prediction: '{result.output_text}'")
        print(f"  P(yes) = {probs['yes']:.1%}")
        print(f"  P(no)  = {probs['no']:.1%}")

        # Show top alternatives
        top_tokens = analyzer.get_top_tokens(result, top_k=5)
        print(f"  Top alternatives:")
        for token, prob in top_tokens[:3]:
            print(f"    '{token}' ({prob:.1%})")


def example_2_attention_analysis():
    """Example 2: Analyze which attention heads drove the decision."""
    print("\n" + "="*60)
    print("EXAMPLE 2: Attention Analysis for Decision")
    print("="*60)

    tracer = ActivationTracer(model_name="gpt2-medium")
    attention_analyzer = AttentionAnalyzer()
    decision_analyzer = DecisionAnalyzer(tracer)

    # Analyze a specific decision
    prompt = "Q: Should we approve this loan application? A:"

    result, probs = decision_analyzer.analyze_choices(prompt, ["yes", "no"])

    print(f"\nPrompt: {prompt}")
    print(f"Decision: '{result.output_text}' (P={probs['yes']:.1%} yes, {probs['no']:.1%} no)")

    # Rank attention heads
    top_heads = attention_analyzer.rank_attention_heads(
        result.attention_cache,
        result.tokens,
        target_token_idx=-1
    )

    print(f"\nTop 5 attention heads that drove this decision:")
    for i, head in enumerate(top_heads[:5], 1):
        print(f"\n  {i}. Layer {head.layer}, Head {head.head}")
        print(f"     Score: {head.score:.3f}")
        print(f"     Attended to:")
        for token, weight in head.top_attended_tokens[:3]:
            print(f"       → '{token}' ({weight:.3f})")

    # Token influence
    token_influence = attention_analyzer.compute_token_influence(
        result.attention_cache,
        result.tokens,
        top_n_heads=10
    )

    print(f"\nMost influential input tokens:")
    sorted_tokens = sorted(token_influence.items(), key=lambda x: x[1], reverse=True)
    for token, score in sorted_tokens[:5]:
        print(f"  '{token}': {score:.3f}")


def example_3_multi_token_generation():
    """Example 3: Generate full answer with tracing."""
    print("\n" + "="*60)
    print("EXAMPLE 3: Multi-Token Generation with Tracing")
    print("="*60)

    tracer = ActivationTracer(model_name="gpt2-medium")
    analyzer = DecisionAnalyzer(tracer)

    prompt = "Q: Should we approve this loan? A:"

    print(f"\nGenerating completion for: {prompt}")
    print("Each token is traced individually...\n")

    # Generate 10 tokens
    full_text, traces = analyzer.generate_completion(
        prompt,
        max_tokens=10,
        stop_on=["\n", "."]
    )

    print(f"Full text: {full_text}")
    print(f"\nGenerated {len(traces)} tokens:")

    for i, trace in enumerate(traces, 1):
        print(f"  {i}. '{trace.output_text}' ({trace.metadata.inference_time_ms:.0f}ms)")

    print(f"\nTotal time: {sum(t.metadata.inference_time_ms for t in traces):.0f}ms")
    print("(This is why we usually only predict 1 token!)")


def example_4_multiple_choice():
    """Example 4: Analyze multiple choice questions."""
    print("\n" + "="*60)
    print("EXAMPLE 4: Multiple Choice Analysis")
    print("="*60)

    tracer = ActivationTracer(model_name="gpt2-medium")
    analyzer = DecisionAnalyzer(tracer)

    # Multiple choice question
    prompt = "Q: What is the capital of France? A) London B) Paris C) Berlin\nA:"

    result, probs = analyzer.analyze_choices(
        prompt,
        ["A", "B", "C", "London", "Paris", "Berlin"]
    )

    print(f"\nQuestion: {prompt}")
    print(f"Prediction: '{result.output_text}'")
    print(f"\nChoice probabilities:")

    for choice, prob in sorted(probs.items(), key=lambda x: x[1], reverse=True):
        bar = "█" * int(prob * 50)
        print(f"  {choice:10s}: {bar} {prob:.2%}")


if __name__ == "__main__":
    print("\n🧠 GlassBox Decision Analysis Examples")
    print("This demonstrates how to use GlassBox for decision analysis")

    # Run examples
    example_1_yes_no_probabilities()
    example_2_attention_analysis()
    # example_3_multi_token_generation()  # Slow, uncomment if needed
    example_4_multiple_choice()

    print("\n✅ All examples complete!\n")
