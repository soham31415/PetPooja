from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.session import DiningSession, SessionParticipant, SessionStatus
from app.models.user import User
import uuid
import uuid

async def create_session(db: AsyncSession, host_id: uuid.UUID, restaurant_id: int):
    # Check if host exists (basic check, could be in API layer)
    # Check if restaurant exists (basic check)

    session = DiningSession(
        host_id=host_id,
        restaurant_id=restaurant_id,
        status=SessionStatus.ACTIVE
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    
    # Add host as a participant
    participant = SessionParticipant(
        session_id=session.id,
        user_id=host_id,
        is_active=True
    )
    db.add(participant)
    await db.commit()
    
    return session

async def join_session(db: AsyncSession, session_id: uuid.UUID, user_id: uuid.UUID):
    # Verify session is active
    session = await db.get(DiningSession, session_id)
    if not session or session.status != SessionStatus.ACTIVE:
        raise ValueError("Session not found or not active")
        
    # Check if already joined
    result = await db.execute(
        select(SessionParticipant).where(
            SessionParticipant.session_id == session_id,
            SessionParticipant.user_id == user_id
        )
    )
    if result.scalars().first():
        return session # Already joined
        
    # Add participant
    participant = SessionParticipant(
        session_id=session_id,
        user_id=user_id,
        is_active=True
    )
    db.add(participant)
    await db.commit()
    
    return session
