# Multi-stage build for FraudGuard Model Serving
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    cmake \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt


# Final stage
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:/opt/homebrew/opt/postgresql@14/bin:/Users/virgileader/.rbenv/shims:/Users/virgileader/.rbenv/bin:/opt/homebrew/opt/ruby@3.2/bin:/Users/virgileader/.yarn/bin:/Users/virgileader/.config/yarn/global/node_modules/.bin:/Users/virgileader/.nvm/versions/node/v22.17.1/bin:/Users/virgileader/.rbenv/shims:/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/System/Cryptexes/App/usr/bin:/usr/bin:/bin:/usr/sbin:/sbin:/var/run/com.apple.security.cryptexd/codex.system/bootstrap/usr/local/bin:/var/run/com.apple.security.cryptexd/codex.system/bootstrap/usr/bin:/var/run/com.apple.security.cryptexd/codex.system/bootstrap/usr/appleinternal/bin:/opt/pmk/env/global/bin:/opt/homebrew/opt/postgresql@14/bin:/Users/virgileader/.rbenv/shims:/Users/virgileader/.rbenv/bin:/opt/homebrew/opt/ruby@3.2/bin:/Users/virgileader/.yarn/bin:/Users/virgileader/.config/yarn/global/node_modules/.bin:/Users/virgileader/Library/pnpm:/Users/virgileader/.nvm/versions/node/v22.17.1/bin:/opt/miniconda3/bin:/opt/miniconda3/condabin:/Users/virgileader/.cargo/bin:/Users/virgileader/Library/Python/3.9/bin:/Users/virgileader/Library/Python/3.9/bin

# Copy application code
COPY app/ /app/app/

# Create models directory
RUN mkdir -p /models

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV MODEL_SERVING_MODEL_PATH=/models/gbdt_v1.bin
ENV MODEL_SERVING_HOST=0.0.0.0
ENV MODEL_SERVING_PORT=8000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
