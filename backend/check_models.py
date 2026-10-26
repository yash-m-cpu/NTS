import asyncio
import sys
from app.core.db import async_session_maker
from app.models.models_registry import ModelVersion
from sqlalchemy import select

async def main():
    async with async_session_maker() as db:
        r = await db.execute(select(ModelVersion))
        models = r.scalars().all()
        for m in models:
            print(m.id)

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(main())
