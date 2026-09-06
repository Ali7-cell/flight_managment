FROM python:3.11-slim

WORKDIR /app

COPY apps/scheduler/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY apps/scheduler /app/apps/scheduler

ENV PYTHONPATH=/app
CMD ["python", "apps/scheduler/main.py"]
