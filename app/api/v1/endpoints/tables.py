from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.api import deps
from app.models.user import User
from app.schemas.session import SessionRead
from app.schemas.table import TableInfo
from app.services import table_service
from app.services.table_service import get_table_by_token, get_active_session_for_table

router = APIRouter()


@router.get("/{qr_token}", response_model=TableInfo)
async def get_table_info(qr_token: str, db: AsyncSession = Depends(deps.get_db)):
    """
    Resolve a scanned QR code to its table/restaurant, and report whether
    the table currently has an active dining session to join. Public.
    """
    table = await get_table_by_token(db, qr_token)
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")

    active_session = await get_active_session_for_table(db, table.id)
    return TableInfo(
        table_id=table.id,
        label=table.label,
        restaurant_id=table.restaurant_id,
        restaurant_name=table.restaurant.name,
        active_session_id=active_session.id if active_session else None,
    )


@router.post("/{qr_token}/session", response_model=SessionRead)
async def start_or_join_session_from_table(
    qr_token: str,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
):
    """
    Scan-to-dine: join the table's active session if there is one,
    otherwise start a brand new session at this table.
    """
    try:
        return await table_service.start_or_join_table_session(db, qr_token, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
