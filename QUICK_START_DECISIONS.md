# Quick Start: Getting Yes/No Decisions with GlassBox

## 🎯 Your Questions Answered

### 1. How to Get Yes/No Instead of Just One Token?

You have **3 options**:

---

## ✅ Option 1: Use DecisionAnalyzer (EASIEST)

```python
from glassbox import ActivationTracer, DecisionAnalyzer

# Initialize
tracer = ActivationTracer(model_name="gpt2-medium")
analyzer = DecisionAnalyzer(tracer)

# Analyze yes/no decision
prompt = "Q: Should we approve this loan? A:"
result, probs = analyzer.analyze_choices(prompt, ["yes", "no"])

print(f"Decision: {result.output_text}")
print(f"P(yes) = {probs['yes']:.1%}")
print(f"P(no) = {probs['no']:.1%}")
```

**Output:**
```
Decision:  Yes
P(yes) = 15.0%
P(no) = 13.3%
```

**Why this works:**
- The prompt format `Q: ... A:` makes the model predict yes/no as the next token
- You get probabilities for BOTH choices, even if one isn't chosen
- You can see which attention heads drove the decision

---

## ✅ Option 2: Check Top Tokens

```python
from glassbox import ActivationTracer, DecisionAnalyzer

tracer = ActivationTracer(model_name="gpt2-medium")
analyzer = DecisionAnalyzer(tracer)

prompt = "Q: Should we approve this loan? A:"
result = tracer.trace(prompt)

# Get top 10 most likely next tokens
top_tokens = analyzer.get_top_tokens(result, top_k=10)

print("Top 10 predictions:")
for token, prob in top_tokens:
    print(f"  '{token}': {prob:.1%}")
```

**Output:**
```
Top 10 predictions:
  ' Yes': 15.0%
  ' No': 13.3%
  ' We': 9.1%
  ' The': 6.2%
  ' I': 4.4%
  ...
```

---

## ✅ Option 3: Generate Multi-Token Completion (SLOW!)

```python
from glassbox import ActivationTracer, DecisionAnalyzer

tracer = ActivationTracer(model_name="gpt2-medium")
analyzer = DecisionAnalyzer(tracer)

prompt = "Q: Should we approve this loan? A:"

# Generate 10 tokens with full tracing
full_text, traces = analyzer.generate_completion(
    prompt,
    max_tokens=10,
    stop_on=["\n"]  # Stop at newline
)

print(full_text)
# Output: "Q: Should we approve this loan? A: Yes, but only if..."
```

**⚠️ Warning:** This is **MUCH slower** (10 tokens = 10x the time) because it traces each token individually!

**When to use:** Only when you need a full explanation AND want to trace each token.

---

## 🎨 Best Practices for Yes/No Decisions

### ✅ Good Prompts (Single Token Response)

```python
# Format 1: Q&A style (best)
"Q: Should we approve this loan? A:"

# Format 2: Direct question with colon
"Loan approval decision:"

# Format 3: Explicit instruction
"Answer yes or no: Should we approve?"

# Format 4: Fill in the blank
"The loan application is: ___"
```

### ❌ Bad Prompts (Multi-Token Response)

```python
# Will generate full sentence, not just yes/no
"Please explain whether we should approve this loan."

# Open-ended, no clear format
"What do you think about this loan?"

# No structure to guide the model
"Loan application details: ..."
```

---

## 📊 Analyzing the Decision

After getting yes/no, analyze WHY:

```python
from glassbox import ActivationTracer, DecisionAnalyzer, AttentionAnalyzer

tracer = ActivationTracer(model_name="gpt2-medium")
decision_analyzer = DecisionAnalyzer(tracer)
attention_analyzer = AttentionAnalyzer()

# Get decision
prompt = "Q: Credit score 750, income $80k, approve? A:"
result, probs = decision_analyzer.analyze_choices(prompt, ["yes", "no"])

print(f"Decision: {result.output_text}")
print(f"Confidence: {probs['yes']:.1%} yes, {probs['no']:.1%} no")

# Analyze which attention heads drove this
top_heads = attention_analyzer.rank_attention_heads(
    result.attention_cache,
    result.tokens
)

print("\nTop 3 attention heads that influenced this decision:")
for i, head in enumerate(top_heads[:3], 1):
    print(f"{i}. Layer {head.layer}, Head {head.head} (score: {head.score:.3f})")
    print(f"   Attended to:")
    for token, weight in head.top_attended_tokens[:2]:
        print(f"     → '{token}' ({weight:.3f})")

# Which input tokens mattered most?
token_influence = attention_analyzer.compute_token_influence(
    result.attention_cache,
    result.tokens
)

print("\nMost influential tokens:")
sorted_tokens = sorted(token_influence.items(), key=lambda x: x[1], reverse=True)
for token, score in sorted_tokens[:5]:
    print(f"  '{token}': {score:.3f}")
```

