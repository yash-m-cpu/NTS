import asyncio
import sys
import uuid
import re
from app.core.db import async_session_maker
from app.models.organizations import OrganizationMember, Organization
from app.models.users import User
from sqlalchemy import select

async def main():
    async with async_session_maker() as db:
        users = (await db.execute(select(User))).scalars().all()
        for u in users:
            # Check if user has an org
            members = (await db.execute(select(OrganizationMember).filter(OrganizationMember.user_id == u.id))).scalars().all()
            if not members:
                print(f"Creating org for {u.email}")
                slug_base = re.sub(r'[^a-z0-9]+', '-', u.full_name.lower())[:20]
                new_org = Organization(name=f"{u.full_name}'s Workspace", slug=f"{slug_base}-{str(uuid.uuid4())[:8]}")
                db.add(new_org)
                await db.flush()
                
                member = OrganizationMember(
                    organization_id=new_org.id,
                    user_id=u.id,
                    role="ADMIN"
                )
                db.add(member)
        await db.commit()
        print("Done fixing orphaned users.")

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(main())
