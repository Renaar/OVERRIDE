FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATA_DIR=/app/data \
    DEFAULTS_DIR=/app/defaults \
    TZ=Europe/Zurich \
    PORT=8087

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && useradd --create-home --uid 1000 override

COPY app ./app
COPY web ./web
# Program JSON files: copied into the data volume on first start, never overwritten afterwards.
COPY data/*.json ./defaults/
RUN mkdir -p /app/data && chown -R override:override /app/data

USER override
EXPOSE 8087
HEALTHCHECK --interval=60s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request,os;urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"PORT\"]}/healthz',timeout=4)"
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --no-server-header"]
