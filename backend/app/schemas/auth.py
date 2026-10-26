from uuid import UUID

from pydantic import BaseModel, EmailStr


class Token(BaseModel):
    access_token: str
    refresh_token: str | None = None
    expires_in: int

class TokenPayload(BaseModel):
    sub: str | None = None
    org_id: str | None = None
    role: str | None = None

class OrganizationSchema(BaseModel):
    id: UUID
    name: str
    role: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str

class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str
    organizations: list[OrganizationSchema]

class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    user: UserResponse
    organizations: list[OrganizationSchema]

class RefreshResponse(BaseModel):
    access_token: str
    expires_in: int
