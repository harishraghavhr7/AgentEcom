"""
Standalone Asynchronous Indexing Worker Runner for AgentEcom.
Runs as a dedicated microservice container to process embedding generation,
BM25 catalog indexing, and real-time inventory updates without blocking the web API.
"""

import os
import sys
import asyncio
import signal
import logging

from agentecom.config import settings
from agentecom.db.database import init_db
from agentecom.db.seed import seed_database
from agentecom.search.worker import index_worker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [agentecom-worker] %(message)s"
)
logger = logging.getLogger("agentecom.worker.runner")

stop_event = asyncio.Event()

def handle_shutdown(sig, frame):
    logger.info(f"Received termination signal {sig}. Initiating graceful shutdown...")
    stop_event.set()

async def run_worker_service():
    logger.info("Starting AgentEcom Indexing Worker Service...")
    
    # 1. Initialize DB and Seed Catalog
    await init_db()
    await seed_database()

    # 2. Run initial full catalog re-indexing
    logger.info("Executing initial full catalog indexing (BM25 + Dense Vectors)...")
    await index_worker._process_reindex_all()
    logger.info("Initial catalog indexing completed successfully.")

    # 3. Start background job consumer
    await index_worker.start()
    logger.info("Worker consumer loop is active and listening for catalog update events.")

    # 4. Periodic health check & keep-alive loop
    poll_interval = int(os.getenv("WORKER_POLL_INTERVAL_SECONDS", "30"))
    while not stop_event.is_set():
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=poll_interval)
        except asyncio.TimeoutError:
            # Periodic heart beat
            logger.info(f"Worker heartbeat OK. Pending queue size: {index_worker.queue.qsize()}")

    # 5. Graceful shutdown
    logger.info("Stopping worker consumer...")
    await index_worker.stop()
    logger.info("Worker service shut down cleanly.")

def main():
    signal.signal(signal.SIGINT, handle_shutdown)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, handle_shutdown)

    asyncio.run(run_worker_service())

if __name__ == "__main__":
    main()
