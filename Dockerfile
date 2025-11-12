# GlassBox - Docker Image for Cloud Deployment
FROM nvidia/cuda:12.1.0-base-ubuntu22.04

LABEL maintainer="GlassBox AI <hello@glassbox-ai.com>"
LABEL description="GlassBox - Interpretable AI Runtime for LLMs"

WORKDIR /app

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install Python and system dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip3 install --no-cache-dir --upgrade pip

# Copy requirements first (for better caching)
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Install GlassBox package
RUN pip3 install -e .

# Create directories for data
RUN mkdir -p data/traces data/models

# Set environment variables
ENV GLASSBOX_MODEL=gpt2-medium
ENV GLASSBOX_HOST=0.0.0.0
ENV GLASSBOX_PORT=8000
ENV HF_HOME=/app/data/models
ENV TRANSFORMERS_CACHE=/app/data/models/transformers

# Expose ports
EXPOSE 8000 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Default command (can be overridden)
CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8000"]
