import asyncio
import sys
from app.core.db import async_session_maker
from app.models.organizations import OrganizationMember, Organization
from app.models.users import User
from sqlalchemy import select

async def main():
    async with async_session_maker() as db:
        users = (await db.execute(select(User))).scalars().all()
        for u in users:
            print(f"User: {u.email} ID: {u.id}")
            
        orgs = (await db.execute(select(Organization))).scalars().all()
        for o in orgs:
            print(f"Org: {o.name} ID: {o.id}")
            
        members = (await db.execute(select(OrganizationMember))).scalars().all()
        for m in members:
            print(f"Member: User {m.user_id} in Org {m.organization_id}")

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(main())
