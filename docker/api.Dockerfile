# Stage 1: Build compile dependencies
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Instantiate virtual environment for dependency isolation
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# Stage 2: Clean runtime image
FROM python:3.11-slim AS runtime

WORKDIR /app

# Eager copy virtualenv from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy source and configurations
COPY src/ /app/src/

EXPOSE 8000
ENV PYTHONPATH=/app

# Setup non-root execution permissions for container hardening
RUN useradd -u 8888 appuser && chown -R appuser:appuser /app /opt/venv
USER appuser

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
