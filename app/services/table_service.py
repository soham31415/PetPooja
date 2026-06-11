from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.models.restaurant import Restaurant, RestaurantTable
from app.models.session import DiningSession, SessionStatus
from app.services import session_service
import secrets
import uuid
from typing import List, Optional


async def create_table(db: AsyncSession, restaurant_id: int, label: str) -> RestaurantTable:
    table = RestaurantTable(
        restaurant_id=restaurant_id,
        label=label,
        qr_token=secrets.token_urlsafe(16),
    )
    db.add(table)
    await db.commit()
    await db.refresh(table)
    return table


async def list_tables(db: AsyncSession, restaurant_id: int) -> List[RestaurantTable]:
    result = await db.execute(
        select(RestaurantTable).where(RestaurantTable.restaurant_id == restaurant_id)
    )
    return result.scalars().all()


async def get_table_by_token(db: AsyncSession, qr_token: str) -> Optional[RestaurantTable]:
    result = await db.execute(
        select(RestaurantTable)
        .options(selectinload(RestaurantTable.restaurant))
        .where(RestaurantTable.qr_token == qr_token)
    )
    return result.scalars().first()


async def get_active_session_for_table(db: AsyncSession, table_id: int) -> Optional[DiningSession]:
    result = await db.execute(
        select(DiningSession).where(
            DiningSession.table_id == table_id,
            DiningSession.status == SessionStatus.ACTIVE,
        )
    )
    return result.scalars().first()


async def start_or_join_table_session(
    db: AsyncSession, qr_token: str, user_id: uuid.UUID
) -> DiningSession:
    """
    Scanning a table's QR code either joins the table's current active
    session, or starts a brand new one (with the scanning user as host).
    """
    table = await get_table_by_token(db, qr_token)
    if not table:
        raise ValueError("Table not found")

    active_session = await get_active_session_for_table(db, table.id)
    if active_session:
        return await session_service.join_session(db, active_session.id, user_id)

    return await session_service.create_session(
        db=db,
        host_id=user_id,
        restaurant_id=table.restaurant_id,
        table_id=table.id,
    )
