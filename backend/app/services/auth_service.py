import secrets
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.core.security import (
    create_access_token,
    get_password_hash,
    hash_refresh_token,
    verify_password,
)
from app.models.auth import RefreshToken
from app.models.organizations import Organization, OrganizationMember
from app.models.users import User
from app.schemas.auth import UserLogin, UserRegister


async def create_user(db: AsyncSession, user_in: UserRegister) -> User:
    result = await db.execute(select(User).filter(User.email == user_in.email))
    user = result.scalars().first()
    if user:
        raise HTTPException(status_code=409, detail="Email exists")
    
    hashed_password = get_password_hash(user_in.password)
    new_user = User(
        email=user_in.email,
        password_hash=hashed_password,
        full_name=user_in.full_name,
        status="invited"
    )
    db.add(new_user)
    await db.flush()  # To get new_user.id
    
    # Create personal organization
    import re
    slug_base = re.sub(r'[^a-z0-9]+', '-', user_in.full_name.lower())[:20]
    import uuid
    new_org = Organization(name=f"{user_in.full_name}'s Workspace", slug=f"{slug_base}-{str(uuid.uuid4())[:8]}")
    db.add(new_org)
    await db.flush()
    
    # Add member
    member = OrganizationMember(
        organization_id=new_org.id,
        user_id=new_user.id,
        role="ADMIN"
    )
    db.add(member)
    
    await db.commit()
    await db.refresh(new_user)
    return new_user

async def authenticate_user(db: AsyncSession, login_data: UserLogin):
    result = await db.execute(select(User).filter(User.email == login_data.email))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not verify_password(login_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    return user

async def create_tokens(db: AsyncSession, user: User, org_id: str = None, role: str = None):
    access_token = create_access_token(subject=user.id, org_id=org_id, role=role)
    raw_refresh_token = secrets.token_urlsafe(32)
    hashed_refresh_token = hash_refresh_token(raw_refresh_token)
    
    refresh_expires = datetime.now(UTC) + timedelta(days=30)
    rt = RefreshToken(
        user_id=user.id,
        token=hashed_refresh_token,
        expires_at=refresh_expires
    )
    db.add(rt)
    await db.commit()
    
    return access_token, raw_refresh_token, settings.JWT_EXPIRATION_MINUTES * 60

async def refresh_tokens(db: AsyncSession, refresh_token: str):
    hashed_rt = hash_refresh_token(refresh_token)
    result = await db.execute(select(RefreshToken).filter(RefreshToken.token == hashed_rt))
    rt = result.scalars().first()
    
    if not rt or rt.expires_at < datetime.now(UTC):
        raise HTTPException(status_code=401, detail="token_expired")
        
    user_result = await db.execute(select(User).filter(User.id == rt.user_id))
    user = user_result.scalars().first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid user")

    await db.delete(rt)
    await db.commit()
    
    orgs = await get_user_organizations(db, user.id)
    org_id = orgs[0]["id"] if orgs else None
    role = orgs[0]["role"] if orgs else None
    
    return await create_tokens(db, user, org_id, role)

async def logout(db: AsyncSession, refresh_token: str):
    hashed_rt = hash_refresh_token(refresh_token)
    result = await db.execute(select(RefreshToken).filter(RefreshToken.token == hashed_rt))
    rt = result.scalars().first()
    if rt:
        await db.delete(rt)
        await db.commit()

async def logout_all(db: AsyncSession, user_id: str):
    result = await db.execute(select(RefreshToken).filter(RefreshToken.user_id == user_id))
    rts = result.scalars().all()
    for rt in rts:
        await db.delete(rt)
    await db.commit()

async def get_user_organizations(db: AsyncSession, user_id: str):
    result = await db.execute(select(OrganizationMember).filter(OrganizationMember.user_id == user_id))
    memberships = result.scalars().all()
    orgs = []
    for m in memberships:
        org_result = await db.execute(select(Organization).filter(Organization.id == m.organization_id))
        org = org_result.scalars().first()
        if org:
            orgs.append({"id": org.id, "name": org.name, "role": m.role})
    return orgs
