import os
import sys
import logging
import httpx
from apscheduler.schedulers.blocking import BlockingScheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("apps.scheduler")

WORKER_URL = os.getenv("WORKER_URL", "http://worker:8001").rstrip("/")

def call_trigger(endpoint: str):
    url = f"{WORKER_URL}{endpoint}"
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url)
            logger.info(f"Trigger {endpoint} -> {resp.status_code}")
    except Exception as e:
        logger.error(f"Failed to call trigger {endpoint}: {e}")

def main():
    logger.info(f"Starting APScheduler targeting {WORKER_URL}...")
    scheduler = BlockingScheduler()

    # 05_langgraph_rag_pinecone.md §9 Option A schedules
    scheduler.add_job(lambda: call_trigger("/trigger/waitlist-promotion"), "interval", minutes=2, id="wl_promo")
    scheduler.add_job(lambda: call_trigger("/trigger/checkin-reminders"), "cron", hour=6, id="checkin_reminders")
    scheduler.add_job(lambda: call_trigger("/trigger/fraud-scan"), "cron", hour="*/4", id="fraud_scan")
    scheduler.add_job(lambda: call_trigger("/trigger/pinecone-ingest"), "cron", hour=3, id="pinecone_ingest")
    scheduler.add_job(lambda: call_trigger("/trigger/refund-escalation"), "cron", hour=9, id="refund_escalation")
    scheduler.add_job(lambda: call_trigger("/trigger/ops-report"), "cron", hour=23, id="ops_report")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Stopping scheduler.")

if __name__ == "__main__":
    main()
