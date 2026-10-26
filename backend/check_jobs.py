import asyncio
import sys
from app.core.db import async_session_maker
from app.models.jobs import ProcessingJob
from sqlalchemy import select

async def main():
    async with async_session_maker() as db:
        r = await db.execute(select(ProcessingJob))
        jobs = r.scalars().all()
        for j in jobs:
            print(f"Job {j.id} status: {j.status} error: {j.error_message}")

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(main())