---

## 🔧 Real-World Examples

### Example 1: Loan Approval

```python
scenarios = [
    ("Q: Credit 750, income $80k, approve? A:", "Good credit, high income"),
    ("Q: Credit 450, income $30k, approve? A:", "Poor credit, low income"),
    ("Q: Credit 680, debt 40%, approve? A:", "Okay credit, high debt"),
]

for prompt, description in scenarios:
    result, probs = analyzer.analyze_choices(prompt, ["yes", "no"])
    print(f"{description}:")
    print(f"  Decision: {result.output_text}")
    print(f"  P(yes)={probs['yes']:.1%}, P(no)={probs['no']:.1%}\n")
```

### Example 2: Risk Assessment

```python
prompt = "Q: High risk transaction, approve? A:"
result, probs = analyzer.analyze_choices(prompt, ["yes", "no", "review"])

print(f"Risk decision: {result.output_text}")
print(f"Probabilities: yes={probs['yes']:.1%}, no={probs['no']:.1%}, review={probs['review']:.1%}")
```

### Example 3: Multiple Choice

```python
prompt = "Q: Best action for fraud case? A) Approve B) Deny C) Investigate\nA:"
result, probs = analyzer.analyze_choices(prompt, ["A", "B", "C"])

for choice, prob in sorted(probs.items(), key=lambda x: x[1], reverse=True):
    print(f"{choice}: {prob:.1%}")
```

---

## 🚀 Full Working Example

Here's a complete script you can run:

```python
#!/usr/bin/env python3
"""
Complete example: Loan approval decision with analysis
"""
from glassbox import ActivationTracer, DecisionAnalyzer, AttentionAnalyzer

# Initialize
print("Loading model...")
tracer = ActivationTracer(model_name="gpt2-medium")
decision_analyzer = DecisionAnalyzer(tracer)
attention_analyzer = AttentionAnalyzer()

# Decision scenario
prompt = "Q: Credit score 750, income $80k, approve loan? A:"
print(f"\nAnalyzing: {prompt}")

# Get yes/no probabilities
result, probs = decision_analyzer.analyze_choices(prompt, ["yes", "no"])

# Show decision
print(f"\n🎯 DECISION: {result.output_text}")
print(f"   P(yes) = {probs['yes']:.1%}")
print(f"   P(no)  = {probs['no']:.1%}")

# Show alternatives
top_tokens = decision_analyzer.get_top_tokens(result, top_k=5)
print(f"\n📊 Top 5 alternatives:")
for i, (token, prob) in enumerate(top_tokens, 1):
    print(f"   {i}. '{token}' ({prob:.1%})")

# Explain why
print(f"\n🔍 WHY this decision?")
print(f"   Top 3 most influential attention heads:")

top_heads = attention_analyzer.rank_attention_heads(
    result.attention_cache,
    result.tokens
)

for i, head in enumerate(top_heads[:3], 1):
    print(f"\n   {i}. Layer {head.layer}, Head {head.head} (contribution: {head.score:.3f})")
    print(f"      Focused on:")
    for token, weight in head.top_attended_tokens[:3]:
        print(f"        → '{token}' ({weight:.3f})")

# Most important input tokens
token_influence = attention_analyzer.compute_token_influence(
    result.attention_cache,
    result.tokens
)

print(f"\n📌 Most influential input tokens:")
sorted_tokens = sorted(token_influence.items(), key=lambda x: x[1], reverse=True)
for token, score in sorted_tokens[:5]:
    bar = "█" * int(score * 20)
    print(f"   '{token:15s}' {bar} {score:.3f}")

print(f"\n✅ Analysis complete!")
```

**Run it:**
```bash
cd examples
python decision_analysis.py
```

---

## 📖 Summary

### To Get Yes/No Answers:

1. **Use DecisionAnalyzer** - easiest way to get probabilities
2. **Format prompts properly** - use `Q: ... A:` format
3. **Check both probabilities** - not just the prediction
4. **Analyze attention** - understand WHY the model decided

### Remember:

- ✅ Single token prediction = fast analysis
- ✅ Can still see probabilities for ALL choices
- ✅ Full tracing shows WHY the decision was made
- ⚠️ Multi-token generation = much slower but gives full response

---

**See `MODEL_REQUIREMENTS.md` for info about which models to use!**
