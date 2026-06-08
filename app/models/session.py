from sqlalchemy import String, ForeignKey, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base
from typing import List, Optional
import uuid
from datetime import datetime
import enum

class SessionStatus(str, enum.Enum):
    ACTIVE = "active"
    CLOSED = "closed"
    CANCELLED = "cancelled"

class DiningSession(Base):
    __tablename__ = "dining_sessions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    host_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    restaurant_id: Mapped[Optional[int]] = mapped_column(ForeignKey("restaurants.id"), nullable=True)
    table_id: Mapped[Optional[int]] = mapped_column(ForeignKey("restaurant_tables.id"), nullable=True)
    status: Mapped[SessionStatus] = mapped_column(Enum(SessionStatus), default=SessionStatus.ACTIVE)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    participants: Mapped[List["SessionParticipant"]] = relationship(back_populates="session")
    orders: Mapped[List["Order"]] = relationship(back_populates="session")
    table: Mapped[Optional["RestaurantTable"]] = relationship()

class SessionParticipant(Base):
    __tablename__ = "session_participants"

    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("dining_sessions.id"), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_active: Mapped[bool] = mapped_column(default=True)

    session: Mapped["DiningSession"] = relationship(back_populates="participants")
    user: Mapped["User"] = relationship(back_populates="participated_sessions")
