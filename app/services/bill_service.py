from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.models.order import Order, OrderItem
from app.models.session import DiningSession, SessionParticipant
from app.models.user import User
from app.models.restaurant import MenuItem
from app.schemas.bill import BillSummary, UserBillShare, BillItemDetail
from collections import defaultdict
import uuid
from typing import Dict


async def calculate_bill(db: AsyncSession, session_id: uuid.UUID) -> BillSummary:
    """
    Calculate the bill breakdown for a dining session.

    Rules:
    - Items with assigned_user_id → full cost goes to that user
    - Items with assigned_user_id = NULL → cost split equally among
      all active participants in the session
    """

    # 1. Fetch active participants
    part_result = await db.execute(
        select(User)
        .join(SessionParticipant)
        .where(
            SessionParticipant.session_id == session_id,
            SessionParticipant.is_active == True,
        )
    )
    participants = part_result.scalars().all()
    if not participants:
        return BillSummary(session_id=session_id)

    participant_map: Dict[uuid.UUID, User] = {u.id: u for u in participants}
    # Stable ordering so that remainder cents are distributed deterministically
    participant_ids = sorted(participant_map.keys(), key=str)
    num_participants = len(participant_ids)

    # 2. Fetch all orders + items for the session
    order_result = await db.execute(
        select(Order)
        .options(selectinload(Order.items).selectinload(OrderItem.menu_item))
        .where(Order.session_id == session_id)
    )
    orders = order_result.scalars().all()

    # 3. Build per-user breakdown
    user_shares: Dict[uuid.UUID, UserBillShare] = {}
    for user in participants:
        user_shares[user.id] = UserBillShare(
            user_id=user.id,
            username=user.username,
        )

    grand_total = 0.0

    for order in orders:
        for item in order.items:
            item_cost = item.menu_item.price * item.quantity
            grand_total += item_cost

            if item.assigned_user_id is not None:
                # Assigned to a specific user
                uid = item.assigned_user_id
                if uid not in user_shares:
                    # Edge case: assigned to someone not in session
                    # Fetch their info
                    user_obj = await db.get(User, uid)
                    user_shares[uid] = UserBillShare(
                        user_id=uid,
                        username=user_obj.username if user_obj else "Unknown",
                    )

                user_shares[uid].items.append(
                    BillItemDetail(
                        menu_item_name=item.menu_item.name,
                        quantity=item.quantity,
                        unit_price=item.menu_item.price,
                        share_amount=item_cost,
                        is_shared=False,
                    )
                )
                user_shares[uid].total += item_cost
            else:
                # Split equally among all active participants. Work in integer
                # cents and hand out the leftover pennies one-by-one so that
                # the shares always sum to exactly the item's cost (no drift
                # like $10 / 3 -> $3.33 x 3 = $9.99).
                item_cost_cents = round(item_cost * 100)
                base_share_cents, remainder_cents = divmod(item_cost_cents, num_participants)

                for idx, uid in enumerate(participant_ids):
                    share_cents = base_share_cents + (1 if idx < remainder_cents else 0)
                    share_amount = share_cents / 100

                    user_shares[uid].items.append(
                        BillItemDetail(
                            menu_item_name=item.menu_item.name,
                            quantity=item.quantity,
                            unit_price=item.menu_item.price,
                            share_amount=share_amount,
                            is_shared=True,
                        )
                    )
                    user_shares[uid].total += share_amount

    # Round totals
    for share in user_shares.values():
        share.total = round(share.total, 2)

    return BillSummary(
        session_id=session_id,
        grand_total=round(grand_total, 2),
        per_person=list(user_shares.values()),
    )
