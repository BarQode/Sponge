# Sponge - AI Root Cause Analysis Tool
# Docker container for running the RCA tool

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ src/
COPY main.py .
COPY LICENSE .
COPY README.md .

# Create necessary directories
RUN mkdir -p /app/data /app/logs /app/models

# Set permissions
RUN chmod +x main.py

# Create a non-root user
RUN useradd -m -u 1000 sponge && \
    chown -R sponge:sponge /app

USER sponge

# Default command
CMD ["python", "main.py"]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Labels
LABEL maintainer="Sponge Development Team" \
      version="1.0.0" \
      description="AI Root Cause Analysis Tool for log analysis"
