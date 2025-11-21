# GlassBox

**X-ray vision for AI decisions.**

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-62%20passing-brightgreen.svg)](https://github.com/isahan78/glassbox-mvp/actions)

---

## The Problem

AI systems make critical decisions every day—loans, hiring, medical diagnoses. But when asked "why did you decide that?" they can't explain. **Regulators are cracking down. Enterprises need answers.**

The EU AI Act requires explainability. Financial services need audit trails. Healthcare demands accountability. Yet current tools offer nothing but black boxes.

## The Solution

**GlassBox opens the black box.**

We intercept AI decision-making in real-time and show you exactly:
- **Which words** influenced the decision
- **Which neural pathways** activated
- **How confident** the model really is
- **What would change** the outcome

No more guessing. No more hand-waving. Real, actionable explanations.

---

## See It In Action

```python
from glassbox import ActivationTracer, DecisionAnalyzer

# Connect to any model
analyzer = DecisionAnalyzer(ActivationTracer("llama-2-7b"))

# Get explainable decisions
result = analyzer.analyze_choices(
    "Applicant: 750 credit score, $85k income. Approve loan?",
    choices=["yes", "no"]
)

print(result)
# → Decision: YES (73% confidence)
# → Key factors: "750 credit" (52%), "85k income" (31%)
# → Risk flag: None
```

**That's it.** Three lines of code. Full explainability.

---

## Why GlassBox Wins

| Feature | GlassBox | SHAP/LIME | Custom Build |
|---------|----------|-----------|--------------|
| Real-time inference | ✅ | ❌ | 6+ months |
| Multi-model support | ✅ GPT, Llama, Mistral | Limited | Varies |
| Interactive dashboard | ✅ | ❌ | Custom |
| Compliance-ready output | ✅ JSON audit trails | ❌ | Custom |
| Setup time | **5 minutes** | Hours | Months |

---

## Key Capabilities

### 1. Decision Explainability
See exactly why the model said yes or no. Token-level influence scores, confidence intervals, and alternative outcomes.

### 2. Interactive Visualizations
3D activation space projections. Circuit graphs. Causal flow heatmaps. All interactive, all exportable.

### 3. Compliance-Ready
JSON audit trails with timestamps, model versions, and reproducible results. Ready for EU AI Act, SOC2, and HIPAA audits.

### 4. Production Infrastructure
API with authentication, rate limiting, health checks. Docker-ready. Cloud deployable. Enterprise-grade.

---

## Quick Start

```bash
# Install (2 minutes)
git clone https://github.com/isahan78/glassbox-mvp.git
cd glassbox-mvp
pip install -r requirements.txt && pip install -e .

# Launch dashboard
streamlit run dashboard/app.py
# → http://localhost:8503

# Or start API
uvicorn api.server:app --port 8000
# → http://localhost:8000/docs
```

---

## Target Markets

**Financial Services** — Loan decisions, fraud detection, credit scoring
**Healthcare** — Diagnostic AI, treatment recommendations
**HR Tech** — Resume screening, hiring decisions
**Legal** — Contract analysis, compliance checking
**Insurance** — Claims processing, risk assessment

**TAM: $12B** explainable AI market by 2028 (Gartner)

---

## Traction

- **Production-ready** with 62 automated tests
- **Multi-model support** — GPT-2, Llama 2, Mistral
- **4 visualization types** — circuits, heatmaps, 3D projections, attention maps
- **REST API** with authentication and rate limiting
- **Cloud deployment** scripts for AWS, GCP, Lambda Labs

---

## Tech Stack

- **Core**: Python, PyTorch, TransformerLens
- **Dashboard**: Streamlit, Plotly, NetworkX
- **API**: FastAPI, Pydantic
- **Infrastructure**: Docker, GitHub Actions CI/CD

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│  Dashboard / API                                │
│  (User-facing explainability interface)         │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│  GlassBox Core                                  │
│  ┌─────────────┐ ┌─────────────┐ ┌───────────┐  │
│  │   Tracer    │ │  Analyzer   │ │ Visualizer│  │
│  │  (capture)  │ │  (explain)  │ │  (show)   │  │
│  └─────────────┘ └─────────────┘ └───────────┘  │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│  Language Models (GPT-2, Llama 2, Mistral)      │
└─────────────────────────────────────────────────┘
```

---

## Roadmap

**Now (v0.1)** — Core explainability, dashboard, API ✅
**Q1 2025** — Enterprise SSO, PostgreSQL backend, multi-GPU
**Q2 2025** — Compliance templates (EU AI Act, SOC2)
**Q3 2025** — Real-time streaming, model comparison tools
**Q4 2025** — On-prem enterprise edition

---

## The Team

Building GlassBox to make AI accountable.

---

## Get Started

**Try it now:**
```bash
git clone https://github.com/isahan78/glassbox-mvp.git
cd glassbox-mvp && pip install -r requirements.txt && pip install -e .
streamlit run dashboard/app.py
```

**Documentation:** [Full docs](docs/) | [API reference](http://localhost:8000/docs)

**Questions?** Open an issue or reach out.

---

<div align="center">

**Stop guessing what AI thinks. Start knowing.**

MIT License • [GitHub](https://github.com/isahan78/glassbox-mvp)

</div>
