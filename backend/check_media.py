import asyncio
import sys
from app.core.db import async_session_maker
from app.models.media import MediaAsset
from sqlalchemy import select

async def main():
    async with async_session_maker() as db:
        r = await db.execute(select(MediaAsset))
        assets = r.scalars().all()
        for a in assets:
            print(a.id, a.meeting_id)

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(main())
