# Security Policy

## Supported Versions

GlassBox is currently in MVP/Alpha status (v0.1.x). Security updates will be provided for the latest release only.

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |
| < 0.1   | :x:                |

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability in GlassBox, please report it responsibly.

### How to Report

**Please do NOT create a public GitHub issue for security vulnerabilities.**

Instead, email us at: **security@glassbox.ai** (or create a private security advisory on GitHub)

Include the following information:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### What to Expect

- **Acknowledgment**: Within 48 hours
- **Initial Assessment**: Within 7 days
- **Fix Timeline**: Depends on severity
  - Critical: Within 7 days
  - High: Within 14 days
  - Medium/Low: Next release cycle

## Security Best Practices

### API Authentication

GlassBox API supports optional authentication using API keys.

#### Development Mode (No Authentication)
By default, if `GLASSBOX_API_KEY` is not set, the API runs in development mode with no authentication required.

```bash
# Development mode - no auth required
uvicorn api.server:app --reload
```

#### Production Mode (Authentication Enabled)
Always set an API key in production:

```bash
# Generate a secure API key
openssl rand -hex 32

# Set environment variable
export GLASSBOX_API_KEY=your_generated_api_key_here

# Start API with authentication enabled
uvicorn api.server:app --host 0.0.0.0 --port 8000
```

#### Using the API with Authentication

Include the API key in the `X-API-Key` header:

```bash
curl -X POST http://localhost:8000/trace \
  -H "X-API-Key: your_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Test prompt"}'
```

```python
from glassbox import GlassBoxClient

# Connect to authenticated API
client = GlassBoxClient(
    "http://your-api-url:8000",
    api_key="your_api_key_here"
)

# Make requests (API key sent automatically)
probs = client.analyze_choices("Q: Approve? A:", ["yes", "no"])
```

### CORS Configuration

Configure allowed origins via environment variable:

```bash
# Development
export GLASSBOX_CORS_ORIGINS="http://localhost:3000,http://localhost:8501"

# Production
export GLASSBOX_CORS_ORIGINS="https://yourdomain.com,https://app.yourdomain.com"
```

**Never use wildcard (`*`) in production.**

### Input Validation

GlassBox implements several security measures:

1. **Path Traversal Prevention**: Trace IDs are validated with regex
2. **Input Length Limits**: Prompts limited to 2000 characters
3. **Type Validation**: Pydantic models enforce type safety
4. **Sequence Length Limits**: Max 512 tokens to prevent DoS

### Deployment Security

#### Docker

When deploying with Docker:

```bash
# Use secrets for API key (don't hardcode in Dockerfile)
docker run -e GLASSBOX_API_KEY=$(cat /run/secrets/api_key) glassbox:latest
```

#### Cloud Deployment

- Use environment variables or secrets management (AWS Secrets Manager, GCP Secret Manager)
- Enable HTTPS/TLS
- Use firewalls to restrict access
- Enable monitoring and logging
- Rotate API keys regularly

### Dependency Security

We use automated tools to scan for vulnerabilities:

- GitHub Dependabot for dependency updates
- `safety check` in CI/CD pipeline
- Regular manual audits

To check dependencies yourself:

```bash
pip install safety
safety check -r requirements.txt
```

## Known Security Considerations

### Model Loading

- Models are loaded from HuggingFace Hub - ensure you trust the model source
- For sensitive data, use models hosted on your infrastructure
- Be aware of model size and RAM requirements to prevent OOM crashes

### Trace Storage

- Traces contain prompt text and model outputs
- Stored as JSON files in `data/traces/`
- **Do not store sensitive/PII data in traces without encryption**
- Consider using encrypted filesystems or database encryption

### API Rate Limiting

Currently, GlassBox does not implement rate limiting. For production:

- Use a reverse proxy (nginx, Caddy) with rate limiting
- Implement application-level rate limiting (see roadmap v0.4)
- Monitor API usage

## Security Roadmap

### v0.2
- Structured logging for audit trails
- Request correlation IDs

### v0.3
- Enhanced input validation
- Request/response sanitization

### v0.4
- API rate limiting
- Advanced authentication (JWT, OAuth)
- Encrypted trace storage
- RBAC (role-based access control)

### v0.5
- SOC 2 compliance documentation
- Penetration testing results
- Security audit reports

## Acknowledgments

We appreciate security researchers and contributors who help keep GlassBox secure.

Reporters who responsibly disclose vulnerabilities will be acknowledged in:
- CHANGELOG.md
- GitHub Security Advisories
- This document (with permission)

## Contact

- Security Issues: security@glassbox.ai
- General Questions: team@glassbox.ai
- GitHub Issues: https://github.com/isahan78/glassbox-engine/issues (non-security only)

---

*Last updated: November 20, 2025*
