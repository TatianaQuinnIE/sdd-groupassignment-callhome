# overlap-service
FROM python:3.12.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Non-root user
RUN groupadd --system app && useradd --system --gid app --no-create-home app

# Pinned dependencies first, for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Only the code the service needs (no COPY . .)
COPY app/ ./app/
COPY migrations/ ./migrations/

USER app
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
