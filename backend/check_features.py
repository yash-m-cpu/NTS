import asyncio
import sys
from app.core.db import async_session_maker
from app.models.features import FeatureExtraction
from sqlalchemy import select

async def main():
    async with async_session_maker() as db:
        r = await db.execute(select(FeatureExtraction))
        features = r.scalars().all()
        print(f"Total features in DB: {len(features)}")

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(main())
