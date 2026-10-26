import sys
from pathlib import Path

# Add backend directory to sys.path so app module can be found
sys.path.insert(0, str(Path(__file__).parent.parent))

from arq.connections import RedisSettings

from app.core.config import settings
from app.workers.base_worker import process_job


class WorkerSettings:
    functions = [process_job]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    job_timeout = 3600

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    import asyncio
    import sys
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    from arq.worker import run_worker
    run_worker(WorkerSettings)
