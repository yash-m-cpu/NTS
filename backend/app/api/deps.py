from collections.abc import AsyncGenerator

from fastapi import Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.db import async_session_maker
from app.core.security import decode_access_token
from app.models.users import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session

async def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalars().first()
    
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
        
    org_id = payload.get("org_id")
    if org_id:
        request.state.org_id = org_id
        
        # Set RLS variable
        await db.execute(text("SELECT set_config('app.current_org_id', :org_id, true)"), {"org_id": org_id})

    return user

async def get_current_org(request: Request):
    if not hasattr(request.state, "org_id") or not request.state.org_id:
        raise HTTPException(status_code=403, detail="Organization not set in token")
    return request.state.org_id
