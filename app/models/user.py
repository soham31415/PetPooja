from sqlalchemy import String, Boolean, ForeignKey, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base
from typing import Optional, List
import uuid

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String, unique=True, index=True)
    hashed_password: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_guest: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Relationships
    taste_profile: Mapped[Optional["TasteProfile"]] = relationship(back_populates="user", uselist=False)
    participated_sessions: Mapped[List["SessionParticipant"]] = relationship(back_populates="user")
    orders: Mapped[List["OrderItem"]] = relationship(back_populates="user")

class TasteProfile(Base):
    __tablename__ = "taste_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), unique=True)
    
    # Store preferences as tags e.g. ["spicy", "vegan"]
    preferences: Mapped[list[str]] = mapped_column(JSON, default=list)
    # Scale of 1-10
    daringness: Mapped[int] = mapped_column(Integer, default=5)
    dietary_restrictions: Mapped[list[str]] = mapped_column(JSON, default=list)

    user: Mapped["User"] = relationship(back_populates="taste_profile")
