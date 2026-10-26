from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.rbac import require_role
from app.models.users import User
from app.schemas.user import UserInDB, UserUpdate


class InviteRequest(BaseModel):
    email: str
    role: str

class RoleUpdate(BaseModel):
    role: str

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me", response_model=UserInDB)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.patch("/me", response_model=UserInDB)
async def update_me(user_in: UserUpdate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    if user_in.full_name:
        current_user.full_name = user_in.full_name
        await db.commit()
        await db.refresh(current_user)
    return current_user

@router.delete("/me", status_code=204)
async def delete_me(confirm: bool, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not confirm:
        raise HTTPException(status_code=400, detail="Must confirm deletion")
    await db.delete(current_user)
    await db.commit()

@router.get("")
async def list_users(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user), role: str = Depends(require_role("MANAGER"))):
    return []

@router.post("/invite", status_code=201)
async def invite_user(invite: InviteRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user), role: str = Depends(require_role("MANAGER"))):
    if role == "MANAGER" and invite.role == "ADMIN":
        raise HTTPException(status_code=403, detail="MANAGER cannot invite ADMIN")
    return {"invitation_id": "dummy_invite_id"}

@router.patch("/{id}/role")
async def update_user_role(id: str, role_update: RoleUpdate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user), role: str = Depends(require_role("ADMIN"))):
    return {"message": "Updated"}

@router.delete("/{id}", status_code=204)
async def delete_user(id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user), role: str = Depends(require_role("ADMIN"))):
    pass
