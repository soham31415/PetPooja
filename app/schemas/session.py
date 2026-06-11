from pydantic import BaseModel, UUID4
from typing import Optional, List
from datetime import datetime
from app.models.session import SessionStatus
from .user import UserRead

class SessionBase(BaseModel):
    restaurant_id: Optional[int] = None

class SessionCreate(SessionBase):
    pass

class SessionRead(SessionBase):
    id: UUID4
    host_id: UUID4
    table_id: Optional[int] = None
    status: SessionStatus
    created_at: datetime
    # We might want to return participants here
    
    class Config:
        from_attributes = True

class SessionJoin(BaseModel):
    session_id: UUID4
