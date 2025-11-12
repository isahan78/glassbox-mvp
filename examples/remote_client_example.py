"""
Example: Using GlassBox Remote Client

This example shows how to connect to a GlassBox instance running on a cloud server
and perform decision analysis remotely.
"""

from glassbox import GlassBoxClient
import sys


def main():
    """Example usage of GlassBox remote client."""

    # Configuration
    # Replace with your cloud instance IP (e.g., from cloud_connection.txt)
    REMOTE_URL = "http://your-instance-ip:8000"

    # If running locally for testing
    # REMOTE_URL = "http://localhost:8000"

    print("🌐 GlassBox Remote Client Example")
    print("=" * 50)
    print()

    # Connect to remote GlassBox instance
    print(f"Connecting to: {REMOTE_URL}")
    try:
        client = GlassBoxClient(REMOTE_URL)
        print("✅ Connected successfully!")
    except ConnectionError as e:
        print(f"❌ Connection failed: {e}")
        print()
        print("Make sure:")
        print("1. Your cloud instance is running")
        print("2. The API server is started: uvicorn api.server:app --host 0.0.0.0 --port 8000")
        print("3. Firewall allows port 8000")
        print("4. You're using the correct IP address")
        sys.exit(1)

    print()

    # Check server health
    print("Checking server status...")
    health = client.health_check()
    print(f"  Model: {health.get('model', 'unknown')}")
    print(f"  Status: {health.get('status', 'unknown')}")
    print()

    # Example 1: Simple trace
    print("Example 1: Tracing a Prompt")
    print("-" * 50)
    prompt = "Q: Should we approve this loan application? A:"
    print(f"Prompt: {prompt}")
    print()

    result = client.trace(prompt)
    print(f"Predicted token: '{result.output_text}'")
    print(f"Log probability: {result.output_logprob:.4f}")
    print(f"Trace ID: {result.trace_id}")
    print()

    # Example 2: Analyze decision choices
    print("Example 2: Analyzing Decision Choices")
    print("-" * 50)
    prompt = "Q: Is this transaction fraudulent? A:"
    choices = ["yes", "no"]
    print(f"Prompt: {prompt}")
    print(f"Choices: {choices}")
    print()

    probs = client.analyze_choices(prompt, choices)
    print("Probabilities:")
    for choice, prob in probs.items():
        print(f"  {choice}: {prob:.2%}")
    print()

    # Determine decision
    decision = max(probs, key=probs.get)
    confidence = probs[decision]
    print(f"Decision: {decision} (confidence: {confidence:.2%})")
    print()

    # Example 3: Get top tokens
    print("Example 3: Top Token Predictions")
    print("-" * 50)
    prompt = "The capital of France is"
    print(f"Prompt: {prompt}")
    print()

    top_tokens = client.get_top_tokens(prompt, top_k=5)
    print("Top 5 predictions:")
    for i, (token, prob) in enumerate(top_tokens, 1):
        print(f"  {i}. '{token}' - {prob:.2%}")
    print()

    # Example 4: Multiple decision analysis
    print("Example 4: Multiple Decision Scenarios")
    print("-" * 50)

    scenarios = [
        {
            "prompt": "Q: Should we approve this loan? Credit score: 750, Income: $80k. A:",
            "choices": ["approve", "deny"]
        },
        {
            "prompt": "Q: Should we approve this loan? Credit score: 580, Income: $30k. A:",
            "choices": ["approve", "deny"]
        },
        {
            "prompt": "Q: Is this email spam? Contains 'FREE MONEY'. A:",
            "choices": ["yes", "no"]
        },
    ]

    for i, scenario in enumerate(scenarios, 1):
        print(f"Scenario {i}:")
        print(f"  Prompt: {scenario['prompt']}")

        probs = client.analyze_choices(scenario['prompt'], scenario['choices'])
        decision = max(probs, key=probs.get)
        confidence = probs[decision]

        print(f"  Decision: {decision} ({confidence:.2%})")
        print()

    # Example 5: Attention analysis
    print("Example 5: Attention Analysis")
    print("-" * 50)
    prompt = "Q: Approve purchase? A:"
    print(f"Prompt: {prompt}")
    print()

    # First trace the prompt
    result = client.trace(prompt)
    trace_id = result.trace_id

    # Then analyze attention patterns
    print(f"Analyzing attention for trace: {trace_id}")
    analysis = client.analyze_attention(trace_id, top_n=5)

    print(f"Top 5 attention heads:")
    for i, head in enumerate(analysis['top_heads'], 1):
        print(f"  {i}. Layer {head['layer']}, Head {head['head']}")
        print(f"     Score: {head['score']:.4f}")
        print(f"     Pattern: {head['pattern']}")
    print()

    print("=" * 50)
    print("✅ All examples completed!")
    print()
    print("💡 Tips:")
    print("1. Replace REMOTE_URL with your cloud instance IP")
    print("2. Check cloud_connection.txt for your instance details")
    print("3. Use this client in your production code to offload heavy models to cloud")
    print()


def async_example():
    """
    Example of async client usage (for high-throughput applications).

    Requires: pip install httpx
    """
    import asyncio
    from glassbox import AsyncGlassBoxClient

    async def run():
        REMOTE_URL = "http://your-instance-ip:8000"

        async with AsyncGlassBoxClient(REMOTE_URL) as client:
            # Run multiple requests concurrently
            tasks = [
                client.trace("Q: Approve? A:"),
                client.trace("Q: Deny? A:"),
                client.analyze_choices("Q: Safe? A:", ["yes", "no"]),
            ]

            results = await asyncio.gather(*tasks)
            print(f"Completed {len(results)} requests concurrently")

    asyncio.run(run())


if __name__ == "__main__":
    # Run sync example
    main()

    # Uncomment to run async example
    # async_example()
