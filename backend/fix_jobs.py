"""
Reset all queued/running jobs to 'failed' so the UI can retry cleanly.
Run once after restarting the worker.
"""
import asyncio
import sys
from app.core.db import async_session_maker
from app.models.jobs import ProcessingJob, ProcessingJobEvent
from sqlalchemy import select

async def main():
    async with async_session_maker() as db:
        r = await db.execute(select(ProcessingJob))
        jobs = r.scalars().all()
        count = 0
        for j in jobs:
            if j.status in ("queued", "running"):
                j.status = "failed"
                j.error_message = "Reset: worker was restarted or crashed before completing."
                event = ProcessingJobEvent(
                    processing_job_id=j.id,
                    event_type="failed",
                    payload={"error_message": j.error_message},
                )
                db.add(event)
                count += 1
        await db.commit()
        print(f"Reset {count} stuck job(s) to 'failed'.")

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(main())
