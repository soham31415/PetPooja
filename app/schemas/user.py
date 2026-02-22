from pydantic import BaseModel, UUID4
from typing import Optional, List
import uuid

class TasteProfileBase(BaseModel):
    preferences: List[str] = []
    daringness: int = 5
    dietary_restrictions: List[str] = []

class TasteProfileCreate(TasteProfileBase):
    pass

class TasteProfileRead(TasteProfileBase):
    id: int
    user_id: UUID4

    class Config:
        from_attributes = True

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str # For registered users

class GuestCreate(BaseModel):
    username: str
    taste_profile: Optional[TasteProfileCreate] = None

class UserRead(UserBase):
    id: UUID4
    is_guest: bool
    taste_profile: Optional[TasteProfileRead] = None

    class Config:
        from_attributes = True

class LoginRequest(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
