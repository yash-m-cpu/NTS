from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.users import User
from app.schemas.auth import (
    LoginResponse,
    RefreshResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)
from app.services import auth_service
from app.tasks.email import send_password_reset_email, send_verification_email

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", status_code=201)
async def register(user_in: UserRegister, db: AsyncSession = Depends(get_db)):
    user = await auth_service.create_user(db, user_in)
    verification_token = "dummy_token"
    await send_verification_email(user.email, verification_token)
    return {"user_id": user.id, "status": user.status}

@router.post("/verify-email")
async def verify_email(token: str, db: AsyncSession = Depends(get_db)):
    if token != "dummy_token":
        raise HTTPException(status_code=400, detail="Invalid token")
    return {"verified": True}

@router.post("/login", response_model=LoginResponse)
async def login(response: Response, login_data: UserLogin, db: AsyncSession = Depends(get_db)):
    user = await auth_service.authenticate_user(db, login_data)
    
    orgs = await auth_service.get_user_organizations(db, user.id)
    org_id = orgs[0]["id"] if orgs else None
    role = orgs[0]["role"] if orgs else None
    
    access_token, refresh_token, expires_in = await auth_service.create_tokens(db, user, org_id, role)
    
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=30*24*60*60
    )
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
        user=UserResponse(id=user.id, email=user.email, full_name=user.full_name, organizations=orgs),
        organizations=orgs
    )

@router.post("/refresh", response_model=RefreshResponse)
async def refresh(response: Response, refresh_token: str = Cookie(None), db: AsyncSession = Depends(get_db)):
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Missing refresh token")
        
    access_token, new_refresh_token, expires_in = await auth_service.refresh_tokens(db, refresh_token)
    
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=30*24*60*60
    )
    
    return RefreshResponse(
        access_token=access_token,
        expires_in=expires_in
    )

@router.post("/logout", status_code=204)
async def logout(response: Response, refresh_token: str = Cookie(None), db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    if refresh_token:
        await auth_service.logout(db, refresh_token)
        response.delete_cookie("refresh_token")

@router.post("/logout-all", status_code=204)
async def logout_all(response: Response, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    await auth_service.logout_all(db, current_user.id)
    response.delete_cookie("refresh_token")

@router.post("/password/forgot", status_code=202)
async def password_forgot(email: str):
    await send_password_reset_email(email, "reset_token")
    return {"message": "Accepted"}

@router.post("/password/reset")
async def password_reset(token: str, new_password: str, db: AsyncSession = Depends(get_db)):
    if token != "reset_token":
        raise HTTPException(status_code=400, detail="Invalid token")
    return {"message": "Password reset"}
