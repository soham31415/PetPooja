from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from app.models.session import DiningSession, SessionParticipant, SessionStatus
from app.models.user import User
from app.models.restaurant import Restaurant
import uuid

_VALID_SESSION_TRANSITIONS = {
    SessionStatus.ACTIVE: [SessionStatus.CLOSED, SessionStatus.CANCELLED],
    SessionStatus.CLOSED: [],
    SessionStatus.CANCELLED: [],
}


async def is_active_participant(db: AsyncSession, session_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    result = await db.execute(
        select(SessionParticipant).where(
            SessionParticipant.session_id == session_id,
            SessionParticipant.user_id == user_id,
            SessionParticipant.is_active == True,
        )
    )
    return result.scalars().first() is not None


async def create_session(db: AsyncSession, host_id: uuid.UUID, restaurant_id: int):
    if restaurant_id is not None:
        restaurant = await db.get(Restaurant, restaurant_id)
        if not restaurant:
            raise ValueError("Restaurant not found")

    session = DiningSession(
        host_id=host_id,
        restaurant_id=restaurant_id,
        status=SessionStatus.ACTIVE
    )
    db.add(session)
    await db.flush()

    # Add host as a participant
    participant = SessionParticipant(
        session_id=session.id,
        user_id=host_id,
        is_active=True
    )
    db.add(participant)
    await db.commit()
    await db.refresh(session)

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

    # Add participant. A concurrent join could race past the check above,
    # so guard against the resulting primary-key collision.
    participant = SessionParticipant(
        session_id=session_id,
        user_id=user_id,
        is_active=True
    )
    db.add(participant)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()

    return session


async def update_session_status(
    db: AsyncSession, session_id: uuid.UUID, new_status: SessionStatus, user_id: uuid.UUID
):
    session = await db.get(DiningSession, session_id)
    if not session:
        raise ValueError("Session not found")

    if session.host_id != user_id:
        raise PermissionError("Only the host can update the session status")

    if new_status not in _VALID_SESSION_TRANSITIONS.get(session.status, []):
        raise ValueError(
            f"Cannot transition from '{session.status.value}' to '{new_status.value}'"
        )

    session.status = new_status
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session
