"""
Decision Analyzer - Analyze model decisions for specific outcomes.

This module extends GlassBox to analyze probabilities for specific answers
like "yes/no", "approve/deny", etc.
"""

from typing import List, Dict, Tuple
import torch
from glassbox.tracer import ActivationTracer, TracerConfig, TraceResult


class DecisionAnalyzer:
    """Analyze model decisions for specific answer choices."""

    def __init__(self, tracer: ActivationTracer):
        """
        Initialize with an existing tracer.

        Args:
            tracer: ActivationTracer instance
        """
        self.tracer = tracer

    def analyze_choices(
        self,
        prompt: str,
        choices: List[str],
        config: TracerConfig = None
    ) -> Tuple[TraceResult, Dict[str, float]]:
        """
        Analyze probabilities for specific answer choices.

        Args:
            prompt: Input prompt
            choices: List of possible answers (e.g., ["yes", "no"])
            config: Optional tracer config

        Returns:
            Tuple of (TraceResult, dict mapping choices to probabilities)

        Example:
            >>> analyzer = DecisionAnalyzer(tracer)
            >>> result, probs = analyzer.analyze_choices(
            ...     "Q: Should we approve this loan? A:",
            ...     ["yes", "no"]
            ... )
            >>> print(f"P(yes) = {probs['yes']:.2%}")
            >>> print(f"P(no) = {probs['no']:.2%}")
        """
        # Run trace
        result = self.tracer.trace(prompt, config)

        # Get probabilities for each choice
        probs_dict = {}
        logits = result.logits[0, -1]
        all_probs = torch.softmax(logits, dim=0)

        for choice in choices:
            # Try with and without leading space
            variations = [choice, f" {choice}", f" {choice.capitalize()}"]
            max_prob = 0.0

            for variation in variations:
                try:
                    token_id = self.tracer.model.to_single_token(variation)
                    prob = all_probs[token_id].item()
                    max_prob = max(max_prob, prob)
                except:
                    pass

            probs_dict[choice] = max_prob

        return result, probs_dict

    def get_top_tokens(
        self,
        result: TraceResult,
        top_k: int = 10
    ) -> List[Tuple[str, float]]:
        """
        Get top K most likely next tokens with their probabilities.

        Args:
            result: TraceResult from trace()
            top_k: Number of top tokens to return

        Returns:
            List of (token_string, probability) tuples
        """
        logits = result.logits[0, -1]
        probs = torch.softmax(logits, dim=0)

        # Get top k
        top_probs, top_indices = torch.topk(probs, top_k)

        top_tokens = []
        for prob, idx in zip(top_probs, top_indices):
            token = self.tracer.model.to_string(idx.item())
            top_tokens.append((token, prob.item()))

        return top_tokens

    def generate_completion(
        self,
        prompt: str,
        max_tokens: int = 10,
        stop_on: List[str] = None
    ) -> Tuple[str, List[TraceResult]]:
        """
        Generate multi-token completion with trace for each token.

        WARNING: This is slower than single-token prediction as it
        traces each token individually. Use for short completions only.

        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            stop_on: Optional list of stop tokens (e.g., ["\n", "."])

        Returns:
            Tuple of (full_text, list of TraceResults for each token)

        Example:
            >>> text, traces = analyzer.generate_completion(
            ...     "Q: Should we approve this loan? A:",
            ...     max_tokens=5
            ... )
            >>> print(text)
            "Q: Should we approve this loan? A: Yes, based on"
        """
        if stop_on is None:
            stop_on = []

        current_text = prompt
        traces = []

        for _ in range(max_tokens):
            # Trace next token
            result = self.tracer.trace(current_text)
            traces.append(result)

            # Add to text
            next_token = result.output_text
            current_text += next_token

            # Check stop condition
            if next_token in stop_on:
                break

        return current_text, traces


# Example usage
if __name__ == "__main__":
    from glassbox.tracer import ActivationTracer

    print("🧠 Decision Analyzer Example\n")
    print("=" * 60)

    # Initialize
    print("\n1. Loading model...")
    tracer = ActivationTracer(model_name="gpt2-medium")
    analyzer = DecisionAnalyzer(tracer)

    # Test yes/no decision
    print("\n2. Analyzing yes/no decision...")
    prompt = "Q: Should we approve this loan? A:"
    result, probs = analyzer.analyze_choices(prompt, ["yes", "no", "maybe"])

    print(f"   Prompt: {prompt}")
    print(f"   Next token: '{result.output_text}'")
    print(f"\n   Choice probabilities:")
    for choice, prob in sorted(probs.items(), key=lambda x: x[1], reverse=True):
        print(f"     {choice:10s}: {prob:.2%}")

    # Show top alternatives
    print("\n3. Top 10 most likely next tokens:")
    top_tokens = analyzer.get_top_tokens(result, top_k=10)
    for i, (token, prob) in enumerate(top_tokens, 1):
        print(f"     {i:2d}. '{token:15s}' - {prob:.2%}")

    # Generate multi-token completion
    print("\n4. Generating multi-token completion...")
    prompt = "The capital of France is"
    text, traces = analyzer.generate_completion(prompt, max_tokens=5)

    print(f"   Input:  {prompt}")
    print(f"   Output: {text}")
    print(f"   Generated {len(traces)} tokens")

    print("\n" + "=" * 60)
    print("✅ Decision Analyzer example complete!\n")
