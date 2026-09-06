FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY packages/flight_domain /app/packages/flight_domain
RUN pip install --no-cache-dir -e /app/packages/flight_domain

COPY apps/worker/requirements.txt /app/apps/worker/requirements.txt
RUN pip install --no-cache-dir -r /app/apps/worker/requirements.txt

COPY apps/worker /app/apps/worker

ENV PYTHONPATH=/app/packages/flight_domain:/app/apps/worker
EXPOSE 8001

CMD ["uvicorn", "apps.worker.main:app", "--host", "0.0.0.0", "--port", "8001"]
