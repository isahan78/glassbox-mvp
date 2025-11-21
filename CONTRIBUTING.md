# Contributing to GlassBox

Thank you for your interest in contributing to GlassBox! This document provides guidelines and instructions for contributing.

## Code of Conduct

Be respectful, inclusive, and constructive. We're building interpretable AI together.

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [GitHub Issues](https://github.com/isahan78/glassbox-engine/issues)
2. If not, create a new issue with:
   - Clear, descriptive title
   - Steps to reproduce
   - Expected vs. actual behavior
   - Environment details (OS, Python version, GlassBox version)
   - Code snippets or error messages

### Suggesting Enhancements

1. Check existing issues and discussions
2. Create an issue with tag `enhancement`
3. Describe:
   - Use case / problem being solved
   - Proposed solution
   - Alternative approaches considered
   - Impact on existing functionality

### Pull Requests

1. **Fork the repository**
2. **Create a feature branch** from `main`
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Make your changes**
4. **Write or update tests**
5. **Run tests locally**
   ```bash
   ./run_tests.sh
   ```
6. **Update documentation**
7. **Commit with clear messages**
8. **Push and create PR**

## Development Setup

### Prerequisites

- Python 3.10 or higher
- Git
- 8GB+ RAM (16GB+ recommended for Llama models)

### Setup Steps

```bash
# 1. Clone your fork
git clone https://github.com/YOUR_USERNAME/glassbox-engine.git
cd glassbox-engine

# 2. Create virtual environment
python3.10 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install GlassBox in editable mode
pip install -e .

# 5. Install dev dependencies
pip install pytest black mypy flake8 pytest-cov

# 6. Run tests to verify setup
./run_tests.sh
```

## Code Style

### Python Style Guide

We follow [PEP 8](https://pep8.org/) with some modifications:

- **Line length**: 120 characters (not 79)
- **Quotes**: Double quotes preferred for strings
- **Imports**: Organized by standard lib → third party → local
- **Type hints**: Required for public functions
- **Docstrings**: Google style for all modules, classes, and functions

### Formatting

Before committing, format your code:

```bash
# Auto-format code
black glassbox/ api/ dashboard/ tests/

# Check types
mypy glassbox/ --ignore-missing-imports

# Lint
flake8 glassbox/ api/ dashboard/ tests/ --max-line-length=120 --ignore=E203,E501,W503
```

### Example

```python
from typing import Optional, List
import torch
from glassbox.tracer import ActivationTracer


def analyze_model_decision(
    prompt: str,
    choices: List[str],
    model_name: str = "gpt2-medium"
) -> dict:
    """
    Analyze model decision probabilities for given choices.

    Args:
        prompt: Input text to analyze
        choices: List of possible answers
        model_name: Model to use for analysis

    Returns:
        Dictionary with probabilities for each choice

    Example:
        >>> result = analyze_model_decision(
        ...     "Q: Is this spam? A:",
        ...     ["yes", "no"]
        ... )
        >>> print(result["probabilities"])
        {"yes": 0.75, "no": 0.25}
    """
    tracer = ActivationTracer(model_name=model_name)
    # ... implementation
```

## Testing

### Running Tests

```bash
# Run all tests
./run_tests.sh

# Run specific test file
pytest tests/test_tracer.py -v

# Run with coverage
pytest tests/ --cov=glassbox --cov-report=html
```

### Writing Tests

- Place tests in `tests/` directory
- Name test files `test_*.py`
- Use descriptive test names: `test_tracer_handles_empty_prompt`
- Test both success and failure cases
- Use fixtures for common setup

Example:

```python
import pytest
from glassbox.tracer import ActivationTracer


@pytest.fixture
def tracer():
    """Fixture providing a tracer instance."""
    return ActivationTracer(model_name="gpt2-small")


def test_tracer_initialization(tracer):
    """Test that tracer initializes correctly."""
    assert tracer.model_name == "gpt2-small"
    assert tracer.num_layers == 12


def test_trace_with_empty_prompt(tracer):
    """Test that empty prompts raise appropriate error."""
    with pytest.raises(ValueError, match="Prompt cannot be empty"):
        tracer.trace("")
```

## Documentation

### Code Documentation

- All public modules, classes, and functions must have docstrings
- Use Google-style docstrings
- Include examples where helpful

### User Documentation

When adding features, update:

- `readme.md` - Add to features list and examples
- Relevant guide in `docs/` or root directory
- `CHANGELOG.md` - Document changes
- API docs (auto-generated from docstrings)

### Example Documentation

Create examples in `examples/` directory:

```python
# examples/my_feature.py
"""
Example demonstrating the new feature.

Run with: python examples/my_feature.py
"""

from glassbox import ActivationTracer

def main():
    print("🧠 My Feature Example\\n")
    print("=" * 60)

    # Your example code here

    print("\\n✅ Example complete!")

if __name__ == "__main__":
    main()
```

## Git Workflow

### Branching Strategy

- `main` - Stable, production-ready code
- `develop` - Integration branch for next release
- `feature/*` - New features
- `fix/*` - Bug fixes
- `docs/*` - Documentation updates

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style (formatting, no logic change)
- `refactor`: Code restructuring (no behavior change)
- `test`: Adding or updating tests
- `chore`: Maintenance (dependencies, build, etc.)

Examples:

```
feat(tracer): add support for Mistral 7B model

Adds Mistral 7B to supported models list with proper configuration.
Tests included for model loading and inference.

Closes #123
```

```
fix(api): validate trace_id format to prevent path traversal

Added regex validation for trace_id parameter to ensure it matches
expected format (YYYYMMDD_HHMMSS_xxxxxx) and prevent directory
traversal attacks.
```

```
docs(readme): update cloud deployment examples

Added Lambda Labs deployment instructions and updated pricing.
```

### Pull Request Process

1. **Update Documentation**
   - Update README if adding features
   - Add/update examples
   - Update CHANGELOG.md

2. **Ensure Tests Pass**
   - All existing tests pass
   - New tests added for new features
   - Code coverage maintained or improved

3. **Code Review**
   - Address reviewer feedback
   - Keep discussions constructive
   - Be patient - reviews may take a few days

4. **Merge**
   - Squash commits for clean history (unless there's reason not to)
   - Update version numbers if needed

## Areas for Contribution

### Good First Issues

Look for issues tagged `good-first-issue`:
- Documentation improvements
- Example scripts
- Test coverage
- Bug fixes

### High Priority

- [ ] Integration tests for API endpoints
- [ ] Async support for tracer
- [ ] PostgreSQL backend for traces
- [ ] Additional model support (GPT-Neo, GPT-J)
- [ ] Performance optimizations

### Advanced Features

- [ ] Activation patching (v0.2 roadmap)
- [ ] Ablation studies
- [ ] Sparse Autoencoder integration (v0.3)
- [ ] Natural language explanations
- [ ] Multi-GPU support

## Project Structure

```
glassbox_mvp/
├── glassbox/           # Core library
│   ├── __init__.py
│   ├── tracer.py      # Activation capture
│   ├── analyzer.py    # Attention analysis
│   ├── serializer.py  # JSON persistence
│   ├── decision_analyzer.py  # Decision analysis
│   └── client.py      # Remote API client
├── api/                # FastAPI server
│   └── server.py
├── dashboard/          # Streamlit UI
│   └── app.py
├── tests/              # Unit tests
├── examples/           # Example scripts
├── cloud/              # Cloud deployment scripts
├── docs/               # Documentation (if applicable)
└── data/traces/        # Trace storage (gitignored)
```

## Getting Help

- **Questions**: Open a GitHub Discussion
- **Bugs**: Create an issue
- **Chat**: (Coming soon - Discord/Slack)
- **Email**: team@glassbox.ai

## Recognition

Contributors will be:
- Listed in CHANGELOG.md
- Mentioned in release notes
- Added to contributors section (if significant contribution)

Thank you for making GlassBox better! 🚀

---

*For security issues, see [SECURITY.md](SECURITY.md)*
