from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from typing import Any, List
from app.api import deps
from app.models.session import DiningSession, SessionParticipant, SessionStatus
from app.models.user import User
from app.schemas.session import SessionCreate, SessionRead, SessionJoin
from app.schemas.user import UserRead
from app.schemas.restaurant import MenuItemRead
from app.services import session_service
from app.services import recommendation_service
from app.services import bill_service
from app.schemas.bill import BillSummary
import uuid

router = APIRouter()


class SessionStatusUpdate(BaseModel):
    status: SessionStatus


@router.post("/", response_model=SessionRead)
async def create_new_session(
    session_in: SessionCreate,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
):
    """
    Host creates a new dining session. Requires authentication.
    """
    try:
        session = await session_service.create_session(
            db=db,
            host_id=current_user.id,
            restaurant_id=session_in.restaurant_id
        )
        return session
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{session_id}/status", response_model=SessionRead)
async def update_session_status(
    session_id: uuid.UUID,
    status_in: SessionStatusUpdate,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
):
    """
    Close or cancel a session. Only the host may change its status.
    Valid transitions: active → closed, active → cancelled.
    """
    try:
        return await session_service.update_session_status(
            db=db,
            session_id=session_id,
            new_status=status_in.status,
            user_id=current_user.id,
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{session_id}/join", response_model=SessionRead)
async def join_existing_session(
    session_id: uuid.UUID,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
):
    """
    Join an existing session. Requires authentication.
    """
    try:
        session = await session_service.join_session(
            db=db,
            session_id=session_id,
            user_id=current_user.id,
        )
        return session
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{session_id}", response_model=SessionRead)
async def get_session_details(
    session_id: uuid.UUID, 
    db: AsyncSession = Depends(deps.get_db)
):
    """
    Get session details (public, no auth required).
    """
    result = await db.execute(
        select(DiningSession).where(DiningSession.id == session_id)
    )
    session = result.scalars().first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@router.get("/{session_id}/participants", response_model=List[UserRead])
async def get_session_participants(
    session_id: uuid.UUID, 
    db: AsyncSession = Depends(deps.get_db)
):
    """
    Get all participants in the session (public).
    """
    result = await db.execute(
        select(User)
        .options(selectinload(User.taste_profile))
        .join(SessionParticipant)
        .where(SessionParticipant.session_id == session_id)
    )
    return result.scalars().all()

@router.get("/{session_id}/recommendations", response_model=List[MenuItemRead])
async def get_session_recommendations(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(deps.get_db),
):
    """
    Get food recommendations for a session based on all participants' taste profiles.
    Returns menu items scored and sorted by relevance to the group.
    """
    session = await db.execute(
        select(DiningSession).where(DiningSession.id == session_id)
    )
    if not session.scalars().first():
        raise HTTPException(status_code=404, detail="Session not found")

    recommended_items = await recommendation_service.generate_recommendations(
        db=db, session_id=session_id
    )
    return recommended_items

@router.get("/{session_id}/bill", response_model=BillSummary)
async def get_session_bill(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(deps.get_db),
):
    """
    Get the bill breakdown for a dining session.
    Shows per-person totals with item-level detail.
    Assigned items go to their user; unassigned items are split equally.
    """
    result = await db.execute(
        select(DiningSession).where(DiningSession.id == session_id)
    )
    if not result.scalars().first():
        raise HTTPException(status_code=404, detail="Session not found")

    return await bill_service.calculate_bill(db=db, session_id=session_id)
