import asyncio
import sys
import uuid
from app.core.db import async_session_maker
from app.services.job_service import enqueue_job

async def main():
    async with async_session_maker() as db:
        # Enqueue a dummy job
        job = await enqueue_job(
            db, 
            uuid.UUID('4402a01b-92c0-442a-8621-818993a16227'), # Existing org id from user trace
            uuid.UUID('bd9a8e1a-1715-4350-af9e-7f2976787942'), # Existing meeting id
            'cv_extraction', 
            None
        )
        print("Enqueued job", job.id)

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(main())
