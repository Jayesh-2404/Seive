FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SIEVE_CACHE_DIR=/data

COPY pyproject.toml README.md ./
COPY sieve ./sieve
RUN pip install --no-cache-dir .

RUN mkdir -p /data
EXPOSE 8000
CMD ["uvicorn", "sieve.http_server:app", "--host", "0.0.0.0", "--port", "8000"]
