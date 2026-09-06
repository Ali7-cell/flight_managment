FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
COPY backend/packages/flight_domain ./backend/packages/flight_domain
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app:/app/backend:/app/backend/packages/flight_domain
ENV PORT=8000
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
