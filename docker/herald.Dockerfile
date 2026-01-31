FROM python:3.12-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl && rm -rf /var/lib/apt/lists/*

# Install Claude CLI (npm)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    npm install -g @anthropic-ai/claude-code

# Copy packages
COPY packages/common /app/packages/common
COPY packages/herald /app/packages/herald

# Install Python deps
RUN pip install --no-cache-dir aiogram python-dotenv httpx

# Set Python path
ENV PYTHONPATH=/app/packages/common:/app/packages/herald

CMD ["python", "-m", "herald.main"]
