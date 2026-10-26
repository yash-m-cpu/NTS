import asyncio
from sqlalchemy import text
from app.core.db import async_session_maker

async def main():
    async with async_session_maker() as session:
        await session.execute(text('DELETE FROM processing_job_events'))
        await session.execute(text('DELETE FROM processing_jobs'))
        await session.commit()

asyncio.run(main())
