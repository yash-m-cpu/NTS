from uuid import UUID

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str

class UserUpdate(BaseModel):
    full_name: str | None = None

class UserInDB(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str
    status: str

    model_config = {"from_attributes": True}
