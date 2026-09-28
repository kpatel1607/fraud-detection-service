FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# --------------------------------------------------
# Create non-root application user
# --------------------------------------------------

RUN useradd \
    --create-home \
    --uid 10001 \
    --shell /usr/sbin/nologin \
    appuser

# --------------------------------------------------
# Install dependencies
# --------------------------------------------------

COPY requirements-runtime.txt .

RUN pip install --no-cache-dir -r requirements-runtime.txt

# --------------------------------------------------
# Copy application and model
# --------------------------------------------------

COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser models/ ./models/

# --------------------------------------------------
# Runtime directories
# --------------------------------------------------

RUN mkdir -p data logs \
    && chown -R appuser:appuser /app

# --------------------------------------------------
# Run as non-root
# --------------------------------------------------

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"

CMD ["sh", "-c", "uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]