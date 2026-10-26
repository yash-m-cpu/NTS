import asyncio
from app.core.db import async_session_maker
from sqlalchemy import select
from app.models.jobs import ProcessingJob

async def main():
    async with async_session_maker() as db:
        jobs = await db.scalars(select(ProcessingJob).where(ProcessingJob.status == 'queued'))
        for j in jobs:
            j.status = 'failed'
            j.error_message = 'Reset to unblock queue'
            print(f'Failed {j.id}')
        await db.commit()

asyncio.run(main())
